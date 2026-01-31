# Quick Start: Persistence & Feedback System

## TL;DR

The system now **learns from optimization outcomes** and **improves over time** through:

- **Persistence**: Rules saved to `learned_rules_db.json`
- **Feedback**: Successful optimizations increase rule scores
- **Pruning**: Bad rules automatically removed

## 30-Second Demo

```bash
cd capstone
python examples/demo_persistence_feedback.py
```

You'll see:

1. Rules persist to disk ✓
2. Memory tracks success/failure ✓
3. Low-performers get pruned ✓
4. System learns over time ✓

## Basic Usage

### Initialize (auto-loads from disk)

```python
from learned_rules import LearnedRuleManager

manager = LearnedRuleManager()
# Automatically loads rules and memory from learned_rules_db.json
```

### Give Feedback

```python
# After applying a rule and extracting optimized code
if optimized_better_than_original:
    manager.update_memory("rule_name", success=True)
else:
    manager.update_memory("rule_name", success=False)

# Automatically:
# - Updates memory
# - Prunes if needed (>50 rules)
# - Saves to disk
```

### Check Status

```python
print(manager)
# Shows:
# - Number of rules
# - Memory statistics
# - Priority scores
```

## How It Works

### Session 1

```
1. Manager created (empty)
2. Generate rules via LLM
3. Apply rules → extract best
4. Feedback: success/failure
5. Save to disk ← happens automatically
```

### Session 2

```
1. Manager created (loads from disk)
2. Apply rules (high-scorers first)
3. Extract best
4. Feedback updates scores
5. Auto-prune if >50 rules
6. Save updated state
```

### Session N

```
System converges to high-quality rules
```

## Configuration

### Change Database Path

```python
manager = LearnedRuleManager(db_path="my_rules.json")
```

### Adjust Pruning

Edit `learned_rules/learned_rule_manager.py`:

```python
MAX_TIER3_RULES = 50      # When to prune
PRUNING_THRESHOLD = 0.1   # Min score to keep
```

**Conservative** (keep more):

```python
MAX_TIER3_RULES = 100
PRUNING_THRESHOLD = 0.05
```

**Aggressive** (strict quality):

```python
MAX_TIER3_RULES = 20
PRUNING_THRESHOLD = 0.2
```

## Inspection

### View Statistics

```python
# All rules
stats = manager.get_memory_stats()
for rule, data in stats.items():
    print(f"{rule}: {data['score']:.3f} "
          f"(✓{data['successes']} ✗{data['failures']})")

# Top performers
top = manager.get_top_rules(n=5)
for name, score in top:
    print(f"{name}: {score:.3f}")
```

### Database Info

```python
from learned_rules.rule_storage import get_database_stats

stats = get_database_stats("learned_rules_db.json")
print(f"Rules: {stats['rule_count']}")
print(f"Tracked: {stats['memory_entries']}")
print(f"Size: {stats['file_size']} bytes")
```

## Common Tasks

### Start Fresh

```python
from learned_rules.rule_storage import clear_database

clear_database("learned_rules_db.json")
manager = LearnedRuleManager()  # Empty state
```

### Backup Rules

```bash
# JSON is human-readable, version control friendly
cp learned_rules_db.json backup_rules.json
```

### Share Rules

```bash
# Send to colleague
scp learned_rules_db.json colleague@machine:/path/

# On colleague's machine
python  # Uses learned_rules_db.json automatically
```

### Merge Databases

```python
# Load both
manager1 = LearnedRuleManager(db_path="db1.json")
manager2 = LearnedRuleManager(db_path="db2.json")

# Combine rules
combined_rules = manager1.proposed_rules + manager2.proposed_rules

# Merge memory (average scores)
for rule in combined_rules:
    # Custom merging logic here
    pass

# Save merged
from learned_rules.rule_storage import save_rules
save_rules(combined_rules, merged_memory, "merged.json")
```

## Integration with Engine

```python
from hierarchical_engine import HierarchicalEngine
from learned_rules import LearnedRuleManager

# Setup
manager = LearnedRuleManager()  # Loads from disk
engine = HierarchicalEngine(
    egraph_api=egraph,
    rules_by_tier={
        0: tier0_rules,
        1: tier1_rules,
        2: tier2_rules,
        3: manager.proposed_rules  # Learned rules
    },
    learned_rule_manager=manager  # Enable feedback
)

# Run (feedback happens automatically inside)
optimized = engine.run(block)

# Rules already saved to disk
```

## Troubleshooting

### "No database found"

This is normal on first run. System starts with empty database.

### "Rules not persisting"

Check file permissions:

```bash
ls -l learned_rules_db.json
```

Verify saves are happening:

```python
manager.update_memory("test", True)
# Should print: "Saved X learned rules to learned_rules_db.json"
```

### "Too many rules"

Increase threshold:

```python
# In learned_rule_manager.py
MAX_TIER3_RULES = 100  # Instead of 50
```

Or manually prune:

```python
manager.proposed_rules = manager.memory.prune_rules(
    manager.proposed_rules,
    threshold=0.3  # More aggressive
)
```

### "Scores not updating"

Verify feedback is being called:

```python
# Add debug print
def update_memory(self, rule_name, success):
    print(f"Feedback: {rule_name} → {'✓' if success else '✗'}")
    # ... rest of method
```

### "Corrupted database"

Reset:

```python
from learned_rules.rule_storage import clear_database
clear_database("learned_rules_db.json")
```

Or fix manually (it's just JSON):

```bash
cat learned_rules_db.json  # Inspect
# Fix any JSON syntax errors
```

## Best Practices

### ✅ DO

- Let system auto-save (don't disable)
- Use version control for databases
- Backup before major changes
- Monitor database size periodically
- Give accurate feedback (real optimizations)

### ❌ DON'T

- Manually edit JSON (use API)
- Share databases across incompatible targets
- Ignore pruning warnings
- Give fake feedback (hurts learning)
- Delete database without backup

## Performance

### Overhead

- **Load**: ~1ms for 50 rules
- **Save**: ~2ms for 50 rules
- **Prune**: ~1ms for 100 rules

**Total**: <5ms per optimization run (negligible)

### Scaling

- **1-50 rules**: No issues
- **50-200 rules**: Consider pruning
- **200+ rules**: Definitely prune or switch to database

## Learn More

- **Full guide**: [docs/persistence_feedback.md](docs/persistence_feedback.md)
- **Architecture**: [docs/architecture.md](docs/architecture.md)
- **Learned rules**: [docs/learned_rules.md](docs/learned_rules.md)

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│  PERSISTENCE & FEEDBACK QUICK REFERENCE             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  INITIALIZE                                         │
│    manager = LearnedRuleManager()                   │
│    # Auto-loads from learned_rules_db.json          │
│                                                      │
│  GIVE FEEDBACK                                      │
│    manager.update_memory("rule_name", success=True) │
│    # Auto-saves to disk                             │
│                                                      │
│  CHECK STATUS                                       │
│    print(manager)                                   │
│    stats = manager.get_memory_stats()               │
│                                                      │
│  RESET                                              │
│    from learned_rules.rule_storage import clear_db  │
│    clear_database("learned_rules_db.json")          │
│                                                      │
│  CONFIG (learned_rule_manager.py)                   │
│    MAX_TIER3_RULES = 50                             │
│    PRUNING_THRESHOLD = 0.1                          │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

**Status**: ✅ System ready to use

**Next**: Run real benchmarks and watch it learn!
