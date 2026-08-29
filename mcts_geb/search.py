"""
MCTS-GEB search engine.

Generalized from the original prototype notebook: instead of a fixed
`RULES` global, everything here takes the action list (names + egglog
Rulesets) as an explicit parameter, so it can run over the repo's
static rules, its LLM-learned rules, or both combined.

Core idea (same as the notebook):
  - One MCTS "action" = running exactly one Ruleset for one egglog
    iteration (`eg.run(1, ruleset=RULES[a])`).
  - A tree node represents a committed sequence of actions.
  - We grow the tree with UCB1 selection + expansion + random rollout
    + backprop, exactly like classic MCTS, but the "reward" is the
    e-graph extraction-cost reduction versus the un-rewritten
    expression.
  - After each round of simulations at the root, we commit to the
    single best child action and repeat (`n_construction_steps`
    rounds), rather than committing to a full random rollout.

This also exposes a plain equality-saturation baseline
(`plain_saturation`) so results can be compared against "just run
egglog's saturation loop with every rule combined".
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Optional, Any

from egglog import EGraph, Ruleset, unstable_combine_rulesets


@dataclass
class MCTSResult:
    action_seq: List[int]
    action_names: List[str]
    initial_cost: int
    final_cost: int
    final_expr: str

    @property
    def improved(self) -> bool:
        return self.final_cost < self.initial_cost


class Node:
    __slots__ = ("action_seq", "children", "N", "W", "untried")

    def __init__(self, action_seq: List[int], n_actions: int):
        self.action_seq = action_seq
        self.children: dict[int, "Node"] = {}
        self.N = 0
        self.W = 0.0
        self.untried = list(range(n_actions))
        random.shuffle(self.untried)


def ucb1(child_N: int, child_W: float, parent_N: int, c: float = 1.4) -> float:
    if child_N == 0:
        return float("inf")
    return (child_W / child_N) + c * math.sqrt(math.log(parent_N) / child_N)


def replay(
    initial_expr_fn: Callable[[], Any],
    action_seq: List[int],
    rules: List[Ruleset],
) -> Tuple[EGraph, Any, int]:
    """Rebuild the e-graph from scratch and apply the given action sequence."""
    eg = EGraph()
    root = eg.let("root", initial_expr_fn())
    for idx in action_seq:
        eg.run(1, ruleset=rules[idx])
    expr, cost = eg.extract(root, True)
    return eg, root, cost


def initial_cost(initial_expr_fn: Callable[[], Any]) -> int:
    eg = EGraph()
    root = eg.let("root", initial_expr_fn())
    _, cost = eg.extract(root, True)
    return cost


def mcts_construct(
    initial_expr_fn: Callable[[], Any],
    rules: List[Ruleset],
    rule_names: List[str],
    n_construction_steps: int = 8,
    n_simulations: int = 100,
    max_sim_step: int = 5,
    ucb_c: float = 1.4,
    seed: Optional[int] = None,
) -> MCTSResult:
    """
    Run MCTS to find a good action sequence for minimizing extraction cost.

    Args:
        initial_expr_fn: zero-arg callable that builds a *fresh* egglog
            expression each time it's called (needed because e-graphs
            are rebuilt from scratch on every replay).
        rules: list of egglog Rulesets; rules[i] is action i.
        rule_names: human-readable name for each action (same length/order as rules).
        n_construction_steps: how many actions to commit to the final sequence.
        n_simulations: MCTS simulations (selection+expansion+rollout+backprop)
            per construction step.
        max_sim_step: random rollout depth after expansion.
        ucb_c: UCB1 exploration constant.
        seed: optional RNG seed for reproducibility.

    Returns:
        MCTSResult with the committed action sequence and resulting cost.
    """
    if seed is not None:
        random.seed(seed)

    n_actions = len(rules)
    init_c = initial_cost(initial_expr_fn)
    committed: List[int] = []

    for _step in range(n_construction_steps):
        root_node = Node(list(committed), n_actions)

        for _sim in range(n_simulations):
            # ---- selection ----
            node = root_node
            path = [node]
            while not node.untried and node.children:
                a = max(
                    node.children,
                    key=lambda a: ucb1(node.children[a].N, node.children[a].W, node.N, ucb_c),
                )
                node = node.children[a]
                path.append(node)

            # ---- expansion ----
            if node.untried:
                a = node.untried.pop()
                child = Node(node.action_seq + [a], n_actions)
                node.children[a] = child
                node = child
                path.append(node)

            # ---- simulation (random rollout) ----
            rollout_seq = list(node.action_seq)
            for _ in range(max_sim_step):
                rollout_seq.append(random.randrange(n_actions))
            _, _, rollout_cost = replay(initial_expr_fn, rollout_seq, rules)
            reward = max(init_c - rollout_cost, 0)

            # ---- backup ----
            for n in path:
                n.N += 1
                n.W += reward

        if not root_node.children:
            break

        best_action = max(
            root_node.children,
            key=lambda a: root_node.children[a].W / max(root_node.children[a].N, 1),
        )
        committed.append(best_action)

    _, _, final_cost = replay(initial_expr_fn, committed, rules)
    final_expr = str(replay(initial_expr_fn, committed, rules)[1])
    # extract the actual best expression string (not just root binding name)
    eg, root, final_cost = replay(initial_expr_fn, committed, rules)
    final_expr_obj, final_cost = eg.extract(root, True)

    return MCTSResult(
        action_seq=committed,
        action_names=[rule_names[a] for a in committed],
        initial_cost=init_c,
        final_cost=final_cost,
        final_expr=str(final_expr_obj),
    )


def plain_saturation(
    initial_expr_fn: Callable[[], Any],
    rules: List[Ruleset],
    iters: int = 8,
) -> Tuple[str, int, int]:
    """
    Baseline: combine every rule into one ruleset and run standard
    egglog equality saturation for `iters` iterations (no search --
    apply everything, every iteration).

    Returns:
        (final_expr_str, initial_cost, final_cost)
    """
    eg = EGraph()
    root = eg.let("root", initial_expr_fn())
    _, init_c = eg.extract(root, True)

    combined = unstable_combine_rulesets(*rules, name="combined_all")
    eg.run(iters, ruleset=combined)

    expr, cost = eg.extract(root, True)
    return str(expr), init_c, cost
