"""
SSA (Static Single Assignment) transformation for control flow graphs.

Converts basic blocks to SSA form where each variable is assigned exactly once.
Inserts phi nodes at join points where multiple definitions reach.
"""
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass
from asm_ir import CFG, BasicBlock, Instruction


@dataclass
class SSAVariable:
    """
    Represents a variable in SSA form with version number.
    
    Example: x_0, x_1, x_2 for different versions of variable x
    """
    name: str      # Original variable name (e.g., "rax")
    version: int   # SSA version number (0, 1, 2, ...)
    
    def __str__(self) -> str:
        return f"{self.name}_{self.version}"
    
    def __repr__(self) -> str:
        return f"SSAVariable({self.name}, {self.version})"
    
    def __hash__(self) -> int:
        return hash((self.name, self.version))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SSAVariable):
            return False
        return self.name == other.name and self.version == other.version


class SSATransformer:
    """
    Transforms a CFG into SSA form.
    
    Algorithm overview:
    1. Insert phi nodes at dominance frontiers
    2. Rename variables to unique versions
    3. Update all uses to refer to correct versions
    """
    
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self.version_counter: Dict[str, int] = {}  # Variable -> next version
        self.current_version: Dict[str, int] = {}  # Variable -> current version in scope
        self.phi_nodes: Dict[str, List[Tuple[str, List[Tuple[str, str]]]]] = {}  # Block -> phi nodes
        
    def get_next_version(self, var: str) -> int:
        """Get next version number for a variable."""
        if var not in self.version_counter:
            self.version_counter[var] = 0
        version = self.version_counter[var]
        self.version_counter[var] += 1
        return version
    
    def get_current_version(self, var: str) -> int:
        """Get current version of a variable in scope."""
        return self.current_version.get(var, 0)
    
    def set_current_version(self, var: str, version: int):
        """Set current version of a variable."""
        self.current_version[var] = version
    
    def get_all_variables(self) -> Set[str]:
        """Extract all variables used in the CFG."""
        variables = set()
        for block in self.cfg.blocks.values():
            for instr in block.instructions:
                # Get written variables
                for reg in instr.writes():
                    variables.add(reg)
                # Get read variables
                for reg in instr.reads():
                    # Filter out immediates (numbers)
                    if not reg.isdigit():
                        variables.add(reg)
        return variables
    
    def compute_dominators(self) -> Dict[str, Set[str]]:
        """
        Compute dominator sets for each block.
        
        Block A dominates block B if all paths from entry to B go through A.
        
        Returns:
            Dict mapping block label to set of dominators
        """
        blocks = list(self.cfg.blocks.keys())
        entry = self.cfg.entry_label
        
        # Initialize: entry dominates itself, all others dominated by all blocks
        dominators = {}
        dominators[entry] = {entry}
        for block in blocks:
            if block != entry:
                dominators[block] = set(blocks)
        
        # Iteratively compute dominators until fixed point
        changed = True
        while changed:
            changed = False
            for block in blocks:
                if block == entry:
                    continue
                
                # Get predecessors
                preds = self.get_predecessors(block)
                if not preds:
                    continue
                
                # New dominators = {block} ∪ (∩ dominators of predecessors)
                new_dom = {block}
                pred_doms = [dominators[pred] for pred in preds]
                if pred_doms:
                    new_dom = new_dom.union(set.intersection(*pred_doms))
                
                if new_dom != dominators[block]:
                    dominators[block] = new_dom
                    changed = True
        
        return dominators
    
    def get_predecessors(self, block_label: str) -> List[str]:
        """Get list of predecessor blocks."""
        predecessors = []
        for label, block in self.cfg.blocks.items():
            if block_label in block.successors:
                predecessors.append(label)
        return predecessors
    
    def compute_dominance_frontier(self) -> Dict[str, Set[str]]:
        """
        Compute dominance frontier for each block.
        
        Dominance frontier of block A: set of blocks where A's dominance ends.
        This is where phi nodes need to be inserted.
        
        Returns:
            Dict mapping block label to dominance frontier
        """
        dominators = self.compute_dominators()
        df = {block: set() for block in self.cfg.blocks}
        
        for block in self.cfg.blocks:
            preds = self.get_predecessors(block)
            if len(preds) > 1:  # Join point
                for pred in preds:
                    runner = pred
                    # Walk up dominator tree until we dominate block
                    while runner not in dominators[block]:
                        df[runner].add(block)
                        # Move to immediate dominator
                        idom = self.get_immediate_dominator(runner, dominators)
                        if not idom:
                            break
                        runner = idom
        
        return df
    
    def get_immediate_dominator(self, block: str, dominators: Dict[str, Set[str]]) -> Optional[str]:
        """Get immediate dominator of a block."""
        doms = dominators[block] - {block}
        if not doms:
            return None
        # Find dominator that is dominated by all others
        for d in doms:
            if all(d in dominators[other] or d == other for other in doms):
                return d
        return None
    
    def insert_phi_nodes(self, variables: Set[str]):
        """
        Insert phi nodes at dominance frontiers.
        
        For each variable, insert phi nodes at join points where
        multiple definitions reach.
        """
        df = self.compute_dominance_frontier()
        
        for var in variables:
            # Find all blocks that define this variable
            def_blocks = set()
            for label, block in self.cfg.blocks.items():
                for instr in block.instructions:
                    if var in instr.writes():
                        def_blocks.add(label)
                        break
            
            # Insert phi nodes at dominance frontiers
            worklist = list(def_blocks)
            phi_inserted = set()
            
            while worklist:
                block = worklist.pop(0)
                for frontier in df.get(block, set()):
                    if frontier not in phi_inserted:
                        # Insert phi node for this variable
                        if frontier not in self.phi_nodes:
                            self.phi_nodes[frontier] = []
                        
                        # Phi node: var = φ(pred1_val, pred2_val, ...)
                        preds = self.get_predecessors(frontier)
                        phi_args = [(pred, var) for pred in preds]
                        self.phi_nodes[frontier].append((var, phi_args))
                        
                        phi_inserted.add(frontier)
                        
                        # If this block didn't already define var, it does now
                        if frontier not in def_blocks:
                            worklist.append(frontier)
                            def_blocks.add(frontier)
    
    def rename_variables(self):
        """
        Rename all variable uses to SSA versions.
        
        Performs depth-first traversal of dominator tree,
        renaming variables to unique versions.
        """
        # Start from entry block
        entry = self.cfg.entry_label
        visited = set()
        
        def rename_block(block_label: str):
            """Recursively rename variables in block and successors."""
            if block_label in visited:
                return
            visited.add(block_label)
            
            block = self.cfg.get_block(block_label)
            if not block:
                return
            
            # Save current versions (for restoring after successors)
            saved_versions = dict(self.current_version)
            
            # Process phi nodes first
            if block_label in self.phi_nodes:
                for var, phi_args in self.phi_nodes[block_label]:
                    # Assign new version to phi result
                    new_version = self.get_next_version(var)
                    self.set_current_version(var, new_version)
            
            # Process instructions
            for instr in block.instructions:
                # Enable SSA for this instruction
                instr.enable_ssa()
                
                # Rename uses (reads) - use current versions
                new_srcs = []
                for src in instr.srcs:
                    if src.isdigit() or src.startswith('['):
                        # Immediate or memory operand - don't rename
                        new_srcs.append(src)
                    else:
                        # Variable - use current version
                        version = self.get_current_version(src)
                        new_srcs.append(f"{src}_{version}")
                instr.srcs = new_srcs
                
                # Rename destination if it's a memory operand with register base
                if instr.dst and instr.is_memory_operand(instr.dst):
                    base = instr.get_memory_base(instr.dst)
                    if base:
                        version = self.get_current_version(base)
                        # Keep memory operand format but update base
                        instr.dst = instr.dst.replace(base, f"{base}_{version}")
                
                # Rename definition (write) - assign new version
                for var in instr.writes():
                    new_version = self.get_next_version(var)
                    self.set_current_version(var, new_version)
                    instr.dst = f"{var}_{new_version}"
            
            # Recursively process successors in dominator tree order
            for succ in block.successors:
                rename_block(succ)
            
            # Restore versions after processing this block's subtree
            self.current_version = saved_versions
        
        rename_block(entry)
    
    def convert_to_ssa(self) -> CFG:
        """
        Convert CFG to SSA form.
        
        Returns:
            Modified CFG in SSA form with phi nodes inserted
        """
        # Step 1: Get all variables
        variables = self.get_all_variables()
        
        # Step 2: Insert phi nodes at dominance frontiers
        self.insert_phi_nodes(variables)
        
        # Step 3: Rename variables to SSA versions
        self.rename_variables()
        
        return self.cfg


def convert_cfg_to_ssa(cfg: CFG) -> CFG:
    """
    Convert a CFG to SSA form.
    
    Args:
        cfg: Control flow graph to convert
    
    Returns:
        CFG in SSA form with phi nodes and versioned variables
    
    Example:
        >>> cfg = CFG("entry")
        >>> # ... build CFG ...
        >>> ssa_cfg = convert_cfg_to_ssa(cfg)
        >>> # Variables now have versions: rax_0, rax_1, etc.
    """
    transformer = SSATransformer(cfg)
    return transformer.convert_to_ssa()


def get_ssa_version(operand: str) -> Optional[int]:
    """
    Extract SSA version from an operand.
    
    Args:
        operand: Operand string (e.g., "rax_3", "rbx", "5")
    
    Returns:
        Version number if operand is SSA-versioned, None otherwise
    
    Example:
        >>> get_ssa_version("rax_3")
        3
        >>> get_ssa_version("rbx")
        None
    """
    if '_' in operand:
        parts = operand.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
    return None


def get_base_name(operand: str) -> str:
    """
    Get base variable name without SSA version.
    
    Args:
        operand: Operand string (e.g., "rax_3", "5", "[rbx_1]")
    
    Returns:
        Base variable name
    
    Example:
        >>> get_base_name("rax_3")
        'rax'
        >>> get_base_name("5")
        '5'
    """
    if '_' in operand:
        parts = operand.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
    return operand
