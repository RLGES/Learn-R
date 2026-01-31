"""
Rule storage module for persisting learned rules and memory to disk.

Stores rules and their effectiveness scores in a human-readable JSON format.
"""
import json
import os
from typing import Tuple, List, Dict, Any
from pathlib import Path
from .rule_parser import ParsedRule
from .rule_memory import RuleMemory


# Default storage location
DEFAULT_DB_PATH = "learned_rules_db.json"


def save_rules(rules: List[ParsedRule], memory: RuleMemory, 
               db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Save learned rules and their memory scores to disk.
    
    Args:
        rules: List of ParsedRule objects to save
        memory: RuleMemory instance with effectiveness scores
        db_path: Path to JSON database file
    """
    # Build the data structure
    data = {
        "version": "1.0",
        "rules": [],
        "memory": {
            "successes": memory.successes,
            "failures": memory.failures
        }
    }
    
    # Serialize each rule
    for rule in rules:
        rule_data = {
            "lhs_seq": rule.lhs_seq,
            "rhs_seq": rule.rhs_seq,
            "conditions": rule.conditions
        }
        data["rules"].append(rule_data)
    
    # Write to file with pretty formatting
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(rules)} learned rules to {db_path}")


def load_rules(db_path: str = DEFAULT_DB_PATH) -> Tuple[List[ParsedRule], RuleMemory]:
    """
    Load learned rules and their memory scores from disk.
    
    Args:
        db_path: Path to JSON database file
    
    Returns:
        Tuple of (list of ParsedRule objects, RuleMemory instance)
        If file doesn't exist, returns empty list and new RuleMemory
    """
    # Check if file exists
    if not os.path.exists(db_path):
        print(f"No learned rules database found at {db_path}, starting fresh")
        return [], RuleMemory()
    
    try:
        # Load from file
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct rules
        rules = []
        for rule_data in data.get("rules", []):
            rule = ParsedRule(
                lhs_seq=rule_data.get("lhs_seq", []),
                rhs_seq=rule_data.get("rhs_seq", []),
                conditions=rule_data.get("conditions", [])
            )
            rules.append(rule)
        
        # Reconstruct memory
        memory = RuleMemory()
        memory_data = data.get("memory", {})
        memory.successes = memory_data.get("successes", {})
        memory.failures = memory_data.get("failures", {})
        
        print(f"Loaded {len(rules)} learned rules from {db_path}")
        return rules, memory
    
    except (json.JSONDecodeError, KeyError, IOError) as e:
        print(f"Error loading learned rules database: {e}")
        print("Starting with empty rule set")
        return [], RuleMemory()


def clear_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Clear the learned rules database.
    
    Args:
        db_path: Path to JSON database file
    """
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Cleared learned rules database at {db_path}")
    else:
        print(f"No database found at {db_path}")


def get_database_stats(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """
    Get statistics about the stored rules database.
    
    Args:
        db_path: Path to JSON database file
    
    Returns:
        Dictionary with statistics
    """
    if not os.path.exists(db_path):
        return {
            "exists": False,
            "rule_count": 0,
            "memory_entries": 0,
            "file_size": 0
        }
    
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        memory_data = data.get("memory", {})
        successes = memory_data.get("successes", {})
        failures = memory_data.get("failures", {})
        all_tracked_rules = set(successes.keys()) | set(failures.keys())
        
        file_size = os.path.getsize(db_path)
        
        return {
            "exists": True,
            "rule_count": len(data.get("rules", [])),
            "memory_entries": len(all_tracked_rules),
            "file_size": file_size,
            "version": data.get("version", "unknown")
        }
    
    except Exception as e:
        return {
            "exists": True,
            "error": str(e)
        }
