---
title: "HexTree Android Track"
date: 2026-10-01 21:40:00 +0900
categories: [Security, Android]
tags: [hextree, android, bugbounty, adb, intent, deeplink, service, broadcast-receiver, content-provider, fileprovider, webview, frida, writeup, mission47]
---

## 1. 들어가며

[HexTree Android Track](https://app.hextree.io/map/android)의 14개 과정을 완료했다.

![HexTree Android Track 14/14 완료 화면](/assets/img/hextree-android-track/01-android-track-14-of-14.png)
_2026년 10월 1일 기준 Android Track 14/14 완료 화면._

## 2. 실습 환경과 분석 흐름

| 항목 | 내용 |
|---|---|
| 플랫폼 | HexTree Android Track |
| 대상 | HexTree가 제공한 교육용 APK 및 Intent Attack Surface 앱 |
| 주요 도구 | Android Studio, Android Emulator, ADB, JADX, apktool, Frida |
| 정적 분석 | `AndroidManifest.xml`, JADX Java 코드, resource, native library |
| 동적 분석 | `am`, `pm`, `content`, `logcat`, Frida Java bridge |

전체 실습 순서.

```text
Manifest에서 외부 진입점 식별
  → Intent/URI/extra/permission 추적
  → 민감 동작까지 도달 가능한지 확인
  → ADB 또는 공격 앱으로 재현
  → 영향과 수정 방안 정리
```

## 3. 14개 과정에서 학습한 내용

| # | 과정 | 핵심 내용 |
|---:|---|---|
| 1 | Your First Android App | Activity, layout, click listener, Intent를 사용하는 공격 앱 제작 기초 |
| 2 | Research Device & Emulator Setup | Emulator, ADB, 패키지 설치·실행, `dumpsys`, `logcat` |
| 3 | Reverse Engineering Android Apps | apktool, JADX, resource, JNI, APK diff 분석 |
| 4 | Network Interception | tcpdump, HTTP proxy, 응답 변조, archive path traversal |
| 5 | Dynamic Instrumentation | Frida attach/spawn, `Java.use`, instance 탐색, method hook |
| 6 | Intent Attack Surface | exported Activity, nested Intent, activity result, implicit Intent, Deep Link |
| 7 | Android Permissions | protection level, custom permission, 권한 있는 앱의 deputy 문제 |
| 8 | Android Services | started/bound service, Messenger, AIDL, Binder 호출 |
| 9 | Broadcast Receivers | broadcast 위조·가로채기, ordered broadcast, notification action |
| 10 | Android (Insecure) Storage | SharedPreferences, SQLite, cache, internal/external storage |
| 11 | Content- and FileProvider | content URI, SQL injection, temporary grant, FileProvider path 설정 |
| 12 | WebViews and CustomTabs | JS bridge, XSS, file access, Custom Tabs `postMessage` |
| 13 | Android Bug Bounty | 도달 가능성, 영향 증명, 재현 절차, 수정안 작성 |
| 14 | Bluetooth Reverse Engineering Basics | BLE central/peripheral, GATT, UUID, read/write/notify |

## 4. ADB와 앱 컴포넌트 열거

런처에 보이는 화면이 앱의 전체 공격 표면이 아니다. `MAIN`/`LAUNCHER` 필터가 없는 Activity도 Manifest에 등록되어 있고, exported 상태라면 명시적 Intent로 열 수 있다.

```bash
adb install -r adb_test_application.apk
adb shell cmd package resolve-activity --brief io.hextree.adbtestapplication
adb shell dumpsys package io.hextree.adbtestapplication

adb shell am start \
  -n io.hextree.adbtestapplication/.HiddenActivity
```

로그 분석에서는 이전 메시지와 섞이지 않게 buffer를 비운 뒤 앱을 다시 실행했다.

```bash
adb logcat -c
adb shell am force-stop io.hextree.adbtestapplication
adb shell monkey -p io.hextree.adbtestapplication 1
adb logcat -d "MainActivity:V *:S"
```

**UI 메뉴만 보지 말고 Manifest와 package manager 결과를 함께 보라**

## 5. Intent와 Activity 공격 표면

### 5.1 exported Activity와 조작 가능한 Intent

Intent Attack Surface 앱의 첫 실습은 `Flag1Activity`, `Flag2Activity`, `Flag3Activity`에 필요한 component, action, data를 구성하는 문제였다.

![Intent startActivity 실습 완료 화면](/assets/img/hextree-android-track/02-intent-startactivity.png)
_공개 Activity, extra, data URI를 조합하는 `Practice startActivity()` _

```bash
# 공개 Activity 직접 실행
adb shell am start \
  -n io.hextree.attacksurface/.activities.Flag1Activity

# action 전달
adb shell am start \
  -n io.hextree.attacksurface/.activities.Flag2Activity \
  -a io.hextree.action.GIVE_FLAG

# action과 data URI 전달
adb shell am start \
  -n io.hextree.attacksurface/.activities.Flag3Activity \
  -a android.intent.action.VIEW \
  -d 'https://app.hextree.io/map/android'
```

명시적 Intent는 대상 component를 바로 고르므로 Manifest의 exported 설정이 첫 번째 경계다. 그 뒤에는 action, data, category, extra가 실제 권한 검증을 대신하고 있지 않은지 확인해야 한다.

### 5.2 Intent redirect와 nested Intent

공개 Activity가 외부에서 받은 `Intent` 객체를 다시 `startActivity()`에 전달하면, 공격자는 그 Activity를 대리자로 사용해 원래 외부에서 열 수 없던 내부 Activity로 이동할 수 있다.

```java
Intent outer = new Intent();
Intent inner = new Intent();

inner.setClassName(
    "io.hextree.attacksurface",
    "io.hextree.attacksurface.activities.Flag6Activity"
);
outer.putExtra("android.intent.extra.INTENT", inner);
```

방어할 때는 nested Intent를 그대로 실행하지 말고 허용된 component와 action을 명시적으로 검증해야 한다. 내부 화면에서도 세션과 권한을 다시 확인해야 한다.

### 5.3 implicit Intent hijacking

암시적인 Intent는 수신 앱을 고정하지 않는다. 민감 정보를 extra에 넣어 보내면 동일한 intent filter를 등록한 공격 앱이 데이터를 받을 수 있다. `startActivityForResult()`를 사용한다면 공격 앱이 조작된 결과까지 돌려줄 수 있다.

민감 데이터가 포함된 앱 간 통신은 explicit Intent, package 제한, signature permission을 우선 사용한다.

## 6. Deep Link와 브라우저 진입점

custom scheme은 여러 앱이 같은 scheme을 등록할 수 있어 소유권을 보장하지 않는다. 또한 category나 `com.android.browser.application_id` 같은 extra는 호출자가 직접 만들 수 있으므로 브라우저에서 왔다는 증거로 볼 수 없다.

```bash
adb shell am start \
  -a android.intent.action.VIEW \
  -c android.intent.category.BROWSABLE \
  -d 'hex://flag?action=give-me' \
  --es com.android.browser.application_id test
```

Chrome의 `intent:` URI는 action, category, package, extra를 브라우저 링크 안에 구성할 수 있다.

```text
intent:#Intent;
package=io.hextree.attacksurface;
action=io.hextree.action.GIVE_FLAG;
category=android.intent.category.BROWSABLE;
S.action=flag;
B.flag=true;
end
```

로그인 callback이라면 HTTPS App Link와 `assetlinks.json`, state/nonce, redirect 대상 검증을 결합해야 한다. callback의 `type=admin` 같은 클라이언트 입력으로 권한을 결정하면 안 된다.

## 7. Broadcast Receiver

exported Receiver가 별도 permission 없이 extra만 확인하면 외부 앱이 동일 broadcast를 만들어 상태를 변경할 수 있다.

```bash
adb shell am broadcast \
  -n io.hextree.attacksurface/.receivers.Flag16Receiver \
  --es flag give-flag-16
```

Ordered broadcast에서는 높은 priority의 공격 Receiver가 먼저 메시지를 읽고 `setResult()`로 결과를 변조할 수 있다. 동적 Receiver도 등록 시 `RECEIVER_EXPORTED` 여부와 수신 permission을 명시해야 한다.

방어 원칙은 다음과 같다.

- 앱 내부 이벤트는 가능한 한 exported 하지 않는다.
- 외부 수신이 필요하면 signature permission을 적용한다.
- action 문자열뿐 아니라 발신자와 데이터의 유효성을 검증한다.
- 민감값을 implicit/ordered broadcast에 싣지 않는다.

## 8. Android Service와 Binder/AIDL

### 8.1 Started Service

exported Service가 `onStartCommand()`의 Intent extra를 그대로 작업 명령으로 쓰면 다른 앱이 대상 앱의 권한 맥락에서 기능을 실행할 수 있다.

```bash
adb shell am startservice \
  -n io.hextree.attacksurface/.services.Flag24Service \
  --es action start
```

서비스를 여러 번 시작하는 상태 머신이라면 호출 순서와 상태 전이도 공격 입력이 된다.

### 8.2 Bound Service와 AIDL

Bound Service는 `IBinder`를 통해 호출 가능한 API를 노출한다. Messenger의 `Message.what`, `replyTo`, Bundle과 AIDL method는 모두 외부 입력이다.

![AIDL Service ClassLoader 실습](/assets/img/hextree-android-track/04-aidl-classloader.png)
_대상 앱의 AIDL Stub class를 동적으로 불러와 `openFlag()`를 호출하는 예제._

```java
ClassLoader loader = getForeignClassLoader(
    this, "io.hextree.attacksurface"
);
Class<?> iface = loader.loadClass(
    "io.hextree.attacksurface.services.IFlag28Interface"
);

// Stub.asInterface(IBinder) → remote interface
// remote openFlag() 호출
```

서비스가 공개되어야 한다면 manifest permission만 보지 말고 각 Binder method에서 caller UID와 세션 권한을 확인해야 한다.

## 9. ContentProvider와 FileProvider

### 9.1 ContentProvider SQL injection

Provider의 `projection`, `selection`, `sortOrder`도 SQL 입력이다. caller가 전달한 문자열을 그대로 SQLite 쿼리에 넣으면 로컬 DB에서도 SQL injection이 발생한다.

```bash
adb shell content query \
  --uri content://io.hextree.flag32/flags \
  --where '1=1) OR 1=1--'
```

경로별 최소 권한, parameter binding, projection allowlist가 필요하다.

### 9.2 Temporary URI permission

비공개 Provider라도 exported Activity가 result Intent에 `FLAG_GRANT_READ_URI_PERMISSION`을 붙여 반환하면 호출 앱이 임시 read grant를 얻는다. URI grant는 데이터를 직접 주는 것과 같은 권한 위임이다.

### 9.3 FileProvider path와 파일명 신뢰

![악성 FileProvider 구현 실습](/assets/img/hextree-android-track/05-fileprovider-attack.png)
_`DISPLAY_NAME`에 경로 이동 문자열을 돌려주는 악성 Provider 예제._

공격 Provider는 `OpenableColumns.DISPLAY_NAME`에 다음 값을 반환한다.

```java
cursor.addRow(new Object[]{
    "../../../filename.txt",
    12345
});
```

수신 앱이 Provider가 알려 준 파일명을 검증하지 않고 로컬 경로에 붙이면 path traversal로 이어진다. 반대로 FileProvider에서 `<root-path path="." />`처럼 너무 넓은 root를 공유하면 URI 조작으로 private file까지 노출할 수 있다.

- 공유 root는 필요한 하위 디렉터리로 최소화한다.
- read/write grant를 용도에 따라 분리한다.
- 파일명은 basename으로 정규화하고 구분자와 `..`을 거부한다.
- 반환된 URI의 authority와 MIME type을 검증한다.

## 10. WebView와 Custom Tabs

### 10.1 `@JavascriptInterface`

`addJavascriptInterface()`는 웹 콘텐츠와 앱의 Java/Kotlin 코드를 연결한다. 신뢰하지 않는 문서가 같은 WebView에 로드되면 JavaScript가 annotation이 붙은 native method를 호출할 수 있다.

![WebView JavaScript Interface 실습](/assets/img/hextree-android-track/06-webview-javascript-interface.png)
_JavaScript bridge 등록과 호출 흐름을 확인한 실습._

```java
class MyNativeBridge {
    @JavascriptInterface
    public void init(String msg) { /* ... */ }

    @JavascriptInterface
    public String getData() { return db.getData(); }
}

webView.addJavascriptInterface(new MyNativeBridge(), "app");
webView.loadUrl(url);
```

웹에서는 다음처럼 호출한다.

```html
<script>
window.app.init("Hello");
</script>
```

Flag 38 유형에서는 exported Activity가 외부의 `URL` extra를 그대로 `loadUrl()`에 전달하고 `hextree.success(true)` bridge를 노출했다. `data:` URL로 JavaScript를 넣으면 secret을 직접 몰라도 앱이 내부 성공 로직을 실행한다.

### 10.2 WebView XSS와 file access

Flag 39 유형은 외부 `NAME` 값을 HTML의 `innerHTML`에 넣어 XSS가 발생했고, XSS가 다시 native bridge 호출로 이어졌다.

```html
<img src=x onerror="hextree.success()">
```

Flag 40 유형은 다음 설정의 조합이 문제였다.

```java
settings.setJavaScriptEnabled(true);
settings.setAllowFileAccess(true);
settings.setAllowFileAccessFromFileURLs(true);
settings.setAllowUniversalAccessFromFileURLs(true);
```

공격 JavaScript가 `file://` origin에서 앱 private directory의 `token.txt`를 읽고 값을 bridge callback에 넘길 수 있었다. 로컬 콘텐츠는 `WebViewAssetLoader`를 사용하고, 외부 입력 URL과 `file://` 로딩을 허용하지 않는 것이 안전하다.

### 10.3 Custom Tabs `postMessage`

Custom Tabs는 WebView보다 브라우저 프로세스에 격리되지만, 앱이 공격자 제어 URL과 message channel을 만들고 origin을 검증하지 않으면 악성 페이지가 JSON을 돌려 앱 로직을 속일 수 있다.

## 11. Frida 동적 계측

정적 분석으로 class와 method signature를 찾은 뒤 Frida에서 같은 경로를 호출했다.

![Frida Java.perform 실습](/assets/img/hextree-android-track/03-frida-java-perform.png)
_JADX 분석과 `Java.perform()`을 결합해 static/instance method를 호출한 실습._

```javascript
Java.perform(function () {
  const FlagClass = Java.use('io.hextree.fridatarget.FlagClass');

  console.log(FlagClass.flagFromStaticMethod());

  const instance = FlagClass.$new();
  console.log(instance.flagFromInstanceMethod());
  console.log(instance.flagIfYouCallMeWithSesame('sesame'));
});
```

정적 분석은 어떤 class와 argument가 필요한지 알려 주고, 동적 계측은 실제 runtime 객체와 호출 결과를 확인한다. 두 방법은 서로 대체하지 않고 결합할 때 가장 효율적이었다.

## 12. 저장소와 권한

### 12.1 저장소

`MODE_PRIVATE`은 다른 일반 UID의 직접 접근을 제한하지만 암호화 기능은 아니다. debug build의 `run-as`, root, backup, 동일 프로세스 코드 실행이 가능한 상황에서는 평문 SharedPreferences와 SQLite가 그대로 노출된다.

```bash
adb shell run-as TARGET_PACKAGE \
  cat shared_prefs/settings.xml

adb shell run-as TARGET_PACKAGE \
  sqlite3 databases/app.db '.tables'
```

cache에는 장기 token을 남기지 않고, 민감 정보가 꼭 필요하면 Android Keystore와 짧은 수명 정책을 함께 사용해야 한다. external/shared storage는 비밀 저장소로 보지 않는다.

### 12.2 권한

Manifest에서는 component별 `exported`, `permission`, custom permission의 `protectionLevel`을 함께 확인했다.

```bash
adb shell dumpsys package TARGET_PACKAGE
adb shell pm list permissions -g -d
adb shell pm check-permission PERMISSION TARGET_PACKAGE
```

권한을 가진 앱이 외부 입력을 받아 대신 민감 작업을 수행하면 confused deputy가 된다. permission check는 진입 시점뿐 아니라 중요한 작업 직전에 다시 수행한다.

## 13. Network Interception과 Zip Path Traversal

패킷 캡처와 proxy를 이용해 앱이 내려받는 HTTP 응답을 관찰하고 변조했다.

```bash
adb shell tcpdump -i any -s 0 -w /sdcard/capture.pcap
adb pull /sdcard/capture.pcap
```

PocketHexMap 사례에서는 앱이 내려받은 archive entry 이름을 안전한 경로로 정규화하지 않고 압축 해제하는 흐름을 분석했다. 공격 응답의 archive에 `../` entry를 넣으면 의도한 디렉터리 밖에 파일을 쓸 수 있다.

안전한 압축 해제는 각 entry의 canonical path가 허용 root 안에 남는지 확인해야 하며, absolute path와 symbolic link도 함께 제한해야 한다.

## 14. Bluetooth Reverse Engineering

BLE 분석에서는 Manifest 권한, Android Bluetooth API, GATT service와 characteristic UUID, read/write/notify 흐름을 연결했다.

```text
앱 코드의 UUID 상수
  → BluetoothGattService
  → BluetoothGattCharacteristic
  → read / write / notification callback
  → 실제 명령 payload와 응답 의미
```

중요 명령이 characteristic write 한 번으로 실행된다면 replay와 위조 가능성을 검토해야 한다. BLE 연결이나 UUID를 아는 것만으로 사용자를 인증했다고 판단하면 안 된다.

## 15. Bug Bounty 보고서로 정리하는 법

```markdown
### 제목
외부 앱에서 exported Activity를 통해 인증 없이 내부 기능 실행 가능

### 요약
공개 Activity가 공격자가 전달한 Intent extra를 신뢰해 민감 기능을 실행한다.

### 환경
- 앱 버전 / package
- Android 버전
- 영향받는 component

### 재현 절차
1. 대상 앱 설치
2. 공격 앱 또는 ADB에서 crafted Intent 전송
3. 인증 없는 내부 기능 실행 확인

### 영향
민감 정보 접근, 권한 우회, 파일 읽기·쓰기, 계정 기능 실행

### 수정 방안
- 불필요한 component는 exported=false
- signature permission과 caller 검증
- Intent/URI/파일명 allowlist
- 내부 기능에서 인증·인가 재검증
```

## 16. 결론

14개 과정 전부 Android component가 연결되는 지점마다 신뢰 경계가 생긴다는 것이었다.

1. exported component는 공격 가능한 API처럼 다뤄야 한다.
2. Intent의 action, category, URI, extra는 공격자가 만들 수 있다.
3. Binder/AIDL, broadcast, Provider도 method와 argument 단위의 권한 검증이 필요하다.
4. FileProvider와 WebView는 설정 하나보다 여러 기능의 조합에서 더 큰 문제가 발생한다.
5. 내부 저장소는 접근 제어이지 자동 암호화가 아니다.
6. Frida는 클라이언트의 검사와 비밀을 절대적인 보안 경계로 삼을 수 없음을 보여 준다.

Android 플랫폼이 여러 보호 장치를 제공하더라도 앱의 잘못된 신뢰 판단까지 자동으로 고쳐 주지는 않기에 앱을 분석할 때는 화면 단위가 아니라 **Manifest 진입점 → IPC 입력 → 내부 동작 → 데이터와 권한의 영향**을 하나의 흐름으로 추적하는 방향이 좋을듯하다.

## 참고 자료

- [HexTree Android Map](https://app.hextree.io/map/android)
- [Android Developers: App components](https://developer.android.com/guide/components/fundamentals)
- [Android Developers: Intents and intent filters](https://developer.android.com/guide/components/intents-filters)
- [Android Developers: Services](https://developer.android.com/develop/background-work/services)
- [Android Developers: Broadcasts](https://developer.android.com/develop/background-work/background-tasks/broadcasts)
- [Android Developers: Content providers](https://developer.android.com/guide/topics/providers/content-providers)
- [Android Developers: FileProvider](https://developer.android.com/reference/androidx/core/content/FileProvider)
- [Android Developers: WebView native bridges](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges)
- [OWASP Mobile Application Security Testing Guide](https://mas.owasp.org/MASTG/)
- [Frida JavaScript API](https://frida.re/docs/javascript-api/)
