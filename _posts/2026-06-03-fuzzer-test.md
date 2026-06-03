---
layout: post
title: "AFL++ 퍼저 실습기: WSL 환경 설치부터 첫 크래시(Crash) 탐지까지"
date: 2026-06-03 15:25:00 +0900
categories: [Cybersecurity, Fuzzing]
tags: [aflplusplus, fuzzing, wsl, digital-forensics, vulnerability]
toc: true
comments: true
---


보안 취약점 진단과 버그 발굴에서 필수 도구로 자리 잡은 커버리지 기반 퍼저, **AFL++(American Fuzzy Lop++)**를 WSL 환경에 직접 설치하고 실습해 보았습니다. 


단순히 성공한 과정만 나열하는 것이 아니라, 최신 버전의 AFL++를 다루며 겪었던 **컴파일러 최적화 문제, obsolete 명령어 에러 등 다양한 삽질 기록과 해결 방법**을 상세히 정리해 공유합니다.


---


## 1. WSL Ubuntu에 AFL++ 수동 빌드 및 설치


처음에는 `sudo apt install aflplusplus` 구조로 간단히 설치하려 했으나, Ubuntu 버전에 따라 `E: Unable to locate package aflplusplus` 에러가 발생할 수 있습니다. 또한, 퍼징의 핵심인 LLVM 모드를 온전하게 활용하기 위해 **GitHub 소스코드를 직접 빌드하는 방식**을 선택했습니다.


### 필수 의존성 패키지 설치

먼저 컴파일러와 LLVM, Clang 등 빌드에 필요한 도구들을 설치합니다.

```bash
sudo apt update
sudo apt install -y build-essential python3-dev automake cmake git flex bison libglib2.0-dev libpixman-1-dev python3-setuptools cargo libgtk-3-dev llvm-dev clang
```

![0](/assets/img/fuzzer_test/1.png)
![0](/assets/img/fuzzer_test/2.png)

### 소스코드 다운로드 및 빌드

최신 소스코드를 가져와 전체 기능(`distributable`) 버전으로 컴파일 후 시스템에 설치합니다.


```bash
git clone [https://github.com/AFLplusplus/AFLplusplus.git](https://github.com/AFLplusplus/AFLplusplus.git)
cd AFLplusplus
make distributable
sudo make install
```
![0](/assets/img/fuzzer_test/3.png)
![0](/assets/img/fuzzer_test/4.png)

설치가 완료된 후 터미널에 `afl-fuzz`를 입력했을 때 화려한 아스키 아트 로고가 출력된다면 성공입니다.

![0](/assets/img/fuzzer_test/5.png)

---


## 2. 퍼징 전 필수 환경 설정 (WSL 특성 반영)


WSL 환경에서 AFL++를 구동할 때 커널 설정 때문에 에러가 발생하며 멈추는 현상이 있습니다. 이를 방지하기 위해 아래 두 가지 설정을 반드시 선행해야 합니다.


```bash
# 1. 크래시 시그널 가로채기를 위한 코어 덤프 패턴 변경 (루트 권한 필요)
echo core | sudo tee /proc/sys/kernel/core_pattern

# 2. 윈도우 가상화 환경으로 인한 CPU 주파수 변동 경고 무시 (환경변수 등록)
echo 'export AFL_SKIP_CPUFREQ=1' >> ~/.bashrc
source ~/.bashrc
```
![0](/assets/img/fuzzer_test/6.png)

---


## 3. 실습용 타겟 코드 및 시드 준비


의도적으로 특정 입력값이 들어왔을 때 크래시를 유발하는 간단한 C 언어 코드(`test.c`)를 작성했습니다. 표준 입력(stdin)을 받아 첫 네 글자가 `F`, `U`, `Z`, `Z`일 때 프로세스가 터지는 구조입니다.


```bash
mkdir ~/afl_test && cd ~/afl_test
nano test.c
```
![0](/assets/img/fuzzer_test/7.png)

```c
/* test.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main() {
    char buf[20];
    memset(buf, 0, sizeof(buf));

    // 표준 입력으로 값을 읽음
    if (read(0, buf, sizeof(buf) - 1) < 0) {
        return 1;
    }

    // 조건 만족 시 확실하게 프로세스 강제 종료(Crash)
    if (buf[0] == 'F') {
        if (buf[1] == 'U') {
            if (buf[2] == 'Z') {
                if (buf[3] == 'Z') {
                    abort(); // 컴파일러 최적화를 방해하고 강제 종료 유도
                }
            }
        }
    }

    return 0;
}
```
![0](/assets/img/fuzzer_test/8.png)

퍼저가 무작위 대입을 시작할 기초 입력값(Seed) 폴더와 파일을 생성합니다.


```bash
mkdir in
echo "AAAA" > in/seed.txt
```

![0](/assets/img/fuzzer_test/9.png)

---


## 4. 트러블슈팅: 내가 겪은 두 가지 막혔던 부분


### ❌ 삽질 1: `corpus count : 1` 상태에서 무한 제자리걸음 (컴파일러 최적화)

초기에 일반적인 명령어로 빌드한 뒤 퍼징을 돌렸을 때, 100만 번이 넘는 대입(`total execs`)이 일어나도 대시보드의 `corpus count`가 `1`에 고정되어 있고 크래시를 찾지 못하는 현상이 발생했습니다.


* **원인:** 최신 LLVM 기반 컴파일러의 강력한 최적화 기능 때문이었습니다. 컴파일러가 소스코드를 분석할 때 `if` 문 내부의 에러 코드를 "실행될 리 없는 미정의 동작" 혹은 "무의미한 분기"로 판단하여 컴파일 과정에서 해당 코드 영역을 통째로 날려버린 것입니다. 눈이 먼 AFL++는 새로운 경로를 찾지 못하고 최초 시드 파일 하나로만 헛바퀴를 돌았습니다.
* **해결책:** 확실하게 버그를 발생시키는 `abort()` 함수를 사용하고, 컴파일할 때 최적화를 완전히 차단하는 **`-O0`** 옵션을 명시해야 합니다.


### ❌ 삽질 2: `[-] PROGRAM ABORT : afl-gcc/afl-clang are obsolete`

우회를 시도하는 과정에서 구버전 가이드에 나오는 `afl-gcc` 명령어를 사용했더니 퍼저가 실행을 거부했습니다.


* **원인:** AFL++ 4.x 최신 버전부터는 오래된 방식인 `afl-gcc`와 `afl-clang` 래퍼가 완전히 제거(Obsolete)되었습니다.
* **해결책:** 무조건 **`afl-clang-fast`** 또는 `afl-gcc-fast`를 사용해야 합니다.


---


## 5. 최종 컴파일 및 퍼징 구동


문제를 모두 해결한 최종 빌드 및 퍼징 명령어 세트입니다.


```bash
# 기존 꼬인 파일 및 출력 폴더 리셋
rm -f test_target
rm -rf out

# 최적화를 끄고(-O0) AFL++ 컴파일러로 빌드
afl-clang-fast -O0 test.c -o test_target
```

![0](/assets/img/fuzzer_test/10.png)

컴파일 시 화면에 `[+] Instrumented 7 locations`라는 문구가 출력되면 코드 내부에 7개의 추적 마커가 정상적으로 삽입된 것입니다. 이제 퍼저를 가동합니다.


```bash
afl-fuzz -i in -o out -- ./test_target
```


### 결과 대시보드 확인

AFL++의 시그니처 대시보드가 켜지고, 정상적으로 마커가 동작하자 **시작한 지 단 수초 만에** 놀라운 변화가 일어났습니다.


* `corpus count`가 `1`에서 `4`로 실시간 상승 (퍼저가 `F` -> `FU` -> `FUZ` 단계를 밟아가며 경로를 스스로 학습함)
* `saved crashes : 1` 획득! (빨간색 불이 들어오며 취약점 유발 입력값 획득 성공)

![0](/assets/img/fuzzer_test/11.png)

---


## 6. 크래시 결과 분석 및 PoC 재현


AFL++가 찾아낸 유니크 크래시 파일은 `out/default/crashes/` 폴더에 박제됩니다.


```bash
ls -l out/default/crashes/
```
![0](/assets/img/fuzzer_test/13.png)

```text
-rw------- 1 iljae iljae  8 Jun  3 13:40 id:000000,sig:06,src:000003,time:4544,execs:12886,op:havoc,rep:3
```


파일명의 `sig:06`은 리눅스의 `SIGABRT` 시그널을 의미하며, 우리가 설계한 `abort()` 영역에 도달했음을 의미합니다. 리눅스 파이프라인을 통해 해당 파일을 타겟에 주입하여 수동으로 버그가 재현되는지 검증합니다.


```bash
./test_target < out/default/crashes/id:000000*
```

![0](/assets/img/fuzzer_test/12.png)

**출력 결과:** `Aborted (core dumped)`



AFL++가 아무런 사전 정보 없이 무작위 대입과 커버리지 피드백만으로 `FUZZ`라는 문자열을 완벽하게 조합해 내어 프로그램을 터뜨리는 데 성공했습니다!


---
