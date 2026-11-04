import os
import shutil
import subprocess
import tkinter as tk

FAILURES_BEFORE_FALLBACK = 3
FALLBACK_INTERVAL = 1.5


def is_wayland():
    return bool(os.environ.get('WAYLAND_DISPLAY')) or os.environ.get('XDG_SESSION_TYPE') == 'wayland'


def run_wl(args, data=None):
    try:
        p = subprocess.run(args, input=data, capture_output=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.decode('utf-8', 'replace') if p.returncode == 0 else None


class ClipboardIO:
    def __init__(self, root, runner=run_wl, which=shutil.which, wayland=None, clock=None):
        import time
        self.root = root
        self.runner = runner
        self.has_paste = bool(which('wl-paste'))
        self.has_copy = bool(which('wl-copy'))
        self.wayland = is_wayland() if wayland is None else wayland
        self.clock = clock or time.monotonic
        self.failures = 0
        self.use_wl = False
        self.next_wl = 0.0
        self.backend = 'tk'

    def read(self):
        if not self.use_wl:
            try:
                text = self.root.clipboard_get()
                self.failures = 0
                self.backend = 'tk'
                return text
            except tk.TclError:
                self.failures += 1
                if self.wayland and self.has_paste and self.failures >= FAILURES_BEFORE_FALLBACK:
                    self.use_wl = True
                else:
                    raise
        now = self.clock()
        if now < self.next_wl:
            raise RuntimeError('rate limited')
        self.next_wl = now + FALLBACK_INTERVAL
        text = self.runner(['wl-paste', '--no-newline'])
        if text is None:
            raise RuntimeError('wl-paste failed')
        self.backend = 'wl-paste'
        return text

    def write(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        if self.wayland and self.has_copy:
            self.runner(['wl-copy'], text.encode('utf-8'))


def check(root):
    lines = ['session: %s' % (os.environ.get('XDG_SESSION_TYPE') or 'unknown'),
             'WAYLAND_DISPLAY: %s' % (os.environ.get('WAYLAND_DISPLAY') or 'unset'),
             'DISPLAY: %s' % (os.environ.get('DISPLAY') or 'unset'),
             'wl-paste installed: %s' % bool(shutil.which('wl-paste'))]
    try:
        lines.append('tk read: ok (%d characters)' % len(root.clipboard_get()))
    except tk.TclError as exc:
        lines.append('tk read: failed (%s)' % exc)
    out = run_wl(['wl-paste', '--no-newline']) if shutil.which('wl-paste') else None
    lines.append('wl-paste read: ' + ('ok (%d characters)' % len(out) if out is not None else 'failed or unavailable'))
    return '\n'.join(lines)
