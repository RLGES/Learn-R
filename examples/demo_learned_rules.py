"""
Demo: Learned rules system for LLM-based optimization.

This demonstrates the complete learned rules pipeline:
1. LLM rule generation
2. Rule parsing
3. Rule filtering
4. Rule memory tracking
5. Rule prioritization
"""
from learned_rules import (
    generate_candidate_rules,
    parse_llm_output,
    filter_candidate_rules,
    RuleMemory,
    LearnedRuleManager,
    rule_to_string
)


def demo_rule_generation():
    """Demonstrate LLM rule generation."""
    print("=" * 60)
    print("DEMO 1: LLM Rule Generation")
    print("=" * 60)
    
    instruction_window = [
        "MOV eax, ebx",
        "MOV ecx, eax",
        "ADD ecx, 5"
    ]
    
    print("\nInput instruction sequence:")
    for instr in instruction_window:
        print(f"  {instr}")
    
    print("\nGenerating candidate rules via LLM...")
    llm_output = generate_candidate_rules(instruction_window)
    
    print("\nLLM Output (stub):")
    print(llm_output)


def demo_rule_parsing():
    """Demonstrate rule parsing."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Rule Parsing")
    print("=" * 60)
    
    # Sample LLM output
    llm_output = """
LHS:
MOV r1, r2
MOV r3, r1
RHS:
MOV r3, r2
Condition: r1 is not used after this sequence

LHS:
ADD r1, 1
ADD r1, 1
RHS:
ADD r1, 2
Condition: None

LHS:
ADD r1, r2
SUB r1, r2
RHS:
Condition: No side effects
"""
    
    print("\nParsing LLM output...")
    parsed_rules = parse_llm_output(llm_output)
    
    print(f"\nParsed {len(parsed_rules)} rules:")
    for i, rule in enumerate(parsed_rules, 1):
        print(f"\n--- Rule {i} ---")
        print(rule)


def demo_rule_filtering():
    """Demonstrate rule filtering."""
    print("\n\n" + "=" * 60)
    print("DEMO 3: Rule Filtering")
    print("=" * 60)
    
    # Create some test rules
    llm_output = """
LHS:
MOV eax, ebx
MOV ecx, eax
RHS:
MOV ecx, ebx

LHS:
ADD eax, 0
RHS:

LHS:
PUSH ebx
POP ebx
RHS:

LHS:
MOV eax, 5
RHS:
MOV eax, 5
MOV ebx, 10
"""
    
    parsed_rules = parse_llm_output(llm_output)
    print(f"\nBefore filtering: {len(parsed_rules)} rules")
    
    existing_rules = {'mov_mov_learned'}
    filtered_rules = filter_candidate_rules(parsed_rules, existing_rules)
    
    print(f"After filtering: {len(filtered_rules)} rules")
    print("\nFiltered rules:")
    for i, rule in enumerate(filtered_rules, 1):
        print(f"\n--- Filtered Rule {i} ---")
        print(rule_to_string(rule))
    
    print("\nFiltering removed:")
    print(f"  - {len(parsed_rules) - len(filtered_rules)} rules")
    print("  Reasons: unsupported opcodes (PUSH/POP), code size increase")


def demo_rule_memory():
    """Demonstrate rule memory system."""
    print("\n\n" + "=" * 60)
    print("DEMO 4: Rule Memory System")
    print("=" * 60)
    
    memory = RuleMemory()
    
    print("\nSimulating rule applications...")
    
    # Rule A: mostly successful
    for _ in range(8):
        memory.record_success('mov_chain_learned')
    for _ in range(2):
        memory.record_failure('mov_chain_learned')
    
    # Rule B: mixed results
    for _ in range(5):
        memory.record_success('add_add_learned')
    for _ in range(5):
        memory.record_failure('add_add_learned')
    
    # Rule C: mostly failures
    for _ in range(2):
        memory.record_success('experimental_learned')
    for _ in range(8):
        memory.record_failure('experimental_learned')
    
    # Rule D: new rule (no history)
    # (not recorded yet)
    
    print("\nRule Memory State:")
    print(memory)
    
    print("\nTop 3 Rules:")
    top_rules = memory.get_top_rules(3)
    for rule, score in top_rules:
        print(f"  {rule}: {score:.3f}")


def demo_learned_rule_manager():
    """Demonstrate the complete learned rule manager."""
    print("\n\n" + "=" * 60)
    print("DEMO 5: Learned Rule Manager")
    print("=" * 60)
    
    # Initialize manager
    existing_rules = {'mov_elimination', 'add_sub_cancel'}
    manager = LearnedRuleManager(existing_rules)
    
    print("\nProposing rules for instruction sequence...")
    instruction_window = [
        "MOV eax, ebx",
        "MOV ecx, eax"
    ]
    
    proposed = manager.propose_rules(instruction_window)
    print(f"\nProposed {len(proposed)} valid rules")
    
    # Simulate some applications
    print("\nSimulating rule applications...")
    manager.update_memory('mov_mov_learned', success=True)
    manager.update_memory('mov_mov_learned', success=True)
    manager.update_memory('mov_mov_learned', success=False)
    manager.update_memory('add_add_learned', success=True)
    manager.update_memory('add_add_learned', success=False)
    manager.update_memory('add_add_learned', success=False)
    
    print("\nManager state:")
    print(manager)
    
    print("\nTop 3 performing rules:")
    top = manager.get_top_rules(3)
    for rule, score in top:
        print(f"  {rule}: {score:.3f}")


def main():
    """Run all demos."""
    demo_rule_generation()
    demo_rule_parsing()
    demo_rule_filtering()
    demo_rule_memory()
    demo_learned_rule_manager()
    
    print("\n\n" + "=" * 60)
    print("All demos complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Integrate real LLM API (OpenAI, Anthropic, etc.)")
    print("  2. Add SMT verification for rule correctness")
    print("  3. Hook into Tier 3 of the rewrite engine")
    print("  4. Implement continuous learning loop")


if __name__ == "__main__":
    main()
