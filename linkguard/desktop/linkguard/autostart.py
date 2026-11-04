import os
import subprocess
import sys
from pathlib import Path

from . import paths

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME = 'LinkGuard'


def interpreter(windowed=True):
    exe = sys.executable
    if paths.IS_WINDOWS and windowed:
        candidate = Path(exe).with_name('pythonw.exe')
        if candidate.exists():
            return str(candidate)
    return exe


def launch_command(root, background=True):
    appimage = os.environ.get('APPIMAGE')
    if appimage:
        return [appimage] + (['--background'] if background else [])
    if paths.FROZEN:
        return [sys.executable] + (['--background'] if background else [])
    cmd = [interpreter(), str(Path(root) / 'desktop' / 'run.py')]
    if background:
        cmd.append('--background')
    return cmd


def desktop_quote(arg):
    out = arg.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    return '"' + out + '"'


def desktop_exec(cmd):
    return ' '.join(desktop_quote(a) for a in cmd)


def autostart_file():
    override = os.environ.get('LINKGUARD_AUTOSTART_DIR')
    if override:
        base = Path(override)
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'autostart'
    return base / 'linkguard.desktop'


def enable(cmd):
    if paths.IS_WINDOWS:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(cmd))
        return
    target = autostart_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Name=Link Guard\n'
        'Comment=URL tracking protection\n'
        'Exec=' + desktop_exec(cmd) + '\n'
        'Terminal=false\n'
        'X-GNOME-Autostart-enabled=true\n',
        encoding='utf-8')


def disable():
    if paths.IS_WINDOWS:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, VALUE_NAME)
        except FileNotFoundError:
            pass
        return
    try:
        autostart_file().unlink()
    except FileNotFoundError:
        pass


def is_enabled():
    if paths.IS_WINDOWS:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, VALUE_NAME)
            return True
        except FileNotFoundError:
            return False
    return autostart_file().exists()
