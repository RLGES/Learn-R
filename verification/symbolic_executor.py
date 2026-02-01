"""
Symbolic executor for assembly instructions.

Executes instructions symbolically using z3 for verification.
"""
from typing import List
try:
    from z3 import BitVecVal, SignExt, Extract
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

from asm_ir import Instruction
from .symbolic_state import SymbolicState


class SymbolicExecutor:
    """
    Symbolic executor for a subset of assembly instructions.
    
    Supports: MOV, ADD, SUB, CMP
    """
    
    def __init__(self):
        """Initialize executor."""
        self.supported_opcodes = {
            'MOV', 'ADD', 'SUB', 'CMP',         # Basic operations
            'IMUL', 'MUL',                       # Multiplication
            'AND', 'OR', 'XOR', 'NOT',           # Bitwise operations
            'SHL', 'SHR'                         # Shift operations
        }
    
    def _parse_operand(self, operand: str, state: SymbolicState):
        """
        Parse an operand (register or immediate).
        
        Args:
            operand: Operand string
            state: Current symbolic state
        
        Returns:
            BitVecRef value
        """
        operand = operand.strip()
        
        # Try to parse as immediate
        try:
            imm_value = int(operand)
            return BitVecVal(imm_value, 64)
        except ValueError:
            pass
        
        # Must be a register
        try:
            return state.get_register(operand)
        except KeyError:
            # Unknown operand, treat as fresh variable
            from z3 import BitVec
            return BitVec(f"unknown_{operand}", 64)
    
    def execute_mov(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute MOV instruction: dst := src
        
        Handles both register-to-register and memory operations:
        - MOV r, imm/reg: dst := src
        - MOV r, [addr]: dst := memory[addr]
        - MOV [addr], r: memory[addr] := src
        
        Args:
            instr: MOV instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        # Case 1: MOV r, [addr] - Load from memory
        if instr.mem_read and instr.is_memory_operand(src):
            # Parse memory address (e.g., [rax] or [rbx+8])
            base_reg = instr.get_memory_base(src)
            if base_reg:
                address = state.get_register(base_reg)
                # TODO: Handle offset if present (e.g., [rbx+8])
                # For now, just use base register as address
                value = state.read_memory(address)
                state.set_register(dst, value)
            else:
                # Fallback for invalid memory operand
                src_value = self._parse_operand(src, state)
                state.set_register(dst, src_value)
        
        # Case 2: MOV [addr], r - Store to memory
        elif instr.mem_write and instr.is_memory_operand(dst):
            # Parse memory address
            base_reg = instr.get_memory_base(dst)
            if base_reg:
                address = state.get_register(base_reg)
                value = self._parse_operand(src, state)
                state.write_memory(address, value)
        
        # Case 3: MOV r, imm/reg - Regular register move
        else:
            src_value = self._parse_operand(src, state)
            state.set_register(dst, src_value)
    
    def execute_add(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute ADD instruction: dst := dst + src
        
        Args:
            instr: ADD instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value + src_value
        state.set_register(dst, result)
        
        # Note: We don't model flags for ADD/SUB in this simplified version
        # A full implementation would set CF, OF, etc.
    
    def execute_sub(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute SUB instruction: dst := dst - src
        
        Args:
            instr: SUB instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value - src_value
        state.set_register(dst, result)
    
    def execute_imul(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute IMUL instruction: dst := dst * src (signed multiply)
        
        Args:
            instr: IMUL instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "1"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value * src_value
        state.set_register(dst, result)
    
    def execute_cmp(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute CMP instruction: sets flags based on dst - src
        
        Sets:
            ZF = (dst == src)
            SF = (dst < src)  [signed comparison]
        
        Args:
            instr: CMP instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        # ZF: Zero flag (dst == src)
        state.set_flag('zf', dst_value == src_value)
        
        # SF: Sign flag (dst < src, signed)
        state.set_flag('sf', dst_value < src_value)
        
        # Note: Full implementation would also set CF (unsigned), OF (overflow)
    
    def execute_and(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute AND instruction: dst := dst & src (bitwise AND)
        
        Uses z3's bvand operation via Python's & operator.
        
        Args:
            instr: AND instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value & src_value  # z3 bvand
        state.set_register(dst, result)
    
    def execute_or(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute OR instruction: dst := dst | src (bitwise OR)
        
        Uses z3's bvor operation via Python's | operator.
        
        Args:
            instr: OR instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value | src_value  # z3 bvor
        state.set_register(dst, result)
    
    def execute_xor(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute XOR instruction: dst := dst ^ src (bitwise XOR)
        
        Uses z3's bvxor operation via Python's ^ operator.
        
        Args:
            instr: XOR instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value ^ src_value  # z3 bvxor
        state.set_register(dst, result)
    
    def execute_not(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute NOT instruction: dst := ~dst (bitwise NOT)
        
        Uses z3's bvnot operation via Python's ~ operator.
        
        Args:
            instr: NOT instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        
        dst_value = state.get_register(dst)
        
        result = ~dst_value  # z3 bvnot
        state.set_register(dst, result)
    
    def execute_shl(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute SHL instruction: dst := dst << src (left shift)
        
        Uses z3's bvshl operation via Python's << operator.
        
        Args:
            instr: SHL instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value << src_value  # z3 bvshl
        state.set_register(dst, result)
    
    def execute_shr(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute SHR instruction: dst := dst >> src (logical right shift)
        
        Uses z3's LShR (logical shift right) via Python's >> operator.
        
        Args:
            instr: SHR instruction
            state: Symbolic state (modified in-place)
        """
        dst = instr.dst
        src = instr.srcs[0] if instr.srcs else "0"
        
        dst_value = state.get_register(dst)
        src_value = self._parse_operand(src, state)
        
        result = dst_value >> src_value  # z3 LShR
        state.set_register(dst, result)
    
    def execute_instruction(self, instr: Instruction, state: SymbolicState) -> None:
        """
        Execute a single instruction symbolically.
        
        Args:
            instr: Instruction to execute
            state: Symbolic state (modified in-place)
        
        Raises:
            ValueError: If opcode is not supported
        """
        opcode = instr.opcode.upper()
        
        if opcode == 'MOV':
            self.execute_mov(instr, state)
        elif opcode == 'ADD':
            self.execute_add(instr, state)
        elif opcode == 'SUB':
            self.execute_sub(instr, state)
        elif opcode == 'IMUL' or opcode == 'MUL':
            self.execute_imul(instr, state)
        elif opcode == 'CMP':
            self.execute_cmp(instr, state)
        elif opcode == 'AND':
            self.execute_and(instr, state)
        elif opcode == 'OR':
            self.execute_or(instr, state)
        elif opcode == 'XOR':
            self.execute_xor(instr, state)
        elif opcode == 'NOT':
            self.execute_not(instr, state)
        elif opcode == 'SHL':
            self.execute_shl(instr, state)
        elif opcode == 'SHR':
            self.execute_shr(instr, state)
        else:
            raise ValueError(f"Unsupported opcode for symbolic execution: {opcode}")
    
    def execute_sequence(self, seq: List[Instruction], state: SymbolicState) -> SymbolicState:
        """
        Execute a sequence of instructions symbolically.
        
        Args:
            seq: List of instructions
            state: Initial symbolic state
        
        Returns:
            Final symbolic state after executing all instructions
        """
        # Work on a copy to avoid modifying the input state
        current_state = state.copy()
        
        for instr in seq:
            self.execute_instruction(instr, current_state)
        
        return current_state


def execute_sequence(seq: List[Instruction], state: SymbolicState) -> SymbolicState:
    """
    Convenience function to execute a sequence symbolically.
    
    Args:
        seq: List of instructions
        state: Initial symbolic state
    
    Returns:
        Final symbolic state
    """
    executor = SymbolicExecutor()
    return executor.execute_sequence(seq, state)
