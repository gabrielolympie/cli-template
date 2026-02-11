"""Token estimation utility using tiktoken."""
import tiktoken


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
        model: The model name to use for encoding (default: gpt-4)
        
    Returns:
        Number of tokens
    """
    if not text:
        return 0
        
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        # Fallback to cl100k_base encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


def estimate_tokens_from_messages(messages: list, model: str = "gpt-4") -> int:
    """Estimate total tokens from a list of messages.
    
    Args:
        messages: List of message objects
        model: The model name to use for encoding (default: gpt-4)
        
    Returns:
        Total number of tokens
    """
    total_tokens = 0
    for msg in messages:
        # Get text content from message
        text = ""
        if hasattr(msg, 'content') and msg.content:
            text = str(msg.content)
        
        total_tokens += estimate_tokens(text, model)
        
    # Add overhead for message formatting (approximate)
    # Typically ~5 tokens per message for metadata/formatting
    total_tokens += len(messages) * 5
    
    return total_tokens


def format_token_estimate(count: int, max_tokens: int = 8196) -> str:
    """Format token count with visual indicator of usage.
    
    Args:
        count: Current token count
        max_tokens: Maximum context window (default: 8196)
        
    Returns:
        Formatted string with token count and visual bar
    """
    percentage = min(100, (count / max_tokens) * 100)
    
    # Create visual bar
    bar_length = 30
    filled_length = int(bar_length * count / max_tokens)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    # Color coding based on usage
    if percentage < 50:
        color = "\033[92m"  # Green
    elif percentage < 80:
        color = "\033[93m"  # Yellow
    else:
        color = "\033[91m"  # Red
    
    reset = "\033[0m"
    
    return f"{color}{count:,}{reset} / {max_tokens:,} tokens [{bar}] ({percentage:.1f}%)"
