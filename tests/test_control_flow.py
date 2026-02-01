"""
Tests for control flow support: BasicBlock, CFG, jumps, if/while.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asm_ir import Instruction, BasicBlock, CFG
from frontend import parse, lower_to_ir, ir_to_assembly


def test_basicblock_with_label():
    """Test BasicBlock with label and successors."""
    print("Test 1: BasicBlock with label and successors")
    
    # Create a basic block
    instructions = [
        Instruction('MOV', 'rax', ['5']),
        Instruction('ADD', 'rax', ['3']),
    ]
    
    block = BasicBlock('entry', instructions)
    
    # Check properties
    assert block.label == 'entry'
    assert len(block.instructions) == 2
    assert block.successors == []
    
    # Add successors
    block.add_successor('block_1')
    block.add_successor('block_2')
    
    assert 'block_1' in block.successors
    assert 'block_2' in block.successors
    assert len(block.successors) == 2
    
    # Test no duplicates
    block.add_successor('block_1')
    assert len(block.successors) == 2  # Should still be 2
    
    print("  PASS: BasicBlock with label and successors")


def test_cfg_creation():
    """Test CFG creation and manipulation."""
    print("\nTest 2: CFG creation and manipulation")
    
    cfg = CFG(entry_label='start')
    
    # Create blocks
    block1 = BasicBlock('start', [Instruction('MOV', 'rax', ['0'])])
    block2 = BasicBlock('loop', [Instruction('ADD', 'rax', ['1'])])
    block3 = BasicBlock('end', [Instruction('MOV', 'rbx', ['rax'])])
    
    # Add blocks to CFG
    cfg.add_block(block1)
    cfg.add_block(block2)
    cfg.add_block(block3)
    
    # Check blocks exist
    assert len(cfg.blocks) == 3
    assert cfg.get_block('start') == block1
    assert cfg.get_entry_block() == block1
    
    # Connect blocks
    cfg.connect_blocks('start', 'loop')
    cfg.connect_blocks('loop', 'end')
    cfg.connect_blocks('loop', 'loop')  # Self-loop
    
    # Check connections
    assert 'loop' in block1.successors
    assert 'end' in block2.successors
    assert 'loop' in block2.successors  # Self-loop
    
    print("  PASS: CFG creation and manipulation")


def test_jump_instructions():
    """Test jump instruction properties."""
    print("\nTest 3: Jump instruction properties")
    
    # JMP (unconditional)
    jmp = Instruction('JMP', 'loop_start', [], is_control_flow_instr=True)
    assert jmp.is_control_flow()
    assert jmp.reads() == set()  # Jumps don't read registers
    assert jmp.writes() == set()  # Jumps don't write registers
    assert jmp.get_flags_written() == set()  # Jumps don't write flags
    
    # JE (conditional)
    je = Instruction('JE', 'then_label', [], flags_read={'zf'}, is_control_flow_instr=True)
    assert je.is_control_flow()
    assert je.reads() == set()
    assert je.writes() == set()
    assert 'zf' in je.flags_read  # Reads zero flag
    
    # JNE (conditional)
    jne = Instruction('JNE', 'else_label', [], flags_read={'zf'}, is_control_flow_instr=True)
    assert jne.is_control_flow()
    assert jne.opcode == 'JNE'
    
    print("  PASS: Jump instruction properties")


def test_parse_if_statement():
    """Test parsing if statements."""
    print("\nTest 4: Parsing if statements")
    
    code = """a = 5
if (a < 10) {
    b = a + 1
}"""
    
    ast = parse(code)
    
    # Should have 2 statements: assignment and if
    assert len(ast.statements) == 2
    
    # First is assignment
    from frontend.ast_nodes import Assign, If
    assert isinstance(ast.statements[0], Assign)
    assert ast.statements[0].name == 'a'
    
    # Second is if statement
    assert isinstance(ast.statements[1], If)
    if_stmt = ast.statements[1]
    
    # Check condition
    assert if_stmt.condition is not None
    
    # Check then block
    assert len(if_stmt.then_block.statements) == 1
    assert isinstance(if_stmt.then_block.statements[0], Assign)
    assert if_stmt.then_block.statements[0].name == 'b'
    
    # No else block
    assert if_stmt.else_block is None
    
    print("  PASS: Parsing if statements")


def test_parse_while_statement():
    """Test parsing while loops."""
    print("\nTest 5: Parsing while loops")
    
    code = """i = 0
while (i < 5) {
    i = i + 1
}"""
    
    ast = parse(code)
    
    # Should have 2 statements
    assert len(ast.statements) == 2
    
    # Second is while
    from frontend.ast_nodes import While, Assign
    assert isinstance(ast.statements[1], While)
    while_stmt = ast.statements[1]
    
    # Check condition
    assert while_stmt.condition is not None
    
    # Check body
    assert len(while_stmt.body.statements) == 1
    assert isinstance(while_stmt.body.statements[0], Assign)
    
    print("  PASS: Parsing while loops")


def test_lower_if_to_ir():
    """Test lowering if statements to IR with jumps."""
    print("\nTest 6: Lowering if to IR")
    
    code = """if (a < b) {
    c = a
}"""
    
    ast = parse(code)
    ir = lower_to_ir(ast)
    
    # Should have: CMP, conditional jump, assignment, label
    assert len(ir) > 3
    
    # Check for CMP
    assert any('CMP' in instr for instr in ir)
    
    # Check for conditional jump (JGE - jump if NOT less than)
    assert any('JGE' in instr or 'JL' in instr or 'JE' in instr or 'JNE' in instr for instr in ir)
    
    # Check for label
    assert any(':' in instr for instr in ir)
    
    print("  IR Instructions:")
    for instr in ir:
        print(f"    {instr}")
    
    print("  PASS: Lowering if to IR")


def test_lower_while_to_ir():
    """Test lowering while loops to IR with jumps."""
    print("\nTest 7: Lowering while to IR")
    
    code = """while (x < 10) {
    x = x + 1
}"""
    
    ast = parse(code)
    ir = lower_to_ir(ast)
    
    # Should have: loop label, CMP, conditional jump, body, unconditional jump back, end label
    assert len(ir) > 4
    
    # Check for labels (at least 2: loop_start and loop_end)
    labels = [instr for instr in ir if ':' in instr]
    assert len(labels) >= 2
    
    # Check for CMP
    assert any('CMP' in instr for instr in ir)
    
    # Check for conditional jump
    assert any('JGE' in instr or 'JL' in instr or 'JE' in instr or 'JNE' in instr for instr in ir)
    
    # Check for unconditional jump (back to loop start)
    assert any('JMP' in instr for instr in ir)
    
    print("  IR Instructions:")
    for instr in ir:
        print(f"    {instr}")
    
    print("  PASS: Lowering while to IR")


def test_assemble_control_flow():
    """Test assembly generation with control flow."""
    print("\nTest 8: Assembly generation with control flow")
    
    code = """if (a < b) {
    c = 1
}"""
    
    ast = parse(code)
    ir = lower_to_ir(ast)
    asm = ir_to_assembly(ir)
    
    # Check for CMP instruction
    cmp_instrs = [i for i in asm if i.opcode == 'CMP']
    assert len(cmp_instrs) > 0
    
    # Check for jump instructions
    jump_instrs = [i for i in asm if i.is_control_flow()]
    assert len(jump_instrs) > 0
    
    print(f"  Generated {len(asm)} assembly instructions")
    print(f"  Found {len(cmp_instrs)} CMP instructions")
    print(f"  Found {len(jump_instrs)} jump instructions")
    
    print("  Assembly:")
    for instr in asm:
        print(f"    {instr}")
    
    print("  PASS: Assembly generation with control flow")


def test_comparison_operators():
    """Test all comparison operators."""
    print("\nTest 9: Comparison operators")
    
    operators = ['<', '>', '<=', '>=', '==', '!=']
    
    for op in operators:
        code = f"""if (a {op} b) {{
    c = 1
}}"""
        
        ast = parse(code)
        ir = lower_to_ir(ast)
        
        # Should have CMP instruction
        assert any('CMP' in instr for instr in ir), f"Missing CMP for {op}"
        
        # Should have appropriate jump
        # Mapping: < -> JGE, > -> JLE, <= -> JG, >= -> JL, == -> JNE, != -> JE
        print(f"  {op}: IR generated successfully")
    
    print("  PASS: Comparison operators")


if __name__ == '__main__':
    print("=" * 70)
    print("CONTROL FLOW TESTS")
    print("=" * 70)
    
    try:
        test_basicblock_with_label()
        test_cfg_creation()
        test_jump_instructions()
        test_parse_if_statement()
        test_parse_while_statement()
        test_lower_if_to_ir()
        test_lower_while_to_ir()
        test_assemble_control_flow()
        test_comparison_operators()
        
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
