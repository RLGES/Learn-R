# Rule Persistence and Feedback System

## Overview

The hierarchical rewrite system includes a complete persistence and feedback mechanism for learned rules. This creates a closed-loop learning system where rules:

1. **Persist** across sessions (saved to disk in JSON format)
2. **Receive feedback** based on optimization outcomes
3. **Are automatically pruned** if they perform poorly
4. **Improve over time** through memory-based prioritization

This document explains the architecture and usage of this system.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  LearnedRuleManager                         │
│  (Orchestrates entire learned rules lifecycle)              │
│                                                              │
│  • Loads rules from disk on initialization                  │
│  • Manages rule proposals and filtering                     │
│  • Updates memory based on feedback                         │
│  • Triggers pruning when rule count exceeds threshold       │
│  • Saves updated state to disk                              │
└──────┬──────────────────────────────────────────────┬───────┘
       │                                               │
       │ Uses                                    Uses  │
       ▼                                               ▼
┌─────────────────┐                          ┌──────────────────┐
│  RuleStorage    │                          │   RuleMemory     │
│                 │                          │                  │
│ • save_rules()  │                          │ • record_success │
│ • load_rules()  │                          │ • record_failure │
│ • JSON format   │                          │ • priority_score │
│ • Pretty print  │                          │ • prune_rules()  │
└─────────────────┘                          └──────────────────┘
       ▲                                               ▲
       │                                               │
       │ Persists                               Tracks │
       │                                               │
┌──────┴────────────────────────────────────────────┴─────────┐
│                  Learned Rules + Memory                      │
│  {                                                           │
│    "version": "1.0",                                        │
│    "rules": [{lhs, rhs, conditions}, ...],                 │
│    "memory": {                                              │
│      "successes": {"rule_name": count},                    │
│      "failures": {"rule_name": count}                      │
│    }                                                         │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Session 1:
  Initialize → Load from disk (empty) → Generate rules → Apply rules
                                                             │
                                                             ▼
  Extract best → Give feedback (success/fail) → Save to disk

Session 2:
  Initialize → Load from disk (with history) → Prioritize by score
                                                      │
                                                      ▼
  Apply high-scoring rules → Extract → Feedback → Prune → Save

Session N:
  (System improves over time as rule effectiveness is tracked)
```

---

## Components

### 1. RuleStorage (`rule_storage.py`)

**Purpose**: Persist learned rules and their memory to disk in JSON format.

**Key Functions**:

```python
def save_rules(rules: List[ParsedRule],
               memory: RuleMemory,
               db_path: str = DEFAULT_DB_PATH) -> None
```

- Saves rules and memory to JSON file
- Creates human-readable format with indent=2
- Overwrites previous version (single source of truth)
- Default path: `learned_rules_db.json`

```python
def load_rules(db_path: str = DEFAULT_DB_PATH) -> Tuple[List[ParsedRule], RuleMemory]
```

- Loads rules and memory from JSON
- Returns empty state if file doesn't exist
- Reconstructs ParsedRule and RuleMemory objects
- Handles corrupt files gracefully

```python
def get_database_stats(db_path: str = DEFAULT_DB_PATH) -> dict
```

- Returns metadata about stored rules
- Useful for diagnostics and monitoring

**JSON Format**:

```json
{
  "version": "1.0",
  "rules": [
    {
      "lhs_seq": ["MOV EAX, EBX", "MOV ECX, EAX"],
      "rhs_seq": ["MOV ECX, EBX"],
      "conditions": []
    }
  ],
  "memory": {
    "successes": {
      "mov_mov_learned": 5
    },
    "failures": {
      "mov_mov_learned": 1
    }
  }
}
```

---

### 2. RuleMemory with Pruning (`rule_memory.py`)

**Purpose**: Track rule effectiveness and prune low-performers.

**New Method**:

```python
def prune_rules(self, rules: List[ParsedRule], threshold: float = 0.1) -> List[ParsedRule]
```

**Pruning Strategy**:

- Filters rules with `priority_score < threshold`
- **Keeps untried rules** (gives them a chance)
- Only prunes rules with actual performance history
- Default threshold: 0.1 (10% success rate)

**Priority Scoring**:

```python
score = successes / (successes + failures + 1)
```

Examples:

- New rule (no history): 0/(0+0+1) = 0.0 → **kept** (no history check)
- 5 successes, 0 failures: 5/(5+0+1) = 0.833 → **kept**
- 1 success, 9 failures: 1/(1+9+1) = 0.091 → **pruned** (below 0.1)

---

### 3. LearnedRuleManager with Persistence (`learned_rule_manager.py`)

**Purpose**: Orchestrate complete lifecycle with persistence.

**Key Changes**:

**Initialization**:

```python
def __init__(self, existing_rule_names: Set[str] = None,
             db_path: str = DEFAULT_DB_PATH):
    # Load from disk on startup
    loaded_rules, loaded_memory = load_rules(db_path)
    self.memory = loaded_memory
    self.proposed_rules = loaded_rules
```

**Update Memory** (with auto-save and auto-prune):

```python
def update_memory(self, rule_name: str, success: bool) -> None:
    # Record outcome
    if success:
        self.memory.record_success(rule_name)
    else:
        self.memory.record_failure(rule_name)

    # Auto-prune if too many rules
    if len(self.proposed_rules) > MAX_TIER3_RULES:
        self.proposed_rules = self.memory.prune_rules(
            self.proposed_rules,
            threshold=PRUNING_THRESHOLD
        )

    # Auto-save to disk
    save_rules(self.proposed_rules, self.memory, self.db_path)
```

**Configuration**:

```python
MAX_TIER3_RULES = 50      # Trigger pruning above this
PRUNING_THRESHOLD = 0.1   # Minimum score to keep
```

---

### 4. EGraph API Extension (`egraph_api.py`)

**Purpose**: Support extraction feedback.

**New Method**:

```python
@abstractmethod
def get_applied_rules(self) -> list[str]:
    """
    Get names of rules that were successfully applied during e-graph expansion.

    This enables extraction feedback - the engine can determine which rules
    contributed to the final optimized sequence.

    Returns:
        List of rule names that were applied
    """
    pass
```

**Stub Implementation**:

```python
class StubEGraphAPI:
    def __init__(self):
        self.applied_rules = []

    def apply_rule(self, rule, match):
        self.applied_rules.append(rule.name)

    def get_applied_rules(self):
        return [app['rule'] for app in self.applied_rules]
```

---

### 5. Engine with Extraction Feedback (`engine.py`)

**Purpose**: Close the learning loop by giving feedback to rules.

**Key Changes**:

**Return Optimized Block**:

```python
def run(self, block: BasicBlock, ...) -> BasicBlock:
    # ... rewrite process ...

    # Extract best sequence
    optimized_instructions = self.egraph_api.extract_best()

    # Calculate improvement
    original_cost = len(block.instructions)
    optimized_cost = len(optimized_instructions)
    improvement = original_cost - optimized_cost

    # Give feedback
    if self.learned_rule_manager:
        applied_rules = self.egraph_api.get_applied_rules()
        success = improvement > 0

        for rule_name in applied_rules:
            if '_learned' in rule_name:  # Only Tier 3
                self.learned_rule_manager.update_memory(rule_name, success)

    return BasicBlock(optimized_instructions)
```

**Feedback Logic**:

- **Success** = optimization reduced instruction count
- **Failure** = optimization did not improve code
- Only tracks Tier 3 (learned) rules (identified by `_learned` suffix)

---

## Usage Examples

### Basic Usage

```python
from learned_rules import LearnedRuleManager

# Create manager (auto-loads from disk if available)
manager = LearnedRuleManager()

# Generate and propose rules
window = ["MOV EAX, EBX", "MOV ECX, EAX"]
rules = manager.propose_rules(window)

# ... apply rules in engine ...

# Give feedback after extraction
manager.update_memory("mov_mov_learned", success=True)
# Auto-saves to disk
```

### Custom Database Path

```python
manager = LearnedRuleManager(db_path="my_rules.json")
```

### Manual Pruning

```python
# Check current rule count
print(f"Current rules: {len(manager.proposed_rules)}")

# Manually prune low scorers
pruned = manager.memory.prune_rules(
    manager.proposed_rules,
    threshold=0.2  # More aggressive
)

# Update and save
manager.proposed_rules = pruned
from learned_rules.rule_storage import save_rules
save_rules(pruned, manager.memory, manager.db_path)
```

### Inspection

```python
# View all rule statistics
stats = manager.get_memory_stats()
for rule, data in stats.items():
    print(f"{rule}: score={data['score']:.3f} "
          f"(✓{data['successes']} ✗{data['failures']})")

# Get top performers
top_rules = manager.get_top_rules(n=10)
for rule_name, score in top_rules:
    print(f"{rule_name}: {score:.3f}")
```

---

## Complete Workflow

### Typical Session Flow

```python
from hierarchical_engine import HierarchicalEngine
from learned_rules import LearnedRuleManager
from asm_ir import BasicBlock, Instruction

# 1. Initialize (loads previous session)
manager = LearnedRuleManager()
print(f"Loaded {len(manager.proposed_rules)} rules from disk")

# 2. Setup engine with learned rules
rules_by_tier = {
    0: normalization_rules,
    1: peephole_rules,
    2: structural_rules,
    3: manager.proposed_rules  # Loaded from disk
}

engine = HierarchicalEngine(
    egraph_api=egraph,
    rules_by_tier=rules_by_tier,
    learned_rule_manager=manager  # Enable feedback
)

# 3. Optimize
block = BasicBlock(instructions)
optimized_block = engine.run(block)
# Feedback automatically given inside engine.run()

# 4. Session ends
# Rules and memory already saved to disk
# Next session will load improved state
```

### Multi-Session Learning

**Session 1**:

```
Load: 0 rules
Generate: 10 new rules
Apply: 5 succeed, 5 fail
Save: 10 rules with scores
```

**Session 2**:

```
Load: 10 rules (prioritized by scores)
Apply: High-scoring rules tried first
Feedback: 3 more successes, 2 more failures
Save: 10 rules with updated scores
```

**Session 5**:

```
Load: 10 rules (scores converged)
Apply: Consistently good rules prioritized
Feedback: 1 rule drops below threshold
Prune: Remove low-scorer
Save: 9 high-quality rules
```

---

## Configuration

### Tunable Parameters

Located in `learned_rule_manager.py`:

```python
# Maximum rules before pruning
MAX_TIER3_RULES = 50

# Minimum score to survive pruning
PRUNING_THRESHOLD = 0.1

# Database path
DEFAULT_DB_PATH = "learned_rules_db.json"
```

### Recommended Settings

**Conservative** (keeps more rules):

```python
MAX_TIER3_RULES = 100
PRUNING_THRESHOLD = 0.05
```

**Aggressive** (strict quality bar):

```python
MAX_TIER3_RULES = 20
PRUNING_THRESHOLD = 0.2
```

**Research/Exploration**:

```python
MAX_TIER3_RULES = 200
PRUNING_THRESHOLD = 0.0  # Never prune
```

---

## Best Practices

### 1. Database Management

**DO**:

- Use version control for rule databases (JSON is diff-friendly)
- Back up high-performing databases
- Use separate databases for different optimization targets
- Monitor database size with `get_database_stats()`

**DON'T**:

- Manually edit JSON (use API instead)
- Share databases across incompatible instruction sets
- Let databases grow unbounded (configure `MAX_TIER3_RULES`)

### 2. Feedback Accuracy

**Ensure feedback reflects actual utility**:

- Use realistic test cases
- Consider multiple cost metrics (not just instruction count)
- Account for context-specific optimizations
- Avoid feedback on synthetic/artificial code

### 3. Pruning Strategy

**Balance exploration vs exploitation**:

- Start with low threshold (0.05) to explore broadly
- Increase threshold (0.2+) once good rules found
- Periodically reset memory to avoid local optima
- Keep untried rules (system does this automatically)

### 4. Multi-Project Usage

```python
# Different databases for different targets
x86_manager = LearnedRuleManager(db_path="x86_rules.json")
arm_manager = LearnedRuleManager(db_path="arm_rules.json")

# Shared rules across projects
shared_manager = LearnedRuleManager(db_path="shared_rules.json")
```

---

## Diagnostics

### Check System Health

```python
from learned_rules.rule_storage import get_database_stats

stats = get_database_stats("learned_rules_db.json")
print(f"Rules: {stats['rule_count']}")
print(f"Tracked rules: {stats['memory_entries']}")
print(f"File size: {stats['file_size']} bytes")

# Rule quality distribution
manager = LearnedRuleManager()
all_stats = manager.get_memory_stats()

high_quality = sum(1 for s in all_stats.values() if s['score'] > 0.5)
low_quality = sum(1 for s in all_stats.values() if s['score'] < 0.2)

print(f"High quality (>0.5): {high_quality}")
print(f"Low quality (<0.2): {low_quality}")
```

### Debugging Persistence Issues

```python
# Verify save/load round-trip
from learned_rules import LearnedRuleManager
from learned_rules.rule_storage import save_rules, load_rules

# Create test data
manager = LearnedRuleManager()
manager.proposed_rules = [test_rule]
manager.memory.record_success("test_rule")

# Save
save_rules(manager.proposed_rules, manager.memory, "test.json")

# Load
loaded_rules, loaded_memory = load_rules("test.json")

# Verify
assert len(loaded_rules) == 1
assert loaded_memory.priority_score("test_rule") == manager.memory.priority_score("test_rule")
print("Round-trip successful!")
```

---

## Demo Script

See `examples/demo_persistence_feedback.py` for a complete demonstration showing:

1. ✓ Rule persistence across sessions
2. ✓ Memory tracking (successes/failures)
3. ✓ Extraction feedback integration
4. ✓ Automatic pruning of low-performers
5. ✓ Closed-loop learning system

Run with:

```bash
python examples/demo_persistence_feedback.py
```

---

## Future Enhancements

### Potential Improvements

1. **Versioned Databases**
   - Keep history of rule evolution
   - A/B test different rule sets
   - Rollback to previous versions

2. **Advanced Pruning**
   - Diversity-aware pruning (keep variety)
   - Context-specific rules (prune per domain)
   - Time-based decay (older rules fade)

3. **Distributed Learning**
   - Merge databases from multiple sources
   - Conflict resolution strategies
   - Federated learning across machines

4. **Analytics**
   - Rule genealogy (which LLM prompt generated it)
   - Cost/benefit analysis per rule
   - Visualization of rule effectiveness over time

---

## Summary

The persistence and feedback system creates a **self-improving optimizer** through:

- **Persistence**: Rules survive across sessions (JSON storage)
- **Feedback**: Extraction outcomes update rule scores
- **Pruning**: Low-performers automatically removed
- **Prioritization**: High-scorers tried first

This closes the learning loop, enabling the system to discover and retain effective optimizations over time without manual curation.
