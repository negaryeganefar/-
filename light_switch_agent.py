# -*- coding: utf-8 -*-
"""
عامل واکنشی برای مسئله «سویچ نور» در محیط 2×2
================================================

مدل مسئله:
  * محیط: شبکه‌ی 2×2 (خانه‌ها با (ردیف، ستون) شماره‌گذاری می‌شوند).
  * هر خانه یک چراغ (روشن/خاموش) و یک سویچ دارد.
  * هدف عامل: خاموش کردن همه‌ی خانه‌های روشن.

دو قانون سویچ‌زنی (toggle mode):
  mode="self" : زدن سویچِ خانه، فقط همان خانه را عوض می‌کند.
  mode="plus" : زدن سویچِ خانه، خودش و همسایه‌های مستقیمش را عوض می‌کند
                (الگوی بازی Lights Out).

دو عامل:
  ReactiveAgent        -> قانون واکنشی ساده و بدون حافظه (برای mode="self")
  ChasingReactiveAgent -> عامل واکنشی با چند بیت حافظه (برای mode="plus")

اجرا:
  python light_switch_agent.py
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

try:  # نمایش درست متن فارسی در کنسول ویندوز
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

Coord = Tuple[int, int]


# ----------------------------------------------------------------------------
# محیط
# ----------------------------------------------------------------------------
class LightEnv2x2:
    """شبکه‌ی 2×2 با قانون سویچ‌زنی."""

    def __init__(self, initial: List[List[bool]], mode: str = "self") -> None:
        if mode not in ("self", "plus"):
            raise ValueError("mode باید 'self' یا 'plus' باشد")
        if len(initial) != 2 or any(len(row) != 2 for row in initial):
            raise ValueError("initial باید 2×2 باشد")
        self.mode = mode
        self.grid: List[List[bool]] = [row[:] for row in initial]
        self.presses = 0  # تعداد سویچ‌زنی‌ها

    # --- ادراک -------------------------------------------------------------
    def lit(self, r: int, c: int) -> bool:
        return self.grid[r][c]

    def all_off(self) -> bool:
        return not any(self.grid[r][c] for r in range(2) for c in range(2))

    def first_lit(self) -> Optional[Coord]:
        """اولین خانه‌ی روشن به ترتیب ردیف‌به‌ردیف."""
        for r in range(2):
            for c in range(2):
                if self.grid[r][c]:
                    return (r, c)
        return None

    # --- اقدام ------------------------------------------------------------
    def press(self, r: int, c: int) -> None:
        """زدن سویچ خانه‌ی (r, c)."""
        self.presses += 1
        if self.mode == "self":
            targets = [(r, c)]
        else:  # plus: خودش + همسایه‌های مستقیم
            targets = [(r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        for rr, cc in targets:
            if 0 <= rr < 2 and 0 <= cc < 2:
                self.grid[rr][cc] = not self.grid[rr][cc]

    # --- نمایش ------------------------------------------------------------
    def state(self) -> str:
        """وضعیت به صورت رشته‌ی 4 بیتی (ترتیب ردیف‌به‌ردیف)."""
        return "".join("1" if self.grid[r][c] else "0"
                       for r in range(2) for c in range(2))

    def render(self) -> str:
        return "\n".join(
            "".join("*" if self.grid[r][c] else "." for c in range(2))
            for r in range(2)
        )


# ----------------------------------------------------------------------------
# عامل 1: قانون واکنشی ساده (بدون حافظه)
# ----------------------------------------------------------------------------
class ReactiveAgent:
    """
    الگوریتم ساده:
      1) اگر همه خاموش‌اند            -> توقف
      2) اگر خانه‌ی من روشن است        -> سویچ آن را بزن
      3) وگرنه                         -> به اولین خانه‌ی روشن برو
    """

    name = "ReactiveAgent (ساده، بدون حافظه)"

    def __init__(self, env: LightEnv2x2) -> None:
        self.env = env
        self.r, self.c = 0, 0  # تنها وضعیت داخلی: جایگاه فعلی

    def step(self) -> str:
        env = self.env
        if env.all_off():                       # گام 1: آزمون هدف
            return "stop"
        first = env.first_lit()
        if first is None:
            return "stop"
        if env.lit(self.r, self.c):             # گام 2: قانون محلی
            env.press(self.r, self.c)
            return f"press ({self.r},{self.c})"
        self.r, self.c = first                  # گام 3: حرکت
        return f"move  ({self.r},{self.c})"

    def run(self, max_steps: int = 40, verbose: bool = True) -> bool:
        env = self.env
        for i in range(1, max_steps + 1):
            action = self.step()
            if verbose:
                print(f"  گام {i:>2}: {action:<13} state={env.state()}")
            if action == "stop":
                return env.all_off()
        return env.all_off()


# ----------------------------------------------------------------------------
# عامل 2: عامل واکنشیِ تعقیب‌کننده (چند بیت حافظه) برای قانون plus
# ----------------------------------------------------------------------------
class ChasingReactiveAgent:
    """
    الگوریتم مرحله‌ای با حافظه‌ی بسیار کوچک (ماشین حالت):
      row0  : اعمالِ ردِ آزمایشیِ سویچ‌های ردیف اول (00 تا 11)
      chase : تعقیب نور - اگر خانه‌ی (0,c) روشن بود، سویچ (1,c) را بزن
      check : اگر همه خاموش شدند -> پایان؛ وگرنه مرحله‌ی بعد
      undo  : واگردانی سویچ‌های همین رد (هر سویچ هم‌وروندی است) و رد بعدی
    """

    name = "ChasingReactiveAgent (تعقیب نور)"

    def __init__(self, env: LightEnv2x2) -> None:
        self.env = env
        self.trial = 0       # ردِ آزمایش برای سویچ‌های ردیف اول (0..3)
        self.row0 = 0        # سویچ‌های ردیف اول که الان زده شده‌اند
        self.row1 = 0        # سویچ‌های ردیف دومِ زده‌شده در این رد (برای واگردانی)
        self.chase = 0       # ستون در حال تعقیب (0، 1 یا 2=تمام)
        self.phase = "row0"  # row0 | chase | check | undo | stuck

    @staticmethod
    def _lowest(mask: int) -> int:
        """کم‌ترین بیت روشن ماسک."""
        return (mask & -mask).bit_length() - 1

    def step(self) -> str:
        env = self.env
        if env.all_off():
            return "stop"
        if self.phase == "stuck":
            return "stuck"

        if self.phase == "row0":
            if self.trial != self.row0:                 # سویچ‌های ردیف اول را هم‌تراز کن
                c = self._lowest(self.trial ^ self.row0)
                env.press(0, c)
                self.row0 ^= (1 << c)
                return f"press (0,{c})"
            self.phase, self.chase = "chase", 0
            return "chase start"

        if self.phase == "chase":
            if self.chase < 2:                          # ستون به ستون
                c = self.chase
                self.chase += 1
                if env.lit(0, c):                       # خانه‌ی بالایی روشن؟
                    env.press(1, c)                     # سویچ پایینی -> خانه‌ی بالا خاموش می‌شود
                    self.row1 ^= (1 << c)
                    return f"press (1,{c})"
                return f"check (0,{c}) off"
            self.phase = "check"
            return "check"

        if self.phase == "check":
            self.phase = "undo"                         # all_off در بالا بررسی شد؛ پس این رد شکست
            return "trial failed"

        # phase == "undo"
        if self.row1:
            c = self._lowest(self.row1)
            env.press(1, c)
            self.row1 ^= (1 << c)
            return f"undo press (1,{c})"
        if self.row0:
            c = self._lowest(self.row0)
            env.press(0, c)
            self.row0 ^= (1 << c)
            return f"undo press (0,{c})"
        self.trial += 1
        if self.trial > 3:
            self.phase = "stuck"
            return "no solution"
        self.phase = "row0"
        return f"next trial {self.trial}"

    def run(self, max_steps: int = 80) -> bool:
        env = self.env
        for i in range(1, max_steps + 1):
            action = self.step()
            print(f"  گام {i:>2}: {action:<14} state={env.state()}")
            if action in ("stop", "stuck"):
                return action == "stop"
        return env.all_off()


# ----------------------------------------------------------------------------
# اجرا و آزمون
# ----------------------------------------------------------------------------
def demo_simple() -> None:
    print("\n[1] عامل ساده با قانون self (سویچ فقط خانه‌ی خودش را عوض می‌کند)")
    print("-" * 70)
    env = LightEnv2x2([[True, True], [False, True]], mode="self")
    print("  وضعیت اولیه:\n" + "\n".join("  " + l for l in env.render().splitlines()))
    ok = ReactiveAgent(env).run()
    print("  نتيجه:", "همه خاموش شدند ✔" if ok else "به سقف گام رسيد ✘")


def demo_cycle() -> None:
    print("\n[2] همان عامل ساده، ولي با قانون plus (نشان‌دادن حلقه)")
    print("-" * 70)
    env = LightEnv2x2([[True, False], [False, False]], mode="plus")
    print("  وضعیت اولیه:\n" + "\n".join("  " + l for l in env.render().splitlines()))
    ok = ReactiveAgent(env).run(max_steps=12)
    print("  نتيجه:", "حلو شد ✔" if ok else "در حلقه گير كرد (اثبات نياز به حافظه) ✘")


def demo_chasing() -> None:
    print("\n[3] عامل تعقیب‌کننده با قانون plus")
    print("-" * 70)
    env = LightEnv2x2([[True, True], [False, True]], mode="plus")
    print("  وضعیت اولیه:\n" + "\n".join("  " + l for l in env.render().splitlines()))
    agent = ChasingReactiveAgent(env)
    ok = agent.run()
    print("  وضعیت نهایی:\n" + "\n".join("  " + l for l in env.render().splitlines()))
    print(f"  تعداد سویچ‌زنی: {env.presses}")
    print("  نتيجه:", "همه خاموش شدند ✔" if ok else "شکست ✘")


def test_all_states() -> None:
    print("\n[4] آزمون همه‌ی 16 وضعیت اولیه‌ی ممکن")
    print("-" * 70)
    total = solved_simple = solved_chase = 0
    worst = 0
    for mask in range(16):
        init = [[bool(mask & (1 << (r * 2 + c))) for c in range(2)] for r in range(2)]

        e1 = LightEnv2x2(init, mode="self")
        if ReactiveAgent(e1).run(max_steps=20, verbose=False):
            solved_simple += 1

        e2 = LightEnv2x2(init, mode="plus")
        agent = ChasingReactiveAgent(e2)
        # شمارش گام‌ها بدون چاپ
        steps = 0
        while steps < 80:
            steps += 1
            if agent.step() == "stop":
                break
        if e2.all_off():
            solved_chase += 1
            worst = max(worst, steps)
        total += 1
    print(f"  عامل ساده  (mode=self): {solved_simple}/{total} حل شد")
    print(f"  عامل تعقیب (mode=plus): {solved_chase}/{total} حل شد (بدترین حالت: {worst} گام)")


if __name__ == "__main__":
    demo_simple()
    demo_cycle()
    demo_chasing()
    test_all_states()
    print("\nپایان اجرا.")
