---
title: "[WSL 보안 실습] OverTheWire Bandit Level 0 → 25"
date: 2026-04-17 12:50:00 +0900
categories: [보안/라이트업]
tags: [WSL, Bandit, 리눅스, CLI, 정보보안, 워크게임, Writeup]
---

## 0. 서론: 왜 Bandit인가?
정보보안의 기초는 서버 환경(Linux)에 익숙해지는 것입니다. 본 포스팅에서는 WSL2 환경을 구축하고, 대표적인 리눅스 워크게임인 Bandit을 통해 0부터 25단계까지의 모든 해킹/보안 과정을 상세히 기록합니다.

---

## 1. WSL2 환경 구축 (인증 사진 포함)

### **WSL2 설치 및 배포판 세팅**
![WSL 설치 화면 1](/assets/img/bandit/p.jpg)
* **명령어**: `wsl --install`

---

## 2. Bandit 단계별 상세 라이트업 (0 → 25)

### **Level 0: 접속**
![Bandit 0 결과](/assets/img/bandit/0.jpg)
* **문제 분석**: 
  이 레벨의 목표는 SSH를 사용하여 게임 서버에 로그인하는 것입니다. 
  - Host: `bandit.labs.overthewire.org`
  - Port: `2220`
  - Username: `bandit0`
  - Password: `bandit0`
* **풀이 과정**: 
  SSH를 통해 서버에 연결하고 제공된 비밀번호를 입력하여 접속을 시도합니다.
  ```bash
  ssh bandit0@bandit.labs.overthewire.org -p 2220

### **Level 0 → 1**
![Bandit 1 결과](/assets/img/bandit/1.jpg)
* **문제 분석**: 
  홈 디렉토리의 `readme` 파일에 저장된 패스워드를 획득하여 `bandit1` 계정으로 로그인해야 합니다.
  - 파일 위치: `~/readme`
  - 목표: 파일 내용을 읽어 다음 레벨(`bandit1`) 접속용 패스워드 추출

* **풀이 과정**: 
  `ls` 명령어로 파일 목록을 확인하고, `cat` 명령어를 통해 `readme` 파일의 내용을 출력하여 패스워드를 확인합니다.
  ```bash
  ls           # 현재 디렉토리 파일 목록 확인
  cat readme   # readme 파일 내용 출력 및 패스워드 확인 / 획득한 패스워드(ZjLjTmM6FvvyRnrb2rfNWOZOTa6ip5If)를 사용하여 다음 레벨로 접속합니다.

### **Level 1 → 2**
![Bandit 2 결과](/assets/img/bandit/2.jpg)
* **문제 분석**: 
  홈 디렉토리에 위치한 `-`라는 이름의 파일에서 다음 레벨의 패스워드를 획득해야 합니다.
  - 파일 위치: `~/-`
  - 목표: 대시(`-`)로 명명된 특수 파일의 내용을 읽어 `bandit2` 계정의 패스워드 확인

* **풀이 과정**: 
  리눅스 시스템에서 `-` 문자는 대개 명령어의 옵션이나 표준 입력을 의미합니다. 따라서 `cat -`를 입력하면 파일이 아닌 사용자의 입력을 기다리게 되므로, `./-`와 같이 상대 경로를 명시하여 파일로 인식하도록 해야 합니다.
  ```bash
  ls           # 현재 디렉토리 파일 목록 확인
  cat ./-      # 상대 경로를 명시하여 '-' 파일 내용 출력 / 획득한 패스워드(263JGJPfgU6LtdEvgfWU1XP5yac29mFx)를 사용하여 다음 레벨로 접속합니다.

### **Level 2 → 3**
![Bandit 3 결과](/assets/img/bandit/3.jpg)
* **문제 분석**: 
  홈 디렉토리에 위치한 공백과 특수 문자(`--`)가 포함된 파일에서 다음 레벨의 패스워드를 찾아야 합니다.
  - 파일 위치: `~/--spaces in this filename--`
  - 목표: 파일 이름에 공백이 있고 대시로 시작하는 특수 파일을 읽어 `bandit3` 계정의 패스워드 확인

* **풀이 과정**: 
  파일명에 공백이 있으면 쉘이 이를 별개의 인자로 인식하므로 따옴표(`" "`)로 묶어줘야 합니다. 또한, 파일명이 `--`로 시작하면 명령어의 옵션으로 오해받을 수 있으므로 `./` 경로를 명시하여 파일임을 확정지어 읽습니다.
  ```bash
  ls                                     # 현재 디렉토리 파일 목록 확인
  cat "./--spaces in this filename--"    # 상대 경로와 따옴표를 사용하여 특수 파일 내용 출력 / 획득한 패스워드(MNk8KNH3Usiio41PRUEoDFPqfxLPlSmx)를 사용하여 다음 레벨로 접속합니다.

### **Level 3 → 4**
![Bandit 4 결과](/assets/img/bandit/4.jpg)
* **문제 분석**: 
  `inhere` 디렉토리 내부에 숨겨진 파일 형태로 저장된 다음 레벨의 패스워드를 찾아야 합니다.
  - 파일 위치: `~/inhere/...Hiding-From-You`
  - 목표: 숨김 파일(점`.`으로 시작하는 파일 등)을 찾아 내용을 읽고 `bandit4` 계정의 패스워드 확인

* **풀이 과정**: 
  `ls` 명령어만으로는 보이지 않는 파일을 확인하기 위해 모든 파일을 보여주는 `-a` 옵션을 사용합니다. `inhere` 디렉토리로 이동한 후 `ls -a`를 통해 발견한 파일을 `cat`으로 읽어 패스워드를 추출합니다.
  ```bash
  ls                               # 현재 디렉토리 확인
  cd inhere                        # inhere 디렉토리로 이동
  ls -a                            # 숨겨진 파일 포함 전체 목록 확인
  cat ...Hiding-From-You           # 숨김 파일 내용 출력 / 획득한 패스워드(2WmrDFRmJIq3IPxneAaMGhapOpFhF3NJ)를 사용하여 다음 레벨로 접속합니다.

### **Level 4 → 5**
![Bandit 5 결과](/assets/img/bandit/5.jpg)
* **문제 분석**: 
  `inhere` 디렉토리 내에 존재하는 여러 파일 중 유일하게 사람이 읽을 수 있는(human-readable) 형식의 파일을 찾아 패스워드를 획득해야 합니다.
  - 파일 위치: `~/inhere` 내 10개의 파일 (`-file00` ~ `-file09`)
  - 목표: 바이너리 파일들 사이에서 아스키(ASCII) 텍스트 파일을 찾아 `bandit5` 계정의 패스워드 확인

* **풀이 과정**: 
  `inhere` 디렉토리로 이동하여 파일 목록을 확인합니다. 파일명이 `-`로 시작하므로 명령어 옵션으로 인식되지 않도록 `./` 경로를 붙여 내용을 확인합니다. 실습 결과 `-file07` 파일이 유일하게 사람이 읽을 수 있는 텍스트 형식을 유지하고 있음을 확인했습니다.
  ```bash
  cd inhere                     # inhere 디렉토리로 이동
  ls                            # 파일 목록 확인 (-file00 ~ -file09)
  cat ./-file07                 # 유일한 텍스트 파일인 -file07 내용 출력 / 획득한 패스워드(4oQYVPkxZ0OE005pTW81fB8j8lXGUoUw)를 사용하여 다음 레벨로 접속합니다.

### **Level 5 → 6**
![Bandit 6 결과](/assets/img/bandit/6.jpg)
* **문제 분석**: 
  `inhere` 디렉토리 하위의 수많은 파일 중 아래의 세 가지 조건을 모두 만족하는 파일을 찾아 패스워드를 획득해야 합니다.
  - 조건 1: 사람이 읽을 수 있는 형식 (human-readable)
  - 조건 2: 파일 크기가 정확히 1033 bytes
  - 조건 3: 실행 파일이 아님 (not executable)

* **풀이 과정**: 
  수동으로 모든 파일을 확인하기 어려우므로 `find` 명령어를 사용하여 조건을 필터링합니다. `-size` 옵션으로 크기를 지정하고, `! -executable` 옵션으로 실행 권한이 없는 파일을 검색하여 타겟 파일을 찾아냅니다.
  ```bash
  cd inhere                     # inhere 디렉토리로 이동
  find . -type f -size 1033c ! -executable
  **검색 결과**: ./maybehere07/.file2
  cat ./maybehere07/.file2      # 검색된 파일의 내용 출력 / 획득한 패스워드(DXjzPULLxYr17uocjS9SOnS9uE64h9cl)를 사용하여 다음 레벨로 접속합니다. 

### **Level 6 → 7**
![Bandit 7 결과-1](/assets/img/bandit/7.jpg)
![Bandit 7 결과-2](/assets/img/bandit/7-1.jpg)
* **문제 분석**: 
  패스워드가 서버 어딘가에 저장되어 있으며, 아래의 세 가지 조건을 모두 만족하는 파일을 찾아야 합니다.
  - 소유자(owner): `bandit7`
  - 그룹(group): `bandit6`
  - 파일 크기: 33 bytes

* **풀이 과정**: 
  홈 디렉토리에는 타겟 파일이 없으므로 루트(`/`) 디렉토리부터 서버 전체를 대상으로 `find` 명령어를 실행합니다. 검색 시 권한이 없는 디렉토리에서 발생하는 'Permission denied' 에러 메시지를 제외하고 필터링하여 유일하게 검색되는 파일의 경로를 파악한 뒤 내용을 확인합니다.
  ```bash
  find / -user bandit7 -group bandit6 -size 33c 2>/dev/null  # 조건에 맞는 파일 검색 (에러 메시지 제외)
  cat /var/lib/dpkg/info/bandit7.password                    # 검색된 파일 내용 출력 / 획득한 패스워드(morbNTDS6WjILUc0ymOdMaLn0LFVAaj)를 사용하여 다음 레벨로 접속합니다.

### **Level 7 → 8**
![Bandit 8 결과](/assets/img/bandit/8.jpg)
* **문제 분석**: 
  홈 디렉토리에 있는 `data.txt` 파일 내에서 `millionth`라는 단어 바로 옆에 저장된 패스워드를 찾아야 합니다.
  - 파일 위치: `~/data.txt`
  - 특이 사항: 파일 내에 수만 줄의 텍스트 데이터가 포함되어 있어 수동으로 찾기 어려움

* **풀이 과정**: 
  많은 양의 텍스트 데이터에서 특정 패턴을 찾을 때는 `grep` 명령어를 사용합니다. `data.txt` 파일에서 `millionth` 키워드를 검색하여 해당 줄에 적힌 패스워드를 획득합니다.
  ```bash
  ls                          # 현재 디렉토리 파일 목록 확인
  grep "millionth" data.txt   # 'millionth' 단어가 포함된 줄을 검색하여 패스워드 확인 / 획득한 패스워드(dfwvzFQi4mU0wfNbFOe9RoWskMLg7eEc)를 사용하여 다음 레벨로 접속합니다.

### **Level 8 → 9**
![Bandit 9 결과](/assets/img/bandit/9.jpg)
* **문제 분석**: 
  홈 디렉토리의 `data.txt` 파일 내에서 딱 한 번만 등장하는 줄을 찾아 패스워드를 획득해야 합니다.
  - 파일 위치: `~/data.txt`
  - 특이 사항: 대다수의 줄이 중복되어 있으며, 전체 내용 중 유일한(unique) 줄 하나가 패스워드임

* **풀이 과정**: 
  `uniq` 명령어는 인접한 줄끼리만 중복을 판별하는 특성이 있습니다. 따라서 `sort` 명령어를 사용하여 동일한 내용의 줄들을 먼저 정렬해준 뒤, 파이프(`|`)를 통해 `uniq -u` 옵션으로 전달하여 중복되지 않은 유일한 줄만 출력합니다.
  ```bash
  ls                          # 현재 디렉토리 파일 목록 확인
  sort data.txt | uniq -u     # 데이터를 정렬한 후 중복 없는 줄만 출력 / 획득한 패스워드(4CKMh1JI91bUIZZPXDqGanal4xvAg0JM)를 사용하여 다음 레벨로 접속합니다.

### **Level 9 → 10**
![Bandit 10 결과](/assets/img/bandit/10.jpg)
* **문제 분석**: 
  홈 디렉토리의 바이너리 파일 `data.txt`에서 특정 패턴(`=`) 뒤에 숨겨진 사람이 읽을 수 있는 패스워드를 찾아야 합니다.
  - 파일 위치: `~/data.txt`
  - 목표: 바이너리 내에서 여러 개의 `=` 문자 뒤에 위치한 문자열을 추출하여 `bandit10` 계정의 패스워드 확인

* **풀이 과정**: 
  `file` 명령어로 확인 시 `data.txt`는 바이너리 데이터이므로, 일반적인 `cat` 대신 바이너리 파일 내의 텍스트만 추출해주는 `strings` 명령어를 사용합니다. 추출된 문자열들 중 문제 조건인 `=` 문자가 포함된 줄을 찾기 위해 `grep`으로 필터링하여 패스워드를 획득합니다.
  ```bash
  ls                          # 현재 디렉토리 파일 목록 확인
  strings data.txt | grep "=" # 바이너리에서 문자열 추출 후 '=' 패턴 필터링 / 획득한 패스워드(FGUW5ilLVJrxX9kMYMmLN4MgbpfMiqey)를 사용하여 다음 레벨로 접속합니다.

### **Level 10 → 11**
![Bandit 11 결과](/assets/img/bandit/11.jpg)
* **문제 분석**: 
  홈 디렉토리의 `data.txt` 파일에 Base64로 인코딩된 패스워드가 저장되어 있습니다.
  - 파일 위치: `~/data.txt`
  - 목표: Base64로 인코딩된 데이터를 디코딩하여 `bandit11` 계정의 패스워드 확인

* **풀이 과정**: 
  `file` 명령어로 확인 결과 해당 파일은 ASCII 텍스트 파일이며, `cat`으로 출력 시 Base64 특유의 인코딩된 문자열을 확인할 수 있습니다. 리눅스의 `base64` 명령어에 `-d` (decode) 옵션을 사용하여 원문 패스워드를 추출합니다.
  ```bash
  ls                          # 현재 디렉토리 파일 목록 확인
  cat data.txt                # 인코딩된 데이터 확인
  base64 -d data.txt          # Base64 디코딩 수행 / 획득한 패스워드(dtR173fZKb0RRsDFSGsg2RWnpNVj3qRr)를 사용하여 다음 레벨로 접속합니다.

### **Level 11 → 12**
![Bandit 12 결과-1](/assets/img/bandit/12.jpg)
![Bandit 12 결과-2](/assets/img/bandit/12-1.jpg)
* **문제 분석**: 
  홈 디렉토리의 `data.txt` 파일에 ROT13으로 암호화된 패스워드가 저장되어 있습니다.
  - 파일 위치: `~/data.txt`
  - 목표: 알파벳을 13자리 뒤로 밀어 암호화하는 치환 암호(ROT13)를 복호화하여 `bandit12` 계정의 패스워드 확인

* **풀이 과정**: 
  `cat` 명령어로 암호화된 문자열을 확인한 후, ROT13 복호화 도구(웹 사이트 또는 리눅스 `tr` 명령어)를 사용하여 평문을 추출합니다. ROT13은 알파벳 26자의 절반을 이동시키는 방식이므로 동일한 변환을 한 번 더 수행하면 원문이 나타납니다.
  ```bash
  ls                          # 현재 디렉토리 파일 목록 확인
  cat data.txt                # ROT13으로 암호화된 데이터 확인
  ROT13 복호화 수행 / 획득한 패스워드(7x16WNeHi5YklhWsfFqoognUTyj9Q4)를 사용하여 다음 레벨로 접속합니다.

### **Level 12 → 13**
![Bandit 13 결과-1](/assets/img/bandit/13.jpg)
![Bandit 13 결과-2](/assets/img/bandit/13-1.jpg)
* **문제 분석**: 
  홈 디렉토리에 있는 `data.txt` 파일은 여러 번 반복적으로 압축된 바이너리 파일의 **hex dump** 형태입니다. 단순히 `cat`으로 읽을 수 없으며, 이를 다시 바이너리로 복원한 뒤 파일의 성격을 파악해가며 껍질을 한 꺼풀씩 벗겨내야 합니다.
  - 파일 위치: `~/data.txt`
  - 주요 도구: `xxd` (hex dump 복원), `file` (파일 타입 확인), `gzip`, `bzip2`, `tar` (압축 해제 도구)

* **풀이 과정**: 
  권한 문제와 작업 편의를 위해 `/tmp` 아래에 개인 디렉토리를 생성하여 작업합니다. `xxd -r` 명령어를 사용해 hex dump를 실제 바이너리 파일로 변환한 뒤, `file` 명령어로 매 단계마다 파일 형식을 확인하며 압축을 해제합니다.
  
  1. **바이너리 복원**: `xxd -r data.txt > data` 명령으로 바이너리 파일 생성
  2. **반복 압축 해제**:
     - **Step 1 (gzip)**: `file` 확인 시 `gzip compressed` -> `mv data data.gz` 후 `gzip -d data.gz`
     - **Step 2 (bzip2)**: `bzip2 compressed` 확인 -> `bzip2 -d data` (data.out 생성)
     - **Step 3 (gzip)**: `gzip compressed` 확인 -> `mv data.out data.gz` 후 `gzip -d data.gz`
     - **Step 4 (tar)**: `POSIX tar archive` 확인 -> `tar -xvf data` 실행 (data5.bin 추출)
     - **Step 5 (tar)**: `data5.bin`이 `tar archive` 확인 -> `tar -xvf data5.bin` (data6.bin 추출)
     - **Step 6 (bzip2)**: `data6.bin`이 `bzip2 compressed` -> `mv data6.bin data6.bz2` 후 `bzip2 -d data6.bz2`
     - **Step 7 (tar)**: `data6`이 `tar archive` 확인 -> `tar -xvf data6` (data8.bin 추출)
     - **Step 8 (gzip)**: `data8.bin`이 `gzip compressed` -> `mv data8.bin data8.gz` 후 `gzip -d data8.gz`
  3. **최종 확인**: 마지막 `data8` 파일이 `ASCII text`임을 확인하고 내용을 출력합니다.

  ```bash
  mkdir /tmp/hercent && cd /tmp/hercent   # 작업 디렉토리 생성 및 이동
  xxd -r ~/data.txt data                  # hex dump를 바이너리로 복원
  # [위의 Step 1~8 과정을 거쳐 압축 해제 반복 수행]
  file data8                              # 최종 파일 타입 확인 (ASCII text)
  cat data8                               # 패스워드 확인 / 획득한 패스워드(FO5dwfsc0bau4h8J2eUks2vdTDWAn)를 사용하여 다음 레벨로 접속합니다.

### **Level 13 → 14**
![Bandit 14 결과-1](/assets/img/bandit/14.jpg)
![Bandit 14 결과-2](/assets/img/bandit/14-1.jpg)
![Bandit 14 결과-3](/assets/img/bandit/14-2.jpg)
* **문제 분석**: 
  다음 레벨인 `bandit14` 계정의 패스워드 파일(`/etc/bandit_pass/bandit14`)은 오직 해당 계정 소유자만 읽을 수 있습니다. 현재 홈 디렉토리에 있는 SSH 개인키(`sshkey.private`)를 활용하여 비밀번호 없이 `bandit14` 계정으로 로그인한 뒤 패스워드를 추출해야 합니다.
  - 파일 위치: `~/sshkey.private`
  - 목표: 개인키를 이용한 SSH 접속 및 실제 패스워드 파일 획득

* **풀이 과정**: 
  `ls` 명령어로 `sshkey.private` 파일의 존재와 형식을 확인합니다. `ssh` 명령의 `-i` 옵션을 사용해 해당 개인키로 `localhost`에 접속을 시도합니다. 
  
  이 과정에서 키 파일의 권한이 너무 열려 있으면(보통 `600` 권한 필요) 접속이 거부되는데, 윈도우 환경에서 작업할 경우 메모장 등을 통해 `.key` 파일로 저장한 뒤 `icacls` 명령어를 사용하여 다른 사용자의 권한을 모두 제거하고 현재 사용자에게만 권한을 부여하는 세밀한 설정이 필요할 수 있습니다. 권한 설정이 완료된 키로 접속에 성공하면 `cat` 명령어로 최종 패스워드 파일의 내용을 확인합니다.

  ```bash
  ls -l                                      # 개인키 파일 확인
  file sshkey.private                        # PEM RSA private key 형식 확인
  (윈도우 환경 등에서 작업 시 icacls 등을 이용해 키 파일 권한 수정 필요)
  ssh -i sshkey.private bandit14@localhost -p 2220  # 개인키를 사용하여 bandit14로 로그인
  cat /etc/bandit_pass/bandit14              # 로그인 후 실제 패스워드 파일 내용 확인 / 획득한 패스워드를 사용하여 다음 레벨로 접속합니다.

### **Level 14 → 15**
![Bandit 15 결과-1](/assets/img/bandit/15.jpg)
![Bandit 15 결과-2](/assets/img/bandit/15-1.jpg)
* **문제 분석**: 
  현재 레벨(`bandit14`)의 패스워드를 `localhost`의 `30000`번 포트로 전송하여 다음 레벨의 패스워드를 응답받아야 합니다.
  - 대상 호스트: `localhost`
  - 대상 포트: `30000`
  - 목표: 네트워크 통신 도구를 사용하여 정확한 데이터를 전송하고 `bandit15` 패스워드 획득

* **풀이 과정**: 
  특정 포트로 데이터를 전송하기 위해 `nc (netcat)`, `/dev/tcp` (bash 내장 기능), `telnet` 등을 활용할 수 있습니다. 
  우선 `/etc/bandit_pass/bandit14` 파일을 읽어 현재 패스워드를 확인한 뒤, `nc` 명령어를 통해 `localhost:30000`에 접속하여 해당 패스워드를 전송합니다. 전송이 성공하면 `Correct!` 메시지와 함께 다음 레벨 패스워드가 출력됩니다.

  ```bash
  cat /etc/bandit_pass/bandit14              # 현재 레벨 패스워드(MU4VWeTyJk8ROof1qqmcBPaLh7lDCPvS) 확인
  nc localhost 30000                         # 30000번 포트 접속 후 패스워드 입력
  방법 1: echo "MU4VWeTyJk8ROof1qqmcBPaLh7lDCPvS" | nc localhost 30000
  방법 2: echo "MU4VWeTyJk8ROof1qqmcBPaLh7lDCPvS" > /dev/tcp/localhost/30000
  획득한 패스워드(8xCxjmgoKbGLhHFAZlGE5tmuHM2tKJQo)를 사용하여 다음 레벨로 접속합니다.  

### **Level 15 → 16**
![Bandit 16 결과-1](/assets/img/bandit/16.jpg)
![Bandit 16 결과-2](/assets/img/bandit/16-1.jpg)
* **문제 분석**: 
  현재 레벨(`bandit15`)의 패스워드를 `localhost`의 `30001`번 포트로 전송해야 합니다. 이전 단계와 비슷하지만, 이번에는 **SSL/TLS 암호화 연결**을 사용해야 한다는 조건이 추가되었습니다.
  - 대상 호스트: `localhost`
  - 대상 포트: `30001`
  - 제약 사항: 일반적인 `nc` 명령어는 암호화 통신을 지원하지 않으므로 사용 불가
  - 목표: SSL 연결 도구를 사용하여 패스워드 전송 및 `bandit16` 패스워드 확인

* **풀이 과정**: 
  암호화된 네트워크 연결을 위해 `openssl`의 `s_client` 기능을 사용합니다. `nc`와 달리 `openssl s_client`는 서버와 TLS 핸드세이크 과정을 거쳐 보안 채널을 형성합니다. 
  연결이 수립된 후 `bandit15`의 패스워드를 입력하면 서버가 이를 검증하고 다음 레벨의 패스워드를 응답합니다. `-quiet` 옵션을 사용하면 인증서 정보나 핸드세이크 과정의 상세 로그를 생략하고 깔끔하게 결과값만 확인할 수 있습니다.

  ```bash
  방법 1: 대화형 접속 (상세 정보 출력됨)
  openssl s_client -connect localhost:30001
  접속 완료 후 bandit15 패스워드(8xCxjmgoKbGLhHFAZlGE5tmuHM2tKJQo) 직접 입력

  방법 2: 파이프를 이용한 한 줄 명령어 (추천)
  echo "8xCxjmgoKbGLhHFAZlGE5tmuHM2tKJQo" | openssl s_client -connect localhost:30001 -quiet
  
  출력 결과:
  Correct!
  kSkvUpMQ7lBYyCM4GBPvCvT1BfWRy0Dx
  
  획득한 패스워드(kSkvUpMQ7lBYyCM4GBPvCvT1BfWRy0Dx)를 사용하여 다음 레벨로 접속합니다.

### **Level 16 → 17**
![Bandit 17 결과-1](/assets/img/bandit/17.jpg)
![Bandit 17 결과-2](/assets/img/bandit/17-1.jpg)
![Bandit 17 결과-3](/assets/img/bandit/17-2.jpg)
![Bandit 17 결과-4](/assets/img/bandit/17-3.jpg)

* **접속 정보**
    - `ssh bandit16@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: `localhost`의 `31000~32000` 포트 범위 중 SSL 서비스가 실행 중인 곳을 찾아 현재 패스워드를 전송하고, 다음 레벨(`bandit17`)로 접속할 수 있는 **SSH RSA Private Key**를 획득합니다.
    - **핵심 과제**: 여러 SSL 포트 중 입력을 그대로 반환하는 `echo` 서비스가 아닌 실제 패스워드를 반환하는 포트를 식별하고, 특정 문자로 시작하는 패스워드 전송 시 발생하는 통신 종료 오류를 해결해야 합니다.

* **풀이 과정**

    **1. 포트 스캔 및 서비스 식별**
    `nmap`을 사용하여 열려 있는 포트와 서비스의 상세 정보를 확인합니다.
    ```bash
    bandit16@bandit:~$ nmap -sV localhost -p 31000-32000
    ```
    * **결과 분석**:
        - `31518/tcp`: `ssl/echo` (데이터를 그대로 반환함)
        - `31790/tcp`: `ssl/unknown` (**타겟 포트: 실제 패스워드 반환 서비스**)

    **2. SSL 접속 및 개인키 추출 (Troubleshooting)**
    `openssl s_client`를 사용하여 타겟 포트(`31790`)에 접속합니다. 
    > **트러블슈팅**: 현재 패스워드가 `k`로 시작할 경우 SSL 핸드세이크 이후 서버가 입력을 기다리지 않고 연결을 끊어버리는 문제가 발생합니다. 이를 방지하기 위해 `-ign_eof` (Ignore End-Of-File) 옵션을 추가하여 데이터 전송을 안정적으로 처리합니다.

    ```bash
    # bandit16 패스워드 전송 및 응답 수신
    echo "kSkvUpMQ7lBYyCM4GBPvCvT1BfWRy0Dx" | openssl s_client -connect localhost:31790 -quiet -ign_eof
    ```
    명령 실행 후 출력된 `-----BEGIN RSA PRIVATE KEY-----`부터 키의 끝까지 복사합니다.

    **3. 외부 환경(Windows)에서의 키 저장 및 권한 설정**
    서버 내 `/tmp` 디렉토리에 키 저장이 원활하지 않은 경우, 로컬 윈도우 환경에서 메모장을 통해 `.key` 파일로 저장하고 권한을 부여합니다.
    ```powershell
    # Windows PowerShell 권한 설정 (icacls 활용)
    # 모든 상속 권한 제거 및 현재 사용자에게만 읽기(R) 권한 부여
    icacls .\bandit17.key /inheritance:r
    icacls .\bandit17.key /grant:r "${env:USERNAME}:(R)"
    ```

    **4. SSH 접속 완료**
    권한 설정이 완료된 키 파일을 사용하여 `bandit17` 계정으로 최종 접속합니다.
    ```bash
    ssh -i .\bandit17.key bandit17@bandit.labs.overthewire.org -p 2220
    ```

### **Level 17 → 18**
![Bandit 18 결과](/assets/img/bandit/18.jpg)

* **접속 정보**
    - `ssh -i [key.pem] bandit17@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: 홈 디렉토리에 있는 `passwords.old`와 `passwords.new` 두 파일을 비교하여, `passwords.old`와 비교했을 때 `passwords.new`에서 유일하게 변경된 줄을 찾아 패스워드를 획득합니다.
    - **핵심 과제**: 리눅스의 파일 비교 도구인 `diff` 명령어를 사용하여 두 대용량 파일 간의 차이점을 신속하게 식별하는 것입니다.

* **풀이 과정**

    **1. 파일 목록 확인**
    `ls` 명령어로 비교해야 할 두 데이터 파일이 홈 디렉토리에 있는지 확인합니다.
    ```bash
    bandit17@bandit:~$ ls
    passwords.new  passwords.old
    ```

    **2. 파일 비교 및 차이점 추출**
    `diff` 명령어를 실행합니다. 명령 결과에서 `<` 기호는 첫 번째 인자로 준 파일(`passwords.new`)의 내용을, `>` 기호는 두 번째 인자로 준 파일(`passwords.old`)의 내용을 나타냅니다.
    ```bash
    bandit17@bandit:~$ diff passwords.new passwords.old
    42c42
    < x2gLTTjFwMOhQ8oWNbMN362QKxfRqGlO
    ---
    > KxOU4IzbXM8j8HeAWPAXTd1eC77mp1qV
    ```
    * **출력 해석**: 42번째 줄이 변경되었으며, `<` 표시가 된 줄이 우리가 찾는 `passwords.new`에만 존재하는 새로운 패스워드입니다.

    **3. 패스워드 획득**
    출력 결과의 상단 줄인 `x2gLTTjFwMOhQ8oWNbMN362QKxfRqGlO`를 복사하여 다음 레벨 접속 시 사용합니다.

* **결과**
    - **획득 패스워드**: `x2gLTTjFwMOhQ8oWNbMN362QKxfRqGlO`
    - **학습 내용**: `diff` 명령어를 통한 텍스트 데이터 비교 원리 및 표준 출력(Standard Output)의 기호 의미 파악.

### **Level 18 → 19**
![Bandit 19 결과](/assets/img/bandit/19.jpg)

* **접속 정보**
    - `ssh bandit18@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: 홈 디렉토리에 있는 `readme` 파일을 읽어 다음 레벨 패스워드를 획득합니다.
    - **핵심 과제**: 로그인 시 `.bashrc` 수정으로 인해 SSH 접속 즉시 세션이 종료(Logout)되는 현상을 우회해야 합니다.

* **풀이 과정**

    **1. 현상 파악**
    일반적인 방법으로 SSH 접속을 시도하면, 사용자 환경 설정 파일인 `.bashrc`가 실행되면서 세션이 강제로 종료됩니다. 이는 대화형 쉘(Interactive Shell)이 열리는 순간 로그아웃 명령이 실행되도록 설정되어 있기 때문입니다.

    **2. SSH 명령 직접 실행 (Command Execution)**
    SSH는 서버에 접속하여 대화형 쉘을 열지 않고도 특정 명령어를 직접 실행하고 그 결과값만 받아올 수 있는 기능을 제공합니다. 이를 통해 `.bashrc`가 실행되어 쉘이 닫히기 전에 `cat` 명령으로 파일을 읽습니다.
    ```bash
    # SSH 접속 시 쉘을 열지 않고 바로 cat readme 실행
    ssh bandit18@bandit.labs.overthewire.org -p 2220 cat readme
    ```

    **3. 기타 우회 방법**
    - `-t` 옵션을 사용하여 쉘을 강제로 할당하되, 초기화 파일을 읽지 않는 옵션(`bash --norc`)을 전달하여 접속할 수 있습니다.
    - `/bin/sh`와 같이 `.bashrc`를 참조하지 않는 다른 쉘을 명시적으로 지정하여 접속을 시도할 수도 있습니다.

* **결과**
    - **획득 패스워드**: `c7G1v9B50osqOf0C0C8qW8b2zE01F827`
    - **학습 내용**: SSH의 원격 명령 실행 기능 및 쉘 초기화 스크립트(`.bashrc`)의 동작 메커니즘 이해.

### **Level 19 → 20**
![Bandit 20 결과](/assets/img/bandit/20.jpg)

* **접속 정보**
    - `ssh bandit19@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: 홈 디렉토리에 존재하는 **setuid 바이너리**(`bandit20-do`)를 이용하여 `bandit20` 계정의 패스워드 파일을 읽고 다음 레벨로 넘어갑니다.
    - **핵심 과제**: 리눅스의 특수 권한인 **SetUID(Set User ID)**의 개념을 이해하고, 해당 바이너리를 통해 일시적으로 상위 권한을 획득하여 제한된 파일에 접근하는 것입니다.

* **풀이 과정**

    **1. 정보 탐색 및 권한 확인**
    `ls -la` 명령어로 홈 디렉토리의 파일들을 확인합니다. `bandit20-do`라는 파일의 권한 부분을 보면 `-rwsr-x---`로 표시되어 있는데, 여기서 소유자 실행 권한 자리에 있는 **`s`** 비트가 바로 **SetUID**를 의미합니다.
    - **SetUID의 특징**: 이 파일이 실행되는 동안 프로세스의 유효 사용자 ID(EUID)는 실행시킨 사람이 아니라 **파일의 소유자(`bandit20`)**의 권한을 갖게 됩니다.

    **2. 바이너리 동작 테스트**
    파일을 그냥 실행해 보면 "Run a command as another user(다른 사용자의 권한으로 명령을 실행하라)"라는 안내 메시지가 출력됩니다. 실제로 어떤 권한으로 실행되는지 확인하기 위해 `whoami` 명령을 이 바이너리를 통해 전달해 봅니다.
    ```bash
    bandit19@bandit:~$ ./bandit20-do whoami
    bandit20
    ```
    결과를 통해 현재 계정은 `bandit19`이지만, 이 바이너리를 거치면 `bandit20` 권한으로 동작함을 알 수 있습니다.

    **3. 패스워드 파일 접근 및 획득**
    일반적인 `cat` 명령으로는 접근 권한이 없어 읽을 수 없는 `/etc/bandit_pass/bandit20` 파일을 해당 바이너리를 이용하여 읽습니다.
    ```bash
    # 직접 실행 시 Permission denied 발생
    bandit19@bandit:~$ cat /etc/bandit_pass/bandit20
    
    # setuid 바이너리를 통해 실행 시 성공
    bandit19@bandit:~$ ./bandit20-do cat /etc/bandit_pass/bandit20
    ```

* **결과**
    - **획득 패스워드**: `0qXahG8Zj0VMN9Ghs7iOwscfzyXOuBY0`
    - **학습 내용**: SetUID 권한이 부여된 실행 파일의 동작 방식 및 보안상 잠재적 위험성(권한 상승)에 대한 이해.

### **Level 20 → 21**
![Bandit 21 결과-1](/assets/img/bandit/21.jpg)
![Bandit 21 결과-2](/assets/img/bandit/21-1.jpg)

* **접속 정보**
    - `ssh bandit20@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: 홈 디렉토리의 `suconnect` **SetUID 바이너리**를 실행하여 다음 레벨의 패스워드를 획득합니다.
    - **동작 원리**: `suconnect`는 지정된 포트로 접속하여 데이터를 읽습니다. 해당 포트에서 보낸 데이터가 **현재 레벨(`bandit20`)의 패스워드**와 일치하면 다음 레벨의 패스워드를 반환합니다.
    - **핵심 과제**: 서버와 클라이언트 역할을 동시에 수행해야 하므로, 네트워크 리스너(`nc`)를 띄워 패스워드를 전송할 준비를 한 뒤 바이너리를 실행해야 합니다.

* **풀이 과정**

    **1. 정보 확인 및 시나리오 설계**
    `ls -al`로 확인한 `suconnect` 파일은 `bandit21` 소유의 SetUID 비트가 설정되어 있습니다. 
    두 개의 터미널 세션을 열거나, 한쪽 세션에서 백그라운드(`&`)로 리스너를 실행하여 패스워드를 "서빙"할 준비를 합니다.

    **2. 네트워크 리스너 설정 (Terminal 1)**
    `netcat(nc)`을 사용하여 임의의 포트(예: 3453)를 열고 대기합니다. 이때 `bandit20`의 패스워드를 미리 입력해 둡니다.
    ```bash
    bandit20@bandit:~$ nc -lp 3453
    0qXahG8Zj0VMN9Ghs7iOwscfzyXOuBY0  # 리스너 실행 후 현재 패스워드 입력 및 대기
    ```

    **3. suconnect 실행 및 연결 (Terminal 2)**
    다른 터미널에서 리스너가 열려 있는 포트로 `suconnect`를 연결시킵니다.
    ```bash
    bandit20@bandit:~$ ./suconnect 3453
    Connecting to localhost:3453...
    Reading password from port 3453...
    Password matches, sending next password
    ```

    **4. 패스워드 획득**
    패스워드가 일치하면 `suconnect`가 리스너가 떠 있는 터미널로 다음 레벨의 패스워드를 전송합니다.
    ```bash
    # Terminal 1(리스너 쪽) 출력 결과
    EeoULMCra2q0dSkYj561DX7s1CpBuOBt
    ```

* **결과**
    - **획득 패스워드**: `EeoULMCra2q0dSkYj561DX7s1CpBuOBt`
    - **학습 내용**: 네트워크 소켓 통신을 통한 데이터 검증 과정과 클라이언트-서버 구조의 기본적인 동작 이해.

### **Level 21 → 22**
![Bandit 22 결과](/assets/img/bandit/22.jpg)

* **접속 정보**
    - `ssh bandit21@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: 시스템 예약 작업 데몬인 `cron`에 의해 정기적으로 실행되는 스크립트를 추적하여 `bandit22` 계정의 패스워드를 획득합니다.
    - **핵심 과제**: `/etc/cron.d/` 설정 파일 분석을 통해 실행되는 쉘 스크립트(`*.sh`)의 경로를 찾고, 해당 스크립트가 패스워드를 어느 경로에 기록(Redirection)하는지 파악하는 것입니다.

* **풀이 과정**

    **1. cron 설정 파일 확인**
    리눅스 시스템 작업 예약 설정이 모여 있는 `/etc/cron.d/` 디렉토리를 확인하여 `bandit22`와 관련된 설정 파일을 찾습니다.
    ```bash
    bandit21@bandit:~$ ls -l /etc/cron.d/
    bandit21@bandit:~$ cat /etc/cron.d/cronjob_bandit22
    ```
    * **출력 분석**:
      `* * * * * bandit22 /usr/bin/cronjob_bandit22.sh &> /dev/null`
      - 매 분마다(`* * * * *`) `bandit22`의 권한으로 특정 스크립트가 실행되고 있음을 확인했습니다.

    **2. 실행 스크립트(`sh`) 내용 분석**
    위에서 찾은 `/usr/bin/cronjob_bandit22.sh` 파일의 내용을 읽어 어떤 동작을 수행하는지 분석합니다.
    ```bash
    bandit21@bandit:~$ cat /usr/bin/cronjob_bandit22.sh
    ```
    * **스크립트 코드**:
      ```bash
      #!/bin/bash
      chmod 644 /tmp/t7O6lds9S0RqQh9aMcz6ShpAoZKF7fgv
      cat /etc/bandit_pass/bandit22 > /tmp/t7O6lds9S0RqQh9aMcz6ShpAoZKF7fgv
      ```
      - 이 스크립트는 `bandit22` 권한으로 실행되면서 자신의 패스워드 파일을 읽어 누구나 읽을 수 있는(644) `/tmp/t7O6...` 경로의 파일에 저장하고 있습니다.

    **3. 최종 패스워드 추출**
    스크립트가 데이터를 넘겨준 임시 파일의 경로를 직접 읽어 패스워드를 획득합니다.
    ```bash
    bandit21@bandit:~$ cat /tmp/t7O6lds9S0RqQh9aMcz6ShpAoZKF7fgv
    ```

* **결과 및 기술 요약**
    - **획득 패스워드**: `tRae0UfB9v0UzbCdn9cY0gQnds9GF58Q`
    - **Technical Insight**: 
        * **Insecure Task Automation**: 관리 편의를 위해 설정한 자동화 작업이 민감한 정보(Password)를 보호받지 못하는 공용 디렉토리(`/tmp`)에 노출할 경우, 권한 상승(Privilege Escalation)의 결정적인 취약점이 될 수 있음을 확인했습니다.
        * **Cron Job Analysis**: 시스템 백그라운드에서 주기적으로 돌아가는 프로세스를 모니터링하고 분석하는 역량을 습득했습니다.

### **Level 22 → 23**
![Bandit 23 결과](/assets/img/bandit/23.jpg)

* **접속 정보**
    - `ssh bandit22@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: 정기적으로 실행되는 `cron` 스크립트를 분석하여, `bandit23`의 패스워드가 저장된 임시 파일의 경로를 계산하고 패스워드를 획득합니다.
    - **핵심 과제**: 쉘 스크립트 내부의 변수 처리와 파이프라인(`md5sum`, `cut`)을 이용한 동적 파일명 생성 로직을 이해하고 이를 역추적하는 것입니다.

* **풀이 과정**

    **1. cron 설정 및 스크립트 확인**
    `/etc/cron.d/` 디렉토리에서 `bandit23` 관련 설정을 찾고, 실행되는 스크립트의 경로와 내용을 분석합니다.
    ```bash
    bandit22@bandit:~$ cat /etc/cron.d/cronjob_bandit23
    # 결과: * * * * * bandit23 /usr/bin/cronjob_bandit23.sh &> /dev/null
    
    bandit22@bandit:~$ cat /usr/bin/cronjob_bandit23.sh
    ```
    * **스크립트 로직 분석**:
      ```bash
      #!/bin/bash
      myname=$(whoami)
      mytarget=$(echo I am user $myname | md5sum | cut -d ' ' -f 1)
      cat /etc/bandit_pass/$myname > /tmp/$mytarget
      ```
      - 이 스크립트는 실행 주체(`whoami`)가 누구냐에 따라 저장될 파일명이 결정됩니다. `cron`에 의해 `bandit23` 권한으로 실행될 때, `bandit23`의 패스워드가 특정 해시값의 파일명으로 `/tmp/`에 저장됨을 알 수 있습니다.

    **2. bandit23의 타겟 파일명 역추적**
    스크립트가 `bandit23` 권한으로 실행될 때 생성할 파일명을 알아내기 위해, `$myname` 변수에 `bandit23`을 대입하여 동일한 명령어를 실행합니다.
    ```bash
    bandit22@bandit:~$ echo "I am user bandit23" | md5sum | cut -d ' ' -f 1
    8ca319486bfbbc3663ea0fbe81326349
    ```

    **3. 패스워드 획득**
    계산된 파일명을 바탕으로 `/tmp/` 디렉토리에 이미 생성되어 있는 파일을 읽어 패스워드를 추출합니다.
    ```bash
    bandit22@bandit:~$ cat /tmp/8ca319486bfbbc3663ea0fbe81326349
    ```

* **결과 및 기술 요약**
    - **획득 패스워드**: `0Zf11ioIjMVN551jX3CmStKLYqjk54Ga`
    - **Technical Insight**: 
        * **Prediction of Execution Context**: 스크립트가 실행되는 환경(User context)을 예측하여 동적으로 생성되는 파일 경로를 찾아내는 분석 역량을 습득했습니다.
        * **Pipeline Analysis**: `md5sum`을 통한 해시 생성과 `cut`을 이용한 문자열 파싱 과정을 정확히 이해하여 데이터의 흐름을 추적했습니다.

### **Level 23 → 24**
![Bandit 24 결과-1](/assets/img/bandit/24.jpg)
![Bandit 24 결과-2](/assets/img/bandit/24-1.jpg)

* **접속 정보**
    - `ssh bandit23@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: `bandit24` 권한으로 정기 실행되는 스크립트의 취약점을 이용해, 자신만의 스크립트를 실행시켜 `bandit24`의 패스워드를 획득합니다.
    - **핵심 과제**: `/var/spool/bandit24/foo` 디렉토리에 있는 파일을 `bandit24` 권한으로 실행해 주는 크론(cron) 작업의 동작 원리를 이해하고, 임무를 수행할 악성(?) 스크립트를 주입하는 것입니다.

* **풀이 과정**

    **1. 크론 작업 및 스크립트 동작 분석**
    `/etc/cron.d/cronjob_bandit24` 설정을 통해 `/usr/bin/cronjob_bandit24.sh`가 매 분마다 실행됨을 확인합니다.
    ```bash
    bandit23@bandit:~$ cat /usr/bin/cronjob_bandit24.sh
    ```
    * **스크립트 주요 로직**:
        - `/var/spool/bandit24/foo` 디렉토리로 이동.
        - 디렉토리 내의 모든 파일을 순회하며 소유자가 `bandit23`인 경우, `timeout` 명령어로 60초간 실행 후 삭제함.

    **2. 패스워드 탈취용 스크립트 작성**
    `bandit24` 권한으로 실행될 때 `/etc/bandit_pass/bandit24` 파일을 읽어 누구나 접근 가능한 `/tmp` 경로에 저장하도록 하는 쉘 스크립트를 작성합니다.
    ```bash
    cat > /tmp/getpass.sh << 'EOF'
    #!/bin/bash
    cat /etc/bandit_pass/bandit24 > /tmp/bandit24pass
    EOF
    ```

    **3. 권한 부여 및 스크립트 배치**
    작성한 스크립트가 실행될 수 있도록 실행 권한(`+x`)을 부여하고, 크론 작업이 감시하는 디렉토리로 복사합니다.
    ```bash
    bandit23@bandit:~$ chmod +x /tmp/getpass.sh
    bandit23@bandit:~$ cp /tmp/getpass.sh /var/spool/bandit24/foo/
    ```

    **4. 결과 확인**
    크론 작업이 실행될 때까지(최대 1분) 기다린 후, 스크립트가 생성한 파일을 읽어 패스워드를 획득합니다.
    ```bash
    bandit23@bandit:~$ cat /tmp/bandit24pass
    ```

* **결과 및 기술 요약**
    - **획득 패스워드**: `gb8KRRcsshuZXI0tUuR6ypOFjiZbf3G8`
    - **Technical Insight**: 
        * **Arbitrary Code Execution**: 신뢰할 수 없는 사용자가 올린 파일을 특정 권한으로 자동 실행하게 설정된 환경은 임의 코드 실행(ACE) 취약점에 노출될 수 있음을 실습했습니다.
        * **Temporary Privilege Escalation**: 크론탭과 같은 백그라운드 서비스의 허점을 이용해 일시적인 권한 상승을 유도하는 기법을 습득했습니다.

### **Level 24 → 25**
![Bandit 25 결과-1](/assets/img/bandit/25.jpg)
![Bandit 25 결과-2](/assets/img/bandit/25-1.jpg)
![Bandit 25 결과-3](/assets/img/bandit/25-2.jpg)

* **접속 정보**
    - `ssh bandit24@bandit.labs.overthewire.org -p 2220`

* **문제 분석**
    - **목표**: `localhost`의 `30002` 포트에 접속하여 현재 레벨의 패스워드와 4자리 숫자 PIN(0000~9999)을 전송하고, 다음 레벨의 패스워드를 획득합니다.
    - **핵심 과제**: 10,000가지의 조합을 수동으로 입력하는 것은 불가능하므로, 스크립트를 이용한 **무차별 대입(Brute-force)** 공격을 수행해야 합니다.

* **풀이 과정**

    **1. 서비스 동작 확인**
    `nc` 명령어로 포트에 접속하여 어떤 형식의 입력을 요구하는지 확인합니다.
    ```bash
    bandit24@bandit:~$ nc localhost 30002
    # "[현재 패스워드] [PIN]" 형식을 한 줄에 입력해야 함을 확인
    ```

    **2. 무차별 대입 스크립트 작성 (성능 최적화)**
    매번 `nc`를 실행하여 연결을 시도하는 방식은 속도가 매우 느립니다. 모든 조합(10,000개)을 먼저 생성한 뒤, 파이프(`|`)를 통해 한 번의 연결로 모든 데이터를 밀어 넣는 방식이 훨씬 효율적입니다.
    ```bash
    # 0000부터 9999까지 생성하여 nc로 전송하는 원라인 스크립트
    for pin in $(seq -w 0 9999); do
        echo "gb8KRRcsshuZXI0tUuR6ypOFjiZbf3G8 $pin"
    done | nc localhost 30002 > /tmp/brute_result.txt
    ```
    * `seq -w 0 9999`: 0부터 9999까지 숫자를 생성하되, `-w` 옵션으로 자리수를 맞춰줍니다 (ex: 0001, 0002...).

    **3. 결과 필터링 및 패스워드 획득**
    전송된 결과값 중 "Wrong!"이 포함되지 않은 줄을 찾거나, 전체 로그의 마지막 부분을 확인하여 `Correct!` 메시지와 함께 출력된 패스워드를 확인합니다.
    ```bash
    bandit24@bandit:~$ grep -v "Wrong" /tmp/brute_result.txt
    # 또는 출력 결과의 최하단 확인
    ```

* **결과 및 기술 요약**
    - **획득 패스워드**: `iCi86ttT4KSNe1armKiwbQNmB3YJP3q4`
    - **Technical Insight**: 
        * **Brute-force Attack**: 가능한 모든 조합을 시도하여 비밀번호나 PIN을 찾아내는 기초적인 공격 기법을 실습했습니다.
        * **Network Pipelining**: 대량의 요청을 보낼 때 매번 세션을 맺는 대신, 파이프라인을 통해 한 세션 내에서 스트리밍 방식으로 데이터를 처리하여 공격 효율을 극대화(성능 최적화)했습니다.

---

## 3. 실습을 마치며 (배운 점)

1. **리눅스 시스템 구조와 명령어 조합의 강력함 체득**
   단순히 파일을 읽고 쓰는 수준을 넘어 `find`, `grep`, `xxd`, `diff` 등 다양한 도구를 파이프라인(`|`)으로 연결하여 시스템 내 숨겨진 정보를 추출하는 법을 익혔습니다. 특히 대량의 데이터를 처리할 때 `sort`, `uniq` 같은 도구가 어떻게 정보의 가독성을 높여주는지, 그리고 `strings` 명령어가 바이너리 파일 내 텍스트 추출(포렌식 기초)의 핵심임을 깨달았습니다.

2. **권한 관리 체계와 보안 취약점의 상관관계 이해**
   `SetUID` 비트가 설정된 바이너리와 `cron` 자동화 스크립트의 취약점을 직접 분석하고 공략하며, "관리자의 편의가 보안의 치명적인 허점이 될 수 있다"는 사실을 배웠습니다. '최소 권한 원칙(Principle of Least Privilege)'이 실무에서 왜 중요한지 실감했으며, 이는 향후 인프라 보안 및 모의해킹 관점에서 시스템을 바라보는 넓은 시야를 갖게 해주었습니다.

3. **환경적 제약을 극복하는 실전 트러블슈팅 역량 강화**
   실습 중 발생한 환경적 변수(패스워드 'k' 시작 이슈 해결을 위한 `-ign_eof` 옵션 활용, Windows 환경에서의 `icacls` 권한 설정 우회 등)를 해결하며 유연한 문제 해결 능력을 길렀습니다. 정해진 매뉴얼에 의존하기보다 문제의 원인을 분석하고 최선의 우회로를 찾아내는 과정이 보안 전문가에게 필요한 '해커 마인드'의 핵심임을 깨달았습니다.

---
