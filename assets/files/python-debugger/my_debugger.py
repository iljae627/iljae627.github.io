"""Mission #61: a small interactive Python debugger.

The implementation intentionally uses only the Python standard library.  Run
this file directly for a demo, or import ``Debugger`` and wrap a function call:

    with Debugger():
        your_function()
"""

from __future__ import annotations

import inspect
import linecache
import os
import shlex
import sys
from collections import deque
from dataclasses import dataclass
from types import FrameType, TracebackType
from typing import Any, Callable, TextIO


_MISSING = object()


@dataclass(frozen=True)
class StopRecord:
    """One place at which the debugger handed control to the user."""

    filename: str
    lineno: int
    function: str
    event: str


class Debugger:
    """A compact line debugger built on :func:`sys.settrace`."""

    def __init__(
        self,
        *,
        stdin: Callable[[str], str] = input,
        stdout: TextIO = sys.stdout,
    ) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.breakpoints: set[tuple[str, int]] = set()
        self.function_breakpoints: set[str] = set()
        self.watchpoints: dict[str, Any] = {}
        self.history: deque[StopRecord] = deque(maxlen=30)
        self.stop_on_exceptions = False

        self._mode = "step"
        self._active = False
        self._quitting = False
        self._root_frame: FrameType | None = None
        self._stop_frame: FrameType | None = None
        self._selected_frame: FrameType | None = None
        self._selected_index = 0
        self._next_frame: FrameType | None = None
        self._until_frame: FrameType | None = None
        self._until_line: int | None = None
        self._finish_frame: FrameType | None = None
        self._internal_codes = self._collect_internal_codes()

    def _collect_internal_codes(self) -> set[Any]:
        codes: set[Any] = set()
        for value in vars(type(self)).values():
            if inspect.isfunction(value):
                codes.add(value.__code__)
        return codes

    def __enter__(self) -> Debugger:
        self._active = True
        self._quitting = False
        self._mode = "step"
        sys.settrace(self._trace)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        sys.settrace(None)
        self._active = False
        return False

    def _trace(self, frame: FrameType, event: str, arg: Any):
        if not self._active or self._quitting:
            return None
        if frame.f_code in self._internal_codes:
            return self._trace

        if self._root_frame is None:
            if event != "call":
                return self._trace
            self._root_frame = frame

        if not self._is_descendant(frame, self._root_frame):
            return self._trace

        watch_changed = self._watch_changed(frame)
        if self._should_stop(frame, event, watch_changed):
            self._interact(frame, event, arg, watch_changed)

        if event == "return" and frame is self._root_frame:
            self._root_frame = None
        return self._trace

    @staticmethod
    def _is_descendant(frame: FrameType, root: FrameType) -> bool:
        current: FrameType | None = frame
        while current is not None:
            if current is root:
                return True
            current = current.f_back
        return False

    def _watch_changed(self, frame: FrameType) -> list[tuple[str, Any, Any]]:
        changes: list[tuple[str, Any, Any]] = []
        namespace = dict(frame.f_globals)
        namespace.update(frame.f_locals)
        for expression, old_value in list(self.watchpoints.items()):
            try:
                new_value = eval(expression, frame.f_globals, frame.f_locals)
            except Exception:
                new_value = _MISSING
            if old_value is _MISSING:
                self.watchpoints[expression] = new_value
            elif new_value is not _MISSING and new_value != old_value:
                changes.append((expression, old_value, new_value))
                self.watchpoints[expression] = new_value
        return changes

    def _should_stop(
        self,
        frame: FrameType,
        event: str,
        watch_changed: list[tuple[str, Any, Any]],
    ) -> bool:
        location = (os.path.abspath(frame.f_code.co_filename), frame.f_lineno)
        if watch_changed:
            return True
        if event == "exception" and self.stop_on_exceptions:
            return True
        if event == "call" and frame.f_code.co_name in self.function_breakpoints:
            return True
        if event == "line" and location in self.breakpoints:
            return True
        if self._mode == "step" and event in {"call", "line", "return", "exception"}:
            return True
        if self._mode == "next" and self._next_frame is frame and event in {"line", "return"}:
            return True
        if self._mode == "until" and self._until_frame is frame:
            if event == "return" or (event == "line" and frame.f_lineno > (self._until_line or 0)):
                return True
        if self._mode == "finish" and self._finish_frame is frame and event == "return":
            return True
        return False

    def _interact(
        self,
        frame: FrameType,
        event: str,
        arg: Any,
        watch_changed: list[tuple[str, Any, Any]],
    ) -> None:
        self._stop_frame = frame
        self._selected_frame = frame
        self._selected_index = 0
        self._mode = "paused"
        self.history.append(
            StopRecord(frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name, event)
        )

        for expression, old, new in watch_changed:
            self._write(f"Watchpoint {expression!r}: {old!r} -> {new!r}")
        if event == "exception":
            exc_type, exc_value, _ = arg
            self._write(f"Exception {exc_type.__name__}: {exc_value}")
        elif event == "return":
            self._write(f"Return value: {arg!r}")
        self._show_location(frame)

        while self._mode == "paused" and not self._quitting:
            try:
                raw = self.stdin("(pydbg) ")
            except (EOFError, StopIteration):
                raw = "continue"
            self.execute(raw)

    def execute(self, raw: str) -> None:
        """Parse and execute one debugger command."""
        try:
            parts = shlex.split(raw)
        except ValueError as error:
            self._write(f"명령어 해석 오류: {error}")
            return
        if not parts:
            return
        command, argument = parts[0].lower(), raw[len(parts[0]) :].strip()
        aliases = {"s": "step", "n": "next", "c": "continue", "p": "print", "b": "break", "q": "quit", "w": "where"}
        command = aliases.get(command, command)
        method = getattr(self, f"do_{command}", None)
        if method is None:
            self._write(f"알 수 없는 명령어: {command!r} (help로 목록 확인)")
            return
        method(argument)

    def do_help(self, argument: str) -> None:
        """help [COMMAND] - 명령어 목록 또는 상세 도움말."""
        commands = sorted(name[3:] for name in dir(self) if name.startswith("do_"))
        if argument:
            method = getattr(self, f"do_{argument}", None)
            self._write(method.__doc__ if method else f"없는 명령어: {argument}")
            return
        for name in commands:
            method = getattr(self, f"do_{name}")
            self._write(method.__doc__ or name)

    def do_step(self, argument: str) -> None:
        """step (s) - 호출 함수 안으로 들어가 다음 이벤트에서 정지."""
        self._mode = "step"

    def do_next(self, argument: str) -> None:
        """next (n) - 함수 호출을 건너뛰고 현재 프레임의 다음 줄에서 정지."""
        self._next_frame = self._stop_frame
        self._mode = "next"

    def do_continue(self, argument: str) -> None:
        """continue (c) - 다음 중단점/감시점까지 실행."""
        self._mode = "continue"

    def do_until(self, argument: str) -> None:
        """until [LINE] - 현재보다 큰 줄 또는 지정 줄 이후까지 실행."""
        assert self._stop_frame is not None
        try:
            target = int(argument) if argument else self._stop_frame.f_lineno
        except ValueError:
            self._write("사용법: until [LINE]")
            return
        self._until_frame = self._stop_frame
        self._until_line = target
        self._mode = "until"

    def do_finish(self, argument: str) -> None:
        """finish - 현재 함수가 반환할 때까지 실행."""
        self._finish_frame = self._stop_frame
        self._mode = "finish"

    def do_break(self, argument: str) -> None:
        """break (b) [LINE|FILE:LINE|FUNCTION] - 중단점 설정/목록."""
        if not argument:
            for filename, lineno in sorted(self.breakpoints):
                self._write(f"{filename}:{lineno}")
            for function in sorted(self.function_breakpoints):
                self._write(f"function {function}")
            return
        assert self._selected_frame is not None
        if argument.isdigit():
            item = (os.path.abspath(self._selected_frame.f_code.co_filename), int(argument))
            self.breakpoints.add(item)
            self._write(f"중단점 설정: {item[0]}:{item[1]}")
        elif ":" in argument and argument.rsplit(":", 1)[1].isdigit():
            filename, line_text = argument.rsplit(":", 1)
            item = (os.path.abspath(filename), int(line_text))
            self.breakpoints.add(item)
            self._write(f"중단점 설정: {item[0]}:{item[1]}")
        else:
            self.function_breakpoints.add(argument)
            self._write(f"함수 중단점 설정: {argument}")

    def do_delete(self, argument: str) -> None:
        """delete [LINE|FUNCTION|CONDITION] - 중단점/감시점 삭제(인자 없으면 전체)."""
        if not argument:
            self.breakpoints.clear()
            self.function_breakpoints.clear()
            self.watchpoints.clear()
            self._write("모든 중단점과 감시점을 삭제했습니다.")
            return
        assert self._selected_frame is not None
        if argument.isdigit():
            self.breakpoints.discard((os.path.abspath(self._selected_frame.f_code.co_filename), int(argument)))
        elif argument in self.function_breakpoints:
            self.function_breakpoints.discard(argument)
        elif argument in self.watchpoints:
            del self.watchpoints[argument]
        else:
            self._write(f"삭제할 항목을 찾지 못했습니다: {argument}")

    def do_watch(self, argument: str) -> None:
        """watch CONDITION - 표현식 값이 바뀌는 순간 정지."""
        if not argument:
            for expression, value in self.watchpoints.items():
                self._write(f"{expression} = {value!r}")
            return
        assert self._selected_frame is not None
        try:
            value = eval(argument, self._selected_frame.f_globals, self._selected_frame.f_locals)
        except Exception:
            value = _MISSING
        self.watchpoints[argument] = value
        self._write(f"감시점 설정: {argument}")

    def do_print(self, argument: str) -> None:
        """print (p) [EXPR] - 표현식 또는 현재 지역 변수를 출력."""
        assert self._selected_frame is not None
        if not argument:
            for name, value in sorted(self._selected_frame.f_locals.items()):
                self._write(f"{name} = {value!r}")
            return
        try:
            value = eval(argument, self._selected_frame.f_globals, self._selected_frame.f_locals)
            self._write(f"{argument} = {value!r}")
        except Exception as error:
            self._write(f"{type(error).__name__}: {error}")

    def do_list(self, argument: str) -> None:
        """list [RADIUS] - 현재 줄 주변 소스 출력."""
        assert self._selected_frame is not None
        try:
            radius = int(argument) if argument else 3
        except ValueError:
            self._write("사용법: list [RADIUS]")
            return
        current = self._selected_frame.f_lineno
        start, end = max(1, current - radius), current + radius
        for number in range(start, end + 1):
            source = linecache.getline(self._selected_frame.f_code.co_filename, number).rstrip()
            if source:
                marker = "->" if number == current else "  "
                self._write(f"{marker} {number:4} {source}")

    def _stack(self) -> list[FrameType]:
        frames: list[FrameType] = []
        current = self._stop_frame
        while current is not None and self._root_frame is not None:
            frames.append(current)
            if current is self._root_frame:
                break
            current = current.f_back
        return frames

    def do_where(self, argument: str) -> None:
        """where (w) - 현재 호출 스택 출력."""
        for index, frame in enumerate(self._stack()):
            marker = "->" if index == self._selected_index else "  "
            self._write(f"{marker} #{index} {frame.f_code.co_name} at {frame.f_code.co_filename}:{frame.f_lineno}")

    def do_up(self, argument: str) -> None:
        """up - 호출자 프레임으로 이동."""
        stack = self._stack()
        if self._selected_index + 1 >= len(stack):
            self._write("가장 위 프레임입니다.")
            return
        self._selected_index += 1
        self._selected_frame = stack[self._selected_index]
        self._show_location(self._selected_frame)

    def do_down(self, argument: str) -> None:
        """down - 피호출자 프레임으로 이동."""
        if self._selected_index == 0:
            self._write("가장 아래 프레임입니다.")
            return
        self._selected_index -= 1
        self._selected_frame = self._stack()[self._selected_index]
        self._show_location(self._selected_frame)

    def do_history(self, argument: str) -> None:
        """history [COUNT] - 최근 정지 지점 출력(추가 기능)."""
        try:
            count = int(argument) if argument else 10
        except ValueError:
            self._write("사용법: history [COUNT]")
            return
        for number, record in enumerate(list(self.history)[-count:], 1):
            self._write(f"{number:2}. {record.event:9} {record.function} {record.filename}:{record.lineno}")

    def do_exceptions(self, argument: str) -> None:
        """exceptions [on|off] - 예외 발생 시 정지 설정(추가 기능)."""
        value = argument.lower()
        if value in {"on", "1", "true"}:
            self.stop_on_exceptions = True
        elif value in {"off", "0", "false"}:
            self.stop_on_exceptions = False
        elif value:
            self._write("사용법: exceptions [on|off]")
            return
        self._write(f"예외 정지: {'on' if self.stop_on_exceptions else 'off'}")

    def do_quit(self, argument: str) -> None:
        """quit (q) - 디버깅을 종료하고 프로그램을 계속 실행."""
        self._quitting = True
        self._mode = "continue"
        sys.settrace(None)

    def _show_location(self, frame: FrameType) -> None:
        source = linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
        self._write(f"{frame.f_code.co_name}() {frame.f_code.co_filename}:{frame.f_lineno}")
        if source:
            self._write(f"    {source}")

    def _write(self, text: str) -> None:
        print(text, file=self.stdout)


def calculate_discount(prices: list[int], rate: float) -> int:
    """Small target program used by the manual and screenshots."""
    total = 0
    for price in prices:
        total += price
    discounted = int(total * (1 - rate))
    return discounted


def demo() -> None:
    with Debugger():
        result = calculate_discount([12000, 8000, 5000], 0.2)
    print(f"최종 결제 금액: {result:,}원")


if __name__ == "__main__":
    demo()
