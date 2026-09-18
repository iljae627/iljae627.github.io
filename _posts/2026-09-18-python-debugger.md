---
title: "[Mission #61] sys.settrace로 나만의 Python 디버거 만들기"
date: 2026-09-18 00:20:00 +0900
categories: [개발, Python]
tags: [python, debugger, sys-settrace, frame, tracing, debugging-book, mission61]
---

## 1. 미션을 시작하며

평소 디버거의 `step`, `next`, 중단점을 당연하게 사용했지만, 프로그램이 **지금 어느 줄을 실행하는지 어떻게 아는가**는 깊게 생각하지 않았다. 이번에는 The Debugging Book의 *Introduction to Debugging*, *Tracing Executions*, *How Debuggers Work*를 읽고 Python 표준 라이브러리만으로 작은 대화형 디버거를 만들었다.

과제의 기준은 *How Debuggers Work* Exercise 2까지다. 따라서 줄 중단점뿐 아니라 함수명 중단점, `next`, 호출 스택, `up/down`, `until`, `finish`, 감시점을 모두 구현했다. 여기에 실제 사용 중 지난 정지 위치를 잊기 쉬웠던 점을 보완하려고 `history`, 예외를 바로 잡기 위한 `exceptions`를 추가했다.

![VS Code에서 디버거 핵심 코드를 구현한 화면](/assets/img/python-debugger/01-source-code.png)
_`sys.settrace()`가 전달한 frame과 event를 정지 조건으로 연결하는 부분._

완성 파일은 아래에서 바로 받을 수 있다.

- [my_debugger.py](/assets/files/python-debugger/my_debugger.py)
- [test_debugger.py](/assets/files/python-debugger/test_debugger.py)
- [사용 매뉴얼](/assets/files/python-debugger/MANUAL.md)

## 2. 먼저 이해한 디버깅 방식

Introduction 챕터에서 가장 기억에 남은 것은 디버깅을 무작정 코드 수정으로 시작하지 않는다는 점이다. 실패를 재현하고, 관찰 가능한 사실과 가설을 분리하며, 한 번의 실험으로 가설 하나를 좁힌다. `print()`도 관찰 도구지만 보고 싶은 지점을 미리 코드에 넣어야 한다. 디버거는 실행을 잠시 멈춘 뒤 그 순간에 필요한 상태를 골라 볼 수 있다.

Tracing 챕터의 핵심은 Python이 trace 함수를 호출해 준다는 사실이었다.

```python
sys.settrace(trace_function)
```

trace 함수는 대략 다음 정보를 받는다.

| 값 | 의미 |
|---|---|
| `frame` | 실행 중인 프레임. 코드·현재 줄·지역/전역 변수·호출자 참조를 가짐 |
| `event` | `call`, `line`, `return`, `exception` 등 실행 사건 |
| `arg` | 반환값이나 예외 튜플처럼 이벤트에 딸린 값 |

흐름을 단순화하면 다음과 같다.

```text
대상 코드 실행
    ↓
CPython이 trace(frame, event, arg) 호출
    ↓
정지 조건 검사 ── 아니오 ──> 계속 실행
    │
   예
    ↓
현재 소스/변수 표시 → 명령 입력 → 실행 모드 변경
```

중단점은 프로그램을 특별한 방식으로 정지시키는 마법이 아니었다. 매 trace 이벤트마다 `frame.f_lineno`가 중단점 집합에 있는지 검사해 참일 때 입력 루프로 들어가는 구조였다.

## 3. 구현 전에 정한 추가 명령

미션 지시에 따라 코드를 붙이기 전에 추가 기능의 인터페이스부터 정했다.

| 명령 | 사용법 | 미리 정한 동작 |
|---|---|---|
| `history` | `history [COUNT]` | 최근 정지한 이벤트·함수·파일·줄을 기본 10개 출력 |
| `exceptions` | `exceptions on\|off` | `exception` 이벤트를 만났을 때 즉시 멈출지 전환 |

`history`는 실행을 바꾸지 않는 관찰 명령이고, `exceptions`는 정지 조건 하나를 켜고 끄는 명령이다. 기존 구조에 억지로 예외 처리를 섞지 않고 각각 `deque`와 불리언 상태로 표현할 수 있어 작은 디버거에 잘 맞았다.

## 4. 디버거의 기본 뼈대

컨텍스트 매니저로 추적의 시작과 끝을 묶었다.

```python
def __enter__(self):
    self._active = True
    self._mode = "step"
    sys.settrace(self._trace)
    return self

def __exit__(self, exc_type, exc, tb):
    sys.settrace(None)
    self._active = False
    return False
```

`__exit__()`이 `False`를 반환하므로 대상 프로그램의 예외를 디버거가 삼키지 않는다. 추적 중 예외를 관찰할 수는 있어도 원래 실행 의미는 바꾸지 않기 위해서다.

trace 함수 안에서는 첫 사용자 호출을 root frame으로 잡고 그 아래 호출만 추적했다. 디버거 명령 자체까지 추적하면 `print` 명령을 처리하는 코드가 다시 디버거를 호출하는 재귀가 생긴다. 그래서 `Debugger` 메서드의 코드 객체를 미리 모아 내부 프레임을 제외했다.

```python
if frame.f_code in self._internal_codes:
    return self._trace

if not self._is_descendant(frame, self._root_frame):
    return self._trace
```

## 5. `frame`에서 알 수 있는 것

이번 구현에서 사용한 frame 속성은 다음과 같다.

- `f_code.co_name`: 현재 함수 이름
- `f_code.co_filename`: 소스 파일 경로
- `f_lineno`: 현재 줄 번호
- `f_locals`: 현재 지역 변수 사전
- `f_globals`: 전역 이름 공간
- `f_back`: 호출자 프레임

`print prices`는 아래처럼 대상 프레임의 문맥에서 식을 평가한다.

```python
value = eval(expression, frame.f_globals, frame.f_locals)
```

편리하지만 보안 경계는 아니다. 입력한 Python 식이 실행될 수 있으므로 본인이 제어하는 로컬 디버깅 세션에서만 사용해야 한다.

![변수 출력과 감시점을 사용한 실제 실행 기록](/assets/img/python-debugger/02-watch-session.png)
_`total`이 0에서 12000으로 바뀌는 순간 감시점이 실행을 멈췄다._

## 6. step과 next는 무엇이 다른가

`step`은 다음 `call`, `line`, `return`, `exception` 이벤트에서 멈춘다. 현재 줄이 함수를 호출하면 새 함수의 `call` 이벤트로 들어간다.

`next`는 명령을 내린 프레임을 기억한다.

```python
self._next_frame = self._stop_frame
self._mode = "next"
```

그 아래 함수의 이벤트는 계속 전달되지만 정지 조건은 `frame is self._next_frame`인 `line` 또는 `return`만 통과한다. 즉 호출된 함수를 실제로 생략하는 것이 아니라 **실행하되 그 내부에서 멈추지 않는 것**이다.

`finish`도 같은 생각이다. 현재 frame의 `return` 이벤트까지 기다린다. `until`은 같은 frame에서 줄 번호가 목표보다 커졌는지를 검사한다. 이런 명령은 모두 실행을 조종하는 별도 API가 아니라 trace 이벤트를 무시하다가 원하는 조건에서 다시 상호작용하는 방식이었다.

## 7. 함수명 중단점과 호출 스택

줄 중단점은 `(절대 파일 경로, 줄 번호)` 튜플로 저장했다. 줄 번호만 저장하면 다른 파일의 같은 줄에서 잘못 멈출 수 있기 때문이다.

함수명 중단점은 `call` 이벤트와 `frame.f_code.co_name`을 비교한다.

```python
if event == "call" and frame.f_code.co_name in self.function_breakpoints:
    return True
```

`where`는 현재 frame부터 `f_back`을 따라 root frame까지 올라간다. 가장 안쪽을 `#0`으로 보여 주고, `up/down`은 이 목록에서 선택한 인덱스만 바꾼다. 선택 프레임에서는 호출자의 지역 변수를 볼 수 있지만 `next`, `finish` 같은 실행 제어는 실제 정지 프레임을 기준으로 했다. 관찰 위치와 실행 위치를 섞으면 엉뚱한 함수의 반환을 기다리는 버그가 생기기 때문이다.

## 8. watchpoint 구현

감시점은 표현식과 직전 값을 사전에 저장한다. 매 이벤트마다 현재 frame에서 다시 평가하고 값이 달라지면 정지한다.

```python
new_value = eval(expression, frame.f_globals, frame.f_locals)
if old_value is not MISSING and new_value != old_value:
    changes.append((expression, old_value, new_value))
```

변수가 아직 만들어지지 않은 시점은 `_MISSING` sentinel로 구분했다. `None`은 정상적인 변수 값일 수 있어서 “없음” 표시로 사용할 수 없다. 이것은 Python에서 고유한 `object()`를 sentinel로 쓰는 전형적인 패턴이다.

다만 리스트 자체를 제자리 수정하면 이전 값과 현재 값이 같은 객체일 수 있다. 그 경우 `watch len(items)`나 `watch tuple(items)`처럼 관찰할 상태를 값으로 만드는 편이 안전하다. 교육용 구현의 범위와 한계도 매뉴얼에 기록했다.

## 9. 명령 디스패치와 Python 문법

명령은 `do_명령어` 메서드 이름으로 연결했다.

```python
method = getattr(self, f"do_{command}", None)
if method is not None:
    method(argument)
```

여기서 배운 문법과 기법은 다음과 같다.

- 컨텍스트 매니저 `__enter__`, `__exit__`
- 타입 힌트의 `FrameType`, `TracebackType`, `Callable`
- 상태 묶음에 `@dataclass(frozen=True)` 사용
- 최근 N개 보관에 `deque(maxlen=N)` 사용
- 코드 객체를 집합에 넣어 내부 함수 판별
- `getattr()`로 문자열과 메서드 연결
- `shlex.split()`로 따옴표가 있는 명령 인자 처리
- `linecache.getline()`으로 실행 중인 소스 한 줄 읽기

`help`도 별도 표를 하드코딩하지 않고 `do_`로 시작하는 메서드와 docstring에서 생성한다. 새 명령을 추가하면 도움말 목록에 자동으로 나타난다.

## 10. 실제 사용

```python
from my_debugger import Debugger

with Debugger():
    result = calculate_discount([12000, 8000, 5000], 0.2)
```

실행 후 다음처럼 조사했다.

```text
(pydbg) print prices
prices = [12000, 8000, 5000]
(pydbg) step
(pydbg) watch total
감시점 설정: total
(pydbg) continue
Watchpoint 'total': 0 -> 12000
(pydbg) print total
total = 12000
(pydbg) history
```

![추가 기능 history로 정지 이력을 확인한 화면](/assets/img/python-debugger/03-history.png)
_call부터 line 이벤트까지 최근 정지 위치가 순서대로 남는다._

모든 명령과 주의점은 별도의 [사용 매뉴얼](/assets/files/python-debugger/MANUAL.md)에 정리했다.

## 11. 자동 테스트

대화형 프로그램은 손으로만 시험하면 기능을 추가할 때 이전 명령이 깨지기 쉽다. 입력 함수와 출력 스트림을 생성자에서 받도록 만들어 명령 목록을 주입하고 결과를 `StringIO`로 검사했다.

```bash
python -m unittest -v test_debugger.py
```

![회귀 테스트 5개가 통과한 화면](/assets/img/python-debugger/04-tests.png)
_기본 결과, step/print/where, 함수 중단점, 감시점, history를 자동 검증했다._

테스트 결과는 5개 모두 통과했다. 별도로 `py_compile`도 실행해 두 파일의 문법 검사를 마쳤다.

## 12. 한계와 개선 방향

직접 만들어 보니 IDE 디버거가 해결한 범위가 훨씬 넓다는 것도 보였다.

1. `sys.settrace()`는 현재 스레드에 설정되므로 새 스레드는 별도 처리가 필요하다.
2. 비동기 태스크는 같은 스레드에서 frame이 교차해 사용자 경험을 더 설계해야 한다.
3. CPython의 `f_locals`는 일반 사전처럼 수정한다고 항상 실행 변수에 반영되지 않는다.
4. 모든 line 이벤트에서 watch 식을 평가하므로 무겁거나 부작용 있는 표현식은 피해야 한다.
5. 같은 이름의 함수가 여러 모듈에 있으면 함수명 중단점이 모두 반응한다. `module.function` 형식으로 확장할 수 있다.

이번 범위에서는 동작을 숨기기보다 이 한계를 매뉴얼에 적는 쪽을 택했다.

## 13. 마무리

디버거의 핵심은 “실행을 멈춘다”보다 **실행 이벤트를 계속 관찰하다가 조건에 맞는 이벤트에서 사용자에게 제어를 돌려준다**는 데 있었다. `step`, `next`, `finish`, 중단점, 감시점은 겉으로 서로 다른 기능이지만 결국 frame·event·상태를 조합한 정지 조건이었다.

작은 구현이지만 Exercise 2의 모든 명령을 실제로 연결하고, 추가 명령을 먼저 문서화한 뒤 구현하고, 자동 테스트와 매뉴얼까지 작성했다. 앞으로 디버거에서 한 줄을 넘길 때 그 뒤에서 어떤 frame과 event가 오가는지 훨씬 구체적으로 떠올릴 수 있을 것 같다.

### 참고 자료

- [The Debugging Book — Introduction to Debugging](https://www.debuggingbook.org/html/Intro_Debugging.html)
- [The Debugging Book — Tracing Executions](https://www.debuggingbook.org/html/Tracer.html)
- [The Debugging Book — How Debuggers Work](https://www.debuggingbook.org/html/Debugger.html)
- [Python 문서 — sys.settrace](https://docs.python.org/3/library/sys.html#sys.settrace)
- [Python 문서 — Frame objects](https://docs.python.org/3/reference/datamodel.html#frame-objects)
