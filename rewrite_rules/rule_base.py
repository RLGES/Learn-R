"""
Base classes for rewrite rules and instruction patterns.
"""
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


@dataclass
class InstructionPattern:
    """
    Represents an instruction pattern for matching.
    Fields can be variable names like "r1", "r2" or concrete values.
    """
    opcode: str
    dst: Optional[str] = None
    srcs: list[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Pretty print the pattern."""
        if self.dst:
            if self.srcs:
                operands = [self.dst] + self.srcs
                return f"{self.opcode} {', '.join(operands)}"
            else:
                return f"{self.opcode} {self.dst}"
        else:
            return self.opcode


@dataclass
class RewriteRule:
    """Base class for assembly rewrite rules."""
    name: str
    tier: int
    lhs: list[InstructionPattern]
    rhs: list[InstructionPattern]
    precondition: Callable[[dict[str, Any]], bool] = field(default=lambda match: True)
    
    def __str__(self) -> str:
        """String representation of the rule."""
        lhs_str = '\n  '.join(str(p) for p in self.lhs)
        rhs_str = '\n  '.join(str(p) for p in self.rhs)
        return f"Rule '{self.name}' (Tier {self.tier}):\n  LHS:\n  {lhs_str}\n  RHS:\n  {rhs_str}"
