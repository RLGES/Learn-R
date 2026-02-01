# Analysis and Optimization Framework

Comprehensive compiler analysis and optimization infrastructure for the ASM IR framework.

## Overview

This directory contains three key compiler analysis and optimization components:

1. **SSA Transformation** (`ssa.py`) - Converts CFG to Static Single Assignment form
2. **Dataflow Analysis** (`dataflow.py`) - Reaching definitions and liveness analysis
3. **Dead Code Elimination** (`dce.py`) - Removes unused instructions

## Features

### SSA Transformation

Static Single Assignment (SSA) is an intermediate representation where each variable is assigned exactly once. This makes dataflow explicit and enables more powerful optimizations.

**Key Algorithms:**

- Dominator computation (iterative fixed-point)
- Dominance frontier calculation
- Phi node insertion at join points
- Variable renaming with version tracking

**Example:**

```python
from asm_ir import CFG, BasicBlock, Instruction
from analysis import convert_cfg_to_ssa

# Create CFG
cfg = CFG("entry")
entry = BasicBlock("entry")
entry.instructions.append(Instruction("MOV", "x", ["1"]))
entry.instructions.append(Instruction("ADD", "x", ["x", "1"]))  # x redefined
cfg.add_block(entry)

# Convert to SSA
convert_cfg_to_ssa(cfg)
# Now: x_0 = 1, x_1 = x_0 + 1
```

**Classes:**

- `SSAVariable`: Represents versioned variable (e.g., `x_0`, `x_1`)
- `SSATransformer`: Implements full SSA transformation algorithm

### Dataflow Analysis

Dataflow analysis computes information about program points using iterative fixed-point algorithms.

#### Reaching Definitions

Tracks which variable definitions reach each program point. A definition reaches a point if there exists a path from the definition to that point without the variable being redefined.

**Example:**

```python
from analysis import compute_reaching_definitions

rd = compute_reaching_definitions(cfg)
rd.print_results()

# Get definitions reaching a specific instruction
reaching = rd.get_reaching_definitions("block2", instr_index=3)
for defn in reaching:
    print(f"{defn.variable} defined at {defn.block_label}[{defn.instr_index}]")
```

**Classes:**

- `Definition`: Represents a variable definition (variable, block, instruction index)
- `ReachingDefinitions`: Computes IN/OUT sets for each block

#### Liveness Analysis

Tracks which variables are live (will be used) after each program point. Used for dead code elimination and register allocation.

**Example:**

```python
from analysis import compute_liveness

liveness = compute_liveness(cfg)
liveness.print_results()

# Check if variable is live after an instruction
is_live = liveness.is_live_after("entry", instr_index=2, variable="x")
print(f"x is {'live' if is_live else 'dead'} after entry[2]")
```

**Classes:**

- `LivenessAnalysis`: Computes LIVE_IN/LIVE_OUT sets using backward dataflow

### Dead Code Elimination

Removes instructions whose results are never used. Two implementations:

#### Basic DCE

Removes instructions with dead destinations (not live after the instruction).

**Example:**

```python
from analysis import eliminate_dead_code

# Remove dead code
eliminated = eliminate_dead_code(cfg, aggressive=False)
print(f"Eliminated {eliminated} instructions")
```

#### Aggressive DCE

Uses a worklist algorithm starting from critical instructions (calls, stores, returns) and marks all dependencies as live. Everything else is eliminated.

**Example:**

```python
from analysis import eliminate_dead_code, iterative_dce

# Aggressive DCE
eliminated = eliminate_dead_code(cfg, aggressive=True)

# Iterative DCE (multiple passes until fixed point)
total = iterative_dce(cfg, max_iterations=10)
print(f"Total eliminated: {total}")
```

**Classes:**

- `DeadCodeEliminator`: Basic DCE using liveness
- `AggressiveDeadCodeEliminator`: Worklist-based DCE

## Integration with Instruction Class

The `Instruction` class has been extended to support SSA:

```python
# Enable SSA on instruction (saves original operands)
instr.enable_ssa()

# Get SSA-versioned operands
ssa_dst, ssa_srcs = instr.get_ssa_operands()  # Returns: "x_1", ["y_0", "z_0"]

# Get original operands (for display)
orig_dst, orig_srcs = instr.get_original_operands()  # Returns: "x", ["y", "z"]

# String representation uses original operands for readability
print(instr)  # "ADD x, y, z" (not "ADD x_1, y_0, z_0")
```

## Usage Examples

### Complete Optimization Pipeline

```python
from asm_ir import CFG, BasicBlock, Instruction
from analysis import convert_cfg_to_ssa, compute_liveness, eliminate_dead_code

# 1. Build CFG with dead code
cfg = build_my_cfg()
print(f"Original: {sum(len(b.instructions) for b in cfg.blocks.values())} instructions")

# 2. Convert to SSA (optional but improves analysis precision)
convert_cfg_to_ssa(cfg)

# 3. Run liveness analysis
liveness = compute_liveness(cfg)
liveness.print_results()

# 4. Eliminate dead code
eliminated = eliminate_dead_code(cfg)
print(f"Eliminated: {eliminated} instructions")

final_count = sum(len(b.instructions) for b in cfg.blocks.values())
print(f"Final: {final_count} instructions")
```

### SSA with Control Flow

```python
from analysis import convert_cfg_to_ssa

# CFG with branches:
#   entry: x = 1
#   then:  x = 2
#   else:  x = 3
#   merge: y = x  (needs phi node)

cfg = build_branching_cfg()
convert_cfg_to_ssa(cfg)

# SSA automatically inserts phi nodes at merge point
# merge: x_3 = PHI(x_1, x_2); y_0 = x_3
```

## Testing

Run comprehensive tests:

```bash
python examples/test_analysis.py
```

Tests cover:

- SSA transformation on straight-line code
- SSA with branches and phi nodes
- Reaching definitions analysis
- Liveness analysis
- Dead code elimination
- DCE with loops

## Demos

Run the complete demo:

```bash
python examples/demo_analysis.py
```

Demonstrates:

1. Complete optimization pipeline (SSA + dataflow + DCE)
2. Phi node insertion at merge points
3. Loop optimization with iterative DCE

## API Reference

### SSA Functions

- `convert_cfg_to_ssa(cfg: CFG) -> CFG`: Convert CFG to SSA form
- `get_ssa_version(operand: str) -> Optional[int]`: Extract version from SSA operand
- `get_base_name(operand: str) -> str`: Strip version from operand

### Dataflow Functions

- `compute_reaching_definitions(cfg: CFG) -> ReachingDefinitions`: Compute reaching definitions
- `compute_liveness(cfg: CFG) -> LivenessAnalysis`: Compute liveness

### DCE Functions

- `eliminate_dead_code(cfg: CFG, aggressive: bool = False) -> int`: Eliminate dead code
- `iterative_dce(cfg: CFG, max_iterations: int = 10) -> int`: Run DCE until fixed point

## Implementation Notes

### SSA Algorithm

The SSA transformation uses the classic algorithm from Cytron et al. (1991):

1. **Compute dominators**: Iterative fixed-point algorithm
2. **Compute dominance frontier**: For each block, find where its dominance ends
3. **Insert phi nodes**: Place phi nodes at dominance frontiers for each variable
4. **Rename variables**: DFS traversal assigning unique versions

### Dataflow Equations

**Reaching Definitions (forward):**

```
IN[B] = ∪ OUT[P] for predecessors P
OUT[B] = GEN[B] ∪ (IN[B] - KILL[B])
```

**Liveness (backward):**

```
LIVE_OUT[B] = ∪ LIVE_IN[S] for successors S
LIVE_IN[B] = USE[B] ∪ (LIVE_OUT[B] - DEF[B])
```

### Dead Code Criteria

An instruction is dead if:

1. It writes to a variable that is not live after the instruction
2. It has no side effects (not a call, store, or control flow instruction)

## Performance Considerations

- **SSA transformation**: O(n) for straight-line code, O(n \* edges) for complex CFGs
- **Dataflow analysis**: O(n \* iterations) where iterations depend on CFG structure
- **DCE**: O(n) per pass, may need multiple passes to reach fixed point

## Future Enhancements

Possible extensions:

- [ ] Constant propagation in SSA form
- [ ] Copy propagation
- [ ] Common subexpression elimination (CSE)
- [ ] Loop-invariant code motion (LICM)
- [ ] SSA deconstruction (converting back to non-SSA)
- [ ] Register allocation with interference graph

## References

- Cytron, R. et al. (1991). "Efficiently computing static single assignment form and the control dependence graph"
- Appel, A. (2004). "Modern Compiler Implementation in ML" (dataflow chapters)
- Cooper, K. & Torczon, L. (2011). "Engineering a Compiler" (optimization chapters)
