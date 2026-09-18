"""Regression tests for Mission #61 debugger."""

from __future__ import annotations

import io
import unittest
from collections.abc import Iterable

from my_debugger import Debugger, calculate_discount


class ScriptedInput:
    def __init__(self, commands: Iterable[str]) -> None:
        self.commands = iter(commands)

    def __call__(self, prompt: str) -> str:
        return next(self.commands, "continue")


class DebuggerTests(unittest.TestCase):
    def run_session(self, commands: list[str]) -> str:
        output = io.StringIO()
        with Debugger(stdin=ScriptedInput(commands), stdout=output):
            calculate_discount([100, 200], 0.1)
        return output.getvalue()

    def test_step_print_and_where(self) -> None:
        text = self.run_session(["print prices", "where", "step", "quit"])
        self.assertIn("prices = [100, 200]", text)
        self.assertIn("calculate_discount", text)

    def test_named_breakpoint(self) -> None:
        def checkout() -> int:
            return calculate_discount([100, 200], 0.1)

        output = io.StringIO()
        commands = ["break calculate_discount", "continue", "print rate", "quit"]
        with Debugger(stdin=ScriptedInput(commands), stdout=output):
            checkout()
        text = output.getvalue()
        self.assertIn("함수 중단점 설정: calculate_discount", text)
        self.assertIn("rate = 0.1", text)

    def test_watchpoint(self) -> None:
        text = self.run_session(["step", "watch total", "continue", "continue", "quit"])
        self.assertIn("감시점 설정: total", text)
        self.assertIn("Watchpoint 'total'", text)

    def test_history(self) -> None:
        text = self.run_session(["step", "history", "quit"])
        self.assertIn("call", text)
        self.assertIn("line", text)

    def test_target_result_unchanged(self) -> None:
        self.assertEqual(calculate_discount([12000, 8000, 5000], 0.2), 20000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
