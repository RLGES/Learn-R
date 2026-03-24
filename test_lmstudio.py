import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import config
from learned_rules.llm_rule_generator import generate_candidate_rules, LLMError
from learned_rules.rule_parser import parse_llm_output

def estimate_performance(instructions: list[str]) -> dict:
    """
    Very simple heuristic to estimate performance cost of x86-64 assembly.
    Space = Number of instructions (excluding labels)
    Time = Estimated CPU cycles
    """
    space_cost = 0
    time_cost = 0
    
    for instr in instructions:
        instr_clean = instr.strip().lower()
        if not instr_clean or instr_clean.startswith('.') or instr_clean.endswith(':'):
            continue # Labels cost nothing
            
        space_cost += 1 # Every instruction consumes memory
        
        # Time heuristics (cycles estimation)
        if any(b in instr_clean for b in ['jmp', 'je', 'jne', 'jle', 'jge', 'jl', 'jg']):
            time_cost += 3 # Branches are expensive (potential pipeline stall/flush)
        elif any(b in instr_clean for b in ['mul', 'div', 'imul', 'idiv']):
            time_cost += 4 # Complex arithmetic
        elif any(b in instr_clean for b in ['cmov']):
            time_cost += 2 # Conditional move (data dependency but branchless)
        else:
            time_cost += 1 # Basic ALU ops, MOV, SETcc
            
        # Memory access penalty (assumes basic memory addressing latency)
        if '[' in instr_clean and ']' in instr_clean:
            time_cost += 2
            
    return {"space": space_cost, "time": time_cost}

def main():
    # Ensure LM Studio endpoint is visible
    print(f"Using Provider: lmstudio")
    print(f"Endpoint: {config.lmstudio_base_url}")
    
    # our example translated to basic branchy Assembly
    # if (src == 0) return 0 else return 1
    branchy_asm = [
        "cmp src, 0",      # Check if src is 0
        "jne .not_zero",   # If not zero, jump
        "mov dst, 0",      # Return 0
        "jmp .done",       # Skip to end
        ".not_zero:",      
        "mov dst, 1",      # Return 1
        ".done:"
    ]
    
    print("\n--- Sending Input Assembly ---")
    for instr in branchy_asm:
        print(f"  {instr}")
        
    print(f"  > Original Metrics: {estimate_performance(branchy_asm)}")
        
    print("\n--- Asking LM Studio for Rewrites... ---")
    
    try:
        # Sends your assembly to the LLM (LM Studio must be running!)
        response = generate_candidate_rules(branchy_asm, provider="lmstudio")
        
        print("\n--- Raw LM Studio Response ---")
        print(response)
        
        print("\n--- PERFORMANCE COMPARISON PARSING ---")
        rules = parse_llm_output(response)
        
        if not rules:
            print("[!] Could not parse strict rules from LLM response. Did it output 'LHS:' and 'RHS:'?")
            return
            
        for i, rule in enumerate(rules, 1):
            original_perf = estimate_performance(rule.lhs_seq)
            optimized_perf = estimate_performance(rule.rhs_seq)
            
            print(f"\nRule #{i}:")
            print(f"[Original Code (LHS)]")
            for inst in rule.lhs_seq: 
                print(f"  {inst}")
            print(f"  -> Space Cost: {original_perf['space']} instructions")
            print(f"  -> Time Cost:  {original_perf['time']} estimated cycles")
            
            print(f"\n[Optimized Code (RHS)]")
            for inst in rule.rhs_seq: 
                print(f"  {inst}")
            print(f"  -> Space Cost: {optimized_perf['space']} instructions")
            print(f"  -> Time Cost:  {optimized_perf['time']} estimated cycles")
            
            # Differences
            time_saved = original_perf['time'] - optimized_perf['time']
            space_saved = original_perf['space'] - optimized_perf['space']
            
            print(f"\n[DIFFERENCE]")
            print(f"  Time  : {'-' if time_saved < 0 else '+'}{abs(time_saved)} cycles")
            print(f"  Space : {'-' if space_saved < 0 else '+'}{abs(space_saved)} instructions")
            print("-" * 40)
            
    except LLMError as e:
        print("\n[!] Error connecting to LM Studio.")
        print(f"Details: {e}")

if __name__ == "__main__":
    main()
