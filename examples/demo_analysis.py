"""
Demo showing SSA transformation, dataflow analysis, and dead code elimination.
"""
from asm_ir import Instruction, BasicBlock, CFG
from analysis.ssa import convert_cfg_to_ssa
from analysis.dataflow import compute_reaching_definitions, compute_liveness
from analysis.dce import eliminate_dead_code, iterative_dce


def demo_complete_optimization_pipeline():
    """
    Demonstrate complete optimization pipeline:
    1. Original code with dead code and inefficiencies
    2. SSA transformation
    3. Dataflow analysis (reaching definitions and liveness)
    4. Dead code elimination
    """
    print("=" * 80)
    print("COMPLETE OPTIMIZATION PIPELINE DEMO")
    print("=" * 80)
    
    # Create a more complex CFG with:
    # - Dead code
    # - Control flow (if statement)
    # - Multiple definitions of same variable
    
    print("\nSource Code (pseudo):")
    print("""
    entry:
        x = 10
        y = 20        # y is dead - never used
        z = 5
        if (x > 0) goto then else else_
    
    then:
        x = x + 1
        a = x * 2
        goto merge
    
    else_:
        x = x - 1
        b = 100       # b is dead - never used
        goto merge
    
    merge:
        result = x + z
        unused = 999  # unused is dead
    """)
    
    # Build CFG
    entry = BasicBlock("entry")
    entry.instructions.append(Instruction("MOV", "x", ["10"]))
    entry.instructions.append(Instruction("MOV", "y", ["20"]))  # DEAD
    entry.instructions.append(Instruction("MOV", "z", ["5"]))
    entry.instructions.append(Instruction("CMP", None, ["x", "0"]))
    entry.successors = ["then", "else_"]
    
    then_block = BasicBlock("then")
    then_block.instructions.append(Instruction("ADD", "x", ["x", "1"]))
    then_block.instructions.append(Instruction("MUL", "a", ["x", "2"]))
    then_block.successors = ["merge"]
    
    else_block = BasicBlock("else_")
    else_block.instructions.append(Instruction("SUB", "x", ["x", "1"]))
    else_block.instructions.append(Instruction("MOV", "b", ["100"]))  # DEAD
    else_block.successors = ["merge"]
    
    merge = BasicBlock("merge")
    merge.instructions.append(Instruction("ADD", "result", ["x", "z"]))
    merge.instructions.append(Instruction("MOV", "unused", ["999"]))  # DEAD
    
    cfg = CFG()
    cfg.add_block(entry)
    cfg.add_block(then_block)
    cfg.add_block(else_block)
    cfg.add_block(merge)
    cfg.entry_label = "entry"
    
    # Step 1: Show original CFG
    print("\n" + "-" * 80)
    print("STEP 1: Original CFG")
    print("-" * 80)
    print(cfg)
    
    total_instructions = sum(len(block.instructions) for block in cfg.blocks.values())
    print(f"\nTotal instructions: {total_instructions}")
    
    # Step 2: Convert to SSA
    print("\n" + "-" * 80)
    print("STEP 2: SSA Transformation")
    print("-" * 80)
    print("Converting to Static Single Assignment form...")
    print("This will:")
    print("  - Give each variable definition a unique version (x -> x_0, x_1, x_2)")
    print("  - Insert phi nodes at join points where multiple definitions merge")
    
    convert_cfg_to_ssa(cfg)
    
    print("\nSSA Form:")
    print(cfg)
    
    # Step 3: Dataflow Analysis
    print("\n" + "-" * 80)
    print("STEP 3: Dataflow Analysis")
    print("-" * 80)
    
    print("\n--- Reaching Definitions ---")
    print("Tracks which variable definitions reach each program point.")
    rd = compute_reaching_definitions(cfg)
    rd.print_results()
    
    print("\n--- Liveness Analysis ---")
    print("Tracks which variables are used after each program point.")
    liveness = compute_liveness(cfg)
    liveness.print_results()
    
    # Step 4: Dead Code Elimination
    print("\n" + "-" * 80)
    print("STEP 4: Dead Code Elimination")
    print("-" * 80)
    print("Removing instructions whose results are never used...")
    
    eliminated = eliminate_dead_code(cfg)
    
    print(f"\n[DCE] Eliminated {eliminated} dead instructions")
    
    print("\nOptimized CFG:")
    print(cfg)
    
    total_after = sum(len(block.instructions) for block in cfg.blocks.values())
    reduction = total_instructions - total_after
    percent = (reduction / total_instructions * 100) if total_instructions > 0 else 0
    
    # Step 5: Summary
    print("\n" + "=" * 80)
    print("OPTIMIZATION SUMMARY")
    print("=" * 80)
    print(f"Instructions before:     {total_instructions}")
    print(f"Instructions after:      {total_after}")
    print(f"Reduction:              {reduction} instructions ({percent:.1f}%)")
    print(f"\nDead code eliminated:")
    print(f"  - y = 20 (never used)")
    print(f"  - b = 100 (never used)")
    print(f"  - unused = 999 (never used)")
    print(f"\nKey optimizations:")
    print(f"  [OK] SSA form enables precise dataflow analysis")
    print(f"  [OK] Liveness analysis identifies dead variables")
    print(f"  [OK] Dead code elimination removes unused instructions")
    
    print("\n" + "=" * 80)


def demo_ssa_phi_nodes():
    """Demonstrate phi node insertion at merge points."""
    print("\n" + "=" * 80)
    print("PHI NODE DEMO")
    print("=" * 80)
    
    print("\nWhen control flow merges, SSA uses phi nodes to merge variable versions:")
    print("""
    entry:
        x = 1         # x_0 = 1
        if cond goto then else else_
    
    then:
        x = 2         # x_1 = 2
        goto merge
    
    else_:
        x = 3         # x_2 = 3
        goto merge
    
    merge:
        # x could be x_1 or x_2 depending on which path was taken
        # SSA inserts: x_3 = PHI(x_1, x_2)
        y = x         # y_0 = x_3
    """)
    
    # Build CFG
    entry = BasicBlock("entry")
    entry.instructions.append(Instruction("MOV", "x", ["1"]))
    entry.instructions.append(Instruction("CMP", None, ["cond", "1"]))
    entry.successors = ["then", "else_"]
    
    then_block = BasicBlock("then")
    then_block.instructions.append(Instruction("MOV", "x", ["2"]))
    then_block.successors = ["merge"]
    
    else_block = BasicBlock("else_")
    else_block.instructions.append(Instruction("MOV", "x", ["3"]))
    else_block.successors = ["merge"]
    
    merge = BasicBlock("merge")
    merge.instructions.append(Instruction("MOV", "y", ["x"]))
    
    cfg = CFG()
    cfg.add_block(entry)
    cfg.add_block(then_block)
    cfg.add_block(else_block)
    cfg.add_block(merge)
    cfg.entry_label = "entry"
    
    print("\nOriginal CFG:")
    print(cfg)
    
    print("\nConverting to SSA...")
    convert_cfg_to_ssa(cfg)
    
    print("\nSSA Form with Phi Nodes:")
    print(cfg)
    
    print("\n[INFO] Phi nodes merge multiple definitions of the same variable")
    print("[INFO] They are implicit in the SSA representation")


def demo_loop_optimization():
    """Demonstrate optimization on a loop."""
    print("\n" + "=" * 80)
    print("LOOP OPTIMIZATION DEMO")
    print("=" * 80)
    
    print("\nOriginal loop with dead code:")
    print("""
    entry:
        i = 0
        sum = 0
        temp = 100     # Dead: never used in loop
    
    loop:
        sum = sum + i
        temp2 = 50     # Dead: value overwritten each iteration
        i = i + 1
        if i < 10 goto loop
    
    exit:
        result = sum
    """)
    
    # Build CFG
    entry = BasicBlock("entry")
    entry.instructions.append(Instruction("MOV", "i", ["0"]))
    entry.instructions.append(Instruction("MOV", "sum", ["0"]))
    entry.instructions.append(Instruction("MOV", "temp", ["100"]))  # DEAD
    entry.successors = ["loop"]
    
    loop = BasicBlock("loop")
    loop.instructions.append(Instruction("ADD", "sum", ["sum", "i"]))
    loop.instructions.append(Instruction("MOV", "temp2", ["50"]))  # DEAD
    loop.instructions.append(Instruction("ADD", "i", ["i", "1"]))
    loop.instructions.append(Instruction("CMP", None, ["i", "10"]))
    loop.successors = ["loop", "exit"]
    
    exit_block = BasicBlock("exit")
    exit_block.instructions.append(Instruction("MOV", "result", ["sum"]))
    
    cfg = CFG()
    cfg.add_block(entry)
    cfg.add_block(loop)
    cfg.add_block(exit_block)
    cfg.entry_label = "entry"
    
    print("\nBefore optimization:")
    print(cfg)
    
    total_before = sum(len(block.instructions) for block in cfg.blocks.values())
    
    # Run iterative DCE
    print("\nRunning iterative dead code elimination...")
    eliminated = iterative_dce(cfg, max_iterations=5)
    
    print("\nAfter optimization:")
    print(cfg)
    
    total_after = sum(len(block.instructions) for block in cfg.blocks.values())
    
    print("\n" + "-" * 80)
    print(f"Instructions before: {total_before}")
    print(f"Instructions after:  {total_after}")
    print(f"Eliminated:         {eliminated} dead instructions")
    print("-" * 80)


def main():
    """Run all demos."""
    demo_complete_optimization_pipeline()
    demo_ssa_phi_nodes()
    demo_loop_optimization()
    
    print("\n" + "=" * 80)
    print("ALL DEMOS COMPLETED")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  1. SSA transformation makes dataflow explicit")
    print("  2. Reaching definitions track where values come from")
    print("  3. Liveness analysis identifies which values are still needed")
    print("  4. Dead code elimination removes unused computations")
    print("  5. Multiple optimization passes can expose more opportunities")


if __name__ == "__main__":
    main()
