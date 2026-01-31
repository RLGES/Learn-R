"""
Tier 0 normalization pass for assembly instructions.
"""
from asm_ir import Instruction, BasicBlock


def normalize_block(block: BasicBlock) -> BasicBlock:
    """
    Normalize a basic block by applying simple cleanup rules.
    
    Normalization rules:
    - Remove MOV rX, rX (self-move)
    - Remove ADD rX, 0
    - Remove SUB rX, 0
    - Convert all register names to lowercase
    
    Args:
        block: The original basic block
    
    Returns:
        A new BasicBlock with normalized instructions (does not mutate original)
    """
    normalized_instructions = []
    
    for instr in block:
        # Convert register names to lowercase
        dst = instr.dst.lower() if instr.dst else None
        srcs = [src.lower() if src.isalpha() or (src and src[0].isalpha()) else src 
                for src in instr.srcs]
        opcode = instr.opcode
        
        # Create normalized instruction
        normalized = Instruction(
            opcode=opcode,
            dst=dst,
            srcs=srcs,
            flags_read=instr.flags_read,
            flags_written=instr.flags_written
        )
        
        # Apply normalization rules
        should_keep = True
        
        # Rule: Remove MOV rX, rX (self-move)
        if opcode == 'MOV' and dst and len(srcs) == 1 and dst == srcs[0]:
            should_keep = False
        
        # Rule: Remove ADD rX, 0
        elif opcode == 'ADD' and len(srcs) == 1 and srcs[0] == '0':
            should_keep = False
        
        # Rule: Remove SUB rX, 0
        elif opcode == 'SUB' and len(srcs) == 1 and srcs[0] == '0':
            should_keep = False
        
        if should_keep:
            normalized_instructions.append(normalized)
    
    return BasicBlock(normalized_instructions)
