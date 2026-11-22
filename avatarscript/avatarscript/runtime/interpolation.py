"""Easing functions and deterministic scalar interpolation."""
import math
from typing import Callable

EasingFunc = Callable[[float], float]


def linear(t: float) -> float:
    return max(0.0, min(1.0, t))


def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 0.5 * (1.0 - math.cos(math.pi * t))


def elastic_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t == 0.0:
        return 0.0
    if t >= 0.9999:
        return 1.0
    p = 0.3
    return math.pow(2.0, -10.0 * t) * math.sin((t - p / 4.0) * (2.0 * math.pi) / p) + 1.0


EASING_FUNCTIONS: dict[str, EasingFunc] = {
    "linear": linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
    "elastic_out": elastic_out,
}


def apply_easing(progress: float, easing_name: str = "linear") -> float:
    func = EASING_FUNCTIONS.get(easing_name, linear)
    return func(progress)


def lerp(start: float, end: float, alpha: float) -> float:
    return start + (end - start) * alpha
