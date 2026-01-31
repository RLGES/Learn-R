"""
Smart instruction window sampling for LLM rule discovery.

Prioritizes windows with:
- Frequently seen opcode sequences
- Patterns that haven't been optimized yet
"""
from typing import List, Dict, Set
from collections import Counter
from asm_ir import BasicBlock


class WindowSampler:
    """
    Intelligent sampler for instruction windows.
    
    Tracks opcode frequency and optimization history to prioritize
    useful patterns for LLM rule generation.
    """
    
    def __init__(self):
        """Initialize sampler state."""
        # Track opcode sequence frequency
        self.sequence_frequency: Counter = Counter()
        
        # Track sequences that were successfully optimized
        self.optimized_sequences: Set[str] = set()
    
    def _get_opcode_sequence(self, instructions: List[str]) -> str:
        """
        Extract opcode sequence from instructions.
        
        Args:
            instructions: List of instruction strings
        
        Returns:
            Space-separated opcode sequence (e.g., "MOV ADD SUB")
        """
        opcodes = []
        for instr in instructions:
            parts = instr.strip().split()
            if parts:
                opcodes.append(parts[0].upper())
        return ' '.join(opcodes)
    
    def record_sequence(self, instructions: List[str]) -> None:
        """
        Record seeing an instruction sequence.
        
        Args:
            instructions: List of instruction strings
        """
        seq = self._get_opcode_sequence(instructions)
        self.sequence_frequency[seq] += 1
    
    def mark_optimized(self, instructions: List[str]) -> None:
        """
        Mark a sequence as having been optimized.
        
        Args:
            instructions: List of instruction strings
        """
        seq = self._get_opcode_sequence(instructions)
        self.optimized_sequences.add(seq)
    
    def _compute_window_score(self, window: List[str]) -> float:
        """
        Compute priority score for a window.
        
        Higher score = more interesting for LLM.
        
        Scoring:
        - +frequency: More common patterns are more valuable
        - -10 if already optimized: Avoid redundant rules
        
        Args:
            window: List of instruction strings
        
        Returns:
            Priority score (higher = more interesting)
        """
        seq = self._get_opcode_sequence(window)
        
        # Base score: frequency (how often we see this pattern)
        frequency = self.sequence_frequency.get(seq, 0)
        score = float(frequency)
        
        # Penalty for already optimized sequences
        if seq in self.optimized_sequences:
            score -= 10.0
        
        return score
    
    def sample_windows(self, basic_block: BasicBlock, 
                      window_size: int = 3,
                      max_windows: int = 5) -> List[List[str]]:
        """
        Sample instruction windows from a basic block.
        
        Uses intelligent sampling strategy:
        1. Extract all possible windows
        2. Score each window by frequency and optimization status
        3. Return top-scored windows
        
        Args:
            basic_block: The basic block to sample from
            window_size: Size of each window (default: 3)
            max_windows: Maximum number of windows to return (default: 5)
        
        Returns:
            List of instruction windows (each window is a list of strings)
        """
        instructions = [str(instr) for instr in basic_block.instructions]
        
        # Generate all possible windows
        windows = []
        for i in range(len(instructions) - window_size + 1):
            window = instructions[i:i + window_size]
            windows.append(window)
        
        # If no windows or very few, return what we have
        if len(windows) <= max_windows:
            return windows
        
        # Score each window
        scored_windows = [(window, self._compute_window_score(window)) 
                         for window in windows]
        
        # Sort by score (highest first)
        scored_windows.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N windows
        return [window for window, _ in scored_windows[:max_windows]]
    
    def get_top_sequences(self, n: int = 10) -> List[tuple[str, int]]:
        """
        Get most frequent opcode sequences.
        
        Args:
            n: Number of top sequences to return
        
        Returns:
            List of (sequence, count) tuples
        """
        return self.sequence_frequency.most_common(n)
    
    def get_unoptimized_sequences(self) -> List[str]:
        """
        Get sequences that haven't been optimized yet.
        
        Returns:
            List of opcode sequences
        """
        all_sequences = set(self.sequence_frequency.keys())
        unoptimized = all_sequences - self.optimized_sequences
        return sorted(unoptimized, 
                     key=lambda s: self.sequence_frequency[s], 
                     reverse=True)
    
    def reset(self) -> None:
        """Clear all sampler state."""
        self.sequence_frequency.clear()
        self.optimized_sequences.clear()
    
    def __str__(self) -> str:
        """String representation of sampler state."""
        result = "WindowSampler:\n"
        result += f"  Tracked sequences: {len(self.sequence_frequency)}\n"
        result += f"  Optimized sequences: {len(self.optimized_sequences)}\n"
        
        if self.sequence_frequency:
            result += "\n  Top 5 sequences:\n"
            for seq, count in self.get_top_sequences(5):
                status = "✓" if seq in self.optimized_sequences else " "
                result += f"    [{status}] {seq}: {count}x\n"
        
        return result


def sample_windows(basic_block: BasicBlock, window_size: int = 3) -> List[List[str]]:
    """
    Convenience function for one-time window sampling.
    
    Creates a temporary sampler (no state tracking).
    
    Args:
        basic_block: The basic block to sample from
        window_size: Size of each window
    
    Returns:
        List of instruction windows
    """
    sampler = WindowSampler()
    return sampler.sample_windows(basic_block, window_size)
