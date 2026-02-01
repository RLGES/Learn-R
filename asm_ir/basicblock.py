"""
Basic block representation.
"""
from typing import Iterator, List
from .instruction import Instruction


class BasicBlock:
    """Stores a list of Instruction objects with control flow information."""
    
    def __init__(self, label: str, instructions: list[Instruction] = None):
        """
        Initialize a basic block.
        
        Args:
            label: Unique identifier for this block
            instructions: List of instructions in the block
        """
        self.label = label
        self.instructions = instructions if instructions is not None else []
        self.successors: List[str] = []  # Labels of successor blocks
    
    def add_successor(self, label: str):
        """
        Add a successor block by label.
        
        Args:
            label: Label of the successor block
        """
        if label not in self.successors:
            self.successors.append(label)
    
    def __iter__(self) -> Iterator[Instruction]:
        """Iterate over instructions in the block."""
        return iter(self.instructions)
    
    def __len__(self) -> int:
        """Return the number of instructions in the block."""
        return len(self.instructions)
    
    def __str__(self) -> str:
        """Print block with label and instructions."""
        result = f"{self.label}:\n"
        for instr in self.instructions:
            result += f"  {instr}\n"
        if self.successors:
            result += f"  -> {', '.join(self.successors)}\n"
        return result
