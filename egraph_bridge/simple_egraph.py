"""
Simple E-Graph implementation for SSA optimization.

Provides basic e-graph data structures (ENode, EClass, EGraph) for
equality saturation.
"""
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ENode:
    """
    E-node: represents an operation with child e-classes.
    
    Example: add(e1, e2) where e1 and e2 are e-class IDs
    """
    op: str
    children: List[Any] = field(default_factory=list)  # Can be int (eclass IDs) or values
    
    def __str__(self) -> str:
        if not self.children:
            return self.op
        child_str = ", ".join(str(c) for c in self.children)
        return f"{self.op}({child_str})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __hash__(self) -> int:
        return hash((self.op, tuple(self.children)))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ENode):
            return False
        return self.op == other.op and self.children == other.children


@dataclass
class EClass:
    """
    E-class: equivalence class of expressions.
    
    Contains multiple e-nodes that are proven equivalent.
    """
    id: int
    nodes: List[ENode] = field(default_factory=list)
    parents: Set[int] = field(default_factory=set)  # E-classes that reference this one
    
    def add_node(self, node: ENode):
        """Add an e-node to this class."""
        if node not in self.nodes:
            self.nodes.append(node)
    
    def __str__(self) -> str:
        return f"EClass({self.id}, nodes={len(self.nodes)})"
    
    def __repr__(self) -> str:
        return self.__str__()


class EGraph:
    """
    E-graph: equivalence graph for equality saturation.
    
    Maintains equivalence classes of expressions and supports:
    - Adding expressions
    - Merging equivalent classes
    - Pattern matching and rewriting
    """
    
    def __init__(self):
        self.eclasses: Dict[int, EClass] = {}
        self.hashcons: Dict[ENode, int] = {}  # Hash-consing: node -> eclass ID
        self.next_id = 0
        self.union_find: Dict[int, int] = {}  # Union-find for merging
        self.pending_merges: List[tuple] = []
    
    def add(self, node: ENode) -> int:
        """
        Add an e-node to the e-graph.
        
        Args:
            node: E-node to add
        
        Returns:
            E-class ID containing the node
        """
        # Canonicalize children (resolve union-find)
        canonical_node = self._canonicalize(node)
        
        # Check if we've seen this node before (hash-consing)
        if canonical_node in self.hashcons:
            return self.hashcons[canonical_node]
        
        # Create new e-class for this node
        eclass_id = self.next_id
        self.next_id += 1
        
        eclass = EClass(id=eclass_id)
        eclass.add_node(canonical_node)
        
        self.eclasses[eclass_id] = eclass
        self.hashcons[canonical_node] = eclass_id
        self.union_find[eclass_id] = eclass_id
        
        # Update parent links
        for child_id in canonical_node.children:
            if isinstance(child_id, int) and child_id in self.eclasses:
                self.eclasses[child_id].parents.add(eclass_id)
        
        return eclass_id
    
    def merge(self, id1: int, id2: int):
        """
        Merge two e-classes (assert they are equivalent).
        
        Args:
            id1: First e-class ID
            id2: Second e-class ID
        """
        if id1 == id2:
            return
        
        # Schedule merge for later (batching improves performance)
        self.pending_merges.append((id1, id2))
    
    def rebuild(self):
        """
        Rebuild e-graph after merges.
        
        Processes pending merges and updates hash-consing.
        """
        # Process all pending merges
        for id1, id2 in self.pending_merges:
            self._union(id1, id2)
        
        self.pending_merges.clear()
        
        # Rebuild hash-consing
        self._rebuild_hashcons()
    
    def _union(self, id1: int, id2: int):
        """Union operation for union-find."""
        root1 = self._find(id1)
        root2 = self._find(id2)
        
        if root1 == root2:
            return
        
        # Merge smaller into larger
        if root1 > root2:
            root1, root2 = root2, root1
        
        self.union_find[root2] = root1
        
        # Merge e-class contents
        if root1 in self.eclasses and root2 in self.eclasses:
            # Add all nodes from root2 to root1
            for node in self.eclasses[root2].nodes:
                self.eclasses[root1].add_node(node)
            
            # Merge parent sets
            self.eclasses[root1].parents.update(self.eclasses[root2].parents)
    
    def _find(self, id: int) -> int:
        """Find operation for union-find with path compression."""
        if id not in self.union_find:
            self.union_find[id] = id
            return id
        
        if self.union_find[id] != id:
            # Path compression
            self.union_find[id] = self._find(self.union_find[id])
        
        return self.union_find[id]
    
    def _canonicalize(self, node: ENode) -> ENode:
        """Canonicalize node by resolving children through union-find."""
        canonical_children = []
        for child in node.children:
            if isinstance(child, int):
                canonical_children.append(self._find(child))
            else:
                canonical_children.append(child)
        
        return ENode(op=node.op, children=canonical_children)
    
    def _rebuild_hashcons(self):
        """Rebuild hash-consing after merges."""
        new_hashcons = {}
        
        for node, eclass_id in self.hashcons.items():
            canonical_id = self._find(eclass_id)
            canonical_node = self._canonicalize(node)
            
            if canonical_node not in new_hashcons:
                new_hashcons[canonical_node] = canonical_id
        
        self.hashcons = new_hashcons
    
    def apply_rule(self, rule) -> int:
        """
        Apply a rewrite rule to the e-graph.
        
        Args:
            rule: Rewrite rule with pattern() and replacement() methods
        
        Returns:
            Number of times the rule was applied
        """
        matches = 0
        
        # Find all matches of the pattern
        for eclass_id, eclass in list(self.eclasses.items()):
            canonical_id = self._find(eclass_id)
            
            if canonical_id != eclass_id:
                continue  # Skip merged classes
            
            for node in eclass.nodes:
                # Try to match pattern
                if self._matches_pattern(node, rule.pattern()):
                    # Apply replacement
                    replacement_node = self._apply_replacement(node, rule)
                    if replacement_node:
                        replacement_id = self.add(replacement_node)
                        self.merge(canonical_id, replacement_id)
                        matches += 1
        
        # Rebuild after applying rules
        if matches > 0:
            self.rebuild()
        
        return matches
    
    def _matches_pattern(self, node: ENode, pattern) -> bool:
        """Check if node matches a pattern."""
        # Simple pattern matching - compare operations
        if hasattr(pattern, 'op'):
            return node.op == pattern.op
        return False
    
    def _apply_replacement(self, node: ENode, rule) -> Optional[ENode]:
        """Apply replacement for a matched node."""
        try:
            # Get replacement pattern
            replacement = rule.replacement()
            
            # Simple replacement - create new node with same children
            if hasattr(replacement, 'op'):
                return ENode(op=replacement.op, children=node.children)
        except:
            pass
        
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get e-graph statistics."""
        active_eclasses = sum(1 for id in self.eclasses if self._find(id) == id)
        total_nodes = sum(len(ec.nodes) for ec in self.eclasses.values())
        
        return {
            'eclasses': active_eclasses,
            'total_eclasses': len(self.eclasses),
            'nodes': total_nodes,
            'hashcons_entries': len(self.hashcons)
        }
    
    def __str__(self) -> str:
        stats = self.get_stats()
        return f"EGraph({stats['eclasses']} classes, {stats['nodes']} nodes)"
    
    def __repr__(self) -> str:
        return self.__str__()
