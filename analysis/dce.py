"""
Dead Code Elimination (DCE) optimization pass.

Removes instructions whose results are never used. Uses liveness analysis
to identify dead code.
"""
from typing import Set, List
from asm_ir import CFG, BasicBlock, Instruction
from analysis.dataflow import LivenessAnalysis, compute_liveness


class DeadCodeEliminator:
    """
    Eliminates dead code from a CFG.
    
    An instruction is dead if:
    1. It writes to a variable that is not live after the instruction
    2. It has no side effects (e.g., not a call, not a memory write)
    """
    
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.liveness: LivenessAnalysis = None
        self.eliminated_count = 0
    
    def has_side_effects(self, instr: Instruction) -> bool:
        """
        Check if instruction has side effects.
        
        Instructions with side effects cannot be eliminated even if their
        destination is dead (e.g., function calls, memory writes).
        """
        # Memory operations have side effects
        if instr.opcode in ['STORE', 'PUSH']:
            return True
        
        # Calls have side effects
        if instr.opcode in ['CALL', 'SYSCALL']:
            return True
        
        # Control flow instructions are not dead
        if instr.opcode in ['JMP', 'JE', 'JNE', 'JG', 'JL', 'JGE', 'JLE', 
                           'RET', 'HALT']:
            return True
        
        # Instructions with no destination cannot be dead
        if not instr.dst:
            return True
        
        return False
    
    def is_dead_instruction(self, block_label: str, instr_index: int, instr: Instruction) -> bool:
        """
        Check if an instruction is dead.
        
        Args:
            block_label: Block containing the instruction
            instr_index: Index of instruction in block
            instr: The instruction to check
        
        Returns:
            True if instruction is dead and can be eliminated
        """
        # Instructions with side effects are not dead
        if self.has_side_effects(instr):
            return False
        
        # If no destination, cannot be dead (phi nodes, labels, etc.)
        if not instr.dst:
            return False
        
        # Check if destination is live after this instruction
        return not self.liveness.is_live_after(block_label, instr_index, instr.dst)
    
    def eliminate(self) -> int:
        """
        Eliminate dead code from the CFG.
        
        Returns:
            Number of instructions eliminated
        """
        # Run liveness analysis
        self.liveness = compute_liveness(self.cfg)
        
        # Track eliminated instructions
        self.eliminated_count = 0
        
        # Mark dead instructions
        to_remove = []  # List of (block_label, instr_index) tuples
        
        for label, block in self.cfg.blocks.items():
            for idx, instr in enumerate(block.instructions):
                if self.is_dead_instruction(label, idx, instr):
                    to_remove.append((label, idx))
        
        # Remove dead instructions (in reverse order to maintain indices)
        for label, idx in sorted(to_remove, key=lambda x: (x[0], -x[1])):
            block = self.cfg.get_block(label)
            if block and idx < len(block.instructions):
                removed = block.instructions.pop(idx)
                self.eliminated_count += 1
                print(f"[DCE] Eliminated: {removed} in {label}[{idx}]")
        
        return self.eliminated_count
    
    def print_statistics(self):
        """Print DCE statistics."""
        print("\n" + "=" * 70)
        print("DEAD CODE ELIMINATION")
        print("=" * 70)
        print(f"Instructions eliminated: {self.eliminated_count}")


class AggressiveDeadCodeEliminator:
    """
    More aggressive DCE that also eliminates unreachable code.
    
    Uses a worklist algorithm to mark live code, then removes everything else.
    """
    
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.liveness: LivenessAnalysis = None
        self.live_instructions: Set[tuple] = set()  # (block_label, instr_index)
        self.eliminated_count = 0
    
    def mark_live(self):
        """
        Mark all live instructions using a worklist algorithm.
        
        Start with critical instructions (calls, stores, returns) and work
        backwards marking all instructions they depend on.
        """
        worklist = []
        
        # Step 1: Mark all critical instructions as live
        for label, block in self.cfg.blocks.items():
            for idx, instr in enumerate(block.instructions):
                if self.is_critical(instr):
                    self.live_instructions.add((label, idx))
                    worklist.append((label, idx, instr))
        
        # Step 2: Work backwards from live instructions
        while worklist:
            block_label, instr_index, instr = worklist.pop()
            
            # Get all variables this instruction reads
            reads = instr.reads()
            
            # Find instructions that define those variables
            for var in reads:
                # Get reaching definitions for this instruction
                reaching = self.get_reaching_definitions(block_label, instr_index, var)
                
                for def_label, def_index in reaching:
                    if (def_label, def_index) not in self.live_instructions:
                        self.live_instructions.add((def_label, def_index))
                        def_block = self.cfg.get_block(def_label)
                        if def_block and def_index < len(def_block.instructions):
                            worklist.append((def_label, def_index, def_block.instructions[def_index]))
    
    def is_critical(self, instr: Instruction) -> bool:
        """
        Check if instruction is critical (must not be eliminated).
        
        Critical instructions include:
        - Memory writes (STORE, PUSH)
        - Function calls
        - Returns and control flow
        """
        return (instr.opcode in ['STORE', 'PUSH', 'CALL', 'SYSCALL', 
                                 'RET', 'HALT', 'JMP', 'JE', 'JNE', 
                                 'JG', 'JL', 'JGE', 'JLE'])
    
    def get_reaching_definitions(self, block_label: str, instr_index: int, variable: str) -> List[tuple]:
        """
        Get reaching definitions for a variable at a specific instruction.
        
        Returns:
            List of (block_label, instr_index) tuples
        """
        # Simple implementation: look for definitions in same block before this instruction
        definitions = []
        block = self.cfg.get_block(block_label)
        if not block:
            return definitions
        
        # Search backwards in current block
        for idx in range(instr_index - 1, -1, -1):
            instr = block.instructions[idx]
            if variable in instr.writes():
                definitions.append((block_label, idx))
                return definitions  # First definition found
        
        # If not found in current block, search predecessors
        for pred_label in self.get_predecessors(block_label):
            pred_block = self.cfg.get_block(pred_label)
            if pred_block:
                # Search backwards from end of predecessor
                for idx in range(len(pred_block.instructions) - 1, -1, -1):
                    instr = pred_block.instructions[idx]
                    if variable in instr.writes():
                        definitions.append((pred_label, idx))
                        break
        
        return definitions
    
    def get_predecessors(self, block_label: str) -> List[str]:
        """Get predecessor blocks."""
        predecessors = []
        for label, block in self.cfg.blocks.items():
            if block_label in block.successors:
                predecessors.append(label)
        return predecessors
    
    def eliminate(self) -> int:
        """
        Eliminate dead code using aggressive algorithm.
        
        Returns:
            Number of instructions eliminated
        """
        # Run liveness analysis
        self.liveness = compute_liveness(self.cfg)
        
        # Mark live instructions
        self.mark_live()
        
        # Remove dead instructions
        to_remove = []
        for label, block in self.cfg.blocks.items():
            for idx in range(len(block.instructions)):
                if (label, idx) not in self.live_instructions:
                    to_remove.append((label, idx))
        
        # Remove in reverse order
        for label, idx in sorted(to_remove, key=lambda x: (x[0], -x[1])):
            block = self.cfg.get_block(label)
            if block and idx < len(block.instructions):
                removed = block.instructions.pop(idx)
                self.eliminated_count += 1
                print(f"[Aggressive DCE] Eliminated: {removed} in {label}[{idx}]")
        
        return self.eliminated_count


def eliminate_dead_code(cfg: CFG, aggressive: bool = False) -> int:
    """
    Eliminate dead code from a CFG.
    
    Args:
        cfg: Control flow graph
        aggressive: If True, use aggressive DCE algorithm
    
    Returns:
        Number of instructions eliminated
    """
    if aggressive:
        eliminator = AggressiveDeadCodeEliminator(cfg)
    else:
        eliminator = DeadCodeEliminator(cfg)
    
    return eliminator.eliminate()


def iterative_dce(cfg: CFG, max_iterations: int = 10) -> int:
    """
    Run DCE iteratively until no more dead code is found.
    
    DCE can expose new dead code, so multiple passes may be beneficial.
    
    Args:
        cfg: Control flow graph
        max_iterations: Maximum number of DCE passes
    
    Returns:
        Total number of instructions eliminated
    """
    total_eliminated = 0
    iteration = 0
    
    while iteration < max_iterations:
        eliminated = eliminate_dead_code(cfg, aggressive=False)
        total_eliminated += eliminated
        iteration += 1
        
        if eliminated == 0:
            break
        
        print(f"[DCE] Pass {iteration}: Eliminated {eliminated} instructions")
    
    print(f"[DCE] Total eliminated after {iteration} passes: {total_eliminated}")
    return total_eliminated
