import sys
import subprocess
import platform


def _browse_folder_windows_tk():
    """Use tkinter folder picker on Windows as the primary, reliable UI path."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(parent=root, title="Select folder")
    root.destroy()
    return folder.strip() if folder else None


def _browse_folder_windows_powershell(is_wsl_env=False):
    """Fallback Windows folder picker via PowerShell WinForms dialog."""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$f=New-Object System.Windows.Forms.FolderBrowserDialog;"
        'if($f.ShowDialog() -eq "OK"){Write-Output $f.SelectedPath}'
    )
    commands = []
    if not is_wsl_env:
        commands.append(["powershell.exe", "-NoProfile", "-STA", "-Command", script])
    else:
        # In some WSL setups, powershell.exe is not directly on PATH.
        commands.extend(
            [
                ["powershell.exe", "-NoProfile", "-STA", "-Command", script],
                [
                    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                    "-NoProfile",
                    "-STA",
                    "-Command",
                    script,
                ],
            ]
        )

    folder = None
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            continue

        if result.returncode in (0, 1):
            folder = result.stdout.strip() or None
            break

    if folder and is_wsl_env:
        result = subprocess.run(
            ["wslpath", "-u", folder],
            capture_output=True,
            text=True,
            timeout=30,
        )
        folder = result.stdout.strip()

    return folder if folder else None


def is_wsl():
    """
    Detect if running in Windows Subsystem for Linux (WSL).
    Returns True if WSL is detected, False otherwise.
    """
    return (
        "wsl" in platform.release().lower() or "microsoft" in platform.release().lower()
    )


def browse_folder():
    """
    Opens a native folder selection dialog and returns the selected folder path.
    Works on Windows, macOS, and Linux (with zenity or kdialog).
    Returns None if cancelled or error.
    """
    try:
        is_windows = sys.platform.startswith("win")
        is_wsl_env = is_wsl()
        if is_windows:
            try:
                # If user cancels tkinter picker, return None directly.
                return _browse_folder_windows_tk()
            except Exception:
                return _browse_folder_windows_powershell(False)
        if is_wsl_env:
            return _browse_folder_windows_powershell(True)
        elif sys.platform == "darwin":
            script = 'POSIX path of (choose folder with prompt "Select folder:")'
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=30
            )
            folder = result.stdout.strip()
            return folder if folder else None
        else:
            # Linux: try zenity, then kdialog
            for cmd in [
                [
                    "zenity",
                    "--file-selection",
                    "--directory",
                    "--title=Select folder",
                ],
                [
                    "kdialog",
                    "--getexistingdirectory",
                    "--title",
                    "Select folder",
                ],
            ]:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0 or result.returncode == 1:  # zenity and kdialog return 1 on cancel
                        folder = result.stdout.strip()
                        return folder if folder else None
                except subprocess.TimeoutExpired:
                    return None
                except (FileNotFoundError, Exception):
                    continue
            return None
    except Exception:
        return None