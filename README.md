# Hierarchical Assembly Rewrite System

A research compiler optimization system that performs hierarchical assembly-level rewrite exploration using an e-graph.

## Overview

This system represents assembly instructions as structured objects, applies rewrite rules in hierarchical tiers, and maintains equivalences in an e-graph without destructive modifications.

## Architecture

```
capstone/
├── asm_ir/                    # Assembly intermediate representation
│   ├── instruction.py         # Instruction dataclass
│   └── basicblock.py          # BasicBlock class
├── rewrite_rules/             # Rewrite rule definitions
│   ├── rule_base.py           # Base classes (InstructionPattern, RewriteRule)
│   └── tier1_peephole/        # Tier 1 peephole optimizations
│       └── mov_elimination.py # MOV chain elimination rule
├── hierarchical_engine/       # Rewrite engine
│   ├── matcher.py             # Pattern matcher with variable binding
│   └── engine.py              # Hierarchical rewrite engine
└── pipeline/                  # Driver and main entry point
    └── main.py                # Main driver script
```

## Supported Instructions

Current minimal instruction set:

- `MOV` - Move data between registers
- `ADD` - Addition
- `SUB` - Subtraction
- `MUL` - Multiplication
- `CMP` - Compare

Each instruction tracks:

- Opcode
- Destination register
- Source operands
- Flags read/written

## Rewrite Rules

### Tier 1: Peephole Optimizations

**MOV Chain Elimination**

```
MOV r1, r2      →     MOV r3, r2
MOV r3, r1
```

## Usage

Run the system:

```bash
cd capstone
python pipeline/main.py
```

Or with explicit PYTHONPATH:

```powershell
$env:PYTHONPATH = 'c:\Users\srini\Desktop\capstone'
python pipeline/main.py
```

## Key Features

- **Non-destructive rewrites**: Rules add equivalences to the e-graph without deleting
- **Hierarchical tiers**: Rules are organized by tier and applied in order
- **Pattern matching**: Sliding window matcher with variable binding
- **Modular design**: Clean separation of concerns across modules
- **No dependencies**: Uses only Python standard library (typing, dataclasses)

## Example Output

```
Original code (5 instructions):
MOV eax, ebx
MOV ecx, eax
ADD ecx, 5
MOV edx, esi
MOV edi, edx

=== Processing Tier 1 ===
  [Tier 1, Iter 0] Applying rule 'mov_chain_elimination' at index 0
    Bindings: {'r1': 'eax', 'r2': 'ebx', 'r3': 'ecx'}
  [Tier 1, Iter 0] Applying rule 'mov_chain_elimination' at index 3
    Bindings: {'r1': 'edx', 'r2': 'esi', 'r3': 'edi'}
```

## Future Extensions

- Tier 0: Normalization rules
- Memory operations
- Branch instructions
- Control flow analysis
- Real e-graph implementation
- More peephole optimizations
- Algebraic simplifications
