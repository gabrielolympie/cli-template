from mirascope import llm
import sys
import os
import json
import pickle
import base64
from pathlib import Path

# Get the current working directory (hard constraint: operations limited to this folder)
# Use CWD as the root to avoid accidentally accessing files elsewhere
PROJECT_ROOT = os.getcwd()

# State file location
STATE_FILE = Path(PROJECT_ROOT) / ".cli_state.json"


def _encode_state(state: dict) -> str:
    """Encode state dictionary to a base64 string for storage."""
    return base64.b64encode(pickle.dumps(state)).decode('utf-8')


def _decode_state(encoded: str) -> dict:
    """Decode base64 string back to state dictionary."""
    return pickle.loads(base64.b64decode(encoded.encode('utf-8')))


@llm.tool
def set_restart_state(key: str, value: str | int | float | bool | None):
    """Store a piece of state to be used after restart.
    
    This tool saves key-value pairs to a state file that will be loaded
    after the CLI restarts. Use this to:
    - Remember user preferences
    - Store context for the next session
    - Save progress or pending tasks
    
    Args:
        key: The state key (should be descriptive, lowercase, underscore-separated)
        value: The state value (string, number, boolean, or null)
    
    Returns:
        Confirmation message with the stored key.
    """
    try:
        # Load existing state
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
        else:
            state = {}
        
        # Store the value (JSON-compatible)
        state[key] = value
        
        # Save state
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        return f"State stored: '{key}' = {repr(value)}"
    except Exception as e:
        return f"Error storing state: {str(e)}"


@llm.tool
def get_restart_state(key: str | None = None) -> str:
    """Retrieve stored state from a previous session.
    
    Use this to check what state was saved before a restart.
    
    Args:
        key: Optional specific key to retrieve. If None, returns all keys.
    
    Returns:
        The stored value(s) or a list of available keys.
    """
    try:
        if not STATE_FILE.exists():
            return "No state file found. The CLI may be running for the first time."
        
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        if key:
            if key in state:
                return f"State '{key}' = {repr(state[key])}"
            else:
                return f"Key '{key}' not found in state."
        else:
            if not state:
                return "No state stored."
            keys = ", ".join(f"'{k}'" for k in state.keys())
            return f"Available state keys: {keys}"
    except Exception as e:
        return f"Error reading state: {str(e)}"


@llm.tool
def clear_restart_state():
    """Clear all stored state from previous sessions.
    
    Use this when you want to start fresh without any prior state.
    
    Returns:
        Confirmation message.
    """
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            return "State file cleared."
        else:
            return "No state file to clear."
    except Exception as e:
        return f"Error clearing state: {str(e)}"


@llm.tool
def restart_cli(state_instruction: str = ""):
    """Restart the CLI application.

    This tool re-executes the mirascope_cli.py script with the same arguments.
    Use this when the user explicitly requests a restart or when the application
    state needs to be reset.

    IMPORTANT: To avoid restart loops, only use this tool when:
    - The user explicitly asks for a restart
    - You need to preserve context with a specific task instruction (not just "continue")
    
    The CLI will automatically execute the stored instruction on startup. To prevent
    loops, the instruction should describe actual work to do, not another restart command.

    Args:
        state_instruction: Optional instruction about what state to store before restarting.
                          This will be saved and executed automatically after restart.
                          Example: "Continue working on fixing the bug in src/main.py"
                          Do NOT use: "continue", "restart", or similar loop-inducing phrases.

    Returns:
        Message indicating the restart is in progress.
    """
    # Encode any state instruction for retrieval after restart
    if state_instruction:
        try:
            # Load existing state
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
            else:
                state = {}
            
            # Store the instruction
            state["last_instruction"] = state_instruction
            
            # Save state
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            # Don't fail the restart if state storage fails
            pass
    
    # Re-execution: Python will reload the module and re-run from __main__
    os.execv(sys.executable, [sys.executable] + sys.argv)
