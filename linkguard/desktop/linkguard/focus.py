import shutil
import subprocess

from . import paths

NOTIFY_TEXT = 'A link needs your attention. Open the Link Guard warning window.'


def has_focus(win):
    try:
        return win.focus_displayof() is not None
    except Exception:
        return False


def _win_hwnd(win):
    return int(win.wm_frame(), 16)


def _win_foreground(win):
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = _win_hwnd(win)
    foreground = user32.GetForegroundWindow()
    this_thread = kernel32.GetCurrentThreadId()
    other_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    attached = bool(other_thread) and other_thread != this_thread
    if attached:
        user32.AttachThreadInput(other_thread, this_thread, True)
    try:
        user32.ShowWindow(hwnd, 9)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(other_thread, this_thread, False)


def _win_flash(win):
    import ctypes
    from ctypes import wintypes

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.UINT), ('hwnd', wintypes.HWND), ('dwFlags', wintypes.DWORD),
                    ('uCount', wintypes.UINT), ('dwTimeout', wintypes.DWORD)]

    info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), _win_hwnd(win), 0x3 | 0xC, 0, 0)
    ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    return 'taskbar flash'


def notify(win):
    try:
        if paths.IS_WINDOWS:
            return _win_flash(win)
        if shutil.which('notify-send'):
            subprocess.Popen(['notify-send', '-u', 'critical', '-a', 'Link Guard', 'Link Guard', NOTIFY_TEXT],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return 'notify-send'
        win.bell()
    except Exception:
        pass
    return None


def present(win, topmost=True, notifier=None, delay_ms=400, scheduler=None):
    win.deiconify()
    win.attributes('-topmost', bool(topmost))
    win.lift()
    try:
        win.focus_force()
    except Exception:
        pass
    if paths.IS_WINDOWS:
        try:
            _win_foreground(win)
        except Exception:
            pass

    def check():
        exists = getattr(win, 'winfo_exists', None)
        if exists is not None and not exists():
            return
        if not has_focus(win):
            (notifier or notify)(win)

    (scheduler or win.after)(delay_ms, check)
