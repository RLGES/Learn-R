"""
Code generator: converts three-address IR to assembly instructions.

Generates assembly instructions compatible with the rewrite system.

Mapping rules:
    t = a + b  →  MOV t, a; ADD t, b
    t = a - b  →  MOV t, a; SUB t, b
    t = a * b  →  MOV t, a; MUL t, b
    t = 5      →  MOV t, 5
    t = a      →  MOV t, a
"""
from typing import List
import re
from asm_ir import Instruction


class CodeGenerator:
    """Generates assembly from three-address IR."""
    
    def __init__(self):
        self.instructions: List[Instruction] = []
    
    def parse_ir_instruction(self, ir_instr: str) -> List[Instruction]:
        """
        Parse a single IR instruction and generate assembly.
        
        Args:
            ir_instr: IR instruction string (e.g., "t1 = a + b")
        
        Returns:
            List of assembly Instruction objects
        """
        ir_instr = ir_instr.strip()
        
        # Pattern: dest = operand1 op operand2
        binary_pattern = r'(\w+)\s*=\s*(\w+)\s*([+\-*])\s*(\w+)'
        match = re.match(binary_pattern, ir_instr)
        
        if match:
            dest = match.group(1)
            operand1 = match.group(2)
            op = match.group(3)
            operand2 = match.group(4)
            
            # Map operation to assembly
            op_map = {
                '+': 'ADD',
                '-': 'SUB',
                '*': 'MUL'
            }
            
            asm_op = op_map.get(op)
            if not asm_op:
                raise ValueError(f"Unknown operator: {op}")
            
            # Generate: MOV dest, operand1; OP dest, operand2
            return [
                Instruction('MOV', dest, [operand1]),
                Instruction(asm_op, dest, [operand2])
            ]
        
        # Pattern: dest = source (simple assignment)
        assign_pattern = r'(\w+)\s*=\s*(\w+)'
        match = re.match(assign_pattern, ir_instr)
        
        if match:
            dest = match.group(1)
            source = match.group(2)
            
            # Generate: MOV dest, source
            return [Instruction('MOV', dest, [source])]
        
        raise ValueError(f"Cannot parse IR instruction: {ir_instr}")
    
    def generate(self, ir_instructions: List[str]) -> List[Instruction]:
        """
        Generate assembly from IR instructions.
        
        Args:
            ir_instructions: List of IR instruction strings
        
        Returns:
            List of assembly Instruction objects
        """
        self.instructions = []
        
        for ir_instr in ir_instructions:
            asm_instrs = self.parse_ir_instruction(ir_instr)
            self.instructions.extend(asm_instrs)
        
        return self.instructions


def ir_to_assembly(ir_instructions: List[str]) -> List[Instruction]:
    """
    Convert three-address IR to assembly instructions.
    
    Args:
        ir_instructions: List of IR instruction strings
    
    Returns:
        List of assembly Instruction objects
    
    Example:
        >>> ir = ["t0 = 5", "a = t0", "t1 = a + 3", "b = t1"]
        >>> asm = ir_to_assembly(ir)
        >>> for instr in asm:
        ...     print(f"{instr.opcode} {instr.dst}, {instr.srcs[0]}")
        MOV t0, 5
        MOV a, t0
        MOV t1, a
        ADD t1, 3
        MOV b, t1
    """
    generator = CodeGenerator()
    return generator.generate(ir_instructions)
