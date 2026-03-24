"""
End-to-end compilation pipeline.

Pipeline stages:
1. Parse high-level code → AST
2. Lower AST → three-address IR
3. Generate assembly from IR
4. Optimize with hierarchical rewrite engine
5. Display results
"""
import sys
from pathlib import Path

# Add project root to path so we can import modules
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List
from asm_ir import Instruction, BasicBlock, CFG
from frontend import parse, lower_to_ir, ir_to_assembly
from hierarchical_engine import HierarchicalEngine
from hierarchical_engine.egraph_api import EGraphAPI
from rewrite_rules.tier1_peephole import (
    mov_elimination_rule,
    add_sub_cancel_rule,
    mov_overwrite_rule,
    double_add_rule
)


class StubEGraph(EGraphAPI):
    """
    Stub e-graph implementation that applies rewrites directly.
    
    This modifies the block in place rather than building an e-graph.
    Sufficient for demonstrating the frontend pipeline.
    """
    
    def __init__(self):
        self.block = None  # Will be set by the engine
        self.applied_rules = []
    
    def add_sequence(self, instructions: List[Instruction]):
        """Store reference - actual modifications happen via block."""
        pass
    
    def apply_rewrite(self, rule, match):
        """
        Apply a rewrite rule by modifying the block's instructions in place.
        
        Args:
            rule: RewriteRule object with lhs and rhs patterns
            match: Match object with start_index and bindings
        """
        from rewrite_rules.rule_base import InstructionPattern
        from asm_ir import Instruction
        
        self.applied_rules.append(rule.name)
        
        # Convert RHS patterns to actual instructions using bindings
        rhs_instructions = []
        for pattern in rule.rhs:
            # Substitute variables in pattern with values from bindings
            dst = pattern.dst
            srcs = list(pattern.srcs) if pattern.srcs else []
            
            # Replace variables with bound values
            if dst and dst in match.bindings:
                dst = match.bindings[dst]
            srcs = [match.bindings.get(s, s) for s in srcs]
            
            rhs_instructions.append(Instruction(pattern.opcode, dst, srcs))
        
        # Apply replacement in the block (hacky but works for demo)
        # Get the block from the match object (it has a reference)
        if hasattr(match, 'block'):
            target_block = match.block
        else:
            # Fallback: assume we're working with a global block
            # This is set by the run_full_pipeline function
            target_block = self.block
        
        if target_block:
            start_idx = match.start_index
            lhs_len = len(rule.lhs)
            
            # Remove LHS instructions
            for _ in range(lhs_len):
                if start_idx < len(target_block.instructions):
                    target_block.instructions.pop(start_idx)
            
            # Insert RHS instructions
            for i, instr in enumerate(rhs_instructions):
                target_block.instructions.insert(start_idx + i, instr)
    
    def get_recent_eclasses(self):
        """Return empty - no e-classes in stub."""
        return []
    
    def extract_best(self) -> List[Instruction]:
        """Return the block's instructions (which we've been modifying)."""
        if self.block:
            return self.block.instructions
        return []
    
    def get_applied_rules(self) -> List[str]:
        """Return list of applied rule names."""
        return self.applied_rules


def build_cfg_from_assembly(instructions: List[Instruction]) -> CFG:
    """
    Build a Control Flow Graph from a list of assembly instructions.
    
    Splits instructions into basic blocks at:
    - Labels (start of new block)
    - Jump instructions (end of current block)
    - Instructions following jumps (start of new block)
    
    Args:
        instructions: List of assembly Instruction objects
    
    Returns:
        CFG with basic blocks and edges
    """
    cfg = CFG(entry_label="entry")
    
    # First pass: identify labels and their positions
    labels_at_position = {}  # position -> label
    label_positions = {}     # label -> position
    
    # Track positions where labels should be (from jump targets)
    jump_targets = set()
    
    for i, instr in enumerate(instructions):
        # Check if instruction is a control flow instruction with a target
        if instr.is_control_flow() and instr.dst:
            jump_targets.add(instr.dst)
    
    # Second pass: create basic blocks
    current_label = "entry"
    current_instructions = []
    block_starts = {0}  # Position 0 always starts a block
    
    # Identify block boundaries
    for i, instr in enumerate(instructions):
        # Start new block after control flow instruction
        if i > 0 and instructions[i-1].is_control_flow():
            block_starts.add(i)
        
        # Start new block at jump target (if we can identify it)
        # For now, we'll handle explicit labels in IR
    
    # Build blocks
    current_block_start = 0
    current_label = "entry"
    label_counter = 0
    
    for i, instr in enumerate(instructions):
        current_instructions.append(instr)
        
        # End block at control flow instruction
        if instr.is_control_flow():
            block = BasicBlock(current_label, current_instructions)
            cfg.add_block(block)
            
            # Connect to successor(s)
            if instr.opcode == 'JMP':
                # Unconditional jump
                if instr.dst in jump_targets:
                    # Will connect after all blocks created
                    pass
            elif instr.opcode in ['JE', 'JNE', 'JZ', 'JNZ', 'JG', 'JL', 'JGE', 'JLE']:
                # Conditional jump - two successors (fall-through and jump target)
                pass
            
            # Start new block
            current_instructions = []
            label_counter += 1
            current_label = f"block_{label_counter}"
        
        # Also end block if next instruction is a target
        elif i + 1 < len(instructions) and i + 1 in block_starts:
            block = BasicBlock(current_label, current_instructions)
            cfg.add_block(block)
            current_instructions = []
            label_counter += 1
            current_label = f"block_{label_counter}"
    
    # Add final block if non-empty
    if current_instructions:
        block = BasicBlock(current_label, current_instructions)
        cfg.add_block(block)
    
    # Third pass: connect blocks based on control flow
    # (Simplified: just create sequential flow for now)
    block_list = list(cfg.blocks.keys())
    for i in range(len(block_list) - 1):
        current = block_list[i]
        next_block = block_list[i + 1]
        
        # Check if current block ends with unconditional jump
        block = cfg.get_block(current)
        if block.instructions and block.instructions[-1].opcode == 'JMP':
            # Jump to target (simplified: connect to next for now)
            pass
        else:
            # Fall-through to next block
            cfg.connect_blocks(current, next_block)
    
    return cfg


def format_instruction(instr: Instruction) -> str:
    """Format an instruction for display."""
    if instr.srcs:
        return f"{instr.opcode} {instr.dst}, {', '.join(instr.srcs)}"
    else:
        return f"{instr.opcode} {instr.dst if instr.dst else ''}"


def print_instructions(instructions: List[Instruction], title: str = "Instructions"):
    """Pretty-print a list of instructions."""
    print(f"\n{title} ({len(instructions)} instructions):")
    print("-" * 50)
    for i, instr in enumerate(instructions):
        print(f"  {i:2d}. {format_instruction(instr)}")


def run_full_pipeline(source_code: str, verbose: bool = True, use_cfg: bool = False):
    """
    Run the complete compilation and optimization pipeline.
    
    Args:
        source_code: High-level source code string
        verbose: If True, print intermediate results
        use_cfg: If True, build CFG and optimize per-block
    
    Returns:
        Tuple of (original_assembly, optimized_assembly, cfg)
    """
    if verbose:
        print("=" * 70)
        print("FULL COMPILATION PIPELINE")
        print("=" * 70)
        print("\nSource Code:")
        print("-" * 50)
        print(source_code)
    
    # Stage 1: Parse
    if verbose:
        print("\nStage 1: Parsing...")
    ast = parse(source_code)
    if verbose:
        print(f"  - Generated AST with {len(ast.statements)} statements")
        for stmt in ast.statements:
            print(f"    {stmt}")
    
    # Stage 2: Lower to IR
    if verbose:
        print("\nStage 2: Lowering to IR...")
    ir_instructions = lower_to_ir(ast)
    if verbose:
        print(f"  - Generated {len(ir_instructions)} IR instructions")
        for ir_instr in ir_instructions:
            print(f"    {ir_instr}")
    
    # Stage 3: Generate assembly
    if verbose:
        print("\nStage 3: Assembly generation...")
    asm_instructions = ir_to_assembly(ir_instructions)
    if verbose:
        print(f"  - Generated {len(asm_instructions)} assembly instructions")
    
    print_instructions(asm_instructions, "Original Assembly")
    
    # Stage 4: Build CFG if requested
    cfg = None
    if use_cfg and any(instr.is_control_flow() for instr in asm_instructions):
        if verbose:
            print("\nStage 4a: Building Control Flow Graph...")
        cfg = build_cfg_from_assembly(asm_instructions)
        if verbose:
            print(f"  - Built CFG with {len(cfg.blocks)} basic blocks")
            print(f"  - Entry: {cfg.entry_label}")
            for label, block in cfg.blocks.items():
                print(f"    {label}: {len(block.instructions)} instructions, successors: {block.successors}")
    
    # Stage 5: Optimize with rewrite engine
    if verbose:
        if cfg:
            print("\nStage 5: Optimization (per-block hierarchical rewrite)...")
        else:
            print("\nStage 5: Optimization (hierarchical rewrite)...")
    
    # Get optimization rules
    tier1_rules = [
        mov_elimination_rule,
        add_sub_cancel_rule,
        mov_overwrite_rule,
        double_add_rule
    ]
    
    if cfg:
        # Optimize each block separately
        for label, block in cfg.blocks.items():
            if verbose:
                print(f"  Optimizing {label}...")
            
            egraph_api = StubEGraph()
            egraph_api.block = block
            
            engine = HierarchicalEngine(
                egraph_api=egraph_api,
                rules_by_tier={1: tier1_rules}
            )
            
            optimized_block = engine.run(block)
            # Update block in place
            block.instructions = optimized_block.instructions
        
        # Collect all optimized instructions from CFG
        optimized_instructions = []
        for label in sorted(cfg.blocks.keys()):
            block = cfg.get_block(label)
            if block and block.instructions:
                optimized_instructions.extend(block.instructions)
        
        optimized_block = BasicBlock("combined", optimized_instructions)
    else:
        # Single block optimization (original behavior)
        basic_block = BasicBlock("main", asm_instructions)
        
        egraph_api = StubEGraph()
        egraph_api.block = basic_block
        
        engine = HierarchicalEngine(
            egraph_api=egraph_api,
            rules_by_tier={1: tier1_rules}
        )
        
        if verbose:
            print(f"  Running engine with {len(tier1_rules)} optimization rules...")
        
        optimized_block = engine.run(basic_block)
    
    # Stage 6: Results
    print_instructions(optimized_block.instructions, "Optimized Assembly")
    
    # Summary
    print("\n" + "=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    original_count = len(asm_instructions)
    optimized_count = len(optimized_block.instructions)
    reduction = original_count - optimized_count
    reduction_pct = (reduction / original_count * 100) if original_count > 0 else 0
    
    print(f"  Original:  {original_count} instructions")
    print(f"  Optimized: {optimized_count} instructions")
    print(f"  Reduction: {reduction} instructions ({reduction_pct:.1f}%)")
    
    if reduction > 0:
        print(f"  >> Successfully reduced code size!")
    elif reduction == 0:
        print(f"  >> No optimizations applied (already optimal)")
    
    print("=" * 70)
    
    return asm_instructions, optimized_block.instructions, cfg


def main():
    """Run example programs through the pipeline."""
    
    # Example 1: Simple arithmetic
    example1 = """a = 5
b = a + 3
c = b + 1"""
    
    print("\n\n" + "=" * 70)
    print("EXAMPLE 1: Simple Arithmetic")
    print("=" * 70)
    run_full_pipeline(example1)
    
    # Example 2: MOV chain optimization
    example2 = """x = 10
y = x
z = y
w = z"""
    
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: MOV Chain Elimination")
    print("=" * 70)
    run_full_pipeline(example2)
    
    # Example 3: Complex expression
    example3 = """a = 5
b = 3
c = a + b
d = c * 2
e = d - 1"""
    
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: Complex Expression")
    print("=" * 70)
    run_full_pipeline(example3)


if __name__ == "__main__":
    main()
