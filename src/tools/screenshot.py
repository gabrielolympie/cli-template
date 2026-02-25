from mirascope import llm
import os
import sys
import platform
import subprocess
import uuid
import shutil
from datetime import datetime
from PIL import Image

PROJECT_ROOT = os.getcwd()

# Try importing mss for cross‑platform screenshots
try:
    from mss import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


def linux_to_windows_path(linux_path: str) -> str:
    """Convert a Linux path from /mnt/c/... to Windows C:\\... format."""
    if linux_path.startswith('/mnt/'):
        parts = linux_path.split('/')
        if len(parts) >= 3:
            drive = parts[2].upper() + ':'
            rel_path = '/'.join(parts[3:])
            return drive + '\\' + rel_path.replace('/', '\\')
    return linux_path


def detect_os() -> str:
    """Detect if we are running on Windows, macOS, Linux, or WSL."""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "mac"
    elif "microsoft" in platform.uname().release.lower():
        return "wsl"
    else:
        return "linux"


def resize_to_1_megapixel(img: Image.Image) -> Image.Image:
    """Resize an image to ~1 MP while preserving aspect ratio."""
    width, height = img.size
    current_pixels = width * height
    target_pixels = 1_000_000

    if current_pixels <= target_pixels:
        return img

    scale_factor = (target_pixels / current_pixels) ** 0.5
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def crop_to_bbox(img: Image.Image, bbox: dict) -> Image.Image:
    """Crop image to a bounding box (supports two bbox formats)."""
    width, height = img.size

    if all(k in bbox for k in ['x1', 'y1', 'x2', 'y2']):
        left = max(0, bbox['x1'])
        top = max(0, bbox['y1'])
        right = min(width, bbox['x2'])
        bottom = min(height, bbox['y2'])
    elif all(k in bbox for k in ['x', 'y', 'width', 'height']):
        left = max(0, bbox['x'])
        top = max(0, bbox['y'])
        right = min(width, bbox['x'] + bbox['width'])
        bottom = min(height, bbox['y'] + bbox['height'])
    else:
        raise ValueError(
            "bbox must contain either 'x','y','width','height' or 'x1','y1','x2','y2'"
        )

    if left >= right or top >= bottom:
        raise ValueError(
            f"Invalid bbox coordinates: left={left}, top={top}, right={right}, bottom={bottom}"
        )

    return img.crop((left, top, right, bottom))


def take_screenshot_mss(path: str) -> None:
    """Take a screenshot using the mss library (cross‑platform)."""
    with mss() as sct:
        sct.shot(mon=-1, output=path)


def _get_windows_temp_dir() -> str:
    """
    Retrieve the Windows %TEMP% directory from WSL using PowerShell.
    Returns the path in Windows format, e.g. ``C:\\Users\\you\\AppData\\Local\\Temp``.
    """
    powershell_path = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [powershell_path, "-NoProfile", "-Command", "[System.IO.Path]::GetTempPath()"],
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError("Failed to obtain Windows TEMP directory")
    win_temp = result.stdout.decode("utf-8", errors="ignore").strip()
    return win_temp.rstrip("\\")


def _get_logical_screen_size(os_type: str, fallback_w: int, fallback_h: int) -> tuple[int, int]:
    """
    Return the logical screen dimensions that match the mouse coordinate system.

    On WSL the PowerShell screenshot captures physical pixels (DPI-aware), but
    Win32 SetCursorPos / mouse_event use *logical* pixels (DPI-independent).
    For example, a 2560×1600 display at 150 % scaling has logical size 1707×1067.
    Grid labels must show logical coords so the agent can use them directly.

    On other platforms mss captures at the OS-reported (logical) resolution, so
    physical == logical and the fallback is always correct.
    """
    if os_type == "wsl":
        try:
            powershell_path = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
            cmd = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "Write-Output \"$($b.Width) $($b.Height)\""
            )
            result = subprocess.run(
                [powershell_path, "-NoProfile", "-Command", cmd],
                capture_output=True,
                timeout=10,
            )
            parts = result.stdout.decode("utf-8", errors="ignore").strip().split()
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except Exception:
            pass
    elif MSS_AVAILABLE:
        try:
            with mss() as sct:
                m = sct.monitors[1]   # primary monitor, logical resolution
                return m["width"], m["height"]
        except Exception:
            pass
    return fallback_w, fallback_h


def take_screenshot_wsl(path: str) -> None:
    """
    WSL‑specific screenshot using PowerShell with DPI‑aware capture.

    The image is first saved to the Windows ``%TEMP%`` directory (guaranteed
    to be a valid Windows path), then moved back into the WSL filesystem at
    the user‑requested ``path``.
    """
    temp_filename = f"capture_{uuid.uuid4().hex[:8]}.png"
    win_temp_dir = _get_windows_temp_dir()
    windows_output_path = os.path.join(win_temp_dir, temp_filename)
    windows_path_escaped = windows_output_path.replace("\\", "\\\\")

    drive_letter = win_temp_dir[0].lower()
    wsl_temp_dir = f"/mnt/{drive_letter}/{win_temp_dir[3:].replace('\\\\', '/').replace('\\', '/')}"
    temp_capture_path = os.path.join(wsl_temp_dir, temp_filename)

    ps_script = fr"""Add-Type @"
using System;
using System.Runtime.InteropServices;

public class ScreenCapture {{
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    public static extern IntPtr GetDC(IntPtr hwnd);

    [DllImport("gdi32.dll")]
    public static extern int GetDeviceCaps(IntPtr hdc, int index);

    [DllImport("user32.dll")]
    public static extern int ReleaseDC(IntPtr hwnd, IntPtr hdc);

    public const int DESKTOPHORZRES = 118;
    public const int DESKTOPVERTRES = 117;

    public static int[] GetPhysicalResolution() {{
        IntPtr hdc = GetDC(IntPtr.Zero);
        int w = GetDeviceCaps(hdc, DESKTOPHORZRES);
        int h = GetDeviceCaps(hdc, DESKTOPVERTRES);
        ReleaseDC(IntPtr.Zero, hdc);
        return new int[] {{ w, h }};
    }}
}}
"@

[ScreenCapture]::SetProcessDPIAware()
Add-Type -AssemblyName System.Drawing

$res = [ScreenCapture]::GetPhysicalResolution()
$width = $res[0]
$height = $res[1]

Write-Host "Capturing at: $width x $height"

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen(0, 0, 0, 0, (New-Object System.Drawing.Size($width, $height)))

$bitmap.Save('{windows_path_escaped}', [System.Drawing.Imaging.ImageFormat]::Png)

$graphics.Dispose()
$bitmap.Dispose()

Write-Host "Screenshot saved successfully"
"""

    temp_dir = os.path.join(PROJECT_ROOT, ".tmp")
    os.makedirs(temp_dir, exist_ok=True)
    ps_script_path = os.path.join(
        temp_dir, f"screenshot_{uuid.uuid4().hex[:8]}.ps1"
    )
    with open(ps_script_path, "w", encoding="utf-8") as f:
        f.write(ps_script)

    try:
        ps_script_windows = linux_to_windows_path(ps_script_path)
        powershell_path = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        result = subprocess.run(
            [powershell_path, "-ExecutionPolicy", "Bypass", "-File", ps_script_windows],
            capture_output=True,
            timeout=30,
        )

        stdout_text = result.stdout.decode("utf-8", errors="ignore") if result.stdout else ""
        stderr_text = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""

        if result.returncode != 0:
            raise RuntimeError(f"PowerShell failed: {stderr_text}")

        if os.path.exists(temp_capture_path):
            shutil.move(temp_capture_path, path)
        else:
            raise FileNotFoundError(
                f"Screenshot not created at expected temp path: {temp_capture_path}"
            )

        return stdout_text

    finally:
        if os.path.exists(ps_script_path):
            os.unlink(ps_script_path)
        if os.path.exists(temp_capture_path):
            try:
                os.unlink(temp_capture_path)
            except Exception:
                pass


def _load_font(size: int = 13):
    """Load a monospace font at the given size, falling back gracefully."""
    from PIL import ImageFont
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",   # macOS
        "C:\\Windows\\Fonts\\consola.ttf",   # Windows
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _apply_coordinate_grid(
    img: Image.Image,
    screen_w: int,
    screen_h: int,
    offset_x: int = 0,
    offset_y: int = 0,
) -> Image.Image:
    """
    Overlay a semi-transparent coordinate grid showing true screen pixel positions.

    screen_w / screen_h : dimensions of the screen region represented by the image.
    offset_x / offset_y : screen coordinates of the image's top-left corner.
    Labels display absolute screen coordinates so the agent can use them directly
    for mouse actions without any conversion.
    """
    from PIL import ImageDraw

    img_w, img_h = img.size
    scale_x = screen_w / img_w
    scale_y = screen_h / img_h

    # Pick a grid step (screen pixels) that gives roughly 8-14 lines per axis
    max_dim = max(screen_w, screen_h)
    screen_step = 500
    for candidate in (50, 100, 150, 200, 250, 300, 500):
        if max_dim / candidate <= 14:
            screen_step = candidate
            break

    font = _load_font(13)

    img_rgba = img.convert("RGBA")
    overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    LINE  = (255, 80,  80,  80)   # semi-transparent red
    LABEL = (255, 255,  0, 230)   # opaque yellow
    SHADE = (  0,   0,  0, 180)   # dark shadow behind labels

    # Vertical lines – step through screen x-coordinates
    screen_x = screen_step * ((offset_x // screen_step) + 1)
    while screen_x < offset_x + screen_w:
        ix = int(round((screen_x - offset_x) / scale_x))
        if 0 < ix < img_w:
            draw.line([(ix, 0), (ix, img_h)], fill=LINE, width=1)
            lbl = str(screen_x)
            draw.text((ix + 3, 5), lbl, fill=SHADE, font=font)
            draw.text((ix + 2, 4), lbl, fill=LABEL, font=font)
        screen_x += screen_step

    # Horizontal lines – step through screen y-coordinates
    screen_y = screen_step * ((offset_y // screen_step) + 1)
    while screen_y < offset_y + screen_h:
        iy = int(round((screen_y - offset_y) / scale_y))
        if 0 < iy < img_h:
            draw.line([(0, iy), (img_w, iy)], fill=LINE, width=1)
            lbl = str(screen_y)
            draw.text((5, iy + 3), lbl, fill=SHADE, font=font)
            draw.text((4, iy + 2), lbl, fill=LABEL, font=font)
        screen_y += screen_step

    return Image.alpha_composite(img_rgba, overlay).convert("RGB")


@llm.tool
def screenshot(
    bbox_x: int | None = None,
    bbox_y: int | None = None,
    bbox_width: int | None = None,
    bbox_height: int | None = None,
):
    """
    Take a screenshot of the entire screen.

    The function automatically selects the appropriate capture method:
    - Windows / macOS / Linux → mss library
    - WSL → PowerShell DPI‑aware capture (writes to %TEMP% first)

    The image is resized to ~1 MP and saved to ./screenshot/<random>.png.

    The bbox_x, bbox_y, bbox_width, and bbox_height parameters allow cropping
    to a specific region of the screen. Unless there is a clear reason to use
    them (e.g. the user explicitly asks to zoom into a region, inspect a
    specific area, or crop the screenshot), leave them all as None to capture
    the full screen.

    Args:
        bbox_x: X coordinate (pixels) of the top-left corner of the crop region. Leave None for full screen.
        bbox_y: Y coordinate (pixels) of the top-left corner of the crop region. Leave None for full screen.
        bbox_width: Width (pixels) of the crop region. Leave None for full screen.
        bbox_height: Height (pixels) of the crop region. Leave None for full screen.
    """
    os_type = detect_os()

    # Coerce string "None" / empty values to Python None (LLM sometimes passes "None")
    def _to_int_or_none(val):
        if val is None or str(val).strip().lower() == "none" or str(val).strip() == "":
            return None
        return int(val)

    bbox_x = _to_int_or_none(bbox_x)
    bbox_y = _to_int_or_none(bbox_y)
    bbox_width = _to_int_or_none(bbox_width)
    bbox_height = _to_int_or_none(bbox_height)

    screenshots_dir = os.path.join(PROJECT_ROOT, "screenshot")

    try:
        random_name = f"{uuid.uuid4().hex[:8]}.png"
        path = os.path.join(screenshots_dir, random_name)

        os.makedirs(screenshots_dir, exist_ok=True)

        use_bbox = all(
            v is not None for v in [bbox_x, bbox_y, bbox_width, bbox_height]
        )

        # ---------- Capture ----------
        print(f"Detected OS: {os_type.upper()}")

        if os_type == "wsl":
            take_screenshot_wsl(path)
        elif MSS_AVAILABLE:
            take_screenshot_mss(path)
        else:
            return (
                f"Error: mss library not available for {os_type}. "
                "Install with: pip install mss"
            )

        if not os.path.exists(path):
            return f"Error: Screenshot file not created at {path}"

        # ---------- Post‑process ----------
        with Image.open(path) as img:
            orig_w, orig_h = img.size
            print(f"Original image size: {orig_w}x{orig_h}")

            # Logical screen size = what mouse coordinates actually use.
            # On WSL the capture is DPI-aware (physical pixels) but SetCursorPos
            # uses logical pixels, so we must query them separately.
            logical_w, logical_h = _get_logical_screen_size(os_type, orig_w, orig_h)
            print(f"Logical screen size: {logical_w}x{logical_h}")

            if use_bbox:
                bbox = {
                    "x": bbox_x,
                    "y": bbox_y,
                    "width": bbox_width,
                    "height": bbox_height,
                }
                img = crop_to_bbox(img, bbox)
                # For bbox crops, scale the logical bbox coords from the DPI ratio
                dpi_scale_x = logical_w / orig_w
                dpi_scale_y = logical_h / orig_h
                region_w = int(round(bbox_width  * dpi_scale_x))
                region_h = int(round(bbox_height * dpi_scale_y))
                off_x    = int(round(bbox_x      * dpi_scale_x))
                off_y    = int(round(bbox_y      * dpi_scale_y))
                print(
                    f"Cropped to bbox: x={bbox_x}, y={bbox_y}, "
                    f"w={bbox_width}, h={bbox_height}"
                )
            else:
                region_w, region_h = logical_w, logical_h
                off_x, off_y = 0, 0

            img = resize_to_1_megapixel(img)
            new_w, new_h = img.size
            print(
                f"Resized to ~1 MP: {new_w}x{new_h} "
                f"({new_w * new_h} pixels)"
            )
            img = _apply_coordinate_grid(img, region_w, region_h, off_x, off_y)
            img.save(path, "PNG")

        return f"screenshot/{os.path.basename(path)}"

    except Exception as e:
        return f"Error taking screenshot on {os_type.upper()}: {str(e)}"


# ----------------------------------------------------------------------
# Example usage (run directly for a quick test)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Basic full-screen screenshot (saved to ./screenshot/<random>.png)
    print(screenshot())

    # Screenshot with a bounding box crop (uncomment to test)
    # print(screenshot(bbox_x=100, bbox_y=100, bbox_width=800, bbox_height=600))