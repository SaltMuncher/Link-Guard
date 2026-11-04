import os
import tkinter as tk
from datetime import datetime

import engine
from . import __version__, autostart, config, ipc, paths
from .clipboard import ClipboardWatcher
from .clipboardio import ClipboardIO
from .history import History
from .ui import UI, popup_request

POLL_MS = 600
LOG_LIMIT = 1024 * 1024


class App:
    def __init__(self, background=False):
        self.background = background
        self._logged_backend = None
        self.settings = config.load()
        self.history = History()
        self.cleaned_count = 0
        self.root = tk.Tk()
        self.root.withdraw()
        self.ui = UI(self.root, lambda: self.settings, self)
        self.clip = ClipboardIO(self.root)
        self.watcher = ClipboardWatcher(
            self.read_clipboard, self.write_clipboard, config.get_rules, lambda: self.settings,
            self.on_clipboard_attention, self.on_clipboard_cleaned)
        self.server = ipc.Server(self.handle)
        self.ui.build_main()
        self.refresh_status()

    def log(self, event, **fields):
        if not self.settings['diagnostic_log']:
            return
        path = paths.config_dir() / 'linkguard.log'
        try:
            if path.exists() and path.stat().st_size > LOG_LIMIT:
                path.unlink()
            line = datetime.now().isoformat(timespec='seconds') + ' ' + event
            line += ''.join(' %s=%s' % (k, v) for k, v in fields.items())
            with open(path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except OSError:
            pass

    def refresh_status(self):
        watching = 'watching the clipboard' if self.settings['clipboard_monitor'] else 'clipboard cleaning is off'
        self.ui.set_status('%s, %d cleaned so far' % (watching, self.cleaned_count))

    def record(self, source, result):
        if self.settings['keep_history'] and result['status'] != 'invalid':
            self.history.add(source, result)

    def manual_clean(self, text):
        result = engine.analyze(text, config.get_rules(), assume_https=True)
        self.record('manual', result)
        return result

    def read_clipboard(self):
        try:
            text = self.clip.read()
        except Exception as exc:
            if self.clip.failures == 1 or self.clip.use_wl:
                self.log('clipboard_read_failed', backend=self.clip.backend, error=type(exc).__name__)
            raise
        if self.clip.backend != self._logged_backend:
            self._logged_backend = self.clip.backend
            self.log('clipboard_backend', backend=self.clip.backend)
        return text

    def write_clipboard(self, text):
        self.clip.write(text)

    def copy_text(self, text):
        self.write_clipboard(text)
        self.watcher.mark_written(text)

    def on_clipboard_cleaned(self, result):
        self.cleaned_count += 1
        self.record('clipboard', result)
        self.log('clipboard_cleaned', host=result['host'], removed=len(result['removed']))
        self.refresh_status()

    def on_clipboard_attention(self, result):
        self.record('clipboard', result)
        self.log('clipboard_flagged', host=result['host'], flags=','.join(f['code'] for f in result['flags']))
        future = self.ui.submit(popup_request(result))

        def finish(fut):
            if fut.result() == 'copy_cleaned':
                self.ui.post(lambda: self.watcher.replace(result['cleaned']))
        future.add_done_callback(finish)

    def clear_history(self):
        self.history.clear()

    def toggle(self, key, value):
        previous = self.settings[key]
        if key == 'autostart':
            try:
                if value:
                    autostart.enable(autostart.launch_command(paths.root_dir()))
                else:
                    autostart.disable()
            except OSError as exc:
                from tkinter import messagebox
                messagebox.showerror('Link Guard', 'Could not change the startup setting:\n' + str(exc),
                                     parent=self.root)
                self.ui.vars[key].set(previous)
                return
        self.settings[key] = value
        config.save(self.settings)
        if key == 'keep_history' and not value:
            self.history.clear()
        self.history._changed()
        self.refresh_status()

    def handle(self, message):
        kind = message.get('type')
        if kind == 'ping':
            return {'ok': True, 'version': __version__}
        if kind == 'show':
            self.ui.post(self.ui.show_main)
            return {'ok': True}
        if kind == 'quit':
            self.ui.post(self.quit)
            return {'ok': True}
        return {'ok': False, 'error': 'unknown_type'}

    def poll(self):
        self.watcher.poll()
        self.root.after(POLL_MS, self.poll)

    def quit(self):
        self.server.close()
        self.root.quit()

    def run(self):
        self.server.start()
        if self.settings['first_run']:
            self.settings['first_run'] = False
            config.save(self.settings)
            try:
                autostart.enable(autostart.launch_command(paths.root_dir()))
                self.settings['autostart'] = True
                self.ui.vars['autostart'].set(True)
            except OSError:
                pass
            self.ui.show_main()
        elif not self.background:
            self.ui.show_main()
        self.root.after(POLL_MS, self.poll)
        try:
            self.root.mainloop()
        finally:
            self.server.close()
            if ipc.family() == 'AF_UNIX':
                try:
                    os.unlink(ipc.address())
                except OSError:
                    pass
