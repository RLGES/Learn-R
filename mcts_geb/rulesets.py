"""
Builds the flat action space for MCTS: a list of (name, Ruleset) pairs,
where each Ruleset wraps exactly ONE rewrite rule. One MCTS action =
applying one such ruleset for one egglog iteration.

Two sources are combined:

  - static_rulesets()  : wraps every rule from egg_egraph.py's
                          create_algebraic_rules / create_strength_reduction_rules
                          / create_commutativity_rules / create_associativity_rules
                          each in its own named Ruleset.

  - learned_rulesets()  : runs the repo's real learned-rules pipeline
                          (LLM generation -> parsing -> filtering ->
                          optional Z3 verification -> egglog conversion)
                          over one or more instruction "windows", and
                          wraps each resulting rule in its own Ruleset.

Both return lists of (name: str, ruleset: egglog.Ruleset) so callers
can build an ordered RULES list (index == MCTS action id) and keep a
human-readable name per action for reporting.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple, Optional, Any

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from egglog import ruleset, Ruleset  # noqa: E402

from egraph_bridge.egg_egraph import (  # noqa: E402
    create_algebraic_rules,
    create_strength_reduction_rules,
    create_commutativity_rules,
    create_associativity_rules,
)
from learned_rules.llm_rule_generator import generate_candidate_rules  # noqa: E402
from learned_rules.rule_parser import parse_llm_output  # noqa: E402
from learned_rules.rule_filter import filter_candidate_rules  # noqa: E402
from learned_rules.rule_to_egglog import RuleToEgglogConverter  # noqa: E402

Action = Tuple[str, Ruleset]


def static_rulesets(
    use_commutativity: bool = False,
    use_associativity: bool = False,
) -> List[Action]:
    """
    Wrap every static rule (rewrite_rules' egglog equivalents, defined
    in egraph_bridge/egg_egraph.py) as its own individually-selectable
    Ruleset.

    Commutativity/associativity are bidirectional (birewrite) and can
    blow up the e-graph, so they're off by default -- pass True to
    include them as extra actions.
    """
    actions: List[Action] = []

    for i, rule in enumerate(create_algebraic_rules()):
        actions.append((f"static/algebraic_{i}", ruleset(rule, name=f"static_algebraic_{i}")))

    for i, rule in enumerate(create_strength_reduction_rules()):
        actions.append((f"static/strength_{i}", ruleset(rule, name=f"static_strength_{i}")))

    if use_commutativity:
        for i, rule in enumerate(create_commutativity_rules()):
            actions.append((f"static/commutativity_{i}", ruleset(rule, name=f"static_comm_{i}")))

    if use_associativity:
        for i, rule in enumerate(create_associativity_rules()):
            actions.append((f"static/associativity_{i}", ruleset(rule, name=f"static_assoc_{i}")))

    return actions


def learned_rulesets(
    instruction_windows: List[List[str]],
    provider: Optional[str] = None,
    verify: bool = False,
    verbose: bool = True,
) -> List[Action]:
    """
    Run the repo's real LLM rule-generation pipeline over each given
    instruction window, and wrap every surviving rule in its own
    Ruleset.

    Pipeline per window (mirrors learned_rules/learned_rule_manager.py):
        generate_candidate_rules -> parse_llm_output ->
        filter_candidate_rules -> RuleToEgglogConverter

    If no LLM provider is configured (no .env / API key), each call
    transparently falls back to a deterministic stub response, so this
    still produces a handful of rules for the demo without any
    network / API key.

    Args:
        instruction_windows: list of instruction-sequence "windows"
            (each a list of assembly strings like "ADD r1, 0") to feed
            to the LLM as generation context.
        provider: optional LLM provider override ("openai", "anthropic", ...)
        verify: run Z3 SMT verification on candidate rules (requires
            z3-solver; skipped automatically if unavailable)
        verbose: print what was generated / kept / dropped

    Returns:
        List of (name, Ruleset) actions, deduplicated by their
        egglog rewrite string.
    """
    actions: List[Action] = []
    seen_rule_strs = set()
    converter = RuleToEgglogConverter(enable_verification=verify)

    counter = 0
    for window in instruction_windows:
        raw = generate_candidate_rules(window, provider=provider)
        parsed = parse_llm_output(raw)
        filtered = filter_candidate_rules(parsed, existing_rule_names=set())

        if verbose:
            print(f"  window {window}: {len(parsed)} parsed -> {len(filtered)} kept after filtering")

        for p_rule in filtered:
            egg_rule = converter.convert_rule(p_rule, verify=verify)
            if egg_rule is None:
                continue

            egg_obj = egg_rule.to_egglog()
            key = str(egg_obj)
            if key in seen_rule_strs:
                continue
            seen_rule_strs.add(key)

            name = f"learned/{counter}"
            actions.append((name, ruleset(egg_obj, name=f"learned_{counter}")))
            if verbose:
                print(f"    + {name}: {egg_rule.lhs_expr} -> {egg_rule.rhs_expr}")
            counter += 1

    return actions


def build_action_space(
    instruction_windows: Optional[List[List[str]]] = None,
    use_llm: bool = True,
    use_commutativity: bool = False,
    use_associativity: bool = False,
    provider: Optional[str] = None,
    verify: bool = False,
    verbose: bool = True,
) -> Tuple[List[str], List[Ruleset]]:
    """
    Build the full MCTS action space: static rules + (optionally)
    LLM-learned rules.

    Returns:
        (names, rulesets) -- two parallel lists; names[i] describes
        rulesets[i]. Index i is the MCTS action id.
    """
    actions = static_rulesets(use_commutativity, use_associativity)

    if use_llm:
        if instruction_windows is None:
            instruction_windows = [
                ["ADD r1, 0"],
                ["MUL r1, 2"],
                ["ADD r1, 1", "ADD r1, 1"],
                ["ADD r1, r2", "SUB r1, r2"],
            ]
        if verbose:
            print(f"Generating learned rules from {len(instruction_windows)} instruction window(s)...")
        actions += learned_rulesets(instruction_windows, provider=provider, verify=verify, verbose=verbose)

    names = [name for name, _ in actions]
    rules = [rs for _, rs in actions]
    return names, rules
