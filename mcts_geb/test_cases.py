"""
Sample test cases for the MCTS-GEB experiment.

Each test case is (name, expr_fn, instruction_window) where:
  - expr_fn is a zero-arg callable returning a *fresh* Asm expression
    (must build a new expression each call -- e-graphs are rebuilt
    from scratch per replay).
  - instruction_window is a short assembly-instruction sequence that
    "explains" the expression to the LLM rule generator (used when
    generating learned rules specific to this case). It doesn't need
    to parse back to exactly expr_fn(); it's prompt context.

Includes both pure algebraic expressions (in the spirit of the
original notebook) and expressions built directly from assembly
instruction sequences via ExprBuilder, since this repo is fundamentally
about optimizing assembly, not just arithmetic.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple, Callable, Any

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from egraph_bridge.egg_egraph import Asm, ExprBuilder  # noqa: E402

TestCase = Tuple[str, Callable[[], Any], List[str]]


def _from_instructions(instructions: List[str]) -> Any:
    """Build an Asm expression from an assembly instruction sequence,
    using the same converter the learned-rules pipeline uses."""
    builder = ExprBuilder()
    from learned_rules.rule_to_egglog import RuleToEgglogConverter
    conv = RuleToEgglogConverter(enable_verification=False)
    expr = conv._parse_instructions_to_expr(instructions)
    if expr is None:
        raise ValueError(f"Could not build expression from {instructions}")
    return expr


def get_test_cases() -> List[TestCase]:
    cases: List[TestCase] = []

    # ---- pure algebraic identities (dead code / no-ops) ----
    cases.append((
        "x_plus_zero_times_one",
        lambda: (Asm.var("x") + Asm(0)) * Asm(1),
        ["ADD r1, 0", "MUL r1, 1"],
    ))

    cases.append((
        "double_add_const",
        lambda: (Asm.var("x") + Asm(1)) + Asm(1),
        ["ADD r1, 1", "ADD r1, 1"],
    ))

    cases.append((
        "add_then_cancel_sub",
        lambda: (Asm.var("x") + Asm.var("y")) - Asm.var("y"),
        ["ADD r1, r2", "SUB r1, r2"],
    ))

    # ---- strength reduction opportunities ----
    cases.append((
        "mul_by_two",
        lambda: Asm.var("x") * Asm(2),
        ["MUL r1, 2"],
    ))

    cases.append((
        "add_self_then_mul",
        lambda: (Asm.var("x") + Asm.var("x")) * Asm(1),
        ["ADD r1, r1", "MUL r1, 1"],
    ))

    # ---- redundant load-bearing chain (mov elimination style) ----
    cases.append((
        "mov_add_zero_chain",
        lambda: _from_instructions(["MOV r2, r1", "ADD r2, 0"]),
        ["MOV r2, r1", "ADD r2, 0"],
    ))

    # ---- constant folding across a chain ----
    cases.append((
        "const_fold_chain",
        lambda: ((Asm(2) + Asm(3)) * Asm(4)) + Asm.var("x"),
        ["ADD r1, 2, 3", "MUL r1, 4"],
    ))

    # ---- xor self / bitwise no-ops ----
    cases.append((
        "xor_self_then_or_zero",
        lambda: (Asm.var("x") ^ Asm.var("x")) | Asm(0),
        ["XOR r1, r1", "OR r1, 0"],
    ))

    # ---- a slightly bigger composite expression ----
    cases.append((
        "composite_expression",
        lambda: (
            ((Asm.var("x") + Asm(0)) * Asm(1))
            + ((Asm.var("x") * Asm(2)) - Asm.var("x"))
        ),
        ["ADD r1, 0", "MUL r1, 1", "MUL r2, 2", "SUB r2, r1"],
    ))

    return cases


def get_instruction_windows() -> List[List[str]]:
    """All instruction windows across test cases, for learned-rule generation."""
    return [instructions for _, _, instructions in get_test_cases()]
