---
title: "[CTF] 안드로이드 계산기 앱 로직 분석 및 트리거 추적 (Write-up)"
date: 2026-05-11 9:00:00 +0900
categories: [Information Security, Reversing]
tags: [android, apk, reversing, jadx, ctf-writeup]
---


## 1. Challenge Overview

![문제](/assets/img/cal_game/1.png)

문제에서 제공된 APK 파일은 표면적으로 일반적인 사칙연산 기능을 수행하는 계산기 앱입니다. 목표는 앱의 소스코드를 분석하여 숨겨진 입력값과 트리거 조건을 찾아 플래그를 획득하는 것입니다.


---


## 2. 정적 분석: 플래그 및 검증 로직 확인


JADX-GUI를 활용해 `com.ctf.calculator.core.stage.Stage1Validator` 클래스를 분석했습니다.


### 2.1 핵심 코드 분석


```java


// Stage1Validator.kt
public static final String FLAG = "FLAG{Arr4y_Hunt3r}";
private static final int EXPECTED_VALUE = 107;
private static final int[] SECRET_ARRAY = {99, 124, 119, 123, 242, EXPECTED_VALUE, 111, 197, 48, 1, 103, 43, 254, 215, 171, 118};

public final ValidationResult validate(String input) {
    Integer inputValue = StringsKt.toIntOrNull(input);
    // SECRET_ARRAY의 5번 인덱스 값인 107과 입력값을 비교
    if (inputValue.intValue() == SECRET_ARRAY[5]) { 
        return ValidationResult.Success.INSTANCE;
    }
    return new ValidationResult.Failure("틀렸습니다");
}


```


위 코드를 통해 최종 플래그가 `FLAG{Arr4y_Hunt3r}`임을 확인했고, 이를 획득하기 위한 입력값이 **`107`**이라는 사실을 파악했습니다.


---


## 3. 분석 병목 구간: 입력 지점 탐색 실패


분석 초기에는 계산기 메인 화면의 결과값이 `107`이 되도록 연산하거나(`100+7` 등), 단순히 `107`을 입력하는 방식으로 접근했으나 아무런 반응이 없었습니다. 


* **문제점**: `Stage1Validator.validate()` 메서드를 호출하는 UI 컴포넌트가 메인 계산기 로직과 분리되어 있음을 간과함.
* **분석 내용**: `MainActivity`가 아닌 별도의 다이얼로그나 프래그먼트에서 해당 검증 로직을 사용하고 있을 것으로 판단하고 UI 패키지를 전수 조사함.


![계산기 메인 화면 스크린샷](/assets/img/cal_game/2.png)
_단순히 107을 입력해도 플래그가 나타나지 않는 상태_


---


## 4. 제어 흐름 분석: 숨겨진 트리거 발견


`UnlockDialogFragment`를 호출하는 트리거를 찾기 위해 `com.ctf.calculator.ui.calculator.CalculatorViewModel` 클래스를 분석했습니다.


### 4.1 트리거 로직 분석


```kotlin


// CalculatorViewModel.kt
private static final String UNLOCK_CODE = "1337";

private final void checkUnlockCode() {
    // 실시간으로 입력되는 currentNumber가 "1337"과 일치하는지 감시
    if (Intrinsics.areEqual(this.currentNumber, UNLOCK_CODE)) {
        this._unlockTrigger.setValue(true); // Observer 패턴을 통해 Fragment에 알림
    }
}


```


분석 결과, 메인 계산기 화면에서 **`1337`**이라는 특정 시퀀스를 입력해야만 `UnlockDialogFragment`(비밀 입력창)가 호출되는 제어 흐름을 확인했습니다.


![ViewModel 트리거 분석](/assets/img/cal_game/3.png)
_트리거 번호 1337을 확인한 소스코드 캡처_


---


## 5. 최종 해결 과정 (Exploit Flow)


1.  **Stage 1 (Trigger)**: 앱 실행 후 메인 패드에서 **`1337`** 입력. `CalculatorViewModel`이 이를 감지하여 비밀 입력 다이얼로그 팝업.
2.  **Stage 2 (Validation)**: 활성화된 비밀 입력창에 아까 분석해둔 검증값 **`107`** 입력.
3.  **Stage 3 (Flag)**: `Stage1Validator`가 성공을 반환하며 하드코딩된 플래그 출력.


![플래그 출력 화면](/assets/img/cal_game/4.png)
_모든 트리거 조건을 만족하여 획득한 플래그 화면_


---


## 6. Takeaway


* **데이터와 로직의 분리**: 데이터(플래그)를 찾았더라도, 해당 데이터에 접근하기 위한 제어 흐름(Control Flow)을 파악하지 못하면 최종 해결이 불가능함을 체감함.
* **ViewModel 분석의 중요성**: 안드로이드 앱 리버싱 시 UI 이벤트 처리는 `ViewModel`에 집중되어 있으므로, `Activity`나 `Fragment`보다 먼저 분석하는 것이 효율적임.


**FINAL FLAG : `FLAG{Arr4y_Hunt3r}`**


---