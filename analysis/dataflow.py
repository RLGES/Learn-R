"""
Dataflow analysis for control flow graphs.

Implements reaching definitions analysis to track which variable definitions
reach each program point. Foundation for dead code elimination and other
optimizations.
"""
from typing import Dict, Set, List, Tuple
from dataclasses import dataclass, field
from asm_ir import CFG, BasicBlock, Instruction


@dataclass
class Definition:
    """
    Represents a variable definition (assignment).
    
    Tracks where a variable is defined and what instruction defines it.
    """
    variable: str         # Variable name (e.g., "rax", "rax_1" if SSA)
    block_label: str      # Block where definition occurs
    instr_index: int      # Index of instruction in block
    instruction: Instruction  # The defining instruction
    
    def __str__(self) -> str:
        return f"{self.variable}@{self.block_label}[{self.instr_index}]"
    
    def __repr__(self) -> str:
        return f"Def({self.variable}, {self.block_label}, {self.instr_index})"
    
    def __hash__(self) -> int:
        return hash((self.variable, self.block_label, self.instr_index))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Definition):
            return False
        return (self.variable == other.variable and 
                self.block_label == other.block_label and
                self.instr_index == other.instr_index)


class ReachingDefinitions:
    """
    Computes reaching definitions for a CFG.
    
    A definition reaches a point if there exists a path from the definition
    to that point along which the variable is not redefined.
    """
    
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.gen: Dict[str, Set[Definition]] = {}  # GEN[block] = definitions generated in block
        self.kill: Dict[str, Set[Definition]] = {}  # KILL[block] = definitions killed in block
        self.in_set: Dict[str, Set[Definition]] = {}  # IN[block] = definitions reaching block entry
        self.out_set: Dict[str, Set[Definition]] = {}  # OUT[block] = definitions reaching block exit
        self.all_definitions: Set[Definition] = set()  # All definitions in program
    
    def collect_definitions(self):
        """Collect all variable definitions in the CFG."""
        for label, block in self.cfg.blocks.items():
            for idx, instr in enumerate(block.instructions):
                for var in instr.writes():
                    defn = Definition(var, label, idx, instr)
                    self.all_definitions.add(defn)
    
    def compute_gen_kill(self):
        """
        Compute GEN and KILL sets for each block.
        
        GEN[B] = definitions generated in B (not killed by later defs in B)
        KILL[B] = definitions killed by B (redefined elsewhere)
        """
        for label, block in self.cfg.blocks.items():
            gen = set()
            kill = set()
            local_defs = {}  # Variable -> most recent definition in this block
            
            # Process instructions in order
            for idx, instr in enumerate(block.instructions):
                for var in instr.writes():
                    # This definition generates a new reaching def
                    defn = Definition(var, label, idx, instr)
                    
                    # Kill previous definition of same variable in this block
                    if var in local_defs:
                        gen.discard(local_defs[var])
                    
                    # Add to gen set
                    gen.add(defn)
                    local_defs[var] = defn
                    
                    # Kill all other definitions of this variable (from other blocks)
                    for other_def in self.all_definitions:
                        if other_def.variable == var and other_def.block_label != label:
                            kill.add(other_def)
                        elif other_def.variable == var and other_def.block_label == label and other_def.instr_index != idx:
                            kill.add(other_def)
            
            self.gen[label] = gen
            self.kill[label] = kill
    
    def analyze(self):
        """
        Perform reaching definitions analysis.
        
        Computes IN and OUT sets for each block using iterative dataflow equations:
        
        IN[B] = ∪ (OUT[P] for P in predecessors(B))
        OUT[B] = GEN[B] ∪ (IN[B] - KILL[B])
        """
        # Step 1: Collect all definitions
        self.collect_definitions()
        
        # Step 2: Compute GEN and KILL sets
        self.compute_gen_kill()
        
        # Step 3: Initialize IN and OUT sets
        for label in self.cfg.blocks:
            self.in_set[label] = set()
            self.out_set[label] = set()
        
        # Step 4: Iterate until fixed point
        changed = True
        iterations = 0
        max_iterations = 100
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for label, block in self.cfg.blocks.items():
                # Compute IN[B] = ∪ OUT[P] for predecessors P
                new_in = set()
                for pred_label in self.get_predecessors(label):
                    new_in.update(self.out_set[pred_label])
                
                # Compute OUT[B] = GEN[B] ∪ (IN[B] - KILL[B])
                new_out = self.gen[label].union(new_in - self.kill[label])
                
                # Check if anything changed
                if new_in != self.in_set[label] or new_out != self.out_set[label]:
                    changed = True
                    self.in_set[label] = new_in
                    self.out_set[label] = new_out
        
        if iterations >= max_iterations:
            print(f"Warning: Reaching definitions analysis did not converge after {max_iterations} iterations")
    
    def get_predecessors(self, block_label: str) -> List[str]:
        """Get list of predecessor blocks."""
        predecessors = []
        for label, block in self.cfg.blocks.items():
            if block_label in block.successors:
                predecessors.append(label)
        return predecessors
    
    def get_reaching_definitions(self, block_label: str, instr_index: int) -> Set[Definition]:
        """
        Get definitions that reach a specific instruction.
        
        Args:
            block_label: Label of the block
            instr_index: Index of instruction in block
        
        Returns:
            Set of definitions reaching this point
        """
        block = self.cfg.get_block(block_label)
        if not block:
            return set()
        
        # Start with IN set for block
        reaching = set(self.in_set[block_label])
        
        # Apply effects of instructions before this one
        for idx in range(instr_index):
            instr = block.instructions[idx]
            for var in instr.writes():
                # Remove previous definitions of this variable
                reaching = {d for d in reaching if d.variable != var}
                # Add this definition
                reaching.add(Definition(var, block_label, idx, instr))
        
        return reaching
    
    def print_results(self):
        """Print analysis results for debugging."""
        print("\n" + "=" * 70)
        print("REACHING DEFINITIONS ANALYSIS")
        print("=" * 70)
        
        for label, block in self.cfg.blocks.items():
            print(f"\nBlock: {label}")
            print(f"  GEN: {{{', '.join(str(d) for d in self.gen[label])}}}")
            print(f"  KILL: {{{', '.join(str(d) for d in self.kill[label])}}}")
            print(f"  IN: {{{', '.join(str(d) for d in self.in_set[label])}}}")
            print(f"  OUT: {{{', '.join(str(d) for d in self.out_set[label])}}}")


class LivenessAnalysis:
    """
    Computes live variable analysis for a CFG.
    
    A variable is live at a point if its value may be used before being redefined.
    Used for dead code elimination.
    """
    
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.use: Dict[str, Set[str]] = {}  # USE[block] = variables used before definition
        self.def_set: Dict[str, Set[str]] = {}  # DEF[block] = variables defined in block
        self.live_in: Dict[str, Set[str]] = {}  # LIVE_IN[block] = variables live at block entry
        self.live_out: Dict[str, Set[str]] = {}  # LIVE_OUT[block] = variables live at block exit
    
    def compute_use_def(self):
        """
        Compute USE and DEF sets for each block.
        
        USE[B] = variables used before being defined in B
        DEF[B] = variables defined in B
        """
        for label, block in self.cfg.blocks.items():
            use = set()
            def_set = set()
            
            for instr in block.instructions:
                # Variables used in this instruction
                for var in instr.reads():
                    if var not in def_set and not var.isdigit():
                        use.add(var)
                
                # Variables defined in this instruction
                for var in instr.writes():
                    def_set.add(var)
            
            self.use[label] = use
            self.def_set[label] = def_set
    
    def analyze(self):
        """
        Perform liveness analysis.
        
        Computes LIVE_IN and LIVE_OUT sets using backward dataflow equations:
        
        LIVE_OUT[B] = ∪ (LIVE_IN[S] for S in successors(B))
        LIVE_IN[B] = USE[B] ∪ (LIVE_OUT[B] - DEF[B])
        """
        # Step 1: Compute USE and DEF sets
        self.compute_use_def()
        
        # Step 2: Initialize LIVE_IN and LIVE_OUT sets
        for label in self.cfg.blocks:
            self.live_in[label] = set()
            self.live_out[label] = set()
        
        # Step 3: Iterate backward until fixed point
        changed = True
        iterations = 0
        max_iterations = 100
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            # Process blocks in reverse order (backward analysis)
            for label in reversed(list(self.cfg.blocks.keys())):
                block = self.cfg.blocks[label]
                
                # Compute LIVE_OUT[B] = ∪ LIVE_IN[S] for successors S
                new_out = set()
                for succ_label in block.successors:
                    new_out.update(self.live_in[succ_label])
                
                # Compute LIVE_IN[B] = USE[B] ∪ (LIVE_OUT[B] - DEF[B])
                new_in = self.use[label].union(new_out - self.def_set[label])
                
                # Check if anything changed
                if new_in != self.live_in[label] or new_out != self.live_out[label]:
                    changed = True
                    self.live_in[label] = new_in
                    self.live_out[label] = new_out
        
        if iterations >= max_iterations:
            print(f"Warning: Liveness analysis did not converge after {max_iterations} iterations")
    
    def is_live_after(self, block_label: str, instr_index: int, variable: str) -> bool:
        """
        Check if a variable is live after a specific instruction.
        
        Args:
            block_label: Label of the block
            instr_index: Index of instruction in block
            variable: Variable to check
        
        Returns:
            True if variable is live after this instruction
        """
        block = self.cfg.get_block(block_label)
        if not block:
            return False
        
        # Start with LIVE_OUT for block
        live = set(self.live_out[block_label])
        
        # Work backwards from end of block to this instruction
        for idx in range(len(block.instructions) - 1, instr_index, -1):
            instr = block.instructions[idx]
            
            # Variable is live if used here
            for var in instr.reads():
                if not var.isdigit():
                    live.add(var)
            
            # Variable is not live if defined here (unless used later)
            for var in instr.writes():
                if var not in instr.reads():
                    live.discard(var)
        
        return variable in live
    
    def print_results(self):
        """Print analysis results for debugging."""
        print("\n" + "=" * 70)
        print("LIVENESS ANALYSIS")
        print("=" * 70)
        
        for label, block in self.cfg.blocks.items():
            print(f"\nBlock: {label}")
            print(f"  USE: {{{', '.join(self.use[label])}}}")
            print(f"  DEF: {{{', '.join(self.def_set[label])}}}")
            print(f"  LIVE_IN: {{{', '.join(self.live_in[label])}}}")
            print(f"  LIVE_OUT: {{{', '.join(self.live_out[label])}}}")


def compute_reaching_definitions(cfg: CFG) -> ReachingDefinitions:
    """
    Compute reaching definitions for a CFG.
    
    Args:
        cfg: Control flow graph
    
    Returns:
        ReachingDefinitions analysis result
    """
    rd = ReachingDefinitions(cfg)
    rd.analyze()
    return rd


def compute_liveness(cfg: CFG) -> LivenessAnalysis:
    """
    Compute live variables for a CFG.
    
    Args:
        cfg: Control flow graph
    
    Returns:
        LivenessAnalysis result
    """
    liveness = LivenessAnalysis(cfg)
    liveness.analyze()
    return liveness
