"""
Driver script for the hierarchical assembly rewrite system.
"""
from asm_ir import Instruction, BasicBlock
from rewrite_rules import mov_elimination_rule
from hierarchical_engine import HierarchicalEngine


class StubEGraphAPI:
    """Stub e-graph API for testing."""
    
    def __init__(self):
        self.applied_rules = []
    
    def apply_rule(self, rule, match):
        """Record rule application (stub implementation)."""
        self.applied_rules.append({
            'rule': rule.name,
            'tier': rule.tier,
            'match': match
        })
    
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
        Instruction(opcode="MOV", dst="eax", srcs=["ebx"]),
        Instruction(opcode="MOV", dst="ecx", srcs=["eax"]),
        Instruction(opcode="ADD", dst="ecx", srcs=["5"]),
        Instruction(opcode="MOV", dst="edx", srcs=["esi"]),
        Instruction(opcode="MOV", dst="edi", srcs=["edx"]),
    ]
    
    block = BasicBlock(instructions)
    print(f"\nOriginal code ({len(block)} instructions):")
    print(block)
    
    # Normalize (Tier 0 - placeholder for now)
    print("\n2. Normalizing (Tier 0 - placeholder)...")
    print("   (No normalization rules implemented yet)")
    
    # Setup rewrite rules by tier
    print("\n3. Setting up rewrite rules...")
    rules_by_tier = {
        1: [mov_elimination_rule]
    }
    print(f"   Tier 1: {len(rules_by_tier[1])} rule(s)")
    
    # Create stub e-graph API
    print("\n4. Initializing e-graph API (stub)...")
    egraph = StubEGraphAPI()
    
    # Create and run engine
    print("\n5. Running hierarchical rewrite engine...")
    engine = HierarchicalEngine(egraph, rules_by_tier)
    engine.run(block, max_iterations_per_tier=5)
    
    # Print e-graph state
    print("\n6. E-graph state after rewriting:")
    print(egraph.get_state())
    
    print("\n" + "=" * 60)
    print("System demonstration complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
