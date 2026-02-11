from mirascope import llm
import os
import json
from pathlib import Path

## Tools
from src.tools.file_create import file_create
from src.tools.file_read import file_read
from src.tools.file_edit import file_edit
from src.tools.execute_bash import execute_bash
from src.multiline_input import multiline_input
from src.tools.plan import plan
from src.tools.browse_internet import browse_internet

os.environ['OPENAI_API_KEY'] = "sk-010101"
os.environ['OPENAI_API_BASE'] = "http://localhost:5000/v1"

llm.register_provider(
    "openai:completions",
    scope="vllm/",
    base_url="http://localhost:5000/v1",
    api_key="vllm",
)

model = llm.Model(
    "vllm/vllm",
    max_tokens=8196,
    thinking={"level": "high", "include_thoughts": True}
)

def load_base_prompt(prompt_path: str = "prompts/cli.md") -> str:
    """Load the base system prompt from a markdown file."""
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def load_claude_md() -> str:
    """Load CLAUDE.md if present at the project root."""
    claude_path = os.path.join(os.getcwd(), "CLAUDE.md")
    if os.path.exists(claude_path):
        with open(claude_path, "r", encoding="utf-8") as f:
            return f"\n\n## ADDITIONAL PROJECT GUIDANCE\n{f.read()}"
    return ""

def cli():
    """Main CLI loop for the assistant."""
    system_prompt = load_base_prompt() + load_claude_md()
    
    print("Welcome to the Custom CLI Assistant! Type your commands below.")
    print("  - Press Alt + Enter for new lines")
    print("  - Press Enter to submit")
    print("  - Press Ctrl+C to cancel input")
    print("  - Type '/quit', '/exit', or '/q' to exit")
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
        
        messages.append(llm.messages.user(user_input))

        response = model.stream(
            messages,
            tools=[
                file_create,
                file_read,
                file_edit,
                execute_bash,
                plan,
                browse_internet,
            ],
        )

        while True:  # The Agent Loop
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
                        border = "=" * 80
                        tool_header = f"🛠️  TOOL CALL: {tool_call.name}"
                        tool_args = json.dumps(tool_call.args, indent=2, ensure_ascii=False)
                        print(f"\n{border}")
                        print(f"{tool_header}")
                        print(f"Args:")
                        print(f"{tool_args}")
                        print(f"{border}\n")

            if not response.tool_calls:
                break

            response = response.resume(response.execute_tools())
        
        messages = response.messages


if __name__ == "__main__":
    cli()