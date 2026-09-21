---
title: "[Mission #61] sys.settrace로 나만의 Python 디버거 만들기"
date: 2026-09-18 00:20:00 +0900
categories: [개발, Python]
tags: [python, debugger, sys-settrace, frame, tracing, debugging-book, mission61]
---

## 1. 시작하며

`print()`를 여러 군데 넣는 대신 실행 중인 줄에서 변수 값을 보고 싶었다. 이를 위해 [The Debugging Book](https://www.debuggingbook.org/)의 *Introduction to Debugging*, *Tracing Executions*, *How Debuggers Work*를 참고해 Python 표준 라이브러리만 쓰는 대화형 디버거를 만들었다.

목표는 *How Debuggers Work*의 Exercise 2다. 책에 나온 기본 명령에 함수명 중단점, `next`, `where`, `up/down`, `until`, `finish`, `watch`를 붙였다. 추가 명령으로는 정지 지점을 다시 보는 `history`와 예외 이벤트에서 멈추는 `exceptions`를 골랐다.

![VS Code에서 연 my_debugger.py의 trace 함수](/assets/img/python-debugger/01-vscode-trace.png)
_VS Code에서 `my_debugger.py`를 열어 본 화면. `_trace()`가 이벤트를 받아 정지 조건으로 넘긴다._

완성 파일은 아래에서 바로 받을 수 있다.

- [my_debugger.py](/assets/files/python-debugger/my_debugger.py)
- [test_debugger.py](/assets/files/python-debugger/test_debugger.py)
- [사용 매뉴얼](/assets/files/python-debugger/MANUAL.md)

## 2. `sys.settrace()`부터 확인

Introduction 챕터의 예제는 실패를 재현한 다음 가설을 하나씩 검증한다. 이 과정에서 보고 싶은 변수는 실행하다가 달라진다. 그래서 코드에 출력문을 미리 심는 방식만으로는 번거롭다.

Tracing 챕터에서 찾은 출발점은 `sys.settrace()`였다.

```python
sys.settrace(trace_function)
```

등록한 함수는 `frame`, `event`, `arg`를 받는다. `event`는 `call`, `line`, `return`, `exception` 등이고, `arg`에는 반환값이나 예외 정보가 실린다. `frame`에는 현재 줄 번호와 지역 변수, 호출자 프레임이 있다.

만든 디버거의 실행 흐름은 이렇다.

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

줄 중단점은 `frame.f_lineno`와 저장해 둔 파일·줄 번호를 비교한다. 같으면 `(pydbg)` 입력 루프로 들어간다. 별도의 기계어 패치를 하지 않아도 Python 수준에서 실행 위치를 관찰할 수 있었다.

## 3. 구현 전에 정한 추가 명령

Exercise 2 외에 넣을 기능은 구현 전에 명령어와 동작부터 정했다.

| 명령 | 사용법 | 미리 정한 동작 |
|---|---|---|
| `history` | `history [COUNT]` | 최근 정지한 이벤트·함수·파일·줄을 기본 10개 출력 |
| `exceptions` | `exceptions on\|off` | `exception` 이벤트를 만났을 때 즉시 멈출지 전환 |

`history`는 최근 정지 기록을 `deque(maxlen=30)`에 보관한다. `exceptions`는 불리언 값을 켜고 끄므로 기존 정지 조건에 한 줄을 추가할 수 있었다.

## 4. 추적을 시작하고 끝내기

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

처음에는 디버거 자신의 메서드까지 trace 대상이 되어 출력·명령 처리 흐름을 따라가게 되는 문제가 있었다. `Debugger` 메서드의 코드 객체를 모아 내부 프레임을 제외하고, 첫 대상 호출을 root frame으로 잡아 그 아래 호출만 관찰했다.

```python
if frame.f_code in self._internal_codes:
    return self._trace

if not self._is_descendant(frame, self._root_frame):
    return self._trace
```

## 5. `frame`에서 변수와 호출자 읽기

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

이 방식은 편하지만 `eval()`은 단순 조회 전용이 아니다. `print`나 `watch`에 입력한 식이 코드를 실행할 수도 있으므로 신뢰할 수 있는 로컬 세션에서만 사용해야 한다.

변수 값이 바뀌는 지점은 `watch total`로 확인했다. 실행 기록에서는 `total`이 `0 → 12000 → 20000 → 25000`으로 변했다. 아래 사진은 그 기록을 합성한 콘솔 화면이 아니라, 실제 VS Code에서 연 감시점 구현 코드다.

![VS Code에서 연 감시점 구현 코드](/assets/img/python-debugger/02-vscode-watch-code.png)
_값을 다시 평가해 이전 값과 비교하는 `_watch_changed()`._

## 6. step과 next는 무엇이 다른가

`step`은 다음 `call`, `line`, `return`, `exception` 이벤트에서 멈춘다. 현재 줄이 함수를 호출하면 새 함수의 `call` 이벤트로 들어간다.

`next`는 명령을 내린 프레임을 기억한다.

```python
self._next_frame = self._stop_frame
self._mode = "next"
```

그 아래 함수의 이벤트는 계속 전달되지만 정지 조건은 `frame is self._next_frame`인 `line` 또는 `return`만 통과한다. 즉 호출된 함수를 실제로 생략하는 것이 아니라 **실행하되 그 내부에서 멈추지 않는 것**이다.

`finish`는 현재 frame의 `return` 이벤트까지 기다린다. `until`은 같은 frame에서 목표보다 큰 줄 번호가 나올 때 멈춘다. 세 명령은 코드를 건너뛰는 게 아니라, 실행 중 들어오는 trace 이벤트 중 어느 것에서 다시 입력 루프를 열지 정하는 방식이다.

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
if old_value is not _MISSING and new_value != old_value:
    changes.append((expression, old_value, new_value))
```

변수가 아직 만들어지지 않은 시점은 `_MISSING = object()`로 구분했다. `None`도 정상적인 변수 값이어서 “아직 값 없음”의 대용으로 쓸 수 없었다.

다만 리스트 자체를 제자리 수정하면 이전 값과 현재 값이 같은 객체일 수 있다. 그 경우 `watch len(items)`나 `watch tuple(items)`처럼 관찰할 상태를 값으로 만드는 편이 안전하다. 교육용 구현의 범위와 한계도 매뉴얼에 기록했다.

## 9. 명령 추가 방식

명령은 `do_명령어` 메서드 이름으로 연결했다.

```python
method = getattr(self, f"do_{command}", None)
if method is not None:
    method(argument)
```

구현에 직접 쓰인 Python 문법·라이브러리는 다음과 같다.

- 컨텍스트 매니저 `__enter__`, `__exit__`
- 타입 힌트의 `FrameType`, `TracebackType`, `Callable`
- 상태 묶음에 `@dataclass(frozen=True)` 사용
- 최근 N개 보관에 `deque(maxlen=N)` 사용
- 코드 객체를 집합에 넣어 내부 함수 판별
- `getattr()`로 문자열과 메서드 연결
- `shlex.split()`로 따옴표가 있는 명령 인자 처리
- `linecache.getline()`으로 실행 중인 소스 한 줄 읽기

`help` 목록은 `do_` 메서드의 docstring에서 만든다. `history`와 `exceptions`를 추가할 때 도움말 표를 따로 고칠 필요가 없었다.

![VS Code에서 연 history와 exceptions 명령 구현](/assets/img/python-debugger/03-vscode-extra-commands.png)
_추가 명령의 구현. 최근 기록 출력과 예외 정지 설정을 각각 독립된 메서드로 넣었다._

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

`history`를 입력하면 직전의 `call`과 `line` 정지 위치를 시간순으로 볼 수 있다. 화면 재현 이미지를 붙이는 대신 사용한 명령과 실제 출력 형식을 위에 적었다.

모든 명령과 주의점은 별도의 [사용 매뉴얼](/assets/files/python-debugger/MANUAL.md)에 정리했다.

## 11. 자동 테스트

대화형 프로그램은 손으로만 시험하면 기능을 추가할 때 이전 명령이 깨지기 쉽다. 입력 함수와 출력 스트림을 생성자에서 받도록 만들어 명령 목록을 주입하고 결과를 `StringIO`로 검사했다.

```bash
python -m unittest -v test_debugger.py
```

![VS Code에서 연 디버거 회귀 테스트 코드](/assets/img/python-debugger/04-vscode-tests-code.png)
_`ScriptedInput`으로 명령을 넣고 `StringIO`의 출력에서 함수 중단점·감시점·이력을 검사했다._

실행 결과는 5개 모두 통과했다.

```text
Ran 5 tests in 0.004s
OK
```

별도로 `python -m py_compile my_debugger.py test_debugger.py`도 통과했다. 사진은 테스트 **결과 화면**이 아니라 테스트 **코드 화면**이고, 결과는 위 명령 출력에서 옮겼다.

## 12. 한계와 개선 방향

IDE 디버거와 비교하면 빠진 부분도 있다.

1. `sys.settrace()`는 현재 스레드에 설정되므로 새 스레드는 별도 처리가 필요하다.
2. 비동기 태스크는 같은 스레드에서 frame이 교차해 사용자 경험을 더 설계해야 한다.
3. CPython의 `f_locals`는 일반 사전처럼 수정한다고 항상 실행 변수에 반영되지 않는다.
4. 모든 line 이벤트에서 watch 식을 평가하므로 무겁거나 부작용 있는 표현식은 피해야 한다.
5. 같은 이름의 함수가 여러 모듈에 있으면 함수명 중단점이 모두 반응한다. `module.function` 형식으로 확장할 수 있다.

이 한계는 [매뉴얼](/assets/files/python-debugger/MANUAL.md)에도 적었다.

## 13. 마무리

가장 오래 들여다본 부분은 `step`과 `next`의 차이였다. 처음에는 `next`가 호출 함수를 실행하지 않는 것처럼 생각했지만, 실제로는 내부 이벤트를 지나치고 원래 frame의 다음 줄에서 다시 멈추는 것이었다. 줄 중단점, 감시점, `finish`도 같은 trace 이벤트 위에서 정지 조건만 달리한 기능이다.

Exercise 2 명령과 추가 명령을 구현하고 테스트까지 마쳤다. 다중 스레드와 `eval()`의 부작용은 남아 있으므로 범용 디버거라기보다 Python 실행 모델을 확인하기 위한 작은 도구로 보는 게 정확하다.

### 참고 자료

- [The Debugging Book — Introduction to Debugging](https://www.debuggingbook.org/html/Intro_Debugging.html)
- [The Debugging Book — Tracing Executions](https://www.debuggingbook.org/html/Tracer.html)
- [The Debugging Book — How Debuggers Work](https://www.debuggingbook.org/html/Debugger.html)
- [Python 문서 — sys.settrace](https://docs.python.org/3/library/sys.html#sys.settrace)
- [Python 문서 — Frame objects](https://docs.python.org/3/reference/datamodel.html#frame-objects)
