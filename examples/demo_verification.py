"""
Demo: SMT-based Rule Verification

Demonstrates the verification system for learned rules.
"""
from asm_ir import Instruction
from learned_rules.rule_parser import ParsedRule

# Check if z3 is available
try:
    from verification import (
        SymbolicState,
        execute_sequence,
        are_sequences_equivalent,
        verify_rule
    )
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    print("⚠ z3-solver not installed. Install with: pip install z3-solver")
    print("Demos will show structure but verification will be skipped.\n")


def demo_symbolic_state():
    """Demo: Symbolic state creation and manipulation."""
    print("=" * 70)
    print("DEMO 1: Symbolic State")
    print("=" * 70)
    
    if not Z3_AVAILABLE:
        print("Skipped (z3 not available)\n")
        return
    
    try:
        # Create symbolic state
        state = SymbolicState(prefix="demo_")
        
        print("Created symbolic state with registers and flags:")
        print(f"  Registers: {', '.join(list(state.registers.keys())[:8])}")
        print(f"  Flags: {', '.join(state.flags.keys())}")
        
        # Access a register
        rax = state.get_register('rax')
        print(f"\n  RAX = {rax}")
        
        # Copy state
        state2 = state.copy(new_prefix="copy_")
        print(f"\n  Copied state with new prefix")
        
        print("\n✓ Symbolic state working!\n")
    
    except Exception as e:
        print(f"✗ Error: {e}\n")


def demo_symbolic_execution():
    """Demo: Symbolic execution of instructions."""
    print("=" * 70)
    print("DEMO 2: Symbolic Execution")
    print("=" * 70)
    
    if not Z3_AVAILABLE:
        print("Skipped (z3 not available)\n")
        return
    
    try:
        # Create instruction sequence
        instructions = [
            Instruction('MOV', 'rax', ['5']),
            Instruction('ADD', 'rax', ['10']),
        ]
        
        print("Instruction sequence:")
        for i, instr in enumerate(instructions, 1):
            print(f"  {i}. {instr.opcode} {instr.dst}, {instr.srcs[0] if instr.srcs else ''}")
        
        # Execute symbolically
        initial_state = SymbolicState()
        final_state = execute_sequence(instructions, initial_state)
        
        print("\n  Final RAX value (symbolic):", final_state.get_register('rax'))
        print("\n✓ Symbolic execution working!\n")
    
    except Exception as e:
        print(f"✗ Error: {e}\n")


def demo_equivalence_checking():
    """Demo: Equivalence checking of sequences."""
    print("=" * 70)
    print("DEMO 3: Equivalence Checking")
    print("=" * 70)
    
    if not Z3_AVAILABLE:
        print("Skipped (z3 not available)\n")
        return
    
    try:
        # Test 1: Equivalent sequences
        seq1 = [
            Instruction('MOV', 'rax', ['rbx']),
            Instruction('MOV', 'rcx', ['rax']),
        ]
        seq2 = [
            Instruction('MOV', 'rcx', ['rbx']),
        ]
        
        print("Test 1: MOV chain elimination")
        print("  LHS: MOV rax, rbx; MOV rcx, rax")
        print("  RHS: MOV rcx, rbx")
        
        result1 = are_sequences_equivalent(seq1, seq2)
        print(f"  Result: {'✓ EQUIVALENT' if result1 else '✗ NOT EQUIVALENT'}")
        
        # Test 2: Non-equivalent sequences
        seq3 = [
            Instruction('ADD', 'rax', ['5']),
        ]
        seq4 = [
            Instruction('SUB', 'rax', ['5']),
        ]
        
        print("\nTest 2: Different operations")
        print("  LHS: ADD rax, 5")
        print("  RHS: SUB rax, 5")
        
        result2 = are_sequences_equivalent(seq3, seq4)
        print(f"  Result: {'✓ EQUIVALENT' if result2 else '✗ NOT EQUIVALENT (expected)'}")
        
        # Test 3: Add/Sub cancellation
        seq5 = [
            Instruction('ADD', 'rax', ['5']),
            Instruction('SUB', 'rax', ['5']),
        ]
        seq6 = []
        
        print("\nTest 3: Add/Sub cancellation")
        print("  LHS: ADD rax, 5; SUB rax, 5")
        print("  RHS: (empty)")
        
        result3 = are_sequences_equivalent(seq5, seq6)
        print(f"  Result: {'✓ EQUIVALENT' if result3 else '✗ NOT EQUIVALENT'}")
        
        print("\n✓ Equivalence checking working!\n")
    
    except Exception as e:
        print(f"✗ Error: {e}\n")


def demo_rule_verification():
    """Demo: Verifying parsed rules."""
    print("=" * 70)
    print("DEMO 4: Rule Verification")
    print("=" * 70)
    
    if not Z3_AVAILABLE:
        print("Skipped (z3 not available)\n")
        return
    
    try:
        # Create a valid rule
        valid_rule = ParsedRule(
            lhs_seq=["MOV RAX, RBX", "MOV RCX, RAX"],
            rhs_seq=["MOV RCX, RBX"],
        )
        
        print("Test 1: Valid rule")
        print(f"  LHS: {' ; '.join(valid_rule.lhs_seq)}")
        print(f"  RHS: {' ; '.join(valid_rule.rhs_seq)}")
        
        result1 = verify_rule(valid_rule)
        print(f"  Result: {'\u2713 VERIFIED' if result1 else '\u2717 REJECTED'}")
        
        # Create an invalid rule
        invalid_rule = ParsedRule(
            lhs_seq=["ADD RAX, 5"],
            rhs_seq=["SUB RAX, 5"],
        )
        
        print("\nTest 2: Invalid rule")
        print(f"  LHS: {' ; '.join(invalid_rule.lhs_seq)}")
        print(f"  RHS: {' ; '.join(invalid_rule.rhs_seq)}")
        
        result2 = verify_rule(invalid_rule)
        print(f"  Result: {'\u2713 VERIFIED' if result2 else '\u2717 REJECTED (expected)'}")
        
        print("\n\u2713 Rule verification working!\n")
    
    except Exception as e:
        print(f"\u2717 Error: {e}\n")


def demo_integration():
    """Demo: Integration with LearnedRuleManager."""
    print("=" * 70)
    print("DEMO 5: Integration with LearnedRuleManager")
    print("=" * 70)
    
    try:
        from learned_rules import LearnedRuleManager
        
        # Create manager with verification enabled
        print("Creating LearnedRuleManager with verification...")
        manager = LearnedRuleManager(enable_verification=True)
        
        print(f"  Verification enabled: {manager.enable_verification}")
        
        if manager.enable_verification:
            print("\n  When rules are proposed, they will be:")
            print("    1. Generated by LLM")
            print("    2. Parsed and filtered")
            print("    3. ✓ Verified using SMT")
            print("    4. Only verified rules are kept")
        
        print("\n  Verification stats:")
        stats = manager.get_verification_stats()
        for key, value in stats.items():
            print(f"    {key}: {value}")
        
        print("\n✓ Integration working!\n")
    
    except Exception as e:
        print(f"✗ Error: {e}\n")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("SMT-BASED RULE VERIFICATION DEMOS")
    print("=" * 70 + "\n")
    
    demo_symbolic_state()
    demo_symbolic_execution()
    demo_equivalence_checking()
    demo_rule_verification()
    demo_integration()
    
    print("=" * 70)
    if Z3_AVAILABLE:
        print("ALL DEMOS COMPLETED ✓")
    else:
        print("DEMOS COMPLETED (z3 not available - install with: pip install z3-solver)")
    print("=" * 70)


if __name__ == "__main__":
    main()
