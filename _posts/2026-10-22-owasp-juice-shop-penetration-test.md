---
title: "OWASP Juice Shop 웹 모의침투: 정찰부터 SQL Injection 공격 체인까지"
date: 2026-10-20 21:00:00 +0900
categories: ["CTF & Wargame"]
tags: [owasp-juice-shop, penetration-testing, sql-injection, authentication-bypass, information-disclosure, web-security, bug-bounty]
toc: true
comments: true
mermaid: true
---

## 1. 미션 개요

이번 미션의 목표는 OWASP Top 10을 기준으로 웹 애플리케이션 모의침투의 전체 흐름을 경험하는 것이다.

1. 정보 수집(Reconnaissance)
2. 취약점 탐색 및 검증
3. 취약점 연결을 통한 공격 시나리오 설계
4. 영향도와 대응 방안 문서화

대상은 OWASP가 교육·보안 인식·CTF 용도로 제공하는 의도적 취약 웹 애플리케이션인 **OWASP Juice Shop**으로 정했다. 공식 저장소는 Juice Shop을 현대적인 웹 애플리케이션에서 발견되는 OWASP Top 10 및 기타 보안 결함을 연습하기 위한 프로젝트로 소개한다. [공식 저장소](https://github.com/juice-shop/juice-shop)

실제 서비스가 아니라 내가 소유한 로컬 인스턴스만 대상으로 했고, 외부 서버·타인 계정·실제 개인정보에는 요청을 보내지 않았다.

## 2. 실습 환경

| 항목 | 값 |
| --- | --- |
| 운영체제 | Windows / PowerShell |
| Node.js | v24.20.0 |
| 대상 소스 | OWASP Juice Shop 공식 저장소 |
| 검증 커밋 | `399fba76194305a312693eee44f4df64bdf0c3ce` |
| 실행 주소 | `http://127.0.0.1:3000` |
| 데이터베이스 | SQLite |

Docker가 설치되어 있지 않아 공식 저장소를 `work/juice-shop`에 shallow clone한 뒤 소스에서 실행했다. 프런트엔드 production build와 서버 TypeScript build가 모두 성공했다. 처음 서버를 실행했을 때 SQLite native binding이 없다는 오류가 발생했으며, `npm rebuild sqlite3 --no-audit --no-fund`로 보완한 후 서버가 정상적으로 시작했다.

## 3. 정보 수집

### 3.1 기본 엔드포인트 확인

브라우저와 HTTP 요청으로 애플리케이션의 기본 노출면을 확인했다.

| 요청 | 결과 | 관찰 내용 |
| --- | --- | --- |
| `GET /` | `200` | Angular 기반 상품 페이지 |
| `GET /rest/products/search?q=test` | `200` | JSON 상품 검색 API |
| `GET /api-docs` | `301` | API 문서 경로 존재 |
| `GET /ftp/` | `200` | 파일 목록을 보여 주는 디렉터리 인덱스 |

응답에는 `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` 같은 보안 헤더도 있었다. 그러나 보안 헤더가 일부 설정되어 있다는 사실만으로 인증·인가나 정보 노출 문제가 해결되는 것은 아니므로, 기능별 접근 통제를 별도로 확인했다.

### 3.2 FTP 디렉터리 인덱스

`/ftp/`에서는 `package.json.bak`, `package-lock.json.bak`, `coupons_2013.md.bak`, `incident-support.kdbx`, `suspicious_errors.yml` 같은 파일명이 노출됐다.

![FTP 디렉터리 인덱스에 노출된 백업 파일과 KDBX 파일명](/assets/img/mission-43-owasp-juice-shop/05-ftp-directory-listing.png)
_파일 서버가 제공하는 디렉터리 목록. 파일명만으로도 백업·설정·자격 증명 저장소로 보이는 관심 대상이 식별된다._

이 단계에서 확인된 사실은 **파일명과 크기 노출**이다. 파일 내용을 모두 읽을 수 있다고 확대 해석하지 않았다. 실제로 `coupons_2013.md.bak`를 열었을 때는 확장자 검증으로 `403`이 반환됐다.

### 3.3 오류 상세 정보 노출

확장자 검증 오류 화면에는 Express 버전과 서버의 로컬 절대 경로가 포함된 stack trace가 표시됐다.

![파일 서버 오류 응답에 노출된 Express stack trace와 로컬 경로](/assets/img/mission-43-owasp-juice-shop/06-file-server-error-disclosure.png)
_403 응답 자체는 접근을 차단했지만, 오류 화면은 내부 파일 경로와 모듈 호출 경로를 반환했다._

운영 환경에서 이런 상세 오류는 공격자에게 프레임워크·파일 구조·배포 경로를 알려 주는 정보가 된다. 애플리케이션 오류 응답은 일반화하고, 상세 stack trace는 서버 로그에만 남겨야 한다.

## 4. 핵심 취약점: 로그인 SQL Injection

### 4.1 입력 지점 확인

로그인 화면의 이메일 입력란과 비밀번호 입력란을 확인했다. 정상 계정 정보를 사용하지 않고, 로컬 교육용 인스턴스에 다음 테스트 문자열을 전달했다.

```http
POST /rest/user/login HTTP/1.1
Host: 127.0.0.1:3000
Content-Type: application/json

{"email":"' OR 1=1--","password":"x"}
```

![로그인 이메일 필드에 SQL Injection 테스트 문자열을 입력한 화면](/assets/img/mission-43-owasp-juice-shop/02-login-sqli-payload.png)
_이메일 조건식에 영향을 주는 테스트 문자열과 임의의 비밀번호를 입력한 상태._

### 4.2 인증 우회 결과

요청 결과는 `200 OK`였고 `authentication.token`이 발급됐다. 토큰 원문은 저장하거나 공개하지 않고 로컬 브라우저 세션에서만 사용했다.

브라우저의 계정 메뉴에서 `admin@juice-sh.op`가 표시되는 것까지 확인해 인증 우회 결과를 검증했다.

같은 요청은 공백을 포함한 주석 변형에서도 재현됐다. 따라서 단순히 오류 페이지가 발생한 것이 아니라, 사용자 입력이 로그인 쿼리의 논리에 영향을 주어 인증이 우회된 것으로 판단했다.

### 4.3 관리자 세션 확인

발급된 세션으로 계정 메뉴를 열어 현재 로그인 주체를 확인했다.

![인증 우회 후 관리자 계정 메뉴](/assets/img/mission-43-owasp-juice-shop/04-admin-account-menu.png)
_계정 메뉴에 `admin@juice-sh.op`가 표시되어 관리자 세션 발급을 확인했다._

HTTP 요청으로도 같은 세션을 검증했다.

| 요청 | 결과 |
| --- | --- |
| `GET /rest/admin/application-configuration` | `200`, 약 36 KB 설정 응답 |
| `GET /api/Challenges` | `200`, 챌린지 메타데이터 응답 |
| `GET /rest/basket/1` | `200`, 보호된 장바구니 응답 |

이 검증에서는 데이터 변경·삭제 요청을 보내지 않았다. 따라서 관리자 API가 제공하는 모든 변경 기능이 실행됐다고 주장하지 않고, 실제로 읽기 요청에서 확인한 권한 상승 범위만 기록한다.

## 5. 공격 체인 설계

이번 실습에서 가장 중요한 부분은 취약점을 따로 나열하는 것이 아니라, 하나의 취약점이 다음 접근 권한으로 이어지는 과정을 확인하는 것이었다.

```mermaid
flowchart LR
  A[로그인 이메일 입력] --> B[SQL Injection]
  B --> C[관리자 인증 토큰 발급]
  C --> D[관리자 계정 메뉴 확인]
  D --> E[관리자 설정 API 접근]
  E --> F[내부 구성·보호된 데이터 노출]
  G[/ftp/ 디렉터리 인덱스] --> H[백업·설정 파일명 수집]
  H --> I[오류 응답에서 내부 경로 노출]
```

정리하면 핵심 공격 체인은 다음과 같다.

```text
로그인 SQL Injection
  → 인증 우회
  → 관리자 세션 발급
  → 관리자 API 접근
  → 내부 설정 및 보호된 업무 데이터 조회
```

`/ftp/` 노출과 오류 상세 노출은 인증 우회와 별개의 정찰 보조 경로다. 이번 검증에서는 이 파일들을 이용해 추가 인증 정보나 비밀키를 획득했다고 주장하지 않는다.

## 6. 영향도 분석

### 기밀성(Confidentiality)

- 관리자용 애플리케이션 설정 응답 조회
- 챌린지와 API 구조에 대한 상세 메타데이터 조회
- 관리자 장바구니 데이터 조회
- 파일 서버의 백업·설정 파일명과 내부 경로 노출

### 무결성(Integrity)

현재 단계에서는 변경 요청을 수행하지 않았다. 다만 인증 주체가 관리자이므로, 관리자용 쓰기 API가 같은 세션을 신뢰한다면 주문·상품·사용자 데이터 변조로 확대될 수 있다. 이 부분은 실제 변경 요청을 하지 않았으므로 **조건부 영향**으로 표시한다.

### 가용성(Availability)

이번 테스트에서는 삭제·대량 요청·부하 유발 행위를 하지 않았다. 가용성 영향은 확인되지 않았다.

### 위험도

로그인 SQL Injection은 정상 비밀번호 없이 관리자 세션을 발급하므로 High로 평가했다. 파일명·stack trace 노출은 단독으로는 중간 수준의 정보 노출이지만, 인증 우회와 결합되면 후속 탐색 비용을 낮추는 보조 정보가 된다.

## 7. 대응 방안

### 7.1 SQL Injection 방어

OWASP는 SQL Injection 대응의 우선순위로 prepared statement/parameterized query를 제시한다. 문자열 연결로 SQL을 만들지 말고, 쿼리 구조와 사용자 데이터를 분리해야 한다.

- ORM의 bind parameter 또는 prepared statement 사용
- 이메일 형식 검사는 보조 방어로만 사용
- 입력값 escape만으로 방어하려 하지 않기
- 애플리케이션 DB 계정에 최소 권한 부여
- SQL Injection payload를 포함한 로그인 회귀 테스트 추가

참고: [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

### 7.2 인증·인가 방어

로그인 성공 여부만 확인하는 것이 아니라, 매 요청마다 서버 측에서 역할과 리소스 권한을 검증해야 한다.

- 관리자 API는 deny-by-default 정책 적용
- 사용자·역할·리소스 소유권을 매 요청 검증
- 세션·JWT 만료와 폐기 정책 적용
- 로그인 rate limit, 감사 로그, 이상 로그인 탐지 추가
- 관리자 설정 API는 필요한 항목만 allow-list로 반환

참고: [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

### 7.3 파일 서버와 오류 처리

- 운영 환경에서 디렉터리 인덱싱 비활성화
- 백업 파일을 웹 루트 밖에 보관
- `.bak`, `.kdbx`, 설정·로그 파일의 배포 차단
- 오류 응답에는 일반화된 메시지만 반환
- stack trace와 절대 경로는 서버 로그에만 기록
- 정적 파일 allow-list와 canonical path 검증 적용

## 8. 검증 결과와 한계

이번 글에서 **확인**으로 표시한 것은 로컬 인스턴스에서 실제 HTTP 응답 또는 브라우저 화면으로 재현한 항목이다. 반대로 관리자 쓰기 작업, 파일 내용 탈취, 외부 서비스 공격은 수행하지 않았다.

| 항목 | 상태 |
| --- | --- |
| 로컬 Juice Shop 실행 | 확인 |
| 기본 API·FTP 경로 발견 | 확인 |
| FTP 디렉터리 파일명 노출 | 확인 |
| 확장자 오류의 내부 경로 노출 | 확인 |
| 로그인 SQL Injection | 확인 |
| 관리자 세션 발급 | 확인 |
| 관리자 읽기 API 접근 | 확인 |
| 관리자 데이터 변경 | 수행하지 않음 |
| 외부 대상 테스트 | 수행하지 않음 |

## 9. 마무리

이번 미션을 통해 모의침투는 페이로드 하나를 입력하고 성공 메시지를 확인하는 데서 끝나지 않는다는 것을 확인했다. 먼저 노출면을 정리하고, 입력 지점을 찾고, 인증 경계를 넘었는지 확인한 다음, 실제 권한으로 접근 가능한 API와 영향 범위를 단계적으로 검증해야 한다.

특히 로그인 SQL Injection은 다음과 같은 공격 체인을 만들었다.

```text
입력 조작 → 인증 우회 → 관리자 세션 → 관리자 API → 내부 데이터 조회
```

보고서에서는 실행하지 않은 변경·삭제 작업을 성공한 것처럼 쓰지 않는 것이 중요하다. 확인된 사실, 조건부 영향, 아직 검증하지 않은 부분을 구분해야 재현성과 신뢰도를 함께 확보할 수 있다.

### 참고 자료

- [OWASP Juice Shop 공식 GitHub 저장소](https://github.com/juice-shop/juice-shop)
- [OWASP Juice Shop 공식 프로젝트 페이지](https://owasp-juice.shop/)
- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
