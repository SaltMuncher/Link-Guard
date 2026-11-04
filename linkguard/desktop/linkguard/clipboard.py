import re

import engine

URL_ONLY = re.compile(r'^https?://\S+$', re.I)
MAX_LENGTH = 8192


class ClipboardWatcher:
    def __init__(self, read, write, rules, settings, on_attention, on_cleaned=None):
        self.read = read
        self.write = write
        self.rules = rules
        self.settings = settings
        self.on_attention = on_attention
        self.on_cleaned = on_cleaned
        self.last = None

    def replace(self, text):
        try:
            self.write(text)
        except Exception:
            return False
        self.last = text
        return True

    def mark_written(self, text):
        self.last = text

    def poll(self):
        if not self.settings()['clipboard_monitor']:
            return
        try:
            text = self.read()
        except Exception:
            return
        if not isinstance(text, str) or text == self.last:
            return
        self.last = text
        s = text.strip()
        if len(s) > MAX_LENGTH or not URL_ONLY.match(s):
            return
        result = engine.analyze(s, self.rules())
        if result['status'] == 'cleaned':
            if self.replace(result['cleaned']) and self.on_cleaned:
                self.on_cleaned(result)
        elif result['status'] == 'attention':
            if self.settings()['warn_clipboard']:
                self.on_attention(result)
            elif result['cleaned'] != result['original']:
                if self.replace(result['cleaned']) and self.on_cleaned:
                    self.on_cleaned(result)
