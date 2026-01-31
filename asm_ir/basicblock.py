"""
Basic block representation.
"""
from typing import Iterator
from .instruction import Instruction


class BasicBlock:
    """Stores a list of Instruction objects."""
    
    def __init__(self, instructions: list[Instruction]):
        """Initialize a basic block with a list of instructions."""
        self.instructions = instructions
    
    def __iter__(self) -> Iterator[Instruction]:
        """Iterate over instructions in the block."""
        return iter(self.instructions)
    
    def __len__(self) -> int:
        """Return the number of instructions in the block."""
        return len(self.instructions)
    
    def __str__(self) -> str:
        """Print block line by line."""
        return '\n'.join(str(instr) for instr in self.instructions)
