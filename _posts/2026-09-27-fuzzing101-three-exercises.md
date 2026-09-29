---
title: "Fuzzing101 3문제 클리어: Xpdf, libexif, TCPdump"
date: 2026-09-27 11:00:00 +0900
categories: [개발, 보안]
tags: [fuzzing, aflplusplus, asan, gdb, xpdf, libexif, tcpdump, cve, mission23]
---

## 1. 시작하며

[Fuzzing101](https://github.com/antonio-morales/Fuzzing101)의 앞 세 문제를 WSL에서 직접 풀어보았다. 퍼징의 개념과 AFL++의 기본 사용법은 이전부터 알고 있었고, 개인적으로 작은 프로그램에 재미 삼아 퍼저를 돌려본 적도 있었다. 다만 환경 구축부터 타겟 분석, 크래시 분류와 수정 버전 검증까지 한 흐름으로 정리해 본 것은 이번이 처음이었다.

이번에는 파일 파서인 Xpdf, 라이브러리인 libexif, 네트워크 패킷 파서인 TCPdump를 각각 AFL++로 계측하고, 나온 크래시를 GDB와 AddressSanitizer(ASan)로 확인했다.

마침 실습 기간이 추석과 겹쳐 중간중간 흐름이 끊겼다. 그래도 단순히 AFL 화면에서 크래시 숫자만 확인하지 않고, 왜 죽었는지와 수정 버전에서는 어떻게 처리되는지까지 보는 것을 목표로 했다.

목표는 크래시 숫자를 만드는 데서 끝내지 않고 다음 흐름을 한 번씩 완주하는 것이었다.

```text
환경 구축 → 타겟·CVE 사전 조사 → 계측 확인 → 퍼징
→ 크래시 재현 → 원인 분석 → 수정 버전 재검증
```

| 문제 | 타겟 | 목표 취약점 | 결과 |
|---|---|---|---|
| Exercise 1 | Xpdf 3.02 | CVE-2019-13288 | 무한 재귀와 SIGSEGV 재현 |
| Exercise 2 | libexif 0.6.14 | CVE-2009-3895, CVE-2012-2836 | 두 경로 모두 ASan으로 확인 |
| Exercise 3 | TCPdump 취약 커밋 | CVE-2017-13028 | BOOTP heap OOB read 재현 |

환경은 Ubuntu 22.04.5 LTS(WSL2), AFL++ 5.03c, clang 14, GCC 11.4다. 원본 가이드는 Ubuntu 20.04와 예전 AFL++를 기준으로 하므로 그대로 복사하기보다 현재 환경에 맞게 빌드와 트리아지 바이너리를 분리했다.

## 2. 공통 환경과 시행착오

퍼징용 바이너리는 AFL 계측만 넣어 빠르게 만들고, 분석용 바이너리는 ASan과 디버그 심볼을 넣어 따로 만들었다.

```bash
# 퍼징용 예시
CC=$HOME/AFLplusplus/afl-clang-fast \
CXX=$HOME/AFLplusplus/afl-clang-fast++ \
CFLAGS="-O2 -g" CXXFLAGS="-O2 -g" ./configure

# 분석용 예시
CC=clang CFLAGS="-O1 -g -fsanitize=address -fno-omit-frame-pointer" \
LDFLAGS="-fsanitize=address" ./configure
```

처음에는 Xpdf에 ASan과 AFL 계측을 한꺼번에 적용했다. 그런데 테스트 입력을 받기도 전에 signal 11로 죽었고 커버리지 튜플도 0이었다.

![ASan과 AFL forkserver 조합이 시작 단계에서 충돌한 화면](/assets/img/fuzzing101-three-exercises/01-initial-instrumentation-crash.png)
_크래시가 잡혔다고 성공이 아니다. 입력 실행 전에 죽었고 커버리지도 0이므로 잘못된 환경이다._

두 빌드를 분리하자 `afl-showmap`이 정상 입력에서 1,269개 튜플을 잡았다.

![Xpdf AFL 계측 확인](/assets/img/fuzzing101-three-exercises/02-xpdf-instrumentation-success.png)
_`afl-showmap`의 튜플 수로 계측이 실제 동작하는지 퍼징 전에 확인했다._

WSL의 `/proc/sys/kernel/core_pattern`은 외부 크래시 수집기로 연결돼 있었다. 관리자 권한 없이 진행했기 때문에 다음 환경 변수를 사용했다.

```bash
export AFL_SKIP_CPUFREQ=1
export AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
```

장시간 실행은 터미널이 닫혀도 유지되도록 `tmux` 세션에서 진행했다. AFL을 재개할 때는 `-i -`를 썼으며, 기존 크래시는 `crashes.<날짜>/`로 보관된다는 점도 확인했다.

## 3. Exercise 1 — Xpdf 3.02

### 3.1 타겟과 전략

목표인 CVE-2019-13288은 조작된 PDF 객체 참조가 `Parser::getObj()` 계열의 무한 재귀를 만들고, 스택이 소진되면서 서비스 거부를 일으키는 취약점이다.

처음에는 PDF를 여러 개 넣었지만 파일이 클수록 실행 속도가 눈에 띄게 떨어졌다. 결국 678바이트짜리 `helloworld.pdf` 하나만 남기고 고정 시드 123으로 실행했다.

```bash
AFL_SKIP_CPUFREQ=1 $HOME/AFLplusplus/afl-fuzz \
  -s 123 -i corpus-min -o out-xpdf-run1 -- \
  ./install-afl/bin/pdftotext @@ /tmp/output.txt
```

약 1시간 동안 118만 회를 실행했고 고유 크래시 2개와 hang 12개를 얻었다.

![Xpdf AFL++ 퍼징 결과](/assets/img/fuzzing101-three-exercises/03-xpdf-afl-crashes.png)
_1.19M executions, saved crashes 2, stability 100%._

### 3.2 GDB로 크래시 분류

첫 크래시는 `EmbedStream::getChar()` 계열이었고, 두 번째 크래시에서 목표한 반복 호출이 나타났다.

```text
Parser::getObj
  → XRef::fetch
    → Object::dictLookup
      → Parser::makeStream
        → Parser::getObj
```

![Parser getObj와 makeStream이 반복되는 GDB backtrace](/assets/img/fuzzing101-three-exercises/04-xpdf-gdb-infinite-recursion.png)
_서로 참조하는 스트림의 길이를 해석하다 같은 호출 고리로 계속 들어간다._

PDF 스트림의 `/Length`가 직접 정수가 아니라 다른 객체 참조일 수 있다. 길이를 얻기 위해 `XRef::fetch()`가 다시 파서를 만들고, 새 객체가 또 스트림이며 이전 객체를 가리키면 종료 조건 없는 고리가 완성된다. 방문 객체나 재귀 깊이를 제한하지 않은 것이 원인이다.

### 3.3 수정 버전 확인

같은 PoC를 Xpdf 3.02와 4.02에 입력했다.

![Xpdf 취약 버전과 수정 버전 비교](/assets/img/fuzzing101-three-exercises/05-xpdf-fixed-version-comparison.png)
_3.02는 SIGSEGV와 종료 코드 139, 4.02는 문법 오류를 출력한 뒤 종료 코드 0._

취약 버전은 스택 소진으로 죽지만 수정 버전은 잘못된 객체 참조를 오류로 처리한다. 이로써 환경 구축, 퍼징, GDB 트리아지, 수정 확인까지 첫 문제를 마쳤다.

## 4. Exercise 2 — libexif 0.6.14

### 4.1 라이브러리 하네스 설계

라이브러리는 실행 파일이 아니므로 JPEG 파일을 받아 API를 호출하는 하네스가 필요하다. 처음 하네스는 파일 파싱과 엔트리 순회만 수행했다.

```c
data = exif_data_new_from_file(argv[1]);
if (!data) return 0;
exif_data_foreach_content(data, visit_content, NULL);
exif_data_unref(data);
```

EXIF 샘플 10개를 시드로 사용했고 `afl-clang-lto`로 정적 라이브러리와 하네스를 계측했다. `Canon_40D.jpg`에서 `afl-showmap`은 312개 튜플을 기록했다.

![libexif 첫 AFL 크래시](/assets/img/fuzzing101-three-exercises/06-libexif-afl-crash.png)
_초기 하네스에서도 2분 만에 저장 크래시가 나왔다._

![libexif 크래시 직접 재현](/assets/img/fuzzing101-three-exercises/07-libexif-crash-reproduction.png)
_AFL이 저장한 JPEG를 하네스에 다시 입력해 SIGSEGV를 확인했다._

### 4.2 CVE-2012-2836 — 잘못된 오프셋

크래시를 ASan 빌드에 입력하자 다음 경로가 나왔다.

```text
exif_get_sshort
→ exif_get_short
→ exif_data_load_data (exif-data.c:819)
→ exif_loader_get_data
→ exif_data_new_from_file
```

![CVE-2012-2836 ASan 보고서](/assets/img/fuzzing101-three-exercises/08-libexif-asan-cve-2012-2836.png)
_조작된 EXIF 오프셋이 `exif_data_load_data()`의 범위 검사를 무너뜨린다._

오프셋과 크기를 부호 없는 정수로 더한 뒤 경계를 검사하면, 덧셈 자체가 wrap-around되어 작은 값이 될 수 있다. 검사가 있어도 계산이 먼저 넘치면 검사가 무의미해진다. 공식 수정은 덧셈 전에 `offset > datasize`를 확인하거나 뺄셈 기반 검사로 바꾼다.

같은 캠페인에서 썸네일 로딩의 `memcpy()` 경로도 별도 크래시로 잡혔다.

![libexif AFL 고유 크래시 2개](/assets/img/fuzzing101-three-exercises/09-libexif-afl-two-crashes.png)

![exif_data_load_data_thumbnail ASan 보고서](/assets/img/fuzzing101-three-exercises/10-libexif-thumbnail-asan.png)
_크래시 숫자가 곧 버그 숫자는 아니므로 상위 프레임을 기준으로 분류했다._

### 4.3 CVE-2009-3895 — 하네스가 결정한 도달 범위

첫 하네스에는 목표 취약점의 함수가 호출되지 않았다. 태그 형식을 자동 교정하는 다음 한 줄을 추가했다.

```c
exif_data_fix(data);
```

이 함수는 `exif_content_fix()`와 `exif_entry_fix()` 경로를 연다. 기존 큐를 시드에 합쳐 6시간 실행한 결과 769만 회, 저장 크래시 16개를 얻었다.

![exif_data_fix 경로 퍼징 결과](/assets/img/fuzzing101-three-exercises/11-libexif-fix-path-16-crashes.png)
_하네스 한 줄이 탐색 가능한 코드 영역을 바꿨다._

16개를 ASan으로 일괄 분류하자 여러 입력이 다음 경로로 묶였다.

```text
exif_data_fix
→ exif_content_fix
→ exif_entry_fix
→ exif_get_srational
→ exif_get_slong
```

![CVE-2009-3895 ASan heap buffer overflow](/assets/img/fuzzing101-three-exercises/13-libexif-cve-2009-3895-asan.png)
_8바이트로 할당된 영역의 끝보다 3바이트 뒤를 읽었다._

태그의 `components` 값과 실제 데이터 버퍼 길이가 일치한다고 믿고 형식을 변환한 것이 원인이다. 반복문은 구성요소 수만큼 LONG 또는 RATIONAL을 읽지만, 읽을 바이트가 버퍼 안에 남았는지 확인하지 않았다. 이 heap buffer overflow가 CVE-2009-3895의 핵심이다.

### 4.4 libexif 0.6.21에서 재검증

동일 하네스를 공식 보안 수정 릴리스인 0.6.21과 ASan으로 다시 빌드했다. CVE-2009-3895 PoC, CVE-2012-2836 PoC, 썸네일 크래시 입력을 각각 넣었다.

![libexif 0.6.21 수정 검증](/assets/img/fuzzing101-three-exercises/14-libexif-fixed-0.6.21.png)
_세 입력 모두 종료 코드 0, ASan 오류 0건._

이 과정에서 하네스가 단순한 입력 전달 코드가 아니라는 점을 확실히 알게 되었다. `exif_data_fix()`를 호출하지 않았다면 퍼저를 아무리 오래 돌려도 CVE-2009-3895 경로에는 도달하지 못했을 것이다.

## 5. Exercise 3 — TCPdump와 CVE-2017-13028

### 5.1 버전과 빌드 확인

원본 가이드는 TCPdump 4.9.2를 적었지만 해당 태그에는 관련 수정이 포함돼 있다는 보고가 있다. 따라서 가이드가 공식 수정으로 제시한 커밋 `85078ee`의 부모인 `0d52da1`을 취약 대상으로 고정하고 libpcap 1.8.0과 함께 빌드했다.

퍼징용은 AFL-only, 트리아지용은 AFL LTO + ASan으로 분리했다.

```text
tcpdump commit: 0d52da1a967932f479912f8049b35c0112a7c708
libpcap version: 1.8.0
ASan build coverage: 891 tuples
AFL-only build coverage: 471 tuples
```

처음에는 저장소의 PCAP 379개를 전부 넣고 4시간 동안 약 800만 회를 실행했다. 그런데 크래시는 하나도 나오지 않았다. 무작정 더 기다리는 대신 공식 수정 diff와 PCAP 입력 구조부터 다시 살펴보았다.

### 5.2 왜 크래시가 안 나왔는가

취약 코드는 BOOTP vendor 영역의 첫 바이트만 검사한 뒤 magic cookie 4바이트를 비교했다.

```c
/* vulnerable */
ND_TCHECK(bp->bp_vend[0]);
if (memcmp(bp->bp_vend, vm_rfc1048, sizeof(vm_rfc1048)) == 0) {
    rfc1048_print(ndo, bp->bp_vend);
}

/* fixed */
ND_TCHECK_LEN(bp->bp_vend, 4);
```

PCAP 레코드의 캡처 길이만 줄여서는 ASan이 반응하지 않았다. libpcap은 글로벌 헤더의 `snaplen`만큼 heap 버퍼를 미리 할당하기 때문이다. 논리적인 패킷 끝을 넘더라도 아직 같은 heap 할당 안이면 ASan 관점에서는 유효한 주소다.

따라서 BOOTP vendor 첫 바이트까지만 남긴 279바이트 패킷을 만들고 글로벌 `snaplen`도 279로 맞췄다. 그러면 `memcmp()`가 실제 heap 끝에서 4바이트를 읽어 3바이트 범위를 넘는다.

### 5.3 표적 코퍼스로 전략 변경

직접 만든 크래시 입력을 시드로 넣은 것이 아니라, vendor cookie 4바이트가 온전히 들어 있는 282바이트 정상 PCAP을 시드로 사용했다. WSL에서 ASan forkserver가 불안정했기 때문에 `AFL_NO_FORKSRV=1`을 사용했다.

```bash
AFL_NO_FORKSRV=1 AFL_MAP_SIZE=200000 \
ASAN_OPTIONS=abort_on_error=1:detect_leaks=0:symbolize=0 \
$HOME/AFLplusplus/afl-fuzz -m none -t 2000 -s 123 \
  -i corpus-bootp -o out-tcpdump-bootp-asan -- \
  ./install-asan/sbin/tcpdump -vvvvXX -ee -nn -r @@
```

넓은 코퍼스에서 800만 번 동안 나오지 않던 목표 크래시가 표적 코퍼스에서는 2,973번째 실행의 `havoc` 단계에서 저장됐다.

![TCPdump 표적 AFL 퍼징의 fuzzer_stats와 크래시 파일](/assets/img/fuzzing101-three-exercises/15-tcpdump-afl-crashes.png)
_종료 후 보존된 `fuzzer_stats`와 크래시 파일을 다시 확인했다. 6,282회 실행 중 2개가 저장됐고, 목표 크래시는 2,973번째 실행에서 생성됐다._

### 5.4 ASan 트리아지와 원인

AFL이 만든 입력의 SHA-256은 다음과 같다.

```text
2333553e910252ee9578435ff03ef9e21580ce2212787a849257c49a4d1ca2bb
```

ASan으로 재실행한 결과는 명확했다.

```text
AddressSanitizer: heap-buffer-overflow
READ of size 4
memcmp
bootp_print, print-bootp.c:382
udp_print → ip_print_demux → ip_print → ether_print
```

![TCPdump CVE-2017-13028 ASan 보고서](/assets/img/fuzzing101-three-exercises/16-tcpdump-cve-2017-13028-asan.png)
_281바이트 heap 영역의 바로 다음 주소에서 4바이트를 읽었다._

처음에는 단순한 경계 검사 누락이라고 생각했지만, 정확히는 검사한 크기와 실제로 읽는 크기가 달랐다. 1바이트가 존재한다고 해서 그 위치부터 4바이트를 읽어도 되는 것은 아니었다.

### 5.5 공식 수정 확인

공식 수정은 검사 대상을 vendor 배열의 첫 요소에서 magic cookie 전체 4바이트로 넓힌다. 같은 PoC를 수정 커밋 이후 일반 Clang 빌드에 입력하면 크래시 없이 잘린 BOOTP 패킷으로 처리하고 정상 종료한다.

![TCPdump 취약 버전과 수정 버전 비교](/assets/img/fuzzing101-three-exercises/17-tcpdump-fixed-comparison.png)
_취약 버전은 heap-buffer-overflow, 수정 버전은 경계에서 파싱을 중단한다._

## 6. 세 문제 비교

| 항목 | Xpdf | libexif | TCPdump |
|---|---|---|---|
| 입력 | PDF | JPEG/EXIF | PCAP |
| 계측 | AFL-only | AFL LTO | AFL-only 및 ASan 분리 |
| 분석 | GDB 반복 backtrace | ASan 상위 프레임 분류 | ASan heap 경계와 patch diff |
| 핵심 원인 | 재귀 깊이·방문 제한 없음 | 정수 wrap-around, 길이 불일치 | 1바이트 검사 후 4바이트 읽기 |
| 전략 변경 | 작은 PDF 하나로 축소 | `exif_data_fix()` 호출 추가 | BOOTP 경계 전용 정상 시드 설계 |
| 수정 검증 | Xpdf 4.02 | libexif 0.6.21 | 공식 수정 커밋 이후 버전 |

공통점은 퍼징 시간이 답이 아니었다는 것이다.

- 계측이 잘못되면 커버리지 0인 상태로 오래 돌게 된다.
- 라이브러리는 하네스가 호출하지 않는 경로를 탐색할 수 없다.
- 입력 형식의 길이 필드가 실제 heap 할당 크기에 영향을 주지 않으면 ASan이 논리적 OOB를 잡지 못할 수 있다.
- `saved crashes`는 버그 수가 아니다. ASan 유형과 상위 호출 프레임으로 분류해야 한다.
- 취약 버전에서 죽는 것뿐 아니라 수정 버전에서 같은 입력이 안전하게 처리되는 것까지 확인해야 원인과 해결을 연결할 수 있다.

## 7. 마치며

처음에는 AFL 화면의 `saved crashes`가 1이 되면 문제가 끝나는 줄 알았다. 막상 해 보니 실제 작업은 그다음부터였다. 시작 단계에서 발생한 오류와 진짜 입력 크래시를 구분해야 했고, 여러 크래시를 원인별로 묶어야 했다. 크래시가 나오지 않을 때는 퍼저만 계속 돌리는 것이 아니라 하네스와 입력 구조를 다시 봐야 했다.

예전에는 퍼저를 가볍게 돌려보고 크래시가 잡히는 과정을 보는 것 자체가 재미있었다면, 이번에는 그 뒤의 분석 과정에 더 집중했다. 세 문제를 풀면서 환경 구축부터 크래시 분류와 수정 버전 확인까지 연결할 수 있었다. 가장 크게 느낀 점은 “더 오래 돌리기” 전에 “지금 만든 입력과 하네스로 목표 코드에 도달할 수 있는가”부터 확인해야 한다는 것이다.

## 8. 참고 자료

- [antonio-morales/Fuzzing101](https://github.com/antonio-morales/Fuzzing101)
- [AFL++ 공식 저장소](https://github.com/AFLplusplus/AFLplusplus)
- [libexif 공식 저장소](https://github.com/libexif/libexif)
- [TCPdump CVE-2017-13028 공식 수정 커밋](https://github.com/the-tcpdump-group/tcpdump/commit/85078eeaf4bf8fcdc14a4e79b516f92b6ab520fc)
- [CVE-2012-2836](https://www.cve.org/CVERecord?id=CVE-2012-2836)
- [karsel83 — Fuzzing101 풀이](https://karsel83.github.io/posts/fuzz2/)
- [mossvana — Fuzzing101 Exercise 1](https://mossvana.github.io/dev/fuzzing101-1/)
- [mossvana — Fuzzing101 Exercise 2](https://mossvana.github.io/dev/fuzzing101-2/)
- [mossvana — Fuzzing101 Exercise 4](https://mossvana.github.io/dev/fuzzing101-4/)
- [MONKEY PATCH — Fuzzing101 Write-up v2](https://wtcyj.github.io/posts/fuzzing101-writeup-v2/)
