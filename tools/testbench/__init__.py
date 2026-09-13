"""
Sony PMCA Cross-Model Static Verification Testbench
Automated multi-tier verification suite for Sony PlayMemories Camera Apps.
"""

from .test_dalvik_verification import run_tier1_tests
from .test_pmca_symbols import run_tier2_tests
from .test_input_ergonomics import run_tier3_tests
from .test_apk_signing import run_tier4_tests

__all__ = [
    "run_tier1_tests",
    "run_tier2_tests",
    "run_tier3_tests",
    "run_tier4_tests",
]
