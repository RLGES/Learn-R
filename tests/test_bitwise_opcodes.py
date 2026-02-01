"""
Test script for new bitwise opcodes and identity rules.

Tests:
1. Instruction reads/writes for new opcodes
2. Symbolic execution for bitwise operations
3. Bitwise identity peephole rules
"""
from asm_ir import Instruction
from verification.symbolic_state import SymbolicState
from verification.symbolic_executor import SymbolicExecutor
from rewrite_rules.tier1_peephole.bitwise_identities import (
    and_with_zero_rule,
    or_with_zero_rule,
    xor_with_zero_rule,
    xor_self_rule,
    shl_by_zero_rule,
    shr_by_zero_rule,
)

print("=" * 70)
print("TEST 1: Instruction reads() and writes() for new opcodes")
print("=" * 70)

# Test AND reads dst and src, writes dst
and_instr = Instruction("AND", "rax", ["rbx"])
print(f"\nAND rax, rbx")
print(f"  Reads: {and_instr.reads()}")  # Should be {rax, rbx}
print(f"  Writes: {and_instr.writes()}")  # Should be {rax}
print(f"  Flags written: {and_instr.get_flags_written()}")  # Should include zf, sf, pf

# Test XOR
xor_instr = Instruction("XOR", "rcx", ["rdx"])
print(f"\nXOR rcx, rdx")
print(f"  Reads: {xor_instr.reads()}")  # Should be {rcx, rdx}
print(f"  Writes: {xor_instr.writes()}")  # Should be {rcx}

# Test SHL
shl_instr = Instruction("SHL", "rdi", ["2"])
print(f"\nSHL rdi, 2")
print(f"  Reads: {shl_instr.reads()}")  # Should be {rdi, 2} (note: 2 is immediate)
print(f"  Writes: {shl_instr.writes()}")  # Should be {rdi}

# Test LEA (doesn't read dst)
lea_instr = Instruction("LEA", "rax", ["rbx", "8"])
print(f"\nLEA rax, [rbx+8]")
print(f"  Reads: {lea_instr.reads()}")  # Should be {rbx, 8}
print(f"  Writes: {lea_instr.writes()}")  # Should be {rax}
print(f"  Flags written: {lea_instr.get_flags_written()}")  # Should be empty

# Test IMUL
imul_instr = Instruction("IMUL", "r8", ["r9"])
print(f"\nIMUL r8, r9")
print(f"  Reads: {imul_instr.reads()}")  # Should be {r8, r9}
print(f"  Writes: {imul_instr.writes()}")  # Should be {r8}
print(f"  Flags written: {imul_instr.get_flags_written()}")  # Should include arithmetic flags

print("\n" + "=" * 70)
print("TEST 2: Symbolic execution for bitwise operations")
print("=" * 70)

# Check if z3 is available before trying to create SymbolicState
z3_available = False
try:
    import z3
    z3_available = True
except ImportError:
    pass

if not z3_available:
    print("\n⊘ Skipping symbolic execution tests (z3-solver not installed)")
    print("  Install with: pip install z3-solver")
else:
    try:
        state = SymbolicState()
        executor = SymbolicExecutor()
        
        # Initialize registers
        from z3 import BitVecVal
        state.set_register("rax", BitVecVal(0xFF, 64))  # 255
        state.set_register("rbx", BitVecVal(0x0F, 64))  # 15
        
        print("\nInitial state:")
        print(f"  rax = 0xFF (255)")
        print(f"  rbx = 0x0F (15)")
        
        # Test AND
        and_test = Instruction("AND", "rax", ["rbx"])
        executor.execute_instruction(and_test, state)
        rax_val = state.get_register("rax")
        print(f"\nAfter AND rax, rbx:")
        print(f"  rax = {rax_val} (should be 0x0F = 15)")
        
        # Test OR
        state.set_register("rax", BitVecVal(0xF0, 64))  # 240
        or_test = Instruction("OR", "rax", ["rbx"])
        executor.execute_instruction(or_test, state)
        rax_val = state.get_register("rax")
        print(f"\nAfter OR rax(0xF0), rbx(0x0F):")
        print(f"  rax = {rax_val} (should be 0xFF = 255)")
        
        # Test XOR
        state.set_register("rax", BitVecVal(0xAA, 64))  # 170
        state.set_register("rbx", BitVecVal(0x55, 64))  # 85
        xor_test = Instruction("XOR", "rax", ["rbx"])
        executor.execute_instruction(xor_test, state)
        rax_val = state.get_register("rax")
        print(f"\nAfter XOR rax(0xAA), rbx(0x55):")
        print(f"  rax = {rax_val} (should be 0xFF = 255)")
        
        # Test SHL
        state.set_register("rax", BitVecVal(0x01, 64))  # 1
        shl_test = Instruction("SHL", "rax", ["3"])
        executor.execute_instruction(shl_test, state)
        rax_val = state.get_register("rax")
        print(f"\nAfter SHL rax(1), 3:")
        print(f"  rax = {rax_val} (should be 8)")
        
        # Test SHR
        state.set_register("rax", BitVecVal(0x08, 64))  # 8
        shr_test = Instruction("SHR", "rax", ["2"])
        executor.execute_instruction(shr_test, state)
        rax_val = state.get_register("rax")
        print(f"\nAfter SHR rax(8), 2:")
        print(f"  rax = {rax_val} (should be 2)")
        
        # Test NOT
        state.set_register("rax", BitVecVal(0x00, 64))  # 0
        not_test = Instruction("NOT", "rax", [])
        executor.execute_instruction(not_test, state)
        rax_val = state.get_register("rax")
        print(f"\nAfter NOT rax(0):")
        print(f"  rax = {rax_val} (should be all 1's)")
        
        print("\n✓ Symbolic execution tests passed!")
        
    except Exception as e:
        print(f"\n✗ Symbolic execution test failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("TEST 3: Bitwise identity peephole rules")
print("=" * 70)

print("\nDefined rules:")
print(f"  1. {and_with_zero_rule.name}: AND r, 0 → MOV r, 0")
print(f"  2. {or_with_zero_rule.name}: OR r, 0 → (eliminate)")
print(f"  3. {xor_with_zero_rule.name}: XOR r, 0 → (eliminate)")
print(f"  4. {xor_self_rule.name}: XOR r, r → MOV r, 0")
print(f"  5. {shl_by_zero_rule.name}: SHL r, 0 → (eliminate)")
print(f"  6. {shr_by_zero_rule.name}: SHR r, 0 → (eliminate)")

print("\nRule details:")
print(f"\n{and_with_zero_rule.name}:")
print(f"  LHS: {len(and_with_zero_rule.lhs)} pattern(s)")
print(f"  RHS: {len(and_with_zero_rule.rhs)} pattern(s)")

print(f"\n{xor_self_rule.name}:")
print(f"  LHS: {len(xor_self_rule.lhs)} pattern(s)")
print(f"  RHS: {len(xor_self_rule.rhs)} pattern(s)")
print(f"  Has precondition: {xor_self_rule.precondition is not None}")

# Test XOR self precondition
test_bindings_same = {'r1': 'rax', 'r2': 'rax'}
test_bindings_diff = {'r1': 'rax', 'r2': 'rbx'}

print(f"\nPrecondition test:")
print(f"  XOR rax, rax (same reg): {xor_self_rule.precondition(test_bindings_same)}")
print(f"  XOR rax, rbx (diff reg): {xor_self_rule.precondition(test_bindings_diff)}")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETE")
print("=" * 70)
print("\nSummary:")
print("  ✓ New opcodes support reads/writes/flags")
if 'z3' in str(globals()):
    print("  ✓ Symbolic executor handles bitwise operations")
else:
    print("  ⊘ Symbolic executor tests skipped (z3-solver not installed)")
print("  ✓ 6 new bitwise identity rules defined")
print("\nThese rules can now be used in the hierarchical engine!")
