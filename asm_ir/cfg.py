"""
Control Flow Graph (CFG) representation.
"""
from typing import Dict, Optional
from .basicblock import BasicBlock


class CFG:
    """
    Control Flow Graph: collection of basic blocks with edges.
    
    A CFG represents the control flow structure of a function or program.
    Each basic block is identified by a unique label, and edges represent
    possible control flow transitions (jumps, branches, fall-through).
    """
    
    def __init__(self, entry_label: str = "entry"):
        """
        Initialize an empty CFG.
        
        Args:
            entry_label: Label of the entry block (default: "entry")
        """
        self.blocks: Dict[str, BasicBlock] = {}
        self.entry_label = entry_label
    
    def add_block(self, block: BasicBlock):
        """
        Add a basic block to the CFG.
        
        Args:
            block: BasicBlock to add
        
        Raises:
            ValueError: If a block with the same label already exists
        """
        if block.label in self.blocks:
            raise ValueError(f"Block with label '{block.label}' already exists")
        self.blocks[block.label] = block
    
    def connect_blocks(self, from_label: str, to_label: str):
        """
        Create an edge from one block to another.
        
        Args:
            from_label: Label of the source block
            to_label: Label of the destination block
        
        Raises:
            KeyError: If either block doesn't exist
        """
        if from_label not in self.blocks:
            raise KeyError(f"Source block '{from_label}' not found")
        if to_label not in self.blocks:
            raise KeyError(f"Destination block '{to_label}' not found")
        
        self.blocks[from_label].add_successor(to_label)
    
    def get_block(self, label: str) -> Optional[BasicBlock]:
        """
        Retrieve a basic block by label.
        
        Args:
            label: Label of the block to retrieve
        
        Returns:
            BasicBlock if found, None otherwise
        """
        return self.blocks.get(label)
    
    def get_entry_block(self) -> Optional[BasicBlock]:
        """
        Get the entry block of the CFG.
        
        Returns:
            Entry BasicBlock if it exists, None otherwise
        """
        return self.get_block(self.entry_label)
    
    def get_all_blocks(self):
        """
        Get all blocks in the CFG.
        
        Returns:
            List of all BasicBlock objects
        """
        return list(self.blocks.values())
    
    def __str__(self) -> str:
        """Print CFG as text."""
        result = f"CFG (entry: {self.entry_label}):\n\n"
        
        # Print entry block first
        entry = self.get_entry_block()
        if entry:
            result += str(entry) + "\n"
        
        # Print remaining blocks
        for label, block in sorted(self.blocks.items()):
            if label != self.entry_label:
                result += str(block) + "\n"
        
        return result
    
    def __repr__(self) -> str:
        return f"CFG(entry={self.entry_label}, blocks={len(self.blocks)})"
