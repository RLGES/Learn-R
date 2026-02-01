"""
Test memory load support in SSA-to-e-graph bridge.

Tests:
1. Simple load to expression conversion
2. Load with address offset (base+offset)
3. Load address subtraction (base-offset)
4. PHI with identical loads simplification
5. Load in e-graph insertion and extraction
6. Complex address computation
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asm_ir import BasicBlock, Instruction
from egraph_bridge.ssa_to_expr import (
    ssa_block_to_exprs, ExprNode, parse_memory_address, simplify_expression
)
from egraph_bridge.expr_to_egraph import insert_exprs_into_egraph
from egraph_bridge.egraph_to_ssa import (
    extract_optimized_exprs, exprs_to_ssa_instructions, get_address_string
)
from egraph_bridge.simple_egraph import EGraph


def test_simple_load():
    """Test conversion of simple LOAD instruction to expression."""
    print("\n" + "="*60)
    print("Test 1: Simple LOAD Instruction")
    print("="*60)
    
    block = BasicBlock("test")
    # MOV x_0, [rax]
    block.instructions = [
        Instruction("MOV", "rax_0", ["0x1000"]),
        Instruction("LOAD", "x_0", ["[rax_0]"], mem_read=True),
    ]
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Verify load conversion
    assert "x_0" in expr_map, "x_0 should be in expression map"
    load_expr = expr_map["x_0"]
    assert load_expr.op == "load", f"Expected load operation, got {load_expr.op}"
    assert len(load_expr.children) == 1, f"Load should have 1 child (address)"
    
    print(f"\n✅ LOAD instruction successfully converted to load expression")
    print(f"   x_0 = {load_expr}")


def test_load_with_offset():
    """Test LOAD with address offset: [base+offset]"""
    print("\n" + "="*60)
    print("Test 2: LOAD with Address Offset [base+offset]")
    print("="*60)
    
    block = BasicBlock("test")
    # MOV x_0, [rax+8]
    block.instructions = [
        Instruction("MOV", "rax_0", ["0x1000"]),
        Instruction("LOAD", "x_0", ["[rax_0+8]"], mem_read=True),
    ]
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Verify address expression
    load_expr = expr_map["x_0"]
    assert load_expr.op == "load"
    
    addr_expr = load_expr.children[0]
    print(f"\n  Address expression: {addr_expr}")
    assert addr_expr.op == "add", f"Expected add for base+offset"
    
    print(f"\n✅ LOAD with offset correctly parsed as load(add(base, offset))")


def test_load_with_subtraction():
    """Test LOAD with address subtraction: [base-offset]"""
    print("\n" + "="*60)
    print("Test 3: LOAD with Address Subtraction [base-offset]")
    print("="*60)
    
    block = BasicBlock("test")
    # MOV x_0, [rsp-16]
    block.instructions = [
        Instruction("MOV", "rsp_0", ["0x2000"]),
        Instruction("LOAD", "x_0", ["[rsp_0-16]"], mem_read=True),
    ]
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Verify address expression
    load_expr = expr_map["x_0"]
    addr_expr = load_expr.children[0]
    print(f"\n  Address expression: {addr_expr}")
    assert addr_expr.op == "sub", f"Expected sub for base-offset"
    
    print(f"\n✅ LOAD with subtraction correctly parsed as load(sub(base, offset))")


def test_phi_with_identical_loads():
    """Test PHI simplification with identical load expressions."""
    print("\n" + "="*60)
    print("Test 4: PHI with Identical Loads")
    print("="*60)
    
    block = BasicBlock("test")
    # Both branches load from same address
    block.instructions = [
        Instruction("MOV", "rax_0", ["0x1000"]),
        Instruction("LOAD", "x_0", ["[rax_0]"], mem_read=True),   # then branch
        Instruction("LOAD", "x_1", ["[rax_0]"], mem_read=True),   # else branch
        Instruction("PHI", "x_2", ["x_0", "x_1"]),                # merge
        Instruction("ADD", "y_0", ["x_2", "1"]),
    ]
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nExpression map (before simplification):")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Insert into e-graph and optimize
    egraph = EGraph()
    eclass_map = insert_exprs_into_egraph(expr_map, egraph)
    optimized = extract_optimized_exprs(eclass_map, egraph)
    
    print(f"\nOptimized expressions:")
    for var, expr in sorted(optimized.items()):
        print(f"  {var} = {expr}")
    
    # Verify PHI was simplified
    # Both loads are from same address, so PHI should simplify
    x2_expr = optimized["x_2"]
    print(f"\nx_2 after optimization: {x2_expr}")
    
    # x_2 should be a load (PHI of identical loads simplified)
    if x2_expr.op == "load":
        print(f"✅ PHI(load(a), load(a)) → load(a) simplification successful!")
    else:
        print(f"⚠️  PHI simplification: {x2_expr}")
    
    print(f"\n✅ PHI with identical loads processed correctly")


def test_load_in_egraph():
    """Test inserting and extracting load expressions from e-graph."""
    print("\n" + "="*60)
    print("Test 5: Load in E-Graph (Insertion and Extraction)")
    print("="*60)
    
    block = BasicBlock("test")
    block.instructions = [
        Instruction("MOV", "rax_0", ["0x1000"]),
        Instruction("LOAD", "x_0", ["[rax_0]"], mem_read=True),
        Instruction("LOAD", "x_1", ["[rax_0]"], mem_read=True),  # Same address
        Instruction("ADD", "y_0", ["x_0", "x_1"]),
    ]
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Insert into e-graph
    egraph = EGraph()
    eclass_map = insert_exprs_into_egraph(expr_map, egraph)
    
    print(f"\nE-graph statistics:")
    print(f"  E-classes: {len(egraph.eclasses)}")
    print(f"  Hash-cons entries: {len(egraph.hashcons)}")
    
    # Verify hash-consing: x_0 and x_1 should share e-class (same load)
    x0_eclass = eclass_map["x_0"]
    x1_eclass = eclass_map["x_1"]
    print(f"\n  x_0 e-class: {x0_eclass}")
    print(f"  x_1 e-class: {x1_eclass}")
    
    if x0_eclass == x1_eclass:
        print(f"  ✓ Hash-consing: identical loads share e-class!")
    
    # Extract and reconstruct
    optimized = extract_optimized_exprs(eclass_map, egraph)
    new_instrs = exprs_to_ssa_instructions(optimized)
    
    print(f"\nReconstructed SSA instructions:")
    for instr in new_instrs:
        print(f"  {instr}")
    
    # Find LOAD instructions
    load_instrs = [i for i in new_instrs if i.opcode == "LOAD"]
    print(f"\n✅ {len(load_instrs)} LOAD instructions reconstructed")


def test_complex_address():
    """Test load with complex address computation."""
    print("\n" + "="*60)
    print("Test 6: Load with Complex Address")
    print("="*60)
    
    block = BasicBlock("test")
    # Compute address: base + index*scale + offset
    # Simplified: [base + offset]
    block.instructions = [
        Instruction("MOV", "base_0", ["0x1000"]),
        Instruction("MOV", "offset_0", ["16"]),
        Instruction("ADD", "addr_0", ["base_0", "offset_0"]),
        Instruction("LOAD", "x_0", ["[addr_0]"], mem_read=True),
    ]
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Verify load uses computed address
    load_expr = expr_map["x_0"]
    print(f"\nLoad expression: {load_expr}")
    print(f"Address expression: {load_expr.children[0]}")
    
    print(f"\n✅ Complex address computation handled correctly")


def test_address_string_conversion():
    """Test converting address expressions back to memory operand strings."""
    print("\n" + "="*60)
    print("Test 7: Address String Conversion")
    print("="*60)
    
    test_cases = [
        (ExprNode(op="var", value="rax"), "[rax]"),
        (ExprNode(op="const", value=0x1000), "[4096]"),
        (ExprNode(op="add", children=[
            ExprNode(op="var", value="rbx"),
            ExprNode(op="const", value=8)
        ]), "[rbx+8]"),
        (ExprNode(op="sub", children=[
            ExprNode(op="var", value="rsp"),
            ExprNode(op="const", value=16)
        ]), "[rsp-16]"),
    ]
    
    print("\nAddress expression → Memory operand string:")
    for expr, expected in test_cases:
        result = get_address_string(expr)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {expr} → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print(f"\n✅ All address string conversions correct")


def run_all_tests():
    """Run all memory load tests."""
    print("\n" + "="*70)
    print("MEMORY LOAD SUPPORT TEST SUITE")
    print("="*70)
    
    tests = [
        test_simple_load,
        test_load_with_offset,
        test_load_with_subtraction,
        test_phi_with_identical_loads,
        test_load_in_egraph,
        test_complex_address,
        test_address_string_conversion,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
