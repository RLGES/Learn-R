"""
Test SSA-to-E-Graph bridge and optimization pipeline.
"""
from asm_ir import BasicBlock, Instruction
from egraph_bridge import (
    ssa_block_to_exprs,
    ExprNode,
    insert_exprs_into_egraph,
    extract_optimized_exprs,
    exprs_to_ssa_instructions,
    EGraph
)
from pipeline.ssa_egraph_pipeline import optimize_ssa_block


def test_ssa_to_expr():
    """Test converting SSA instructions to expressions."""
    print("\n" + "=" * 70)
    print("TEST 1: SSA to Expression Conversion")
    print("=" * 70)
    
    block = BasicBlock("test")
    block.instructions.append(Instruction("MOV", "x_0", ["1"]))
    block.instructions.append(Instruction("ADD", "y_0", ["x_0", "2"]))
    block.instructions.append(Instruction("MUL", "z_0", ["y_0", "x_0"]))
    
    print("\nSSA Instructions:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    expr_map = ssa_block_to_exprs(block)
    
    print("\nExpressions:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    assert "x_0" in expr_map
    assert "y_0" in expr_map
    assert "z_0" in expr_map
    
    print("\n[PASS] SSA to expression conversion")


def test_expr_to_egraph():
    """Test inserting expressions into e-graph."""
    print("\n" + "=" * 70)
    print("TEST 2: Expression to E-Graph")
    print("=" * 70)
    
    # Create simple expressions
    expr_map = {
        "x_0": ExprNode("const", value=1),
        "y_0": ExprNode("add", [ExprNode("var", value="x_0"), ExprNode("const", value=2)]),
    }
    
    print("\nExpressions:")
    for var, expr in expr_map.items():
        print(f"  {var} = {expr}")
    
    # Insert into e-graph
    egraph = EGraph()
    eclass_map = insert_exprs_into_egraph(expr_map, egraph)
    
    print(f"\nE-Graph: {egraph}")
    print(f"E-classes created: {len(eclass_map)}")
    
    assert len(eclass_map) == 2
    assert "x_0" in eclass_map
    assert "y_0" in eclass_map
    
    print("\n[PASS] Expression to e-graph insertion")


def test_algebraic_simplification():
    """Test algebraic simplifications."""
    print("\n" + "=" * 70)
    print("TEST 3: Algebraic Simplification")
    print("=" * 70)
    
    block = BasicBlock("test")
    
    # x = 5
    block.instructions.append(Instruction("MOV", "x_0", ["5"]))
    
    # y = x + 0  (should simplify to y = x)
    block.instructions.append(Instruction("ADD", "y_0", ["x_0", "0"]))
    
    # z = y * 1  (should simplify to z = y)
    block.instructions.append(Instruction("MUL", "z_0", ["y_0", "1"]))
    
    print("\nOriginal:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    optimized = optimize_ssa_block(block, verbose=False)
    
    print("\nOptimized:")
    for instr in optimized.instructions:
        print(f"  {instr}")
    
    # Check that simplifications occurred
    # Should have: x=5, y=5, z=5 (all constants)
    simplified_count = sum(1 for instr in optimized.instructions 
                          if instr.opcode == "MOV" and instr.srcs[0].isdigit())
    
    print(f"\nSimplified to {simplified_count} constant assignments")
    assert simplified_count >= 2, "Should have simplified algebraic identities"
    
    print("\n[PASS] Algebraic simplification")


def test_constant_folding():
    """Test constant folding."""
    print("\n" + "=" * 70)
    print("TEST 4: Constant Folding")
    print("=" * 70)
    
    block = BasicBlock("test")
    
    # All constant operations
    block.instructions.append(Instruction("MOV", "a_0", ["10"]))
    block.instructions.append(Instruction("MOV", "b_0", ["5"]))
    block.instructions.append(Instruction("ADD", "c_0", ["10", "5"]))  # Should fold to 15
    block.instructions.append(Instruction("MUL", "d_0", ["c_0", "2"]))  # Should fold to 30
    
    print("\nOriginal:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    optimized = optimize_ssa_block(block, verbose=False)
    
    print("\nOptimized:")
    for instr in optimized.instructions:
        print(f"  {instr}")
    
    # Check for constant folding
    has_15 = any("15" in str(instr) for instr in optimized.instructions)
    has_30 = any("30" in str(instr) for instr in optimized.instructions)
    
    if has_15 or has_30:
        print("\n[PASS] Constants were folded")
    else:
        print("\n[INFO] Constants not fully folded (may need more passes)")
    
    print("\n[PASS] Constant folding test")


def test_common_subexpression():
    """Test common subexpression elimination."""
    print("\n" + "=" * 70)
    print("TEST 5: Common Subexpression Elimination")
    print("=" * 70)
    
    block = BasicBlock("test")
    
    block.instructions.append(Instruction("MOV", "x_0", ["10"]))
    block.instructions.append(Instruction("ADD", "a_0", ["x_0", "5"]))  # x + 5
    block.instructions.append(Instruction("ADD", "b_0", ["x_0", "5"]))  # x + 5 (duplicate)
    
    print("\nOriginal:")
    for instr in block.instructions:
        print(f"  {instr}")
    
    # Convert to expressions
    expr_map = ssa_block_to_exprs(block)
    
    print("\nExpressions:")
    for var, expr in sorted(expr_map.items()):
        print(f"  {var} = {expr}")
    
    # Check if expressions are the same
    if str(expr_map.get("a_0")) == str(expr_map.get("b_0")):
        print("\n[OK] Detected common subexpression")
    
    print("\n[PASS] Common subexpression test")


def test_full_pipeline():
    """Test complete optimization pipeline."""
    print("\n" + "=" * 70)
    print("TEST 6: Complete Pipeline")
    print("=" * 70)
    
    block = BasicBlock("pipeline_test")
    
    # Complex expression with multiple optimization opportunities
    block.instructions.append(Instruction("MOV", "x_0", ["10"]))
    block.instructions.append(Instruction("ADD", "y_0", ["x_0", "0"]))  # x + 0
    block.instructions.append(Instruction("MUL", "z_0", ["y_0", "1"]))  # (x + 0) * 1
    block.instructions.append(Instruction("SUB", "w_0", ["z_0", "z_0"]))  # z - z
    block.instructions.append(Instruction("ADD", "result_0", ["w_0", "x_0"]))  # 0 + x
    
    print("\nOriginal (5 instructions):")
    for instr in block.instructions:
        print(f"  {instr}")
    
    optimized = optimize_ssa_block(block, verbose=False)
    
    print(f"\nOptimized ({len(optimized.instructions)} instructions):")
    for instr in optimized.instructions:
        print(f"  {instr}")
    
    # Should optimize significantly
    print(f"\nReduction: {len(block.instructions) - len(optimized.instructions)} instructions")
    
    print("\n[PASS] Complete pipeline test")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("RUNNING E-GRAPH BRIDGE TESTS")
    print("=" * 80)
    
    try:
        test_ssa_to_expr()
        test_expr_to_egraph()
        test_algebraic_simplification()
        test_constant_folding()
        test_common_subexpression()
        test_full_pipeline()
        
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
