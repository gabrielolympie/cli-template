from mirascope import llm
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import utilities for model and prompt loading
from src.utils.load_model import get_model
from src.utils.load_prompts import (
    load_base_prompt,
    load_model_config_section,
    load_claude_md,
)
from src.utils.multiline_input import multiline_input

## Tools
from src.tools.file_create import file_create
from src.tools.file_read import file_read
from src.tools.file_edit import file_edit
from src.tools.execute_bash import execute_bash
from src.tools.screenshot import screenshot
from src.tools.plan import plan
from src.tools.summarize_conversation import (
    summarize_conversation,
    generate_conversation_summary,
)
from src.tools.browse_internet import browse_internet
from src.tools.estimate_tokens import (
    estimate_tokens_from_messages,
    format_token_estimate,
)
from src.tools.clarify import clarify
from src.tools.speak import speak, configure_speak
from src.tools.computer_use import computer_use

# Skill Management
from src.utils.skills.manager import get_skill_manager, SkillManager

# --------------------------------------------------------------------------- #
# Load configuration and model using utils (must load before skill manager)
model, config = get_model()

# Tool enable/disable mapping
ALL_TOOLS = {
    "file_create": file_create,
    "file_read": file_read,
    "file_edit": file_edit,
    "execute_bash": execute_bash,
    "screenshot": screenshot,
    "plan": plan,
    "browse_internet": browse_internet,
    "clarify": clarify,
    "summarize_conversation": summarize_conversation,
    "speak": speak,
    "computer_use": computer_use,
}


def get_enabled_tools(include_voice: bool = False) -> list:
    """Get list of enabled tools from config."""
    tools_config = config.get("tools", {})
    enabled = []

    for tool_name, tool_func in ALL_TOOLS.items():
        # speak tool only available during voice mode
        if tool_name == "speak" and not include_voice:
            continue
        # Default to enabled if not specified
        if tools_config.get(tool_name, True):
            enabled.append(tool_func)

    return enabled


def is_skill_enabled(skill_name: str) -> bool:
    """Check if a skill is enabled based on config.

    Args:
        skill_name: Name of the skill to check

    Returns:
        True if skill is enabled, False otherwise
    """
    skills_config = config.get("skills", {})
    # Empty config or skill not listed means enabled by default
    if not skills_config or skill_name not in skills_config:
        return True
    return skills_config.get(skill_name, True)


# Initialize skill manager on startup (after config is loaded)
# Pass the skill enabled checker to filter skills
skill_manager: SkillManager = get_skill_manager(skill_enabled_checker=is_skill_enabled)
skill_manager.load_skills()

# Generate skill inventory for system prompt
skill_inventory = skill_manager.generate_prompt_context()
skill_writer_guide = skill_manager.generate_skill_writer_guide()
# --------------------------------------------------------------------------- #

def cli() -> None:
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
    print("  - Type '/voice' to toggle voice output mode")
    print()

    # Voice mode state
    voice_active = False

    messages = [
        llm.messages.system(system_prompt),
    ]

    # Track conversation length and auto-compact when approaching context limit
    CONTEXT_WINDOW_SIZE = config["llm"]["context_size"]
    CONTEXT_LIMIT_PERCENTAGE = config.get("context_limit_percentage", 0.8)
    CONTEXT_LIMIT = int(CONTEXT_WINDOW_SIZE * CONTEXT_LIMIT_PERCENTAGE)
    last_known_token_count = 0  # Track the most recent accurate token count

    def should_auto_compact():
        """Check if conversation should be auto-compacted."""
        nonlocal last_known_token_count
        if last_known_token_count > 0:
            return last_known_token_count >= CONTEXT_LIMIT
        try:
            token_count = estimate_tokens_from_messages(messages)
            return token_count >= CONTEXT_LIMIT
        except Exception:
            return False

    def auto_compact_conversation(messages, system_prompt):
        """Auto-compact conversation and return new message history."""
        print(f"\n🔄 Auto-compacting conversation (approaching context limit)...")
        summary = generate_conversation_summary(messages)
        print("📝 Conversation summary:")
        print(summary)
        print()

        return [
            llm.messages.system(system_prompt),
            llm.messages.user(
                f"Previous conversation auto-compacted. Here's a summary of what we've discussed so far:\n\n{summary}\n\nYou can now continue the conversation from this point."
            ),
        ]

    while True:
        try:
            user_input = multiline_input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # ------------------------------------------------------------------- #
        # Command handling
        if user_input.lower().strip() in ["/quit", "/exit", "/q"]:
            print("Goodbye!")
            break

        if user_input.lower().strip() == "/reset":
            print("\n🔄 Conversation history cleared. Restarting with initial configuration...\n")
            messages = [llm.messages.system(system_prompt)]
            last_known_token_count = 0
            continue

        if user_input.lower().strip() == "/compact":
            print("\n🔄 Compacting conversation history...\n")
            summary = generate_conversation_summary(messages)
            print("📝 Conversation summary:")
            print(summary)
            print()
            messages = [
                llm.messages.system(system_prompt),
                llm.messages.user(
                    f"Previous conversation compacted. Here's a summary of what we've discussed so far:\n\n{summary}\n\nYou can now continue the conversation from this point."
                ),
            ]
            last_known_token_count = 0
            print("✅ Conversation compacted and history cleared.\n")
            continue

        if user_input.lower().strip() == "/voice":
            if not voice_active:
                try:
                    from src.voice.tts import create_tts
                    from src.voice.audio_io import AudioPlayer
                    voice_cfg = config.get("voice", {})
                    tts = create_tts(voice_cfg.get("tts", {}))
                    player = AudioPlayer()
                    configure_speak(tts, player)
                    voice_active = True
                    print("[Voice mode ON] Agent can now speak aloud. /voice to disable.\n")
                except ImportError as e:
                    print(f"[Voice] Missing dependencies: {e}")
                    print("[Voice] Install with: pip install sounddevice numpy pocket-tts\n")
                except Exception as e:
                    print(f"[Voice] Failed to start: {e}\n")
            else:
                configure_speak(None, None)
                voice_active = False
                print("[Voice mode OFF]\n")
            continue
        # ------------------------------------------------------------------- #

        # Auto-compact if conversation is too long
        if should_auto_compact():
            messages = auto_compact_conversation(messages, system_prompt)
            last_known_token_count = 0

        messages.append(llm.messages.user(user_input))

        # Inject voice context hint when voice mode is active
        if voice_active:
            messages.append(llm.messages.user(
                "[System: Voice mode is active. Use the 'speak' tool to respond verbally "
                "when appropriate. Keep spoken responses concise (1-3 sentences). "
                "Still use text for code, file contents, etc. Speech plays in background.]"
            ))

        response = model.stream(
            messages,
            tools=get_enabled_tools(include_voice=voice_active),
        )

        while True:  # The Agent Loop
            clarify_responses: list[llm.ToolOutput] = []
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
                            print("🧠 THOUGHT")
                            print(f"{border}")
                            for chunk in stream:
                                print(chunk, flush=True, end="")
                            print(f"\n{border}\n")
                        case "tool_call":
                            tool_call = stream.collect()

                            # ------------------------------------------------------- #
                            # Clarify tool – ask the user for extra info
                            if tool_call.name == "clarify":
                                args = tool_call.args
                                if isinstance(args, str):
                                    args = json.loads(args)
                                question = args.get("question", "Clarifying question?")
                                print("\n❓ CLARIFYING QUESTION:")
                                print(f"{question}\n")
                                try:
                                    user_response = multiline_input("Your answer: ")
                                    clarify_responses.append(
                                        llm.ToolOutput(
                                            id=tool_call.id,
                                            name=tool_call.name,
                                            result=f"User response: {user_response}",
                                        )
                                    )
                                except (EOFError, KeyboardInterrupt):
                                    print("\nClarification cancelled.")
                                    clarify_responses.append(
                                        llm.ToolOutput(
                                            id=tool_call.id,
                                            name=tool_call.name,
                                            result="Clarification cancelled by user.",
                                        )
                                    )
                            # ------------------------------------------------------- #
                            else:
                                # Print other tool calls for transparency
                                border = "=" * 80
                                tool_header = f"🛠️  TOOL CALL: {tool_call.name}"
                                args = tool_call.args
                                if isinstance(args, str):
                                    args = json.loads(args)
                                tool_args = json.dumps(args, indent=2, ensure_ascii=False)
                                print(f"\n{border}")
                                print(tool_header)
                                print("Args:")
                                print(tool_args)
                                print(f"{border}\n")
            except KeyboardInterrupt:
                interrupted = True
                print("\n\n⚠️  Generation interrupted by user.\n")

            # --------------------------------------------------------------- #
            # If we collected clarify responses, resume with them
            if clarify_responses:
                response = response.resume(clarify_responses)
                continue  # loop again to process the clarified response

            # --------------------------------------------------------------- #
            # Execute any pending tool calls
            if response.tool_calls:
                tool_outputs = response.execute_tools()

                # ----------------------------------------------------------- #
                # ----- IMAGE SUPPORT FOR SCREENSHOT TOOL ------------------- #
                llm_config = config.get("llm", {})
                supports_images = llm_config.get("support_image", False)

                loaded_images = []
                if supports_images:
                    for result in tool_outputs:
                        if result.type == "tool_output":
                            is_screenshot = result.name == "screenshot"
                            is_computer_use_screenshot = (
                                result.name == "computer_use"
                                and isinstance(result.result, str)
                                and result.result.endswith(".png")
                            )
                            if is_screenshot or is_computer_use_screenshot:
                                print("Adding result image to tool outputs")
                                loaded_images.append(llm.Text(text = f'--- Screenshot saved at: {result.result}'))
                                loaded_images.append(llm.Image.from_file(result.result))

                # ----------------------------------------------------------- #
                # Auto-compact if conversation is too long before resuming
                # Update token count from response usage if available
                try:
                    last_known_token_count = response.usage.total_tokens
                except Exception:
                    pass
                if should_auto_compact():
                    messages = auto_compact_conversation(messages, system_prompt)
                    last_known_token_count = 0

                # Resume the LLM with the (possibly image‑enhanced) tool outputs
                response = response.resume(tool_outputs + loaded_images)
            else:
                # No tool calls left – exit the inner loop
                break

        # --------------------------------------------------------------- #
        # Update the conversation history unless we were interrupted
        if not interrupted:
            messages = response.messages

        # --------------------------------------------------------------- #
        # Show token usage after each turn and update tracked count
        if not interrupted:
            try:
                last_known_token_count = response.usage.total_tokens
                token_count = last_known_token_count
            except Exception:
                token_count = estimate_tokens_from_messages(messages)
                last_known_token_count = token_count

            max_tokens = config["llm"]["context_size"]
            print()
            print(f"📊 Context window usage: {format_token_estimate(token_count, max_tokens)}")
            print()

if __name__ == "__main__":
    cli()