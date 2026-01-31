"""
Pattern matcher for finding instruction sequences in basic blocks.
"""
from dataclasses import dataclass
from typing import Optional
from asm_ir import Instruction, BasicBlock
from rewrite_rules import InstructionPattern


@dataclass
class Match:
    """Represents a successful pattern match."""
    bindings: dict[str, str]  # Maps variable names to actual register names
    start_index: int  # Starting position in the basic block
    length: int  # Number of instructions matched
    
    def __str__(self) -> str:
        """String representation of the match."""
        return f"Match(start={self.start_index}, len={self.length}, bindings={self.bindings})"


class Matcher:
    """Pattern matcher for instruction sequences."""
    
    @staticmethod
    def is_variable(name: str) -> bool:
        """Check if a name is a variable (starts with lowercase or is a pattern variable)."""
        # Variables are things like "r1", "r2", "reg", etc.
        # Concrete registers might be "RAX", "EAX", etc.
        # For simplicity, we treat any name as potentially a variable in patterns
        return True
    
    @staticmethod
    def match_operand(pattern_op: Optional[str], concrete_op: Optional[str], 
                     bindings: dict[str, str]) -> bool:
        """
        Match a single operand against a pattern.
        Updates bindings if successful.
        """
        if pattern_op is None and concrete_op is None:
            return True
        if pattern_op is None or concrete_op is None:
            return False
        
        # If pattern operand is already bound, check consistency
        if pattern_op in bindings:
            return bindings[pattern_op] == concrete_op
        
        # Otherwise, create a new binding
        bindings[pattern_op] = concrete_op
        return True
    
    @staticmethod
    def match_instruction(pattern: InstructionPattern, instruction: Instruction,
                         bindings: dict[str, str]) -> bool:
        """
        Check if an instruction matches a pattern.
        Updates bindings if successful.
        """
        # Opcode must match exactly
        if pattern.opcode != instruction.opcode:
            return False
        
        # Make a copy of bindings to avoid partial updates on failure
        temp_bindings = bindings.copy()
        
        # Match destination
        if not Matcher.match_operand(pattern.dst, instruction.dst, temp_bindings):
            return False
        
        # Match sources
        if len(pattern.srcs) != len(instruction.srcs):
            return False
        
        for pat_src, inst_src in zip(pattern.srcs, instruction.srcs):
            if not Matcher.match_operand(pat_src, inst_src, temp_bindings):
                return False
        
        # Success - update actual bindings
        bindings.update(temp_bindings)
        return True
    
    @staticmethod
    def find_matches(patterns: list[InstructionPattern], 
                    block: BasicBlock) -> list[Match]:
        """
        Find all occurrences of a pattern sequence in a basic block.
        Uses sliding window matching with variable binding.
        """
        matches = []
        pattern_len = len(patterns)
        
        if pattern_len == 0:
            return matches
        
        # Slide window across the block
        for start_idx in range(len(block) - pattern_len + 1):
            bindings: dict[str, str] = {}
            success = True
            
            # Try to match all patterns starting at start_idx
            for offset, pattern in enumerate(patterns):
                instruction = block.instructions[start_idx + offset]
                if not Matcher.match_instruction(pattern, instruction, bindings):
                    success = False
                    break
            
            if success:
                matches.append(Match(
                    bindings=bindings,
                    start_index=start_idx,
                    length=pattern_len
                ))
        
        return matches
