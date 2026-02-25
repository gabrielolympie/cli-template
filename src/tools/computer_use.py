from mirascope import llm
from pydantic import Field
import os
import uuid
import subprocess
import shutil

from PIL import Image

from src.tools.screenshot import (
    detect_os,
    linux_to_windows_path,
    take_screenshot_wsl,
    take_screenshot_mss,
    resize_to_1_megapixel,
    _apply_coordinate_grid,
    _get_logical_screen_size,
    MSS_AVAILABLE,
)

PROJECT_ROOT = os.getcwd()
POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _to_int_or_none(val):
    """Coerce 'None' string or empty value to Python None, else int."""
    if val is None or str(val).strip().lower() == "none" or str(val).strip() == "":
        return None
    return int(val)


def _run_powershell(script: str, timeout: int = 15) -> str:
    """Write a PS1 script to a temp file and execute it. Returns stdout."""
    tmp_dir = os.path.join(PROJECT_ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    ps_path = os.path.join(tmp_dir, f"cu_{uuid.uuid4().hex[:8]}.ps1")

    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(script)

    try:
        ps_win = linux_to_windows_path(ps_path)
        result = subprocess.run(
            [POWERSHELL, "-ExecutionPolicy", "Bypass", "-File", ps_win],
            capture_output=True,
            timeout=timeout,
        )
        stderr = result.stderr.decode("utf-8", errors="ignore")
        if result.returncode != 0:
            raise RuntimeError(stderr)
        return result.stdout.decode("utf-8", errors="ignore").strip()
    finally:
        if os.path.exists(ps_path):
            os.unlink(ps_path)


# ---------------------------------------------------------------------------
# Screenshot helper
# ---------------------------------------------------------------------------

def _take_screenshot() -> str:
    """Take a screenshot and return the relative path."""
    screenshots_dir = os.path.join(PROJECT_ROOT, "screenshot")
    os.makedirs(screenshots_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(screenshots_dir, name)

    os_type = detect_os()
    if os_type == "wsl":
        take_screenshot_wsl(path)
    elif MSS_AVAILABLE:
        take_screenshot_mss(path)
    else:
        raise RuntimeError("mss library not available. Install with: pip install mss")

    with Image.open(path) as img:
        orig_w, orig_h = img.size
        logical_w, logical_h = _get_logical_screen_size(os_type, orig_w, orig_h)
        img = resize_to_1_megapixel(img)
        img = _apply_coordinate_grid(img, logical_w, logical_h)
        img.save(path, "PNG")

    return f"screenshot/{name}"


# ---------------------------------------------------------------------------
# Win32 C# stub (shared by all WSL mouse/keyboard helpers)
# ---------------------------------------------------------------------------

_WIN32_STUB = r"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinInput {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, IntPtr extra);
}
"@
"""


# ---------------------------------------------------------------------------
# WSL mouse helpers
# ---------------------------------------------------------------------------

def _wsl_mouse_move(x: int, y: int) -> str:
    script = _WIN32_STUB + f"""
[WinInput]::SetCursorPos({x}, {y})
Write-Host "OK"
"""
    _run_powershell(script)
    return f"Moved mouse to ({x}, {y})"


def _wsl_mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> str:
    flags = {
        "left":   (0x0002, 0x0004),
        "right":  (0x0008, 0x0010),
        "middle": (0x0020, 0x0040),
    }
    down, up = flags.get(button, (0x0002, 0x0004))
    clicks = 2 if double else 1
    click_block = "\n".join([
        f"    [WinInput]::mouse_event({down}, 0, 0, 0, [IntPtr]::Zero)",
        f"    Start-Sleep -Milliseconds 30",
        f"    [WinInput]::mouse_event({up}, 0, 0, 0, [IntPtr]::Zero)",
        f"    Start-Sleep -Milliseconds 30",
    ])
    script = _WIN32_STUB + f"""
[WinInput]::SetCursorPos({x}, {y})
Start-Sleep -Milliseconds 50
for ($i = 0; $i -lt {clicks}; $i++) {{
{click_block}
}}
Write-Host "OK"
"""
    _run_powershell(script)
    label = "Double-clicked" if double else "Clicked"
    return f"{label} {button} at ({x}, {y})"


def _wsl_scroll(x: int, y: int, direction: str, amount: int) -> str:
    if direction == "up":
        flag, delta = 0x0800, 120 * amount
    elif direction == "down":
        flag, delta = 0x0800, -120 * amount
    elif direction == "right":
        flag, delta = 0x1000, 120 * amount
    else:  # left
        flag, delta = 0x1000, -120 * amount

    script = _WIN32_STUB + f"""
[WinInput]::SetCursorPos({x}, {y})
Start-Sleep -Milliseconds 50
[WinInput]::mouse_event({flag}, 0, 0, {delta}, [IntPtr]::Zero)
Write-Host "OK"
"""
    _run_powershell(script)
    return f"Scrolled {direction} {amount} step(s) at ({x}, {y})"


def _wsl_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    script = _WIN32_STUB + f"""
[WinInput]::SetCursorPos({start_x}, {start_y})
Start-Sleep -Milliseconds 50
[WinInput]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 50
$steps = 20
for ($i = 1; $i -le $steps; $i++) {{
    $px = [int]({start_x} + ({end_x} - {start_x}) * $i / $steps)
    $py = [int]({start_y} + ({end_y} - {start_y}) * $i / $steps)
    [WinInput]::SetCursorPos($px, $py)
    Start-Sleep -Milliseconds 10
}}
[WinInput]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
Write-Host "OK"
"""
    _run_powershell(script)
    return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"


# ---------------------------------------------------------------------------
# WSL keyboard helpers
# ---------------------------------------------------------------------------

def _key_to_sendkeys(key: str) -> str:
    """Convert a friendly key name/combo to PowerShell SendKeys notation."""
    modifier_map = {"ctrl": "^", "control": "^", "alt": "%", "shift": "+"}
    key_map = {
        "enter": "{ENTER}", "return": "{ENTER}",
        "escape": "{ESCAPE}", "esc": "{ESCAPE}",
        "tab": "{TAB}",
        "backspace": "{BACKSPACE}",
        "delete": "{DELETE}", "del": "{DELETE}",
        "insert": "{INSERT}",
        "home": "{HOME}", "end": "{END}",
        "pageup": "{PGUP}", "page_up": "{PGUP}",
        "pagedown": "{PGDN}", "page_down": "{PGDN}",
        "up": "{UP}", "down": "{DOWN}", "left": "{LEFT}", "right": "{RIGHT}",
        "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4": "{F4}",
        "f5": "{F5}", "f6": "{F6}", "f7": "{F7}", "f8": "{F8}",
        "f9": "{F9}", "f10": "{F10}", "f11": "{F11}", "f12": "{F12}",
        "space": " ", "caps_lock": "{CAPSLOCK}", "print_screen": "{PRTSC}",
        "windows": "^{ESC}",
    }

    parts = key.lower().split("+")
    modifiers = ""
    for part in parts[:-1]:
        modifiers += modifier_map.get(part, "")
    main = parts[-1]
    if main in key_map:
        return modifiers + key_map[main]
    elif len(main) == 1:
        return modifiers + main
    else:
        return modifiers + "{" + main.upper() + "}"


def _wsl_type(text: str) -> str:
    """Type text via clipboard paste (handles all characters reliably)."""
    tmp_dir = os.path.join(PROJECT_ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    txt_path = os.path.join(tmp_dir, f"type_{uuid.uuid4().hex[:8]}.txt")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    win_txt = linux_to_windows_path(txt_path)
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
$text = [System.IO.File]::ReadAllText("{win_txt}", [System.Text.Encoding]::UTF8)
[System.Windows.Forms.Clipboard]::SetText($text)
[System.Windows.Forms.SendKeys]::SendWait("^v")
Write-Host "OK"
"""
    try:
        _run_powershell(script)
    finally:
        if os.path.exists(txt_path):
            os.unlink(txt_path)
    return f"Typed {len(text)} character(s)"


def _wsl_key(key: str) -> str:
    sendkeys = _key_to_sendkeys(key)
    # Escape double-quotes in the sendkeys string for embedding in PS
    sendkeys_escaped = sendkeys.replace('"', '`"')
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("{sendkeys_escaped}")
Write-Host "OK"
"""
    _run_powershell(script)
    return f"Pressed key: {key}"


# ---------------------------------------------------------------------------
# Non-WSL helpers (pyautogui)
# ---------------------------------------------------------------------------

def _get_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        return pyautogui
    except ImportError:
        raise RuntimeError(
            "pyautogui is required for non-WSL platforms. "
            "Install with: pip install pyautogui"
        )


def _other_mouse_move(x: int, y: int) -> str:
    _get_pyautogui().moveTo(x, y)
    return f"Moved mouse to ({x}, {y})"


def _other_mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> str:
    pg = _get_pyautogui()
    pg.click(x, y, button=button, clicks=2 if double else 1, interval=0.05)
    label = "Double-clicked" if double else "Clicked"
    return f"{label} {button} at ({x}, {y})"


def _other_scroll(x: int, y: int, direction: str, amount: int) -> str:
    pg = _get_pyautogui()
    if direction in ("up", "down"):
        pg.scroll(amount if direction == "up" else -amount, x=x, y=y)
    else:
        pg.hscroll(amount if direction == "right" else -amount, x=x, y=y)
    return f"Scrolled {direction} {amount} step(s) at ({x}, {y})"


def _other_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    pg = _get_pyautogui()
    pg.moveTo(start_x, start_y)
    pg.dragTo(end_x, end_y, duration=0.4, button="left")
    return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"


def _other_type(text: str) -> str:
    pg = _get_pyautogui()
    pg.write(text, interval=0.02)
    return f"Typed {len(text)} character(s)"


def _other_key(key: str) -> str:
    pg = _get_pyautogui()
    pg.hotkey(*key.lower().split("+"))
    return f"Pressed key: {key}"


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

@llm.tool
def computer_use(
    action: str = Field(
        description=(
            "Action to perform. One of: "
            "screenshot | mouse_move | left_click | right_click | double_click | "
            "middle_click | scroll | left_click_drag | type | key. "
            "Always call 'screenshot' first to see the current screen state before "
            "performing other actions."
        )
    ),
    x: int | None = Field(default=None, description="X coordinate in pixels (required for all mouse actions)"),
    y: int | None = Field(default=None, description="Y coordinate in pixels (required for all mouse actions)"),
    end_x: int | None = Field(default=None, description="End X coordinate for left_click_drag"),
    end_y: int | None = Field(default=None, description="End Y coordinate for left_click_drag"),
    text: str | None = Field(default=None, description="Text to type (for 'type' action). Uses clipboard paste internally."),
    key: str | None = Field(default=None, description="Key or combo to press, e.g. 'enter', 'escape', 'ctrl+c', 'alt+f4' (for 'key' action)"),
    scroll_direction: str | None = Field(default=None, description="Scroll direction: up | down | left | right (for 'scroll' action)"),
    scroll_amount: int | None = Field(default=None, description="Number of scroll steps (for 'scroll', default 3)"),
):
    """
    Control the computer using mouse and keyboard actions.

    Workflow for iterative computer control:
    1. Call action='screenshot' to see the current screen state.
    2. Identify the target element and its coordinates from the screenshot.
    3. Perform the desired action (click, type, scroll, etc.).
    4. Call action='screenshot' again to verify the result.
    5. Repeat as needed.

    Coordinate system: (0, 0) is the top-left corner of the screen.
    Pixel coordinates in screenshots correspond directly to screen coordinates.

    Note: The 'type' action uses clipboard paste temporarily — it will briefly
    overwrite the clipboard contents but restores normal operation immediately after.
    """
    # Coerce string "None" / empty values to Python None
    x = _to_int_or_none(x)
    y = _to_int_or_none(y)
    end_x = _to_int_or_none(end_x)
    end_y = _to_int_or_none(end_y)
    scroll_amount = _to_int_or_none(scroll_amount)
    if scroll_amount is None:
        scroll_amount = 3

    try:
        os_type = detect_os()
        is_wsl = os_type == "wsl"

        match action:
            case "screenshot":
                return _take_screenshot()

            case "mouse_move":
                if x is None or y is None:
                    return "Error: x and y are required for mouse_move"
                return _wsl_mouse_move(x, y) if is_wsl else _other_mouse_move(x, y)

            case "left_click":
                if x is None or y is None:
                    return "Error: x and y are required for left_click"
                return (
                    _wsl_mouse_click(x, y, "left")
                    if is_wsl
                    else _other_mouse_click(x, y, "left")
                )

            case "right_click":
                if x is None or y is None:
                    return "Error: x and y are required for right_click"
                return (
                    _wsl_mouse_click(x, y, "right")
                    if is_wsl
                    else _other_mouse_click(x, y, "right")
                )

            case "double_click":
                if x is None or y is None:
                    return "Error: x and y are required for double_click"
                return (
                    _wsl_mouse_click(x, y, "left", double=True)
                    if is_wsl
                    else _other_mouse_click(x, y, "left", double=True)
                )

            case "middle_click":
                if x is None or y is None:
                    return "Error: x and y are required for middle_click"
                return (
                    _wsl_mouse_click(x, y, "middle")
                    if is_wsl
                    else _other_mouse_click(x, y, "middle")
                )

            case "scroll":
                if x is None or y is None:
                    return "Error: x and y are required for scroll"
                if scroll_direction not in ("up", "down", "left", "right"):
                    return "Error: scroll_direction must be up, down, left, or right"
                return (
                    _wsl_scroll(x, y, scroll_direction, scroll_amount)
                    if is_wsl
                    else _other_scroll(x, y, scroll_direction, scroll_amount)
                )

            case "left_click_drag":
                if any(v is None for v in (x, y, end_x, end_y)):
                    return "Error: x, y, end_x, and end_y are required for left_click_drag"
                return (
                    _wsl_drag(x, y, end_x, end_y)
                    if is_wsl
                    else _other_drag(x, y, end_x, end_y)
                )

            case "type":
                if not text:
                    return "Error: text is required for type action"
                return _wsl_type(text) if is_wsl else _other_type(text)

            case "key":
                if not key:
                    return "Error: key is required for key action"
                return _wsl_key(key) if is_wsl else _other_key(key)

            case _:
                return (
                    f"Unknown action: '{action}'. Valid actions: screenshot, mouse_move, "
                    "left_click, right_click, double_click, middle_click, scroll, "
                    "left_click_drag, type, key"
                )

    except Exception as e:
        return f"Error performing '{action}': {e}"
