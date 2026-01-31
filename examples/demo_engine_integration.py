"""
Integration demo: Learned rules in the rewrite engine.

This shows how learned rules can be integrated into Tier 3 of the
hierarchical rewrite engine.
"""
from asm_ir import Instruction, BasicBlock
from rewrite_rules import RewriteRule, InstructionPattern
from rewrite_rules.tier0_normalization import normalize_block
from rewrite_rules.tier1_peephole import (
    mov_elimination_rule,
    add_sub_cancel_rule,
    mov_overwrite_rule,
    double_add_rule
)
from hierarchical_engine import HierarchicalEngine
from learned_rules import LearnedRuleManager, ParsedRule


class StubEGraphAPI:
    """Stub e-graph API for testing."""
    
    def __init__(self):
        self.applied_rules = []
    
    def apply_rule(self, rule, match):
        """Record rule application."""
        self.applied_rules.append({
            'rule': rule.name,
            'tier': rule.tier,
            'match': match
        })


def create_learned_tier3_rule() -> RewriteRule:
    """
    Create a sample Tier 3 learned rule.
    
    In a real implementation, this would be dynamically generated
    from LLM output and ParsedRule objects.
    """
    # Example: A learned pattern for triple MOV simplification
    return RewriteRule(
        name="triple_mov_learned",
        tier=3,
        lhs=[
            InstructionPattern(opcode="MOV", dst="r1", srcs=["r2"]),
            InstructionPattern(opcode="MOV", dst="r3", srcs=["r1"]),
            InstructionPattern(opcode="MOV", dst="r4", srcs=["r3"])
        ],
        rhs=[
            InstructionPattern(opcode="MOV", dst="r4", srcs=["r2"])
        ],
        precondition=lambda match: True
    )


def demo_engine_with_learned_rules():
    """Demonstrate engine with learned rules in Tier 3."""
    print("=" * 60)
    print("Engine Integration with Learned Rules (Tier 3)")
    print("=" * 60)
    
    # Create instruction sequence
    print("\n1. Creating test instruction sequence...")
    instructions = [
        Instruction(opcode="MOV", dst="EAX", srcs=["EBX"]),
        Instruction(opcode="MOV", dst="ECX", srcs=["EAX"]),
        Instruction(opcode="ADD", dst="ECX", srcs=["0"]),
        Instruction(opcode="MOV", dst="EDX", srcs=["5"]),
    ]
    
    block = BasicBlock(instructions)
    print(f"\nOriginal code ({len(block)} instructions):")
    print(block)
    
    # Normalize
    print("\n2. Normalizing (Tier 0)...")
    normalized_block = normalize_block(block)
    print(f"Normalized code ({len(normalized_block)} instructions):")
    print(normalized_block)
    
    # Setup learned rule manager
    print("\n3. Initializing learned rule manager...")
    existing_rules = {
        'mov_chain_elimination',
        'add_sub_cancellation',
        'mov_overwrite_elimination',
        'double_add_folding'
    }
    learned_manager = LearnedRuleManager(existing_rules)
    
    # Simulate some rule performance history
    learned_manager.update_memory('triple_mov_learned', success=True)
    learned_manager.update_memory('triple_mov_learned', success=True)
    learned_manager.update_memory('triple_mov_learned', success=True)
    learned_manager.update_memory('experimental_rule', success=False)
    
    print("\nLearned rule memory:")
    print(learned_manager.memory)
    
    # Setup rules by tier
    print("\n4. Setting up rules by tier...")
    tier3_learned_rule = create_learned_tier3_rule()
    
    rules_by_tier = {
        1: [
            mov_elimination_rule,
            add_sub_cancel_rule,
            mov_overwrite_rule,
            double_add_rule
        ],
        3: [
            tier3_learned_rule  # Learned rule in Tier 3
        ]
    }
    
    for tier, rules in rules_by_tier.items():
        print(f"   Tier {tier}: {len(rules)} rule(s)")
        for rule in rules:
            print(f"     - {rule.name}")
    
    # Create engine with learned rule manager
    print("\n5. Running hierarchical rewrite engine...")
    egraph = StubEGraphAPI()
    engine = HierarchicalEngine(egraph, rules_by_tier, learned_manager)
    engine.run(normalized_block)
    
    # Show results
    print("\n6. E-graph state after rewriting:")
    print(f"   Total rules applied: {len(egraph.applied_rules)}")
    
    tier_breakdown = {}
    for app in egraph.applied_rules:
        tier = app['tier']
        if tier not in tier_breakdown:
            tier_breakdown[tier] = []
        tier_breakdown[tier].append(app['rule'])
    
    for tier in sorted(tier_breakdown.keys()):
        rules = tier_breakdown[tier]
        print(f"   Tier {tier}: {len(rules)} application(s)")
        for rule in set(rules):
            count = rules.count(rule)
            print(f"     - {rule}: {count}x")


def demo_rule_learning_loop():
    """Demonstrate a learning loop concept."""
    print("\n\n" + "=" * 60)
    print("Learned Rules Learning Loop Concept")
    print("=" * 60)
    
    print("\nConcept: Continuous learning loop")
    print("  1. Observe instruction sequences in real programs")
    print("  2. Generate candidate rules via LLM")
    print("  3. Filter and validate rules")
    print("  4. Apply rules in Tier 3")
    print("  5. Track success/failure")
    print("  6. Prioritize successful rules")
    print("  7. Demote failing rules")
    print("  8. Repeat")
    
    print("\nAdvantages:")
    print("  ✓ Adapts to new code patterns")
    print("  ✓ Learns domain-specific optimizations")
    print("  ✓ Improves over time with feedback")
    print("  ✓ Reduces manual rule engineering")
    
    print("\nFuture enhancements:")
    print("  • Real LLM API integration (OpenAI, Anthropic)")
    print("  • SMT solver verification for correctness")
    print("  • Automated A/B testing of rules")
    print("  • Rule effectiveness metrics (speed, size)")
    print("  • Multi-tier learned rules (not just Tier 3)")


def main():
    """Run all demos."""
    demo_engine_with_learned_rules()
    demo_rule_learning_loop()
    
    print("\n\n" + "=" * 60)
    print("Integration demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
