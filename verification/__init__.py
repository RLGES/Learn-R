"""
Verification package for SMT-based equivalence checking of rewrite rules.

Uses z3-solver for symbolic execution and verification.
"""
from .symbolic_state import SymbolicState
from .symbolic_executor import execute_sequence
from .equivalence_checker import are_sequences_equivalent
from .rule_verifier import verify_rule

__all__ = [
    'SymbolicState',
    'execute_sequence',
    'are_sequences_equivalent',
    'verify_rule',
]
