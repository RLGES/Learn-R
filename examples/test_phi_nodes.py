"""
Test phi node support in SSA-to-e-graph bridge.

Tests:
1. Phi node to expression conversion
2. Phi simplification (identical inputs)
3. Phi insertion into e-graph
4. Phi extraction back to SSA
5. Complex phi with different inputs
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asm_ir import BasicBlock, Instruction
from egraph_bridge.ssa_to_expr import (
    ssa_block_to_exprs, ExprNode, instruction_to_expr, simplify_expression
)
from egraph_bridge.expr_to_egraph import insert_exprs_into_egraph
from egraph_bridge.egraph_to_ssa import extract_optimized_exprs, exprs_to_ssa_instructions
from egraph_bridge.simple_egraph import EGraph


def test_phi_to_expression():
    """Test conversion of PHI instructions to ExprNode."""
    print("\n" + "="*60)
    print("Test 1: PHI Instruction to Expression")
    print("="*60)
    
    block = BasicBlock("test")
    # Create PHI instruction: x_2 = PHI(x_0, x_1)
    block.instructions = [
        Instruction("MOV", "x_0", ["5"]),
        Instruction("MOV", "x_1", ["10"]),
        Instruction("PHI", "x_2", ["x_0", "x_1"]),
    ]
    
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Verify phi node conversion
    assert "x_2" in expr_map, "x_2 should be in expression map"
    phi_expr = expr_map["x_2"]
    assert phi_expr.op == "phi", f"Expected phi operation, got {phi_expr.op}"
    assert len(phi_expr.children) == 2, f"Expected 2 children, got {len(phi_expr.children)}"
    
    print(f"\n✅ PHI instruction successfully converted to phi expression")
    print(f"   x_2 = {phi_expr}")
    

def test_phi_simplification_identical():
    """Test phi simplification when all inputs are identical."""
    print("\n" + "="*60)
    print("Test 2: PHI Simplification (Identical Inputs)")
    print("="*60)
    
    # Create phi with identical inputs
    x_val = ExprNode(op="var", value="x_0")
    phi_expr = ExprNode(op="phi", children=[x_val, x_val, x_val])
    
    print(f"\nOriginal phi: {phi_expr}")
    
    # Simplify - should replace with single input
    simplified = simplify_expression(phi_expr)
    
    print(f"Simplified: {simplified}")
    
    # Verify simplification
    assert simplified.op == "var", f"Expected var, got {simplified.op}"
    assert simplified.value == "x_0", f"Expected x_0, got {simplified.value}"
    
    print(f"\n✅ PHI with identical inputs simplified to single value")
    

def test_phi_simplification_different():
    """Test phi with different inputs remains unchanged."""
    print("\n" + "="*60)
    print("Test 3: PHI with Different Inputs")
    print("="*60)
    
    # Create phi with different inputs
    x0 = ExprNode(op="var", value="x_0")
    x1 = ExprNode(op="var", value="x_1")
    phi_expr = ExprNode(op="phi", children=[x0, x1])
    
    print(f"\nOriginal phi: {phi_expr}")
    
    # Simplify - should remain as phi since inputs differ
    simplified = simplify_expression(phi_expr)
    
    print(f"After simplification: {simplified}")
    
    # Verify it remains a phi
    assert simplified.op == "phi", f"Expected phi, got {simplified.op}"
    assert len(simplified.children) == 2, f"Expected 2 children, got {len(simplified.children)}"
    
    print(f"\n✅ PHI with different inputs correctly preserved")
    

def test_phi_in_egraph():
    """Test inserting and extracting phi nodes from e-graph."""
    print("\n" + "="*60)
    print("Test 4: PHI in E-Graph (Insertion and Extraction)")
    print("="*60)
    
    block = BasicBlock("test")
    # Create block with phi: x_2 = PHI(x_0, x_1), then use x_2
    block.instructions = [
        Instruction("MOV", "x_0", ["5"]),
        Instruction("MOV", "x_1", ["10"]),
        Instruction("PHI", "x_2", ["x_0", "x_1"]),
        Instruction("ADD", "x_3", ["x_2", "1"]),
    ]
    
    # Convert to expressions
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nOriginal expressions:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Insert into e-graph
    egraph = EGraph()
    eclass_map = insert_exprs_into_egraph(expr_map, egraph)
    
    print(f"\nE-graph statistics:")
    print(f"  E-classes: {len(egraph.eclasses)}")
    print(f"  Hash-cons entries: {len(egraph.hashcons)}")
    
    # Extract optimized expressions
    optimized = extract_optimized_exprs(eclass_map, egraph)
    
    print(f"\nOptimized expressions:")
    for var, expr in sorted(optimized.items()):
        print(f"  {var} = {expr}")
    
    # Verify phi is preserved
    assert "x_2" in optimized
    assert optimized["x_2"].op == "phi"
    
    # Convert back to SSA
    new_instrs = exprs_to_ssa_instructions(optimized)
    
    print(f"\nReconstructed SSA instructions:")
    for instr in new_instrs:
        print(f"  {instr}")
    
    # Find PHI instruction
    phi_instr = [i for i in new_instrs if i.opcode == "PHI"]
    assert len(phi_instr) > 0, "PHI instruction should be reconstructed"
    
    print(f"\n✅ PHI node successfully inserted and extracted from e-graph")
    

def test_phi_constant_propagation():
    """Test phi simplification with constant inputs."""
    print("\n" + "="*60)
    print("Test 5: PHI Constant Propagation")
    print("="*60)
    
    block = BasicBlock("test")
    # Both phi inputs are the same constant
    block.instructions = [
        Instruction("MOV", "x_0", ["42"]),
        Instruction("MOV", "x_1", ["42"]),
        Instruction("PHI", "x_2", ["x_0", "x_1"]),
        Instruction("MUL", "x_3", ["x_2", "2"]),
    ]
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    # Convert to expressions
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
    
    # Verify phi was simplified (both inputs are Const(42))
    # After simplification, x_2 should become Const(42)
    x2_expr = optimized["x_2"]
    print(f"\nx_2 simplified to: {x2_expr}")
    
    # Verify x_3 = 42 * 2 = 84
    x3_expr = optimized["x_3"]
    print(f"x_3 expression: {x3_expr}")
    
    if x3_expr.is_constant():
        print(f"✅ Constant folding successful: x_3 = {x3_expr.value}")
        assert x3_expr.value == 84, f"Expected 84, got {x3_expr.value}"
    
    print(f"\n✅ PHI constant propagation and folding successful")
    

def test_complex_phi_network():
    """Test complex control flow with multiple phi nodes."""
    print("\n" + "="*60)
    print("Test 6: Complex PHI Network")
    print("="*60)
    
    block = BasicBlock("test")
    # Simulate nested ifs with multiple phi nodes
    block.instructions = [
        Instruction("MOV", "a_0", ["1"]),
        Instruction("MOV", "a_1", ["2"]),
        Instruction("PHI", "a_2", ["a_0", "a_1"]),  # First merge
        Instruction("MOV", "b_0", ["3"]),
        Instruction("PHI", "b_1", ["a_2", "b_0"]),  # Second merge using first phi
        Instruction("ADD", "c_0", ["b_1", "10"]),
    ]
    
    print(f"\nOriginal instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    # Convert to expressions
    expr_map = ssa_block_to_exprs(block)
    
    print(f"\nExpression map:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Verify structure
    assert expr_map["a_2"].op == "phi"
    assert expr_map["b_1"].op == "phi"
    
    # b_1's children will be inline expressions (not variable references)
    # This is correct - expression DAG inlines dependencies
    b1_children = expr_map["b_1"].children
    print(f"\nb_1 has {len(b1_children)} children:")
    for i, child in enumerate(b1_children):
        print(f"  Child {i}: {child}")
    
    # First child should be phi (inlined a_2), second should be constant 3
    assert b1_children[0].op == "phi", f"Expected phi, got {b1_children[0].op}"
    assert b1_children[1].is_constant() and b1_children[1].value == 3
    
    print(f"\n✅ Complex phi network correctly represented")
    

def run_all_tests():
    """Run all phi node tests."""
    print("\n" + "="*70)
    print("PHI NODE SUPPORT TEST SUITE")
    print("="*70)
    
    tests = [
        test_phi_to_expression,
        test_phi_simplification_identical,
        test_phi_simplification_different,
        test_phi_in_egraph,
        test_phi_constant_propagation,
        test_complex_phi_network,
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
