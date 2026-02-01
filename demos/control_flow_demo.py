"""
Demo: Control flow support with if/while statements.

Showcases:
- If statements with comparison operators
- While loops
- CFG construction
- Per-block optimization
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from frontend import parse, lower_to_ir, ir_to_assembly
from asm_ir import CFG, BasicBlock, Instruction
from pipeline.full_pipeline import run_full_pipeline


def demo_if_statement():
    """Demonstrate if statement compilation."""
    print("\n" + "=" * 70)
    print("DEMO 1: IF STATEMENT")
    print("=" * 70)
    
    code = """a = 5
b = 10
if (a < b) {
    c = a
} else {
    c = b
}
d = c + 1"""
    
    print("\nSource Code:")
    print(code)
    
    # Parse
    ast = parse(code)
    print("\nAST:")
    for stmt in ast.statements:
        print(f"  {stmt}")
    
    # Lower to IR
    ir = lower_to_ir(ast)
    print("\nIR (Three-Address Code with Jumps):")
    for instr in ir:
        print(f"  {instr}")
    
    # Generate assembly
    asm = ir_to_assembly(ir)
    print(f"\nAssembly ({len(asm)} instructions):")
    for i, instr in enumerate(asm):
        print(f"  {i:2d}. {instr}")


def demo_while_loop():
    """Demonstrate while loop compilation."""
    print("\n" + "=" * 70)
    print("DEMO 2: WHILE LOOP")
    print("=" * 70)
    
    code = """i = 0
sum = 0
while (i < 5) {
    sum = sum + i
    i = i + 1
}"""
    
    print("\nSource Code:")
    print(code)
    
    # Parse
    ast = parse(code)
    print("\nAST:")
    for stmt in ast.statements:
        print(f"  {stmt}")
    
    # Lower to IR
    ir = lower_to_ir(ast)
    print("\nIR (Three-Address Code with Jumps and Labels):")
    for instr in ir:
        print(f"  {instr}")
    
    # Generate assembly
    asm = ir_to_assembly(ir)
    print(f"\nAssembly ({len(asm)} instructions):")
    for i, instr in enumerate(asm):
        marker = ""
        if instr.is_control_flow():
            marker = " <-- Control Flow"
        elif instr.opcode == 'CMP':
            marker = " <-- Comparison"
        print(f"  {i:2d}. {instr}{marker}")


def demo_nested_control_flow():
    """Demonstrate nested if inside while."""
    print("\n" + "=" * 70)
    print("DEMO 3: NESTED CONTROL FLOW")
    print("=" * 70)
    
    code = """i = 0
while (i < 10) {
    if (i < 5) {
        x = i
    }
    i = i + 1
}"""
    
    print("\nSource Code:")
    print(code)
    
    # Parse
    ast = parse(code)
    
    # Lower to IR
    ir = lower_to_ir(ast)
    print("\nIR (Nested Control Flow):")
    for instr in ir:
        print(f"  {instr}")
    
    # Generate assembly
    asm = ir_to_assembly(ir)
    print(f"\nAssembly ({len(asm)} instructions):")
    
    # Count control flow
    jumps = sum(1 for i in asm if i.is_control_flow())
    cmps = sum(1 for i in asm if i.opcode == 'CMP')
    
    for i, instr in enumerate(asm):
        print(f"  {i:2d}. {instr}")
    
    print(f"\nControl Flow Summary:")
    print(f"  Comparisons: {cmps}")
    print(f"  Jumps: {jumps}")


def demo_comparison_operators():
    """Demonstrate all comparison operators."""
    print("\n" + "=" * 70)
    print("DEMO 4: COMPARISON OPERATORS")
    print("=" * 70)
    
    operators = [
        ('<', 'less than'),
        ('>', 'greater than'),
        ('<=', 'less or equal'),
        ('>=', 'greater or equal'),
        ('==', 'equal'),
        ('!=', 'not equal')
    ]
    
    for op, desc in operators:
        code = f"""if (a {op} b) {{
    c = 1
}}"""
        
        print(f"\n{desc.upper()} ({op}):")
        print(f"  Code: if (a {op} b) {{ c = 1 }}")
        
        ast = parse(code)
        ir = lower_to_ir(ast)
        
        # Find the jump instruction
        jump_instr = next((instr for instr in ir if 'J' in instr and instr != 'JMP'), None)
        if jump_instr:
            print(f"  Generated: {jump_instr} (inverted logic)")


def demo_cfg_construction():
    """Demonstrate CFG construction from control flow."""
    print("\n" + "=" * 70)
    print("DEMO 5: CONTROL FLOW GRAPH")
    print("=" * 70)
    
    # Create a simple CFG manually
    cfg = CFG(entry_label='entry')
    
    # Entry block
    entry = BasicBlock('entry', [
        Instruction('MOV', 'rax', ['0']),
        Instruction('MOV', 'rcx', ['10'])
    ])
    cfg.add_block(entry)
    
    # Loop start block
    loop_start = BasicBlock('loop_start', [
        Instruction('CMP', 'rax', ['rcx']),
        Instruction('JGE', 'loop_end', [], is_control_flow_instr=True)
    ])
    cfg.add_block(loop_start)
    
    # Loop body block
    loop_body = BasicBlock('loop_body', [
        Instruction('ADD', 'rax', ['1']),
        Instruction('JMP', 'loop_start', [], is_control_flow_instr=True)
    ])
    cfg.add_block(loop_body)
    
    # Loop end block
    loop_end = BasicBlock('loop_end', [
        Instruction('MOV', 'rbx', ['rax'])
    ])
    cfg.add_block(loop_end)
    
    # Connect blocks
    cfg.connect_blocks('entry', 'loop_start')
    cfg.connect_blocks('loop_start', 'loop_body')
    cfg.connect_blocks('loop_start', 'loop_end')
    cfg.connect_blocks('loop_body', 'loop_start')
    
    # Display CFG
    print("\nControl Flow Graph:")
    print(cfg)
    
    print("Graph Structure:")
    print("  entry -> loop_start")
    print("  loop_start -> loop_body (if rax < rcx)")
    print("  loop_start -> loop_end (if rax >= rcx)")
    print("  loop_body -> loop_start (back edge)")


def demo_full_pipeline_with_cfg():
    """Demonstrate full pipeline with CFG-based optimization."""
    print("\n" + "=" * 70)
    print("DEMO 6: FULL PIPELINE WITH CONTROL FLOW")
    print("=" * 70)
    
    code = """a = 5
if (a < 10) {
    b = a + 1
    c = b
}"""
    
    print("\nRunning with use_cfg=True:\n")
    
    # Run pipeline with CFG support
    original, optimized, cfg = run_full_pipeline(code, verbose=True, use_cfg=True)
    
    if cfg:
        print("\nCFG Details:")
        print(f"  Blocks: {len(cfg.blocks)}")
        print(f"  Entry: {cfg.entry_label}")


def main():
    """Run all demos."""
    print("=" * 70)
    print("CONTROL FLOW DEMONSTRATIONS")
    print("=" * 70)
    print("\nShowcasing:")
    print("  - If statements with else clauses")
    print("  - While loops")
    print("  - Nested control flow")
    print("  - All comparison operators (<, >, <=, >=, ==, !=)")
    print("  - CFG construction and visualization")
    print("  - Per-block optimization")
    
    demo_if_statement()
    demo_while_loop()
    demo_nested_control_flow()
    demo_comparison_operators()
    demo_cfg_construction()
    demo_full_pipeline_with_cfg()
    
    print("\n" + "=" * 70)
    print("ALL DEMOS COMPLETE")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  [x] If/else statement parsing and lowering")
    print("  [x] While loop parsing and lowering")
    print("  [x] Comparison operators (6 types)")
    print("  [x] Jump instructions (JMP, JE, JNE, JGE, etc.)")
    print("  [x] CMP instruction for comparisons")
    print("  [x] Label generation and tracking")
    print("  [x] CFG construction with basic blocks")
    print("  [x] Control flow edges (successors)")
    print("  [x] Per-block optimization (when CFG enabled)")


if __name__ == '__main__':
    main()
