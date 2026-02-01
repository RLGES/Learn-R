# Control Flow Support

This document describes the control flow capabilities added to the capstone project, including basic blocks with control flow edges, control flow graphs (CFG), jump instructions, if/while statements, and CFG-based optimization.

## Overview

The control flow extension adds support for:

- **Control flow constructs**: if/else statements and while loops in the high-level language
- **Jump instructions**: JMP (unconditional), JE, JNE, JZ, JNZ, JG, JL, JGE, JLE (conditional)
- **Comparison instruction**: CMP for setting flags used by conditional jumps
- **Basic blocks with successors**: Extended BasicBlock class to track control flow edges
- **Control Flow Graph (CFG)**: Data structure representing program control flow
- **CFG-based optimization**: Per-block optimization that respects control flow boundaries

## Changes Made

### 1. BasicBlock Extension (`asm_ir/basicblock.py`)

**Before:**

```python
class BasicBlock:
    def __init__(self, instructions: list[Instruction]):
        self.instructions = instructions
```

**After:**

```python
class BasicBlock:
    def __init__(self, label: str, instructions: list[Instruction] = None):
        self.label = label
        self.instructions = instructions if instructions is not None else []
        self.successors: List[str] = []  # Labels of successor blocks

    def add_successor(self, label: str):
        """Add a successor block by label."""
        if label not in self.successors:
            self.successors.append(label)
```

**Key Changes:**

- Added `label` field: Unique identifier for the block
- Constructor now requires a label parameter
- Added `successors` list: Track control flow edges to other blocks
- Added `add_successor()` method: Add edges to the CFG
- Enhanced `__str__()`: Display label and successors

**Impact:**

- Basic blocks can now represent nodes in a control flow graph
- Enables tracking of program structure and control dependencies
- Foundation for CFG-based analysis and optimization

### 2. Control Flow Graph (`asm_ir/cfg.py`)

**New File:**

```python
class CFG:
    def __init__(self, entry_label: str = "entry"):
        self.blocks: Dict[str, BasicBlock] = {}
        self.entry_label = entry_label

    def add_block(self, block: BasicBlock):
        """Add a basic block to the CFG."""
        if block.label in self.blocks:
            raise ValueError(f"Block with label '{block.label}' already exists")
        self.blocks[block.label] = block

    def connect_blocks(self, from_label: str, to_label: str):
        """Create an edge from one block to another."""
        if from_label not in self.blocks:
            raise KeyError(f"Source block '{from_label}' not found")
        if to_label not in self.blocks:
            raise KeyError(f"Destination block '{to_label}' not found")
        self.blocks[from_label].add_successor(to_label)

    def get_block(self, label: str) -> Optional[BasicBlock]:
        """Retrieve a basic block by label."""
        return self.blocks.get(label)
```

**Features:**

- **Block Storage**: Dictionary mapping labels to BasicBlock objects
- **Entry Point**: Designated entry_label marks program start
- **Block Management**: add_block(), get_block(), get_entry_block()
- **Edge Creation**: connect_blocks() creates control flow edges
- **Visualization**: **str**() displays CFG structure

**Example Usage:**

```python
cfg = CFG(entry_label='entry')

# Create blocks
entry = BasicBlock('entry', [Instruction('MOV', 'rax', ['0'])])
loop = BasicBlock('loop', [Instruction('ADD', 'rax', ['1'])])
exit = BasicBlock('exit', [Instruction('MOV', 'rbx', ['rax'])])

# Add to CFG
cfg.add_block(entry)
cfg.add_block(loop)
cfg.add_block(exit)

# Connect edges
cfg.connect_blocks('entry', 'loop')
cfg.connect_blocks('loop', 'exit')
cfg.connect_blocks('loop', 'loop')  # Back edge for loop
```

### 3. Jump Instructions (`asm_ir/instruction.py`)

**Added Fields:**

```python
@dataclass
class Instruction:
    opcode: str
    dst: Optional[str] = None
    srcs: list[str] = field(default_factory=list)
    flags_read: Set[str] = field(default_factory=set)
    flags_written: Set[str] = field(default_factory=set)
    mem_read: bool = False
    mem_write: bool = False
    is_control_flow_instr: bool = False  # NEW: Marks control flow instructions
```

**Added Method:**

```python
def is_control_flow(self) -> bool:
    """Check if this is a control flow instruction."""
    return self.is_control_flow_instr or self.opcode in {
        'JMP', 'JE', 'JNE', 'JZ', 'JNZ', 'JG', 'JL', 'JGE', 'JLE'
    }
```

**Updated Methods:**

- **reads()**: Control flow instructions don't read registers (may read flags)
- **writes()**: Control flow instructions don't write registers
- **get_flags_written()**: Control flow instructions don't write flags (conditional jumps read them)
- ****str**()**: Special formatting for jump instructions

**Jump Instruction Types:**

1. **Unconditional Jump:**

   ```python
   JMP label  # Jump to label unconditionally
   ```

2. **Conditional Jumps:**

   ```python
   JE  label  # Jump if equal (ZF=1)
   JNE label  # Jump if not equal (ZF=0)
   JZ  label  # Jump if zero (ZF=1)
   JNZ label  # Jump if not zero (ZF=0)
   JG  label  # Jump if greater (signed: SF=OF and ZF=0)
   JL  label  # Jump if less (signed: SF≠OF)
   JGE label  # Jump if greater or equal (signed: SF=OF)
   JLE label  # Jump if less or equal (signed: SF≠OF or ZF=1)
   ```

3. **Comparison Instruction:**
   ```python
   CMP operand1, operand2  # Sets flags based on operand1 - operand2
   ```

**Example:**

```python
# Unconditional jump
jmp = Instruction('JMP', 'loop_start', [], is_control_flow_instr=True)

# Conditional jump
je = Instruction('JE', 'then_block', [], flags_read={'zf'}, is_control_flow_instr=True)

# Comparison (sets flags)
cmp = Instruction('CMP', 'rax', ['rbx'])
```

### 4. Frontend Extensions

#### 4.1 AST Nodes (`frontend/ast_nodes.py`)

**Added Nodes:**

```python
@dataclass
class If:
    """If statement with optional else clause."""
    condition: Expr
    then_block: Block
    else_block: Block = None

@dataclass
class While:
    """While loop statement."""
    condition: Expr
    body: Block
```

**Enhanced BinOp:**

```python
@dataclass
class BinOp(Expr):
    """Binary operation expression."""
    op: str  # '+', '-', '*', '<', '>', '<=', '>=', '==', '!='
    left: Expr
    right: Expr
```

**Key Addition:**

- Added `from __future__ import annotations` for forward references
- Block.statements changed from `List[Assign]` to `List` (mixed statement types)

#### 4.2 Parser (`frontend/parser.py`)

**New Tokens:**

- Keywords: `IF`, `ELSE`, `WHILE`
- Comparison operators: `LT` (<), `GT` (>), `LTE` (<=), `GTE` (>=), `EQEQ` (==), `NEQ` (!=)
- Braces: `LBRACE` ({), `RBRACE` (})

**New Grammar:**

```
program   -> statement*
statement -> assignment | if_stmt | while_stmt
assignment -> IDENT '=' expr NEWLINE
if_stmt    -> 'if' '(' expr ')' '{' statement* '}' ('else' '{' statement* '}')?
while_stmt -> 'while' '(' expr ')' '{' statement* '}'
expr      -> term (('+' | '-') term)* (('<' | '>' | '<=', '>=' | '==' | '!=') expr)?
```

**New Parsing Methods:**

- `if_statement()`: Parse if with optional else
- `while_statement()`: Parse while loop
- `assignment()`: Renamed from statement()
- `statement()`: Dispatch to appropriate parser based on token

**Example Input:**

```python
a = 5
if (a < 10) {
    b = a + 1
}
while (b > 0) {
    b = b - 1
}
```

#### 4.3 IR Lowering (`frontend/ir_lowering.py`)

**Added to IRGenerator:**

```python
def __init__(self):
    self.temp_counter = 0
    self.label_counter = 0  # NEW
    self.instructions: List[str] = []

def new_label(self) -> str:
    """Generate a new label name."""
    label = f"L{self.label_counter}"
    self.label_counter += 1
    return label
```

**New Lowering Methods:**

1. **lower_if()**: Lower if statements to IR

   ```python
   # Input: if (a < b) { c = a } else { c = b }
   # Output:
   CMP a, b
   JGE L0        # Jump if NOT(a < b)
   c = a
   JMP L1
   L0:
   c = b
   L1:
   ```

2. **lower_while()**: Lower while loops to IR

   ```python
   # Input: while (a < 10) { a = a + 1 }
   # Output:
   L0:           # Loop start
   CMP a, 10
   JGE L1        # Exit if NOT(a < 10)
   a = a + 1
   JMP L0        # Jump back to start
   L1:           # Loop end
   ```

3. **lower_statements()**: Handle mixed statement types

**Comparison Handling:**

- Comparisons in expressions emit CMP instructions
- Returns placeholder like `_cmp_<` to indicate comparison type
- If/while lowering extracts operator and generates appropriate jump

**Jump Mapping (Inverted Logic):**

```python
jump_map = {
    '<': 'JGE',   # Jump if NOT less than
    '>': 'JLE',   # Jump if NOT greater than
    '<=': 'JG',   # Jump if NOT less or equal
    '>=': 'JL',   # Jump if NOT greater or equal
    '==': 'JNE',  # Jump if NOT equal
    '!=': 'JE'    # Jump if NOT not-equal
}
```

**Why Inverted?** Conditional jumps skip the "then" block when condition is FALSE.

#### 4.4 Assembly Codegen (`frontend/asm_codegen.py`)

**Extended parse_ir_instruction():**

1. **Label Recognition:**

   ```python
   if ir_instr.endswith(':'):
       label = ir_instr[:-1]
       self.labels.append(label)
       return []  # Labels are markers, not instructions
   ```

2. **CMP Instruction:**

   ```python
   # Pattern: CMP a, b
   cmp_pattern = r'CMP\s+(\w+),\s*(\w+)'
   return [Instruction('CMP', operand1, [operand2])]
   ```

3. **Unconditional Jump:**

   ```python
   # Pattern: JMP label
   jmp_pattern = r'JMP\s+(\w+)'
   return [Instruction('JMP', label, [], is_control_flow_instr=True)]
   ```

4. **Conditional Jumps:**
   ```python
   # Pattern: JE label, JNE label, etc.
   cond_jmp_pattern = r'(JE|JNE|JZ|JNZ|JL|JG|JLE|JGE)\s+(\w+)'
   flags_read = {'zf'}
   if opcode in ['JL', 'JG', 'JLE', 'JGE']:
       flags_read.update({'sf', 'of'})
   return [Instruction(opcode, label, [], flags_read=flags_read, is_control_flow_instr=True)]
   ```

### 5. Pipeline Updates (`pipeline/full_pipeline.py`)

**New Function: build_cfg_from_assembly()**

```python
def build_cfg_from_assembly(instructions: List[Instruction]) -> CFG:
    """
    Build a Control Flow Graph from assembly instructions.

    Splits instructions into basic blocks at:
    - Labels (start of new block)
    - Jump instructions (end of current block)
    - Instructions following jumps (start of new block)
    """
```

**Algorithm:**

1. Identify jump targets from all jump instructions
2. Split instructions at control flow boundaries
3. Create BasicBlock for each segment
4. Connect blocks based on jumps and fall-through

**Modified run_full_pipeline():**

```python
def run_full_pipeline(source_code: str, verbose: bool = True, use_cfg: bool = False):
    # ... parse, lower, generate assembly ...

    # Stage 4: Build CFG if requested
    if use_cfg and any(instr.is_control_flow() for instr in asm_instructions):
        cfg = build_cfg_from_assembly(asm_instructions)

    # Stage 5: Optimize
    if cfg:
        # Optimize each block separately
        for label, block in cfg.blocks.items():
            egraph_api = StubEGraph()
            egraph_api.block = block
            engine = HierarchicalEngine(egraph_api, rules_by_tier={1: tier1_rules})
            optimized_block = engine.run(block)
            block.instructions = optimized_block.instructions

        # Collect optimized instructions from all blocks
        optimized_instructions = []
        for label in sorted(cfg.blocks.keys()):
            optimized_instructions.extend(cfg.get_block(label).instructions)
        optimized_block = BasicBlock("combined", optimized_instructions)
    else:
        # Single block optimization (original)
        ...
```

**Benefits:**

- Respects control flow boundaries during optimization
- Avoids incorrect optimizations across basic block boundaries
- Enables future inter-block optimizations (dead code elimination, constant propagation)

## Integration with Existing System

### Verification System

- **Symbolic Executor**: Can be extended to handle jumps and labels
- **Equivalence Checker**: Need to handle branching (multiple paths)
- **Rule Verifier**: Control flow rules require path-sensitive verification

### Optimization Rules

- **Tier 1 Peephole**: Work within basic blocks (no changes needed)
- **Tier 2 Structural**: Can now use CFG for pattern matching across edges
- **Tier 3 Learned**: Can learn control flow patterns

### Dependency Analysis

- **Register Dependencies**: Still work within blocks
- **Memory Dependencies**: Conservative approach still valid
- **Control Dependencies**: New concept - instructions dependent on branch outcomes

## Testing

### Test Suite (`tests/test_control_flow.py`)

**Test Coverage:**

1. **test_basicblock_with_label()**: BasicBlock label and successors
2. **test_cfg_creation()**: CFG construction and connections
3. **test_jump_instructions()**: Jump instruction properties
4. **test_parse_if_statement()**: If/else parsing
5. **test_parse_while_statement()**: While loop parsing
6. **test_lower_if_to_ir()**: If lowering with jumps
7. **test_lower_while_to_ir()**: While lowering with loops
8. **test_assemble_control_flow()**: Assembly generation
9. **test_comparison_operators()**: All 6 comparison operators

**Test Results:**

```
======================================================================
CONTROL FLOW TESTS
======================================================================
Test 1: BasicBlock with label and successors
  PASS: BasicBlock with label and successors

Test 2: CFG creation and manipulation
  PASS: CFG creation and manipulation

... (all 9 tests pass) ...

======================================================================
ALL TESTS PASSED
======================================================================
```

### Demo (`demos/control_flow_demo.py`)

**Demonstrations:**

1. **If Statement**: Parsing, IR generation, assembly with jumps
2. **While Loop**: Loop structure with back edges
3. **Nested Control Flow**: If inside while
4. **Comparison Operators**: All 6 operators (<, >, <=, >=, ==, !=)
5. **CFG Construction**: Manual CFG creation and visualization
6. **Full Pipeline with CFG**: End-to-end compilation with per-block optimization

**Sample Output:**

```
======================================================================
DEMO 2: WHILE LOOP
======================================================================

Source Code:
i = 0
sum = 0
while (i < 5) {
    sum = sum + i
    i = i + 1
}

IR (Three-Address Code with Jumps and Labels):
  t0 = 0
  i = t0
  t1 = 0
  sum = t1
  L0:              <- Loop start label
  t2 = 5
  CMP i, t2        <- Comparison
  JGE L1           <- Exit loop if i >= 5
  t3 = sum + i
  sum = t3
  t4 = 1
  t5 = i + t4
  i = t5
  JMP L0           <- Jump back to loop start
  L1:              <- Loop end label

Assembly (15 instructions):
   0. MOV t0, 0
   1. MOV i, t0
   2. MOV t1, 0
   3. MOV sum, t1
   4. MOV t2, 5
   5. CMP t2 <-- Comparison
   6. JGE L1 <-- Control Flow
   7. MOV t3, sum
   8. ADD t3, i
   9. MOV sum, t3
  10. MOV t4, 1
  11. MOV t5, i
  12. ADD t5, t4
  13. MOV i, t5
  14. JMP L0 <-- Control Flow
```

## Examples

### Example 1: Simple If Statement

**Input:**

```python
a = 5
if (a < 10) {
    b = 1
}
```

**IR:**

```
t0 = 5
a = t0
t1 = 10
CMP a, t1
JGE L1       # Skip then block if a >= 10
t2 = 1
b = t2
L1:          # End label
```

**Assembly:**

```
MOV t0, 5
MOV a, t0
MOV t1, 10
CMP a, t1
JGE L1
MOV t2, 1
MOV b, t2
```

### Example 2: If-Else

**Input:**

```python
if (x > y) {
    max = x
} else {
    max = y
}
```

**IR:**

```
CMP x, y
JLE L0       # Jump to else if x <= y
max = x
JMP L1       # Skip else block
L0:          # Else label
max = y
L1:          # End label
```

### Example 3: While Loop

**Input:**

```python
i = 0
while (i < 5) {
    i = i + 1
}
```

**IR:**

```
t0 = 0
i = t0
L0:          # Loop start
t1 = 5
CMP i, t1
JGE L1       # Exit if i >= 5
t2 = 1
t3 = i + t2
i = t3
JMP L0       # Back to loop start
L1:          # Loop end
```

### Example 4: CFG for Loop

**Code:**

```python
while (i < 10) {
    i = i + 1
}
```

**CFG Structure:**

```
entry:
  MOV t0, 0
  MOV i, t0
  -> loop_start

loop_start:
  MOV t1, 10
  CMP i, t1
  JGE loop_end
  -> loop_body, loop_end

loop_body:
  MOV t2, 1
  MOV t3, i
  ADD t3, t2
  MOV i, t3
  JMP loop_start
  -> loop_start

loop_end:
  (exit)
```

**Edges:**

- entry → loop_start (fall-through)
- loop_start → loop_body (conditional: i < 10)
- loop_start → loop_end (conditional: i >= 10)
- loop_body → loop_start (back edge)

## Current Limitations

1. **CFG Construction**: Simplified implementation
   - Doesn't handle all edge cases (function calls, indirect jumps)
   - Limited support for recognizing jump targets
   - Sequential fall-through assumed in many cases

2. **Inter-Block Optimization**: Not yet implemented
   - Optimizations only within basic blocks
   - No cross-block constant propagation
   - No dead code elimination across blocks

3. **Verification**: Control flow not fully verified
   - Symbolic execution doesn't handle branches yet
   - Equivalence checking limited to straight-line code
   - No path-sensitive analysis

4. **Parser Limitations**:
   - No short-circuit evaluation for && and ||
   - No break/continue statements
   - No for loops (only while)
   - No switch statements

5. **Optimization Limitations**:
   - Per-block optimization may miss opportunities
   - No loop invariant code motion
   - No loop unrolling

## Future Enhancements

### 1. Advanced Control Flow

- **For Loops**: `for (i = 0; i < 10; i++) { ... }`
- **Break/Continue**: Early loop exit and iteration skip
- **Switch Statements**: Multi-way branching
- **Short-Circuit Evaluation**: && and || with lazy evaluation

### 2. CFG Analysis

- **Dominators**: Identify dominator tree
- **Post-Dominators**: Reverse dominance
- **Natural Loops**: Detect loop structures
- **Reducibility**: Check if CFG is reducible

### 3. Inter-Block Optimization

- **Dead Code Elimination**: Remove unreachable blocks
- **Constant Propagation**: Propagate values across blocks
- **Common Subexpression Elimination**: Across block boundaries
- **Loop Optimizations**: Invariant code motion, unrolling, fusion

### 4. Verification Support

- **Path-Sensitive Verification**: Verify all paths through CFG
- **Symbolic Execution with Branching**: Handle conditional jumps
- **Loop Invariants**: Prove loop correctness
- **Termination Analysis**: Verify loops terminate

### 5. Code Generation

- **Jump Table Generation**: For switch statements
- **Branch Prediction Hints**: Optimize likely/unlikely paths
- **Function Calls**: Support call/return instructions
- **Exception Handling**: Try/catch blocks with unwinding

## Performance Considerations

### Memory Usage

- CFG adds overhead: one BasicBlock object per block
- Each block stores label, instructions, and successor list
- Acceptable for small-to-medium programs

### Optimization Time

- Per-block optimization is fast (linear in block size)
- CFG construction is O(n) in instruction count
- Inter-block optimizations would be more expensive (O(n²) or worse)

### Code Size

- Control flow adds jump instructions (overhead)
- Optimizations can reduce overhead (e.g., remove unnecessary jumps)
- Trade-off between code size and execution speed

## Conclusion

The control flow extension successfully adds:

- ✅ If/else and while statements to the language
- ✅ Jump instructions (conditional and unconditional)
- ✅ CMP instruction for comparisons
- ✅ CFG data structure with basic blocks and edges
- ✅ Per-block optimization respecting control flow
- ✅ Comprehensive tests and demos

This foundation enables future enhancements like inter-block optimization, advanced control flow analysis, and path-sensitive verification. The system now supports a more complete subset of imperative programming with structured control flow.
