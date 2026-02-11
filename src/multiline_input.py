import sys


def multiline_input(prompt: str = "> ") -> str:
    """
    Multiline input function using prompt_toolkit.
    
    Supports:
    - Enter: adds a newline (continue typing)
    - Alt+Enter (or Escape then Enter): submits the input
    - Ctrl+C: cancels input (returns empty string)
    
    Args:
        prompt: The prompt to display before each line
        
    Returns:
        The complete multiline input string, or empty string if cancelled
    """
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings

        bindings = KeyBindings()
        session = PromptSession(key_bindings=bindings, multiline=True)

        @bindings.add('escape', 'enter')
        def submit(event):
            """Submit on Alt+Enter (or Escape then Enter)."""
            buffer = event.current_buffer
            buffer.validate_and_handle()

        @bindings.add('c-c')
        def cancel(event):
            """Cancel input with Ctrl+C."""
            buffer = event.current_buffer
            buffer.text = ""
            buffer.validate_and_handle()

        while True:
            try:
                result = session.prompt(prompt)
                return result if result else ""
            except KeyboardInterrupt:
                print("\n(input cancelled)")
                return ""

    except ImportError:
        # Fallback to standard input with instructions
        print(f"{prompt} (prompt_toolkit not installed - using basic input)")
        print("  - Type your input, press Enter for new lines")
        print("  - Press Ctrl+D (or Ctrl+Z on Windows) to submit")

        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        except KeyboardInterrupt:
            print("\n")
            return ""

        return "\n".join(lines)