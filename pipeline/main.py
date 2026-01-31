"""
Driver script for the hierarchical assembly rewrite system.
"""
from asm_ir import Instruction, BasicBlock
from rewrite_rules import mov_elimination_rule
from rewrite_rules.tier1_peephole import (
    add_sub_cancel_rule,
    mov_overwrite_rule,
    double_add_rule
)
from rewrite_rules.tier0_normalization import normalize_block
from hierarchical_engine import HierarchicalEngine


class StubEGraphAPI:
    """Stub e-graph API for testing."""
    
    def __init__(self):
        self.applied_rules = []
        self.sequences = []
    
    def add_sequence(self, instructions):
        """Add instruction sequence to e-graph (stub implementation)."""
        self.sequences.append(instructions)
    
    def apply_rule(self, rule, match):
        """Record rule application (stub implementation)."""
        self.applied_rules.append({
            'rule': rule.name,
            'tier': rule.tier,
            'match': match
        })
    
    def extract_best(self):
        """Extract best sequence (stub - returns original for now)."""
        if self.sequences:
            # In a real implementation, this would return the optimized sequence
            # For now, return the original sequence
            return self.sequences[0]
        return []
    
    def get_applied_rules(self):
        """Get list of applied rule names."""
        return [app['rule'] for app in self.applied_rules]
    
    def get_state(self) -> str:
        """Return current e-graph state (stub)."""
        if not self.applied_rules:
            return "E-graph state: No rules applied"
        
        result = "E-graph state:\n"
        result += f"  Total rules applied: {len(self.applied_rules)}\n"
        for i, app in enumerate(self.applied_rules, 1):
            result += f"  {i}. Rule '{app['rule']}' (Tier {app['tier']}) - {app['match']}\n"
        return result


def main():
    """Main driver function."""
    
    print("=" * 60)
    print("Hierarchical Assembly Rewrite System")
    print("=" * 60)
    
    # Create a hardcoded assembly sequence
    print("\n1. Parsing hardcoded assembly sequence...")
    instructions = [
        Instruction(opcode="MOV", dst="EAX", srcs=["EBX"]),
        Instruction(opcode="MOV", dst="ECX", srcs=["EAX"]),
        Instruction(opcode="ADD", dst="ECX", srcs=["0"]),  # ADD with 0 (will be normalized)
        Instruction(opcode="MOV", dst="EDX", srcs=["ESI"]),
        Instruction(opcode="MOV", dst="EDX", srcs=["EDI"]),  # Overwrites previous MOV
        Instruction(opcode="ADD", dst="EAX", srcs=["1"]),
        Instruction(opcode="ADD", dst="EAX", srcs=["1"]),  # Double ADD
        Instruction(opcode="ADD", dst="EBX", srcs=["5"]),
        Instruction(opcode="SUB", dst="EBX", srcs=["5"]),  # Cancels with previous ADD
    ]
    
    block = BasicBlock(instructions)
    print(f"\nOriginal code ({len(block)} instructions):")
    print(block)
    
    # Normalize (Tier 0)
    print("\n2. Normalizing (Tier 0)...")
    normalized_block = normalize_block(block)
    print(f"Normalized code ({len(normalized_block)} instructions):")
    print(normalized_block)
    
    # Setup rewrite rules by tier
    print("\n3. Setting up rewrite rules...")
    rules_by_tier = {
        1: [
            mov_elimination_rule,
            add_sub_cancel_rule,
            mov_overwrite_rule,
            double_add_rule
        ]
    }
    print(f"   Tier 1: {len(rules_by_tier[1])} rule(s)")
    for rule in rules_by_tier[1]:
        print(f"     - {rule.name}")
    
    # Create stub e-graph API
    print("\n4. Initializing e-graph API (stub)...")
    egraph = StubEGraphAPI()
    
    # Create and run engine
    print("\n5. Running hierarchical rewrite engine...")
    engine = HierarchicalEngine(egraph, rules_by_tier)
    optimized_block = engine.run(normalized_block, max_iterations_per_tier=5)
    
    # Print optimized result
    print(f"\nOptimized code ({len(optimized_block)} instructions):")
    print(optimized_block)
    
    # Print e-graph state
    print("\n6. E-graph state after rewriting:")
    print(egraph.get_state())
    
    print("\n" + "=" * 60)
    print("System demonstration complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
