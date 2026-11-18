"""Solve analysis: CFOP segmentation, OLL/PLL recognition, statistics."""

from .cases import OLL_ALGS, PLL_ALGS, CaseMatch, recognize_oll, recognize_pll
from .cfop import STEPS, CfopResult, StepRange, segment
from .stats import analyze, compute_stats, timed_segments

__all__ = [
    "OLL_ALGS",
    "PLL_ALGS",
    "STEPS",
    "CaseMatch",
    "CfopResult",
    "StepRange",
    "analyze",
    "compute_stats",
    "recognize_oll",
    "recognize_pll",
    "segment",
    "timed_segments",
]
