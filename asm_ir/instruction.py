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
    mem_read: bool = False   # True if instruction reads from memory
    mem_write: bool = False  # True if instruction writes to memory
    is_control_flow_instr: bool = False  # True for JMP, JE, JNE, etc.
    ssa_enabled: bool = False  # True if operands are SSA-versioned
    original_dst: Optional[str] = None  # Original destination before SSA
    original_srcs: list[str] = field(default_factory=list)  # Original sources before SSA
    
    def reads(self) -> Set[str]:
        """Return all registers read by this instruction."""
        result = set()
        
        # Control flow instructions don't read registers (they may read flags)
        if self.is_control_flow_instr:
            return result
        
        # Add source operands, extracting base registers from memory operands
        for src in self.srcs:
            if self.is_memory_operand(src):
                # Memory operand like [rax] or [rbx+8] - extract base register
                base = self.get_memory_base(src)
                if base:
                    result.add(base)
            else:
                # Regular register or immediate
                result.add(src)
        
        # For destination operands that are memory (e.g., MOV [rax], rbx)
        if self.dst and self.is_memory_operand(self.dst):
            base = self.get_memory_base(self.dst)
            if base:
                result.add(base)
        
        # Operations that read the destination register (read-modify-write)
        read_modify_write_ops = {
            'ADD', 'SUB', 'MUL', 'IMUL',  # Arithmetic
            'AND', 'OR', 'XOR',            # Bitwise
            'SHL', 'SHR'                   # Shifts
        }
        
        if self.dst and self.opcode in read_modify_write_ops:
            result.add(self.dst)
        
        # CMP reads operands but doesn't write
        if self.opcode == 'CMP' and self.dst:
            result.add(self.dst)
        
        return result
    
    def writes(self) -> Set[str]:
        """Return all registers written by this instruction."""
        # Control flow instructions don't write registers
        if self.is_control_flow_instr:
            return set()
        
        # CMP only sets flags, doesn't write to destination
        if self.dst and self.opcode != 'CMP':
            # Memory write: MOV [addr], r doesn't write to a register
            if self.mem_write:
                return set()
            return {self.dst}
        return set()
    
    def get_flags_written(self) -> Set[str]:
        """Return flags written by this instruction."""
        # Arithmetic operations write flags
        arithmetic_ops = {'ADD', 'SUB', 'MUL', 'IMUL', 'CMP'}
        if self.opcode in arithmetic_ops:
            return {'zf', 'sf', 'cf', 'of'}  # Zero, Sign, Carry, Overflow
        
        # Bitwise operations write flags (typically ZF, SF, PF)
        bitwise_ops = {'AND', 'OR', 'XOR', 'NOT'}
        if self.opcode in bitwise_ops:
            return {'zf', 'sf', 'pf'}  # Zero, Sign, Parity
        
        # Shift operations write flags
        shift_ops = {'SHL', 'SHR'}
        if self.opcode in shift_ops:
            return {'zf', 'sf', 'cf', 'of'}
        
        # Control flow instructions don't write flags (but may read them)
        # JMP doesn't read/write flags
        # JE, JNE read flags (zf) but don't write them
        
        # MOV and LEA don't affect flags
        return set()
    
    def is_memory_operand(self, operand: str) -> bool:
        """Check if an operand is a memory reference (e.g., [base+offset])."""
        return operand.startswith('[') and operand.endswith(']')
    
    def get_memory_base(self, operand: str) -> Optional[str]:
        """
        Extract base register from memory operand.
        
        Examples:
            [rax] -> rax
            [rbx+8] -> rbx
            [rcx-16] -> rcx
        
        Returns:
            Base register name, or None if not a memory operand
        """
        if not self.is_memory_operand(operand):
            return None
        
        # Remove brackets
        inner = operand[1:-1]
        
        # Handle [base+offset] or [base-offset]
        if '+' in inner:
            return inner.split('+')[0].strip()
        elif '-' in inner:
            return inner.split('-')[0].strip()
        else:
            # Just [base]
            return inner.strip()
    
    def is_control_flow(self) -> bool:
        """Check if this is a control flow instruction."""
        return self.is_control_flow_instr or self.opcode in {'JMP', 'JE', 'JNE', 'JZ', 'JNZ', 'JG', 'JL', 'JGE', 'JLE'}
    
    def enable_ssa(self):
        """Enable SSA mode - save original operands for printing."""
        if not self.ssa_enabled:
            self.ssa_enabled = True
            self.original_dst = self.dst
            self.original_srcs = list(self.srcs) if self.srcs else []
    
    def get_ssa_operands(self) -> tuple[Optional[str], list[str]]:
        """Get SSA-versioned operands (dst, srcs)."""
        return (self.dst, self.srcs)
    
    def get_original_operands(self) -> tuple[Optional[str], list[str]]:
        """Get original operands before SSA transformation."""
        if self.ssa_enabled:
            return (self.original_dst, self.original_srcs)
        return (self.dst, self.srcs)
    
    def __str__(self) -> str:
        """Pretty print the instruction in assembly form."""
        # Use original operands if SSA is enabled (for readable output)
        dst_str = self.original_dst if self.ssa_enabled and self.original_dst else self.dst
        srcs_str = self.original_srcs if self.ssa_enabled and self.original_srcs else self.srcs
        
        # Jump instructions: JMP label or JE label
        if self.is_control_flow_instr:
            if dst_str:
                return f"{self.opcode} {dst_str}"
            return self.opcode
        
        if self.opcode == 'CMP':
            # CMP src1, src2
            if len(srcs_str) >= 2:
                return f"{self.opcode} {srcs_str[0]}, {srcs_str[1]}"
            return f"{self.opcode} {', '.join(srcs_str)}"
        elif dst_str:
            if srcs_str:
                # opcode dst, src1, src2, ...
                operands = [dst_str] + srcs_str
                return f"{self.opcode} {', '.join(operands)}"
            else:
                # opcode dst
                return f"{self.opcode} {dst_str}"
        else:
            # opcode (no operands)
            return self.opcode
