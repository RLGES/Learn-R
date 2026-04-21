"""
LLM-based assembly rewrite rule generator.

This module generates candidate assembly rewrite rules using LLM APIs.
Supports multiple providers: OpenAI (GPT-4), Anthropic (Claude), Google (Gemini).
"""
import time
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for config import
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import config

# Import LLM provider libraries (optional - graceful degradation)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Hugging Face inference - uses requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# LM Studio uses OpenAI-compatible API
LMSTUDIO_AVAILABLE = OPENAI_AVAILABLE  # Uses OpenAI client
HUGGINGFACE_AVAILABLE = REQUESTS_AVAILABLE


class LLMError(Exception):
    """Exception raised for LLM API errors."""
    pass


class RateLimitError(LLMError):
    """Exception raised when rate limit is hit."""
    pass


def _call_openai(prompt: str, model: str = None, max_tokens: int = None, 
                 temperature: float = None) -> str:
    """
    Call OpenAI API (GPT-4, GPT-4o).
    
    Args:
        prompt: The prompt to send
        model: Model name (defaults to config)
        max_tokens: Max response tokens (defaults to config)
        temperature: Generation temperature (defaults to config)
    
    Returns:
        Generated text response
    
    Raises:
        LLMError: If API call fails
    """
    if not OPENAI_AVAILABLE:
        raise LLMError("OpenAI library not installed. Run: pip install openai")
    
    api_key = config.openai_api_key
    if not api_key or api_key.startswith("your_"):
        raise LLMError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
    
    model = model or config.openai_model
    max_tokens = max_tokens or config.llm_max_tokens
    temperature = temperature if temperature is not None else config.llm_temperature
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert compiler optimizer specializing in assembly code transformations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=config.llm_timeout
        )
        
        return response.choices[0].message.content
        
    except openai.RateLimitError as e:
        raise RateLimitError(f"OpenAI rate limit exceeded: {e}")
    except openai.APIError as e:
        raise LLMError(f"OpenAI API error: {e}")
    except Exception as e:
        raise LLMError(f"OpenAI call failed: {e}")


def _call_anthropic(prompt: str, model: str = None, max_tokens: int = None,
                    temperature: float = None) -> str:
    """
    Call Anthropic API (Claude).
    
    Args:
        prompt: The prompt to send
        model: Model name (defaults to config)
        max_tokens: Max response tokens (defaults to config)
        temperature: Generation temperature (defaults to config)
    
    Returns:
        Generated text response
    
    Raises:
        LLMError: If API call fails
    """
    if not ANTHROPIC_AVAILABLE:
        raise LLMError("Anthropic library not installed. Run: pip install anthropic")
    
    api_key = config.anthropic_api_key
    if not api_key or api_key.startswith("your_"):
        raise LLMError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
    
    model = model or config.anthropic_model
    max_tokens = max_tokens or config.llm_max_tokens
    temperature = temperature if temperature is not None else config.llm_temperature
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system="You are an expert compiler optimizer specializing in assembly code transformations.",
            temperature=temperature
        )
        
        return response.content[0].text
        
    except anthropic.RateLimitError as e:
        raise RateLimitError(f"Anthropic rate limit exceeded: {e}")
    except anthropic.APIError as e:
        raise LLMError(f"Anthropic API error: {e}")
    except Exception as e:
        raise LLMError(f"Anthropic call failed: {e}")


def _call_google(prompt: str, model: str = None, max_tokens: int = None,
                 temperature: float = None) -> str:
    """
    Call Google Generative AI API (Gemini).
    
    Args:
        prompt: The prompt to send
        model: Model name (defaults to config)
        max_tokens: Max response tokens (defaults to config)
        temperature: Generation temperature (defaults to config)
    
    Returns:
        Generated text response
    
    Raises:
        LLMError: If API call fails
    """
    if not GOOGLE_AVAILABLE:
        raise LLMError("Google Generative AI library not installed. Run: pip install google-generativeai")
    
    api_key = config.google_api_key
    if not api_key or api_key.startswith("your_"):
        raise LLMError("Google API key not configured. Set GOOGLE_API_KEY in .env")
    
    model_name = model or config.google_model
    max_tokens = max_tokens or config.llm_max_tokens
    temperature = temperature if temperature is not None else config.llm_temperature
    
    try:
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction="You are an expert compiler optimizer specializing in assembly code transformations."
        )
        
        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        return response.text
        
    except Exception as e:
        error_str = str(e).lower()
        if "rate" in error_str or "quota" in error_str:
            raise RateLimitError(f"Google rate limit exceeded: {e}")
        raise LLMError(f"Google API call failed: {e}")


def _call_lmstudio(prompt: str, model: str = None, max_tokens: int = None,
                   temperature: float = None) -> str:
    """
    Call LM Studio local server (OpenAI-compatible API).
    
    LM Studio runs locally and provides an OpenAI-compatible API.
    Make sure LM Studio is running with a model loaded.
    
    Args:
        prompt: The prompt to send
        model: Model name (ignored - uses loaded model)
        max_tokens: Max response tokens
        temperature: Generation temperature
    
    Returns:
        Generated text response
    
    Raises:
        LLMError: If API call fails
    """
    if not LMSTUDIO_AVAILABLE:
        raise LLMError("OpenAI library not installed (required for LM Studio). Run: pip install openai")
    
    base_url = config.lmstudio_base_url
    max_tokens = max_tokens or config.llm_max_tokens
    temperature = temperature if temperature is not None else config.llm_temperature
    
    try:
        # LM Studio uses OpenAI-compatible API, no API key needed
        client = openai.OpenAI(base_url=base_url, api_key="lm-studio")
        
        response = client.chat.completions.create(
            model="local-model",  # LM Studio ignores this, uses loaded model
            messages=[
                {"role": "system", "content": "You are an expert compiler optimizer specializing in assembly code transformations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=config.llm_timeout
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        error_str = str(e).lower()
        if "connection" in error_str or "refused" in error_str:
            raise LLMError(f"Cannot connect to LM Studio. Make sure it's running at {base_url}")
        raise LLMError(f"LM Studio call failed: {e}")


def _call_huggingface(prompt: str, model: str = None, max_tokens: int = None,
                      temperature: float = None) -> str:
    """
    Call Hugging Face Inference API.
    
    Uses the Hugging Face serverless inference API.
    Requires HF_TOKEN or HUGGINGFACE_API_KEY environment variable.
    
    Args:
        prompt: The prompt to send
        model: Model ID (e.g., "mistralai/Mistral-7B-Instruct-v0.3")
        max_tokens: Max response tokens
        temperature: Generation temperature
    
    Returns:
        Generated text response
    
    Raises:
        LLMError: If API call fails
    """
    if not HUGGINGFACE_AVAILABLE:
        raise LLMError("requests library not installed. Run: pip install requests")
    
    api_key = config.huggingface_api_key
    if not api_key or api_key.startswith("your_"):
        raise LLMError("Hugging Face API key not configured. Set HF_TOKEN or HUGGINGFACE_API_KEY in .env")
    
    model_id = model or config.huggingface_model
    max_tokens = max_tokens or config.llm_max_tokens
    temperature = temperature if temperature is not None else config.llm_temperature
    
    # Hugging Face Inference API endpoint
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Format prompt for instruction-tuned models
    full_prompt = f"""<s>[INST] You are an expert compiler optimizer specializing in assembly code transformations.

{prompt} [/INST]"""
    
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "return_full_text": False
        }
    }
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=config.llm_timeout
        )
        
        if response.status_code == 429:
            raise RateLimitError("Hugging Face rate limit exceeded")
        
        if response.status_code == 503:
            # Model is loading
            data = response.json()
            estimated_time = data.get("estimated_time", 20)
            raise LLMError(f"Model is loading. Try again in ~{estimated_time:.0f} seconds.")
        
        response.raise_for_status()
        
        result = response.json()
        
        # Handle different response formats
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict):
                return result[0].get("generated_text", "")
            return str(result[0])
        elif isinstance(result, dict):
            return result.get("generated_text", str(result))
        else:
            return str(result)
        
    except requests.exceptions.Timeout:
        raise LLMError("Hugging Face API request timed out")
    except requests.exceptions.RequestException as e:
        raise LLMError(f"Hugging Face API request failed: {e}")


def _get_stub_response() -> str:
    """Return stub response for testing when no LLM is configured."""
    return """LHS:
MOV r1, r2
MOV r3, r1
RHS:
MOV r3, r2
Condition: r1 is not used after this sequence

LHS:
ADD r1, 1
ADD r1, 1
RHS:
ADD r1, 2
Condition: None

LHS:
ADD r1, r2
SUB r1, r2
RHS:
(empty - cancel out)
Condition: No side effects
"""


def call_llm_api(prompt: str, provider: str = None, max_retries: int = 3,
                 retry_delay: float = 1.0, use_stub_on_error: bool = True) -> str:
    """
    Call an LLM API to generate rewrite rules.
    
    Supports multiple providers with automatic retry on rate limits.
    Falls back to stub response if no provider is configured.
    
    Args:
        prompt: The prompt to send to the LLM
        provider: LLM provider ("openai", "anthropic", "google"). Defaults to config.
        max_retries: Maximum retry attempts on rate limit errors
        retry_delay: Initial delay between retries (exponential backoff)
        use_stub_on_error: If True, return stub response on error instead of raising
    
    Returns:
        Raw text output from the LLM
    
    Raises:
        LLMError: If API call fails and use_stub_on_error is False
    """
    provider = (provider or config.llm_provider).lower()
    
    # Check if provider is configured
    if not config.is_configured(provider):
        available = config.get_available_providers()
        if available:
            # Try first available provider
            provider = available[0]
            if config.llm_debug:
                print(f"⚠ Switching to configured provider: {provider}")
        else:
            if config.llm_debug:
                print("⚠ No LLM provider configured. Using stub response.")
            return _get_stub_response()
    
    # Map provider to call function
    provider_funcs = {
        "openai": _call_openai,
        "anthropic": _call_anthropic,
        "google": _call_google,
        "lmstudio": _call_lmstudio,
        "huggingface": _call_huggingface,
    }
    
    call_func = provider_funcs.get(provider)
    if not call_func:
        raise LLMError(f"Unknown provider: {provider}. Supported: openai, anthropic, google, lmstudio, huggingface")
    
    # Call with retry logic
    last_error = None
    for attempt in range(max_retries):
        try:
            if config.llm_debug:
                print(f"📤 Calling {provider} (attempt {attempt + 1}/{max_retries})...")
            
            response = call_func(prompt)
            
            if config.llm_debug:
                print(f"✓ Received response ({len(response)} chars)")
            
            return response
            
        except RateLimitError as e:
            last_error = e
            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
            if config.llm_debug:
                print(f"⏳ Rate limited. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            
        except LLMError as e:
            last_error = e
            break  # Don't retry on non-rate-limit errors
    
    # All retries failed
    if use_stub_on_error:
        print(f"⚠ LLM call failed: {last_error}. Using stub response.")
        return _get_stub_response()
    else:
        raise last_error or LLMError("LLM call failed after retries")


def generate_candidate_rules(instruction_window: list[str], provider: str = None) -> str:
    """
    Generate candidate rewrite rules for an instruction sequence.
    
    Constructs a prompt asking an LLM to suggest semantically equivalent
    rewrites that are safe algebraic or structural transformations.
    
    Args:
        instruction_window: List of assembly instructions as strings
        provider: Optional LLM provider override
    
    Returns:
        Raw LLM text output containing candidate rules
    """
    # Format the instruction window
    instruction_text = '\n'.join(f"  {instr}" for instr in instruction_window)
    
    # Construct the prompt with branchless optimization context
    prompt = f"""You are a Compiler Optimization expert specializing in x86-64 assembly.
Your goal is to generate "Rewrite Rules" that transform inefficient code into high-performance machine code.

Given the following assembly instruction sequence:

{instruction_text}

CRITICAL INSTRUCTIONS:

1. PRIORITIZE BRANCHLESS LOGIC: The highest value optimizations remove 'jle', 'jge', 'jmp' and replace them with:
   - 'cmov' (Conditional Move): cmovg, cmovl, cmove, cmovne
   - 'set' (Set Byte): setne, sete, setg, setl
   - 'neg' (Negate)
   - 'sbb' (Subtract with Borrow)
   - 'test' (Efficient comparison against 0)

2. DO NOT BREAK SEMANTICS:
   - You CANNOT remove a 'cmp' instruction if a subsequent jump or cmov depends on the flags it sets.
   - 'test reg, reg' is equivalent to comparing reg against 0 and sets ZF/SF flags.
   - Conditional jumps (jle, jge, je, jne) REQUIRE preceding cmp or test to set flags.

3. ALGEBRAIC IDENTITIES (always safe):
   - xor reg, reg → Sets reg to 0 (shorter than mov reg, 0)
   - add reg, 0 → No-op, can be removed
   - sub reg, reg → Sets reg to 0
   - mul reg, 1 → No-op
   - and reg, reg → No-op
   - or reg, reg → No-op

4. PATTERN MATCHING SYNTAX:
   - Use 'src', 'dst', 'r1', 'r2' as placeholders for registers
   - Use 'imm' for immediate values
   - Use 'Label_A', 'Label_B' for jump targets

EXAMPLE OF A GOOD RULE (Branchless Signum):
Name: "branch_to_cmov"
LHS:
  cmp src, 0
  jle Label_A
  mov dst, 1
  jmp Label_B
  Label_A:
  mov dst, -1
  Label_B:
RHS:
  xor eax, eax    ; Clear temp
  test src, src   ; Check sign/zero
  mov edx, 1      ; Load positive case
  setne al        ; Set if not zero
  neg eax         ; -1 if set
  cmovg eax, edx  ; Move 1 if greater than 0
Condition: dst can be clobbered; eax, edx available as scratch

EXAMPLE OF A BAD RULE (NEVER DO THIS):
Name: "remove_cmp"
LHS:
  cmp src, 0
  jle Label_A
RHS:
  jle Label_A
WHY IT'S WRONG: jle depends on flags set by cmp! Without cmp, jle uses garbage flags.

Output format (strictly follow this):
Rule: [name]
LHS:
instruction1
instruction2
RHS:
instruction1
instruction2
Condition: [required conditions, or "None"]

Generate 3 candidate rewrite rules for the input assembly."""

    # Call the LLM API
    response = call_llm_api(prompt, provider=provider)
    
    return response


# Convenience function to check LLM availability
def check_llm_availability() -> dict:
    """
    Check which LLM providers are available and configured.
    
    Returns:
        Dictionary with provider availability status
    """
    return {
        "openai": {
            "library": OPENAI_AVAILABLE,
            "configured": config.is_configured("openai"),
            "model": config.openai_model if config.is_configured("openai") else None
        },
        "anthropic": {
            "library": ANTHROPIC_AVAILABLE,
            "configured": config.is_configured("anthropic"),
            "model": config.anthropic_model if config.is_configured("anthropic") else None
        },
        "google": {
            "library": GOOGLE_AVAILABLE,
            "configured": config.is_configured("google"),
            "model": config.google_model if config.is_configured("google") else None
        },
        "lmstudio": {
            "library": LMSTUDIO_AVAILABLE,
            "configured": config.is_configured("lmstudio"),
            "model": config.lmstudio_model if config.is_configured("lmstudio") else None,
            "base_url": config.lmstudio_base_url
        },
        "huggingface": {
            "library": HUGGINGFACE_AVAILABLE,
            "configured": config.is_configured("huggingface"),
            "model": config.huggingface_model if config.is_configured("huggingface") else None
        },
        "default_provider": config.llm_provider,
        "available_providers": config.get_available_providers()
    }


if __name__ == "__main__":
    # Test LLM availability
    print("=== LLM Availability Check ===")
    status = check_llm_availability()
    
    for provider in ["openai", "anthropic", "google", "lmstudio", "huggingface"]:
        info = status[provider]
        lib_status = "✓" if info["library"] else "✗"
        config_status = "✓" if info["configured"] else "✗"
        print(f"{provider}: library={lib_status} configured={config_status}")
    
    print(f"\nDefault provider: {status['default_provider']}")
    print(f"Available providers: {status['available_providers'] or 'None'}")
    
    # Test generate rules
    print("\n=== Testing Rule Generation ===")
    test_window = ["ADD r1, 0", "MOV r2, r1", "SUB r2, 0"]
    print(f"Input: {test_window}")
    
    try:
        result = generate_candidate_rules(test_window)
        print(f"\nGenerated rules:\n{result}")
    except LLMError as e:
        print(f"Error: {e}")
