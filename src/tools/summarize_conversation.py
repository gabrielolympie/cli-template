from mirascope import llm


@llm.tool
def summarize_conversation(messages: list[str]) -> str:
    """Summarize a conversation history for context preservation.
    
    This tool takes the conversation history and generates a concise summary
    that preserves important context, decisions, and progress. This allows
    the conversation to be compacted and resumed later without losing key
    information.
    
    Args:
        messages: List of message strings from the conversation history
    
    Returns:
        A concise summary of the conversation that preserves important context
        and decisions, suitable for restoring the conversation state later.
    """
    # The summarization will be done by the LLM when this tool is called
    return "Conversation summary placeholder"


def generate_conversation_summary(messages: list) -> str:
    """Generate a summary of the conversation history using the LLM.
    
    Args:
        messages: List of message objects from the conversation
    
    Returns:
        A concise summary of the conversation
    """
    # Build the summary prompt
    summary_prompt = """You are an expert conversation summarizer. Your task is to summarize the following conversation history into a concise, informative summary that preserves all important context, decisions, and progress.

IMPORTANT: The summary should be written in a way that allows the assistant to "come back" to the initial state by preserving:
1. Key facts and decisions made
2. User preferences and requirements
3. Progress on tasks or goals
4. Important context about the project or topic
5. Any pending actions or follow-ups

Format your response as a well-structured summary that can be provided as context in a new conversation.

Conversation history:
"""

    # Build message history string
    for msg in messages:
        if hasattr(msg, 'role'):
            summary_prompt += f"{msg.role.upper()}: "
        if hasattr(msg, 'content'):
            if isinstance(msg.content, list):
                for item in msg.content:
                    if hasattr(item, 'text'):
                        summary_prompt += item.text + "\n"
            else:
                summary_prompt += str(msg.content) + "\n"
        else:
            summary_prompt += str(msg) + "\n"
    
    summary_prompt += "\n\nPlease provide a comprehensive summary of this conversation:"

    # Use the main model to generate the summary
    model = llm.Model(
        "vllm/vllm",
        max_tokens=8196,
        thinking={"level": "high", "include_thoughts": True}
    )

    try:
        response = model.stream(
            [llm.messages.user(summary_prompt)],
        )
        
        # Collect the full response
        summary_text = ""
        for stream in response.streams():
            match stream.content_type:
                case "text":
                    for chunk in stream:
                        summary_text += chunk
                case "thought":
                    # Thoughts are internal, don't include in summary
                    pass
                case "tool_call":
                    # Shouldn't happen for summarization
                    pass

        return summary_text.strip()
        
    except Exception as e:
        # Fallback: create a basic summary from message count
        return f"Conversation compacted. Original conversation had {len(messages)} messages. Summary could not be generated due to error: {str(e)}"
