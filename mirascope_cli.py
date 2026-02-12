from mirascope import llm
import os
import json
from pathlib import Path
import yaml

## Tools
from src.tools.file_create import file_create
from src.tools.file_read import file_read
from src.tools.file_edit import file_edit
from src.tools.execute_bash import execute_bash
from src.tools.screenshot import screenshot
from src.multiline_input import multiline_input
from src.tools.plan import plan
from src.tools.summarize_conversation import summarize_conversation, generate_conversation_summary
from src.tools.browse_internet import browse_internet
from src.tools.estimate_tokens import estimate_tokens_from_messages, format_token_estimate
from src.tools.clarify import clarify

# Skill Management
from src.skills.manager import get_skill_manager, SkillManager

# Initialize skill manager on startup
skill_manager: SkillManager = get_skill_manager()
skill_manager.load_skills()

# Generate skill inventory for system prompt
skill_inventory = skill_manager.generate_prompt_context()
skill_writer_guide = skill_manager.generate_skill_writer_guide()

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from config.yaml"""
    config = {
        "llm": {
            "api_base": None,
            "provider": "openai",
            "model_name": "gpt-4",
            "max_completion_tokens": 8192,
            "context_size": 128000,
            "support_image": False,
            "support_audio_input": False,
            "support_audio_output": False,
            "thinking": {"level": None, "include_thoughts": False}
        },
        "debug": False
    }
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            loaded_config = yaml.safe_load(f)
            if loaded_config:
                config.update(loaded_config)
    
    return config

def setup_provider_from_config(config: dict):
    """Set up the LLM provider based on config"""
    llm_config = config.get("llm", {})
    api_base = llm_config.get("api_base")
    provider = llm_config.get("provider", "openai")
    api_key = os.environ.get("OPENAI_API_KEY", "vllm")
    
    if api_base:
        llm.register_provider(
            "openai:completions",
            scope=f"{provider}/",
            base_url=api_base,
            api_key=api_key,
        )

def create_model_from_config(config: dict) -> llm.Model:
    """Create an LLM model instance from config"""
    llm_config = config.get("llm", {})
    
    model_name = llm_config.get("model_name", "gpt-4")
    max_tokens = llm_config.get("max_completion_tokens", 8192)
    thinking_config = llm_config.get("thinking", {"level": None, "include_thoughts": False})
    
    thinking = None
    if thinking_config.get("level") and thinking_config.get("level") != "None":
        thinking = {
            "level": thinking_config.get("level"),
            "include_thoughts": thinking_config.get("include_thoughts", True)
        }
    
    return llm.Model(
        model_name,
        max_tokens=max_tokens,
        thinking=thinking
    )

# Load configuration
config = load_config()
setup_provider_from_config(config)
model = create_model_from_config(config)

def load_base_prompt(prompt_path: str = "prompts/system.md") -> str:
    """Load the system prompt from prompts/system.md."""
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def load_model_config_section(config: dict) -> str:
    """Generate a model configuration section for the system prompt."""
    llm_config = config.get("llm", {})
    
    model_name = llm_config.get("model_name", "Unknown")
    provider = llm_config.get("provider", "Unknown")
    max_completion_tokens = llm_config.get("max_completion_tokens", "Unknown")
    context_size = llm_config.get("context_size", "Unknown")
    support_image = llm_config.get("support_image", False)
    support_audio_input = llm_config.get("support_audio_input", False)
    support_audio_output = llm_config.get("support_audio_output", False)
    
    return f"""
## MODEL CONFIGURATION

Your LLM configuration:
- **Model**: {model_name}
- **Provider**: {provider}
- **Max completion tokens**: {max_completion_tokens}
- **Context window size**: {context_size} tokens
- **Supports images**: {support_image}
- **Supports audio input**: {support_audio_input}
- **Supports audio output**: {support_audio_output}

Use this information to understand your capabilities and limitations.
""".strip()


def load_claude_md() -> str:
    """Load CLAUDE.md if present at the project root."""
    claude_path = os.path.join(os.getcwd(), "CLAUDE.md")
    if os.path.exists(claude_path):
        with open(claude_path, "r", encoding="utf-8") as f:
            return f"\n\n## ADDITIONAL PROJECT GUIDANCE\n{f.read()}"
    return ""

def cli():
    """Main CLI loop for the assistant."""
    # Load base prompt and skill information
    base_prompt = load_base_prompt()
    claude_md = load_claude_md()

    # Build system prompt with all components
    system_prompt = base_prompt + claude_md + "\n\n" + load_model_config_section(config)

    # Add skill inventory if available
    if skill_inventory:
        system_prompt += "\n\n" + skill_inventory

    # Add skill writer guide for documentation
    if skill_writer_guide:
        system_prompt += "\n\n" + skill_writer_guide

    print("Welcome to the Custom CLI Assistant! Type your commands below.")
    print("  - Press Alt + Enter for new lines")
    print("  - Press Enter to submit")
    print("  - Press Ctrl+C to cancel input")
    print("  - Type '/quit', '/exit', or '/q' to exit")
    print("  - Type '/reset' to clear conversation history and restart")
    print("  - Type '/compact' to summarize conversation, clear history, and preserve context")
    print()

    messages = [
        llm.messages.system(system_prompt),
    ]

    while True:
        try:
            user_input = multiline_input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower().strip() in ['/quit', '/exit', '/q']:
            print("Goodbye!")
            break


        if user_input.lower().strip() == '/reset':
            print("\n🔄 Conversation history cleared. Restarting with initial configuration...\n")
            messages = [
                llm.messages.system(system_prompt),
            ]
            continue

        if user_input.lower().strip() == '/compact':
            print("\n🔄 Compacting conversation history...\n")
            
            # Generate summary of conversation
            summary = generate_conversation_summary(messages)
            
            print("📝 Conversation summary:")
            print(summary)
            print()
            
            # Reset messages with system prompt and summary
            messages = [
                llm.messages.system(system_prompt),
                llm.messages.user(f"Previous conversation compacted. Here's a summary of what we've discussed so far:\n\n{summary}\n\nYou can now continue the conversation from this point.")
            ]
            print("✅ Conversation compacted and history cleared.\n")
            continue
        messages.append(llm.messages.user(user_input))

        response = model.stream(
            messages,
            tools=[
                file_create,
                file_read,
                file_edit,
                execute_bash,
                plan,
                screenshot,
                browse_internet,
                clarify,
                summarize_conversation,
                # Skill tools will be added dynamically
            ],
        )

        while True:  # The Agent Loop
            # Process tool calls
            clarify_responses = []  # Collect clarify tool responses
            interrupted = False

            try:
                for stream in response.streams():
                    match stream.content_type:
                        case "text":
                            for chunk in stream:
                                print(chunk, flush=True, end="")
                            print("\n")
                        case "thought":
                            border = "~" * 80
                            print(f"\n{border}")
                            print(f"🧠 THOUGHT")
                            print(f"{border}")
                            for chunk in stream:
                                print(chunk, flush=True, end="")
                            print(f"\n{border}\n")
                        case "tool_call":
                            tool_call = stream.collect()

                            # Handle clarify tool specially - prompt user for input
                            if tool_call.name == "clarify":
                                # Parse args if it's a JSON string
                                args = tool_call.args
                                if isinstance(args, str):
                                    args = json.loads(args)
                                question = args.get("question", "Clarifying question?")
                                print(f"\n❓ CLARIFYING QUESTION:")
                                print(f"{question}")
                                print()
                                try:
                                    user_response = multiline_input("Your answer: ")
                                    clarify_responses.append(
                                        llm.ToolOutput(id=tool_call.id, name=tool_call.name, result=f"User response: {user_response}")
                                    )
                                except (EOFError, KeyboardInterrupt):
                                    print("\nClarification cancelled.")
                                    clarify_responses.append(
                                        llm.ToolOutput(id=tool_call.id, name=tool_call.name, result="Clarification cancelled by user.")
                                    )
                            else:
                                # Print other tool calls normally
                                border = "=" * 80
                                tool_header = f"🛠️  TOOL CALL: {tool_call.name}"
                                # Parse args if it's a JSON string
                                args = tool_call.args
                                if isinstance(args, str):
                                    args = json.loads(args)
                                tool_args = json.dumps(args, indent=2, ensure_ascii=False)
                                print(f"\n{border}")
                                print(f"{tool_header}")
                                print(f"Args:")
                                print(f"{tool_args}")
                                print(f"{border}\n")
            except KeyboardInterrupt:
                interrupted = True
                print("\n\n⚠️  Generation interrupted by user.\n")

            if interrupted:
                # Preserve partial context: response.messages contains
                # whatever was accumulated before the interruption
                try:
                    messages = response.messages
                except Exception:
                    # If messages aren't available from partial response,
                    # add a synthetic assistant message with what we had
                    messages.append(llm.messages.assistant("[Response interrupted by user]"))
                break

            # Execute clarify responses if any
            if clarify_responses:
                response = response.resume(clarify_responses)
                continue  # Continue the loop with the clarified response

            # Check if there are any tool calls to execute
            if response.tool_calls:
                response = response.resume(response.execute_tools())
            else:
                break

        if not interrupted:
            messages = response.messages

        # Display token estimate at the end of each turn
        if not interrupted:
            token_count = estimate_tokens_from_messages(messages)
            max_tokens = config["llm"]["context_size"]
            print()
            print(f"📊 Context window usage: {format_token_estimate(token_count, max_tokens)}")
            print()

if __name__ == "__main__":
    cli()
