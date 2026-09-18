# 나만의 Python 디버거 사용 매뉴얼

Mission #61의 결과물인 `my_debugger.py`는 Python 표준 라이브러리만 사용하는 교육용 라인 디버거다. Python 3.10 이상을 권장한다.

## 1. 시작하기

같은 폴더에서 다음과 같이 실행하면 예제 함수가 디버거 안에서 시작된다.

```bash
python my_debugger.py
```

다른 프로그램에서 사용할 때는 디버깅할 호출만 `with Debugger():`로 감싼다.

```python
from my_debugger import Debugger

with Debugger():
    result = my_function(10)
```

`(pydbg)` 프롬프트가 보이면 아래 명령어를 입력한다. `s`, `n`, `c`, `p`, `b`, `w`, `q`처럼 자주 쓰는 명령은 한 글자로 줄일 수 있다.

## 2. 명령어 빠른 참조

| 명령어 | 축약 | 사용법 | 동작 |
|---|---:|---|---|
| `help` |  | `help [COMMAND]` | 전체 명령 또는 한 명령의 도움말 |
| `step` | `s` | `step` | 다음 실행 이벤트로 이동. 호출한 함수 내부로 진입 |
| `next` | `n` | `next` | 호출 함수를 한 번에 실행하고 현재 프레임의 다음 줄에서 정지 |
| `continue` | `c` | `continue` | 다음 중단점·감시점까지 계속 실행 |
| `break` | `b` | `break LINE` | 현재 파일의 줄 중단점 설정 |
| `break` | `b` | `break FILE:LINE` | 지정 파일과 줄에 중단점 설정 |
| `break` | `b` | `break FUNCTION` | 이름이 같은 함수가 호출될 때 정지 |
| `delete` |  | `delete TARGET` | 줄·함수 중단점 또는 감시점 삭제 |
| `watch` |  | `watch EXPR` | 표현식 값이 변하는 순간 정지 |
| `print` | `p` | `print [EXPR]` | 표현식 또는 전체 지역 변수 출력 |
| `list` |  | `list [RADIUS]` | 현재 줄 주변 소스 출력 |
| `where` | `w` | `where` | 호출 스택 출력 |
| `up` |  | `up` | 호출자 프레임으로 이동하여 변수·소스 탐색 |
| `down` |  | `down` | 피호출자 프레임으로 이동 |
| `until` |  | `until [LINE]` | 현재 줄 또는 지정 줄보다 큰 줄까지 실행 |
| `finish` |  | `finish` | 현재 함수가 반환할 때 정지 |
| `history` |  | `history [COUNT]` | 최근 정지 이력 출력(추가 기능) |
| `exceptions` |  | `exceptions on\|off` | 예외 발생 즉시 정지 여부(추가 기능) |
| `quit` | `q` | `quit` | 디버거 종료 후 프로그램 계속 실행 |

## 3. 대표 사용 흐름

### 함수 중단점과 변수 확인

```text
(pydbg) break calculate_discount
함수 중단점 설정: calculate_discount
(pydbg) continue
calculate_discount() .../my_debugger.py:409
(pydbg) print prices
prices = [12000, 8000, 5000]
```

숫자만 주면 현재 파일의 줄 번호로 해석한다. 경로에 공백이 있다면 전체 `FILE:LINE` 인자를 따옴표로 감싼다.

### 감시점

```text
(pydbg) watch total
감시점 설정: total
(pydbg) continue
Watchpoint 'total': 0 -> 12000
```

감시 표현식에 아직 존재하지 않는 변수가 들어 있어도 바로 실패하지 않는다. 변수가 처음 평가된 뒤부터 값 변화를 비교한다. 가변 객체 내부를 제자리에서 바꾸는 경우 동일 객체 비교의 한계가 있으므로 `len(items)`처럼 관찰하고 싶은 값을 표현식으로 쓰는 편이 명확하다.

### 호출 스택 탐색

`where`의 `#0`은 실제로 멈춘 가장 안쪽 프레임이다. `up`으로 호출자 프레임을 선택한 뒤 `print`와 `list`를 사용할 수 있고, `down`으로 돌아온다. 실행 제어 명령은 실제 정지 프레임을 기준으로 한다.

### 반복문을 빠져나오기

`until`은 같은 프레임에서 현재 줄보다 큰 줄이 실행될 때까지 반복을 건너뛴다. `until 120`처럼 목표 줄을 직접 줄 수도 있다. 현재 함수 전체를 빠져나오려면 `finish`를 사용한다.

### 예외에서 멈추기

```text
(pydbg) exceptions on
예외 정지: on
(pydbg) continue
Exception ZeroDivisionError: division by zero
```

Python의 trace 함수는 처리되는 예외도 `exception` 이벤트로 보고한다. 따라서 `try/except`가 잡을 예외에서도 먼저 멈출 수 있다.

## 4. 종료와 주의점

- `quit`은 대상 프로그램을 강제 종료하지 않는다. tracing만 해제하고 프로그램은 계속 실행한다.
- 이 구현은 한 스레드의 `sys.settrace()`를 사용한다. 새 스레드는 기본적으로 추적하지 않는다.
- `print`, `watch`는 대상 프로그램의 전역·지역 이름 공간에서 `eval()`을 사용한다. 신뢰할 수 없는 디버거 명령을 대신 입력하면 안 된다.
- CPython 최적화와 프레임 구현 특성 때문에 `frame.f_locals`를 바꾸는 기능은 제공하지 않는다.
- 디버거 자체 코드는 코드 객체를 기준으로 필터링해 재귀 추적을 피한다.

## 5. 테스트

```bash
python -m unittest -v test_debugger.py
```

테스트는 기본 실행 결과, 변수 출력과 호출 스택, 함수명 중단점, 감시점, 정지 이력을 확인한다.

## 6. 파일 구성

- `my_debugger.py`: 디버거 구현과 실행 예제
- `test_debugger.py`: 자동 회귀 테스트
- `MANUAL.md`: 이 문서
- `LICENSE`: MIT 라이선스 전문

라이선스는 학습·개인 프로젝트 용도로 자유롭게 수정할 수 있도록 MIT 방식으로 제공한다.
