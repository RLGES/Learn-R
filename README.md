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
- **Rule metrics**: Per-rule performance tracking and analytics
- **Smart sampling**: Intelligent window selection for LLM
- **Rule cooldown**: Failing rules temporarily disabled
- **SMT verification**: Formal verification of learned rules with z3
- **SSA transformation**: Complete Static Single Assignment conversion  NEW
- **Dataflow analysis**: Reaching definitions and liveness analysis  NEW
- **Dead code elimination**: Remove unused instructions  NEW
- **E-graph bridge**: SSA to e-graph optimization pipeline  NEW
- **Frontend compiler**: High-level language → ASM IR compilation  NEW
- **Control flow**: If/while statements and CFG construction  NEW
- **Modular design**: Clean separation of concerns across modules
- **No external dependencies**: Uses only Python standard library (z3-solver optional for verification)

## Architecture

```
capstone/
├── asm_ir/                      # Assembly intermediate representation
│   ├── instruction.py           # Instruction dataclass with SSA support
│   ├── basicblock.py            # BasicBlock class
│   └── cfg.py                   # Control Flow Graph  NEW
├── frontend/                    # High-level language frontend  NEW
│   ├── parser.py                # Lexer and parser
│   ├── ast_nodes.py             # Abstract syntax tree nodes
│   ├── ir_lowering.py           # AST → IR lowering
│   └── asm_codegen.py           # IR → assembly code generation
├── analysis/                    # Compiler analysis passes  NEW
│   ├── ssa.py                   # SSA transformation with phi nodes
│   ├── dataflow.py              # Reaching definitions & liveness
│   └── dce.py                   # Dead code elimination
├── egraph_bridge/               # SSA to e-graph optimization  NEW
│   ├── ssa_to_expr.py           # SSA → expression DAG
│   ├── expr_to_egraph.py        # Expression → e-graph insertion
│   ├── egraph_to_ssa.py         # E-graph → optimized SSA
│   └── simple_egraph.py         # E-graph data structures
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
│   ├── rule_memory.py           # Track effectiveness & pruning + cooldown
│   ├── rule_storage.py          # Persist rules to disk (JSON)
│   ├── window_sampler.py        # Smart window sampling
│   └── learned_rule_manager.py  # Orchestrate full pipeline
├── evaluation/                  # Evaluation and metrics
│   └── rule_metrics.py          # Per-rule performance tracking
├── verification/                # SMT-based verification
│   ├── symbolic_state.py        # Symbolic machine state
│   ├── symbolic_executor.py     # Symbolic instruction execution
│   ├── equivalence_checker.py   # SMT equivalence checking
│   └── rule_verifier.py         # Verify learned rules
├── pipeline/                    # Complete optimization pipelines  NEW
│   ├── main.py                  # Main hierarchical pipeline
│   ├── full_pipeline.py         # Frontend + optimization + verification
│   └── ssa_egraph_pipeline.py   # SSA e-graph optimization
├── docs/                        # Documentation
│   ├── architecture.md          # System architecture
│   ├── tiers.md                 # Tier system details
│   ├── learned_rules.md         # Learned rules overview
│   ├── persistence_feedback.md  # Persistence & feedback system
│   ├── enhancements.md          # Metrics, sampling, cooldown
│   ├── verification.md          # SMT verification guide
│   ├── CONTROL_FLOW.md          # Control flow documentation  NEW
│   └── MEMORY_OPERATIONS.md     # Memory operations guide  NEW
├── examples/                    # Demonstrations
│   ├── demo_tier0.py            # Normalization demo
│   ├── demo_tier1.py            # Peephole rules demo
│   ├── demo_learned_rules.py    # Learned rules demo
│   ├── demo_persistence_feedback.py  # Persistence & feedback demo
│   ├── demo_enhancements.py     # New enhancements demo
│   ├── demo_frontend.py         # Frontend compilation demo  NEW
│   ├── demo_analysis.py         # SSA/dataflow/DCE demo  NEW
│   ├── test_analysis.py         # Analysis tests  NEW
│   ├── test_egraph_bridge.py    # E-graph bridge tests  NEW
│   └── test_verification_with_z3.py  # Full verification test
└── tests/                       # Test suites  NEW
    ├── test_bitwise_opcodes.py  # Bitwise operation tests
    ├── test_memory_ops.py       # Memory operation tests
    └── test_control_flow.py     # Control flow tests
```

## Supported Instructions

Comprehensive instruction set with multiple operation categories:

**Data Movement:**

- `MOV` - Move data between registers/memory

**Arithmetic:**

- `ADD`, `SUB`, `MUL`, `DIV`, `MOD` - Basic arithmetic
- `INC`, `DEC` - Increment/decrement

**Bitwise:**

- `AND`, `OR`, `XOR`, `NOT` - Logical operations
- `SHL`, `SHR`, `SAR` - Shift operations

**Memory:**

- `LOAD`, `STORE` - Memory access
- `PUSH`, `POP` - Stack operations

**Control Flow:**

- `JMP` - Unconditional jump
- `JE`, `JNE`, `JG`, `JL`, `JGE`, `JLE` - Conditional jumps
- `CMP` - Compare
- `CALL`, `RET` - Function calls

**System:**

- `HALT` - Stop execution
- `SYSCALL` - System call

Each instruction tracks:

- Opcode
- Destination register
- Source operands
- Flags read/written
- SSA version information (optional)

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

### Run Complete Frontend Pipeline  NEW

```bash
python pipeline/full_pipeline.py
```

Demonstrates the complete compilation pipeline:

- High-level language parsing
- AST construction
- IR lowering
- Control flow (if/while statements)
- Assembly code generation
- Optimization
- Verification

### Run SSA E-Graph Optimization  NEW

```bash
python pipeline/ssa_egraph_pipeline.py
```

Demonstrates state-of-the-art optimization:

- SSA transformation
- Expression DAG construction
- E-graph insertion
- Algebraic simplification (x+0→x, x\*1→x, x-x→0)
- Constant folding
- Optimized SSA reconstruction

### Run Analysis Demos  NEW

```bash
python examples/demo_analysis.py      # SSA, dataflow, DCE demo
python examples/test_analysis.py      # Analysis test suite (6 tests)
python examples/test_egraph_bridge.py # E-graph bridge tests (6 tests)
```

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

### Run Enhancements Demo  NEW

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
# Frontend and compilation
python examples/demo_frontend.py           # High-level language compilation  NEW

# Optimization tiers
python examples/demo_tier0.py              # Normalization
python examples/demo_tier1.py              # Peephole rules
python examples/demo_learned_rules.py      # Learned rules system

# Verification
python examples/demo_verification.py       # SMT verification
python examples/test_verification_with_z3.py  # Full verification test (installs z3)

# Control flow
python demos/control_flow_demo.py          # If/while statements demo  NEW
```

### PowerShell Environment Setup

```powershell
$env:PYTHONPATH = 'c:\Users\srini\Desktop\capstone'
python pipeline/main.py
```

## Documentation

### Core System

- **[Architecture](docs/architecture.md)** - System overview and design principles
- **[Tiers](docs/tiers.md)** - Detailed explanation of the tier system
- **[Learned Rules](docs/learned_rules.md)** - LLM-based rule generation pipeline
- **[Persistence & Feedback](docs/persistence_feedback.md)** - Complete guide to the learning system
- **[Enhancements](docs/enhancements.md)** - Metrics, sampling, and cooldown guide
- **[Verification](docs/verification.md)** - SMT-based rule verification

### New Features 

- **[Control Flow](docs/CONTROL_FLOW.md)** - If/while statements and CFG construction
- **[Memory Operations](docs/MEMORY_OPERATIONS.md)** - Load/store and stack operations
- **[SSA Analysis](analysis/README.md)** - SSA transformation, dataflow, and DCE
- **[E-Graph Bridge](egraph_bridge/README.md)** - SSA to e-graph optimization pipeline

## Example Output

### Hierarchical Rewriting

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

### SSA E-Graph Optimization  NEW

```
Original SSA:
  MOV x_0, 1
  ADD y_0, x_0, 0    # x + 0
  MUL z_0, y_0, 1    # y * 1
  SUB w_0, z_0, z_0  # z - z
  MUL a_0, w_0, 5    # 0 * 5

Optimized SSA (after algebraic simplification):
  MOV x_0, 1
  MOV y_0, 1         # 1 + 0 → 1
  MOV z_0, 1         # 1 * 1 → 1
  MOV w_0, 0         # 1 - 1 → 0
  MOV a_0, 0         # 0 * 5 → 0
```

### Dead Code Elimination  NEW

```
Before DCE (5 instructions):
  MOV x, 1
  MOV y, 2           # Dead - never used
  ADD z, x, 1
  MUL w, z, 2        # Dead - never used
  ADD a, z, 3

After DCE (2 instructions):
  MOV x, 1
  ADD z, x, 1

Reduction: 3 instructions (60%)
```

## Future Extensions

### Planned Features

- Real e-graph implementation (replacing stub)
- Advanced pruning strategies
- Distributed rule learning
- Multi-target support (x86, ARM, RISC-V)
- More structural optimizations

### Implemented 

-  SSA transformation with phi nodes
-  Dataflow analysis (reaching definitions, liveness)
-  Dead code elimination
-  E-graph bridge for algebraic optimization
-  Frontend compiler (high-level language → assembly)
-  Control flow (if/while, CFG)
-  Memory operations (load/store, stack)
-  Bitwise operations (and/or/xor/not/shl/shr)
-  SMT verification with z3
-  Complete test suites (30+ tests)
