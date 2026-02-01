"""
Code generator: converts three-address IR to assembly instructions.

Generates assembly instructions compatible with the rewrite system.

Mapping rules:
    t = a + b  →  MOV t, a; ADD t, b
    t = a - b  →  MOV t, a; SUB t, b
    t = a * b  →  MOV t, a; MUL t, b
    t = 5      →  MOV t, 5
    t = a      →  MOV t, a
    CMP a, b   →  CMP a, b (comparison)
    JE label   →  JE label (conditional jump)
    JMP label  →  JMP label (unconditional jump)
    L0:        →  Label marker (not an instruction)
"""
from typing import List
import re
from asm_ir import Instruction


class CodeGenerator:
    """Generates assembly from three-address IR."""
    
    def __init__(self):
        self.instructions: List[Instruction] = []
        self.labels: List[str] = []  # Track labels encountered
    
    def parse_ir_instruction(self, ir_instr: str) -> List[Instruction]:
        """
        Parse a single IR instruction and generate assembly.
        
        Args:
            ir_instr: IR instruction string (e.g., "t1 = a + b", "JMP L0", "L0:")
        
        Returns:
            List of assembly Instruction objects (may be empty for labels)
        """
        ir_instr = ir_instr.strip()
        
        # Check for label (e.g., "L0:", "loop_start:")
        if ir_instr.endswith(':'):
            label = ir_instr[:-1]
            self.labels.append(label)
            # Labels are not instructions - they mark positions
            return []
        
        # Check for CMP instruction (e.g., "CMP a, b")
        cmp_pattern = r'CMP\s+(\w+),\s*(\w+)'
        match = re.match(cmp_pattern, ir_instr, re.IGNORECASE)
        if match:
            operand1 = match.group(1)
            operand2 = match.group(2)
            # CMP is special: dst is first operand, src is second
            return [Instruction('CMP', operand1, [operand2])]
        
        # Check for unconditional jump (e.g., "JMP label")
        jmp_pattern = r'JMP\s+(\w+)'
        match = re.match(jmp_pattern, ir_instr, re.IGNORECASE)
        if match:
            label = match.group(1)
            return [Instruction('JMP', label, [], is_control_flow_instr=True)]
        
        # Check for conditional jumps (e.g., "JE label", "JNE label")
        cond_jmp_pattern = r'(JE|JNE|JZ|JNZ|JL|JG|JLE|JGE)\s+(\w+)'
        match = re.match(cond_jmp_pattern, ir_instr, re.IGNORECASE)
        if match:
            opcode = match.group(1).upper()
            label = match.group(2)
            # Conditional jumps read flags but don't write registers
            flags_read = {'zf'}  # Most conditional jumps read zero flag
            if opcode in ['JL', 'JG', 'JLE', 'JGE']:
                flags_read.update({'sf', 'of'})  # Signed comparisons also check sign/overflow
            return [Instruction(opcode, label, [], flags_read=flags_read, is_control_flow_instr=True)]
        
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
