"""
Assembly instruction representation.
"""
from dataclasses import dataclass, field
from typing import Optional, Set


@dataclass
class Instruction:
    """Represents a simplified assembly instruction."""
    opcode: str
    dst: Optional[str] = None
    srcs: list[str] = field(default_factory=list)
    flags_read: Set[str] = field(default_factory=set)
    flags_written: Set[str] = field(default_factory=set)
    
    def reads(self) -> Set[str]:
        """Return all registers read by this instruction."""
        result = set(self.srcs)
        if self.dst and self.opcode in ['ADD', 'SUB', 'MUL', 'CMP']:
            # These operations read the destination register
            if self.opcode != 'CMP':  # CMP doesn't write dst
                result.add(self.dst)
        return result
    
    def writes(self) -> Set[str]:
        """Return all registers written by this instruction."""
        if self.dst and self.opcode != 'CMP':
            return {self.dst}
        return set()
    
    def __str__(self) -> str:
        """Pretty print the instruction in assembly form."""
        if self.opcode == 'CMP':
            # CMP src1, src2
            if len(self.srcs) >= 2:
                return f"{self.opcode} {self.srcs[0]}, {self.srcs[1]}"
            return f"{self.opcode} {', '.join(self.srcs)}"
        elif self.dst:
            if self.srcs:
                # opcode dst, src1, src2, ...
                operands = [self.dst] + self.srcs
                return f"{self.opcode} {', '.join(operands)}"
            else:
                # opcode dst
                return f"{self.opcode} {self.dst}"
        else:
            # opcode (no operands)
            return self.opcode
