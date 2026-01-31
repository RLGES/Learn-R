# Hierarchical Assembly Rewrite System

A research compiler optimization system that performs hierarchical assembly-level rewrite exploration using an e-graph with **learned rules** that improve over time.

## Overview

This system represents assembly instructions as structured objects, applies rewrite rules in hierarchical tiers, and maintains equivalences in an e-graph without destructive modifications. The system includes a **complete learned rules pipeline** with LLM-based rule generation, memory-based prioritization, **persistence**, and **extraction feedback** for continuous improvement.

## Key Features

- **Non-destructive rewrites**: Rules add equivalences to the e-graph without deleting
- **Hierarchical tiers**: Rules organized in 4 tiers (normalization → peephole → structural → learned)
- **Pattern matching**: Sliding window matcher with variable binding
- **Learned rules**: LLM-generated rules that improve through feedback
- **Rule persistence**: Rules and their effectiveness saved to disk
- **Extraction feedback**: Optimization outcomes update rule priorities
- **Automatic pruning**: Low-performing rules removed automatically
- **Rule metrics**: Per-rule performance tracking and analytics ⭐ NEW
- **Smart sampling**: Intelligent window selection for LLM ⭐ NEW
- **Rule cooldown**: Failing rules temporarily disabled ⭐ NEW
- **SMT verification**: Formal verification of learned rules ⭐ NEW
- **Modular design**: Clean separation of concerns across modules
- **No external dependencies**: Uses only Python standard library (z3-solver optional for verification)

## Architecture

```
capstone/
├── asm_ir/                      # Assembly intermediate representation
│   ├── instruction.py           # Instruction dataclass
│   └── basicblock.py            # BasicBlock class
├── rewrite_rules/               # Rewrite rule definitions
│   ├── rule_base.py             # Base classes (InstructionPattern, RewriteRule)
│   ├── tier0_normalization/     # Tier 0: Cleanup/canonicalization
│   ├── tier1_peephole/          # Tier 1: Local optimizations (4 rules)
│   └── tier2_structural/        # Tier 2: Instruction reordering
├── hierarchical_engine/         # Rewrite engine core
│   ├── matcher.py               # Pattern matcher with variable binding
│   ├── engine.py                # Hierarchical rewrite engine with feedback
│   ├── egraph_api.py            # Abstract e-graph interface
│   ├── dependency.py            # Dependency analysis utilities
│   └── tier_scheduler.py        # Per-tier iteration limits
├── learned_rules/               # Complete learned rules system
│   ├── llm_rule_generator.py    # LLM-based rule generation
│   ├── rule_parser.py           # Parse LLM output to rules
│   ├── rule_filter.py           # Filter invalid rules
│   ├── rule_memory.py           # Track effectiveness & pruning + cooldown ⭐
│   ├── rule_storage.py          # Persist rules to disk (JSON)
│   ├── window_sampler.py        # Smart window sampling ⭐ NEW
│   └── learned_rule_manager.py  # Orchestrate full pipeline
├── evaluation/                  # Evaluation and metrics ⭐ NEW
│   └── rule_metrics.py          # Per-rule performance tracking
├── verification/                # SMT-based verification ⭐ NEW
│   ├── symbolic_state.py        # Symbolic machine state
│   ├── symbolic_executor.py     # Symbolic instruction execution
│   ├── equivalence_checker.py   # SMT equivalence checking
│   └── rule_verifier.py         # Verify learned rules
├── docs/                        # Documentation
│   ├── architecture.md          # System architecture
│   ├── tiers.md                 # Tier system details
│   ├── learned_rules.md         # Learned rules overview
│   ├── persistence_feedback.md  # Persistence & feedback system
│   └── enhancements.md          # Metrics, sampling, cooldown ⭐ NEW
├── examples/                    # Demonstrations
│   ├── demo_tier0.py            # Normalization demo
│   ├── demo_tier1.py            # Peephole rules demo
│   ├── demo_learned_rules.py    # Learned rules demo
│   ├── demo_persistence_feedback.py  # Persistence & feedback demo
│   └── demo_enhancements.py     # New enhancements demo ⭐ NEW
└── pipeline/                    # Driver scripts
    └── main.py                  # Main pipeline demonstration
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

### Tier 0: Normalization (1 iteration)

- Remove self-moves (`MOV r1, r1`)
- Remove ADD/SUB with zero
- Convert to lowercase

### Tier 1: Peephole Optimizations (5 iterations)

**1. MOV Chain Elimination**

```
MOV r1, r2      →     MOV r3, r2
MOV r3, r1
```

**2. ADD/SUB Cancellation**

```
ADD r1, imm     →     (removed)
SUB r1, imm
```

**3. MOV Overwrite**

```
MOV r1, r2      →     MOV r1, r3
MOV r1, r3
```

**4. Double ADD Folding**

```
ADD r1, imm1    →     ADD r1, (imm1+imm2)
ADD r1, imm2
```

### Tier 2: Structural (2 iterations)

- Instruction reordering based on dependencies

### Tier 3: Learned Rules (1 iteration)

- LLM-generated rules
- Memory-based prioritization
- Persistence across sessions
- Automatic pruning

See [docs/persistence_feedback.md](docs/persistence_feedback.md) for complete details on the learning system.

## Usage

### Run Main Pipeline

```bash
cd capstone
python pipeline/main.py
```

### Run Persistence & Feedback Demo

```bash
python examples/demo_persistence_feedback.py
```

This demonstrates:

- ✓ Rules persisting to disk (JSON)
- ✓ Memory tracking across sessions
- ✓ Extraction feedback updating scores
- ✓ Automatic pruning of low-performers
- ✓ Complete closed-loop learning

### Run Enhancements Demo ⭐ NEW

```bash
python examples/demo_enhancements.py
```

This demonstrates:

- ✓ Rule metrics tracking (per-rule analytics)
- ✓ Smart window sampling (intelligent LLM input)
- ✓ Rule cooldown mechanism (skip failing rules)
- ✓ Integrated workflow

### Run Other Demos

```bash
python examples/demo_tier0.py              # Normalization
python examples/demo_tier1.py              # Peephole rules
python examples/demo_learned_rules.py      # Learned rules system
python examples/demo_verification.py       # SMT verification ⭐ NEW
python examples/test_verification_with_z3.py  # Full verification test (installs z3)
```

### PowerShell Environment Setup

```powershell
$env:PYTHONPATH = 'c:\Users\srini\Desktop\capstone'
python pipeline/main.py
```

## Documentation

- **[Architecture](docs/architecture.md)** - System overview and design principles
- **[Tiers](docs/tiers.md)** - Detailed explanation of the tier system
- **[Learned Rules](docs/learned_rules.md)** - LLM-based rule generation pipeline
- **[Persistence & Feedback](docs/persistence_feedback.md)** - Complete guide to the learning system
- **[Enhancements](docs/enhancements.md)** ⭐ - Metrics, sampling, and cooldown guide
- **[Verification](docs/verification.md)** ⭐ NEW - SMT-based rule verification

## Example Output

```
=== Processing Tier 1 ===
  [Tier 1, Iter 0] Applying rule 'mov_chain_elimination' at index 0
    Bindings: {'r1': 'eax', 'r2': 'ebx', 'r3': 'ecx'}
  [Tier 1, Iter 0] Applying rule 'double_add_folding' at index 4
    Bindings: {'r1': 'eax', 'imm1': '1', 'imm2': '1'}

=== Extracting optimized sequence ===
Original cost: 8 instructions
Optimized cost: 5 instructions

=== Extraction Feedback ===
Applied rules: ['mov_chain_elimination', 'double_add_folding']
Improvement: 3 instructions
  Recording success for rule: mov_chain_elimination
  Recording success for rule: double_add_folding
```

## Future Extensions

- Tier 0: Additional normalization patterns
- Memory operations (load/store)
- Branch instructions and control flow
- Real e-graph implementation (replacing stub)
- More structural optimizations
- Multi-target support (x86, ARM, etc.)
- Advanced pruning strategies
- Distributed rule learning
