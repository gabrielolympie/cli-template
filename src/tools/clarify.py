from mirascope import llm


@llm.tool
def clarify(question: str) -> str:
    """Ask a clarifying question to the user.
    
    This tool allows you to request additional information when you need to make
    informed decisions, especially when:
    - The task has multiple possible interpretations
    - Important implementation decisions need to be made
    - Requirements are unclear or incomplete
    - The approach could vary significantly based on preferences or constraints
    - You need to understand the scope or priority of a task
    
    Args:
        question: The clarifying question to ask the user
    
    Returns:
        The user's response to the clarifying question
    """
    # This tool is special - it pauses execution to get user input
    # The response will be provided via the CLI interface
    return f"CLARIFY: {question}"
