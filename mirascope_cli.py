from mirascope import llm
import os
import json
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

## Tools
from src.tools.file_create import file_create
from src.tools.file_read import file_read
from src.tools.file_edit import file_edit
from src.tools.execute_bash import execute_bash
from src.tools.screenshot import screenshot
from src.utils.multiline_input import multiline_input
from src.tools.plan import plan
from src.tools.summarize_conversation import summarize_conversation, generate_conversation_summary
from src.tools.browse_internet import browse_internet
from src.tools.estimate_tokens import estimate_tokens_from_messages, format_token_estimate
from src.tools.clarify import clarify

# Skill Management
from src.utils.skills.manager import get_skill_manager, SkillManager

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
    """Set up the LLM provider based on config.

    Supports:
    - Native providers: anthropic, google, openai, ollama, mlx (auto-registered by Mirascope)
    - OpenAI-compatible providers: vllm, zai, together, xai, etc. (requires registration)
    """
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "openai")
    api_base = llm_config.get("api_base")
    api_key_env = llm_config.get("api_key_env")  # Optional: provider-specific API key env var

    # Native providers - Mirascope handles these automatically
    # Just ensure the correct env var is set
    native_providers = ["anthropic", "google", "openai", "ollama", "mlx"]
    if provider in native_providers and not api_base:
        # No registration needed - Mirascope auto-registers native providers
        return

    # OpenAI-compatible providers (vllm, zai, together, xai, custom endpoints)
    # Build API key lookup: try provider-specific first, then OPENAI_API_KEY
    if api_key_env:
        api_key = os.environ.get(api_key_env)
    else:
        # Auto-determine provider-specific env var name
        provider_env_map = {
            "vllm": "VLLM_API_KEY",
            "zai": "ZAI_API_KEY",
            "together": "TOGETHER_API_KEY",
            "xai": "XAI_API_KEY",
        }
        env_var = provider_env_map.get(provider, "OPENAI_API_KEY")
        api_key = os.environ.get(env_var)

        # Fallback for local servers that don't need real keys
        if not api_key and provider in ["vllm", "ollama"]:
            api_key = "unused"  # vLLM/Ollama often don't validate API keys

    if api_base and api_key:
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

def load_prompt(prompt_path: str) -> str:
    """Load a single prompt file. Returns empty string if file doesn't exist."""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def load_base_prompt() -> str:
    """Load and integrate PERSONA.md, AGENT.md, and SYSTEM.md into the system prompt."""
    prompts_dir = "prompts"

    # Load all three prompt components
    persona = load_prompt(os.path.join(prompts_dir, "PERSONA.md"))
    agent = load_prompt(os.path.join(prompts_dir, "AGENT.md"))
    system = load_prompt(os.path.join(prompts_dir, "SYSTEM.md"))

    # Integrate all prompts into a single system prompt
    parts = []
    if persona:
        parts.append(f"## PERSONA\n{persona}")
    if agent:
        parts.append(f"## AGENT MEMORY\n{agent}")
    if system:
        parts.append(system)

    return "\n\n".join(parts)

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
    # Load base prompt (includes PERSONA, AGENT, and SYSTEM)
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
                tool_outputs = response.execute_tools()

                # Check for screenshot tools with image data and LLM supports images
                llm_config = config.get("llm", {})
                supports_images = llm_config.get("support_image", False)

                if supports_images:
                    # Look for screenshot results with IMAGE_BASE64 data
                    screenshot_messages = []
                    for output in tool_outputs:
                        if output.name == "screenshot" and "IMAGE_BASE64:" in output.result:
                            parts = output.result.split("|")
                            print(parts)

                response = response.resume(tool_outputs)
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
