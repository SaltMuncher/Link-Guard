import queue
import tkinter as tk
from collections import deque
from concurrent.futures import Future
from tkinter import font as tkfont
from tkinter import messagebox

from . import __version__, focus, paths

GREY = '#d4d0c8'
WHITE = '#ffffff'
POPUP_TIMEOUT_MS = 300000

REASONS = {
    'shortener': 'shortened link',
    'redirect_param': 'redirects to another site',
    'punycode': 'odd characters in the site name',
    'ip_host': 'raw IP address',
    'userinfo': 'name@ in front of the site',
    'encoded_host': 'encoded site name',
    'mixed_script': 'mixed alphabets in the site name',
    'lookalike_chars': 'lookalike letters in the site name',
    'invisible_chars': 'invisible characters in the link',
    'odd_host_chars': 'unusual characters in the site name',
}


def families(root):
    return set(tkfont.families(root))


class Styles:
    def __init__(self, root):
        have = families(root)
        face = next((f for f in ('Tahoma', 'MS Sans Serif', 'DejaVu Sans', 'Liberation Sans') if f in have),
                    'TkDefaultFont')
        mono = next((f for f in ('Courier New', 'DejaVu Sans Mono', 'Liberation Mono') if f in have), 'TkFixedFont')
        self.normal = (face, 9)
        self.bold = (face, 9, 'bold')
        self.mono = (mono, 9)
        root.option_add('*Font', self.normal)

    def button(self, parent, text, command, width=None, **kw):
        return tk.Button(parent, text=text, command=command, width=width, bg=GREY, activebackground=GREY,
                         relief='raised', bd=2, padx=6, pady=1, **kw)

    def label(self, parent, text='', **kw):
        return tk.Label(parent, text=text, bg=GREY, anchor='w', justify='left', **kw)

    def entry(self, parent, var=None, readonly=False, **kw):
        return tk.Entry(parent, textvariable=var, relief='sunken', bd=2, bg=WHITE, font=self.mono,
                        state='readonly' if readonly else 'normal', readonlybackground=WHITE, **kw)

    def readonly_text(self, parent, text, width=70, max_lines=4):
        lines = max(1, min(max_lines, -(-len(text) // width)))
        box = tk.Text(parent, width=width, height=lines, wrap='char', bg=WHITE, relief='sunken', bd=2,
                      font=self.mono, highlightthickness=0)
        box.insert('1.0', text)
        box.configure(state='disabled')
        return box


def popup_request(result):
    differs = result['cleaned'] != result['original']
    actions = []
    if differs:
        actions.append(('Use cleaned link', 'copy_cleaned'))
    actions.append(('Leave it alone' if differs else 'OK', 'keep'))
    return {'result': result, 'actions': actions, 'cancel': 'keep'}


class Popup:
    def __init__(self, ui, request, done):
        self.ui = ui
        self.request = request
        self.done = done
        self.finished = False
        s = ui.styles
        result = request['result']
        top = tk.Toplevel(ui.root)
        self.top = top
        top.title('Link Guard')
        top.configure(bg=GREY)
        top.resizable(False, False)
        top.protocol('WM_DELETE_WINDOW', lambda: self.finish(request['cancel']))
        top.bind('<Escape>', lambda e: self.finish(request['cancel']))

        body = tk.Frame(top, bg=GREY, padx=12, pady=10)
        body.pack(fill='both')
        s.label(body, 'You just copied a link worth a second look.', font=s.bold).pack(fill='x')
        for flag in result['flags']:
            s.label(body, '- ' + REASONS.get(flag['code'], flag['code']) + ': ' + flag['message'],
                    wraplength=480).pack(fill='x', pady=(4, 0))

        s.label(body, 'As copied:').pack(fill='x', pady=(10, 2))
        s.readonly_text(body, result['original']).pack(fill='x')
        if result['cleaned'] != result['original']:
            s.label(body, 'With the tracking removed:').pack(fill='x', pady=(8, 2))
            s.readonly_text(body, result['cleaned']).pack(fill='x')

        row = tk.Frame(body, bg=GREY)
        row.pack(fill='x', pady=(12, 0))
        self.buttons = {}
        for label, action in request['actions']:
            b = s.button(row, label, lambda a=action: self.finish(a), width=18)
            b.pack(side='left', padx=(0, 6))
            self.buttons[action] = b
        self.buttons[request['cancel']].focus_set()
        top.bind('<Return>', lambda e: self.finish(request['cancel']))
        ui.root.after(POPUP_TIMEOUT_MS, lambda: self.finish(request['cancel']))

        top.update_idletasks()
        x = (top.winfo_screenwidth() - top.winfo_reqwidth()) // 2
        y = (top.winfo_screenheight() - top.winfo_reqheight()) // 3
        top.geometry('+%d+%d' % (x, y))
        focus.present(top, topmost=ui.settings()['always_on_top'], scheduler=ui.root.after)

    def finish(self, action):
        if self.finished:
            return
        self.finished = True
        try:
            self.top.destroy()
        except tk.TclError:
            pass
        self.done(action)


class UI:
    def __init__(self, root, settings, app):
        self.root = root
        self.settings = settings
        self.app = app
        self.styles = Styles(root)
        self.inbox = queue.Queue()
        self.pending = deque()
        self.current = None
        self.vars = {}
        self.last = None
        self.status_var = tk.StringVar(root)
        self._pump_id = self.root.after(150, self._pump)

    def close(self):
        self.root.after_cancel(self._pump_id)

    def post(self, fn):
        self.inbox.put(('call', fn))

    def submit(self, request):
        future = Future()
        self.inbox.put(('popup', (request, future)))
        return future

    def _pump(self):
        try:
            while True:
                kind, payload = self.inbox.get_nowait()
                if kind == 'call':
                    payload()
                else:
                    self.pending.append(payload)
        except queue.Empty:
            pass
        if self.current is None and self.pending:
            request, future = self.pending.popleft()

            def done(action, future=future):
                self.current = None
                if not future.done():
                    future.set_result(action)
            self.current = Popup(self, request, done)
        self._pump_id = self.root.after(150, self._pump)

    def show_main(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass

    def build_main(self):
        root, s, app = self.root, self.styles, self.app
        root.title('Link Guard')
        root.configure(bg=GREY)
        root.minsize(560, 470)
        root.protocol('WM_DELETE_WINDOW', root.withdraw)
        try:
            icon = paths.resource('assets/linkguard.png')
            if icon.exists():
                self.icon = tk.PhotoImage(file=str(icon))
                root.iconphoto(True, self.icon)
        except tk.TclError:
            pass

        bar = tk.Menu(root)
        filemenu = tk.Menu(bar, tearoff=False)
        filemenu.add_command(label='Hide window', command=root.withdraw)
        filemenu.add_separator()
        filemenu.add_command(label='Quit Link Guard', command=app.quit)
        bar.add_cascade(label='File', menu=filemenu)
        opts = tk.Menu(bar, tearoff=False)
        for key, text in (('clipboard_monitor', 'Clean links as I copy them'),
                          ('keep_history', 'Keep a history (memory only)'),
                          ('warn_clipboard', 'Pop up for risky links'),
                          ('always_on_top', 'Pop-ups stay on top'),
                          ('autostart', 'Start when I log in'),
                          ('diagnostic_log', 'Write a debug log (no links in it)')):
            var = tk.BooleanVar(root, value=self.settings()[key])
            self.vars[key] = var
            opts.add_checkbutton(label=text, variable=var, command=lambda k=key, v=var: app.toggle(k, v.get()))
        bar.add_cascade(label='Options', menu=opts)
        helpmenu = tk.Menu(bar, tearoff=False)
        helpmenu.add_command(label='About', command=self.about)
        bar.add_cascade(label='Help', menu=helpmenu)
        root.config(menu=bar)

        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        top = tk.Frame(root, bg=GREY, padx=8, pady=8)
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure(1, weight=1)
        s.label(top, 'Link:').grid(row=0, column=0, sticky='w')
        self.entry = s.entry(top)
        self.entry.grid(row=0, column=1, sticky='ew', padx=6)
        self.entry.bind('<Return>', lambda e: self.do_clean())
        s.button(top, 'Clean', self.do_clean, width=8).grid(row=0, column=2)
        self.result_var = tk.StringVar(root)
        self.note_var = tk.StringVar(root)
        s.label(top, 'Result:').grid(row=1, column=0, sticky='w', pady=(6, 0))
        s.entry(top, self.result_var, readonly=True).grid(row=1, column=1, sticky='ew', padx=6, pady=(6, 0))
        s.label(top, '', textvariable=self.note_var, wraplength=500).grid(row=2, column=1, sticky='w', padx=6)
        btns = tk.Frame(top, bg=GREY)
        btns.grid(row=3, column=1, sticky='w', padx=6, pady=(4, 0))
        self.copy_clean = s.button(btns, 'Copy cleaned', lambda: self.copy('cleaned'), width=14)
        self.copy_clean.pack(side='left')
        self.copy_orig = s.button(btns, 'Copy original', lambda: self.copy('original'), width=14)
        self.copy_orig.pack(side='left', padx=6)
        self.set_result_buttons(False)

        self.history_title = tk.StringVar(root)
        s.label(root, '', textvariable=self.history_title, font=s.bold).grid(row=1, column=0, sticky='w', padx=8)
        mid = tk.Frame(root, bg=GREY, padx=8)
        mid.grid(row=2, column=0, sticky='nsew')
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)
        self.listbox = tk.Listbox(mid, height=8, font=s.mono, relief='sunken', bd=2, bg=WHITE,
                                  exportselection=False, activestyle='none')
        self.listbox.grid(row=0, column=0, sticky='nsew')
        scroll = tk.Scrollbar(mid, command=self.listbox.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind('<<ListboxSelect>>', lambda e: self.show_entry())

        low = tk.Frame(root, bg=GREY, padx=8, pady=6)
        low.grid(row=3, column=0, sticky='ew')
        low.columnconfigure(1, weight=1)
        self.orig_var = tk.StringVar(root)
        self.clean_var = tk.StringVar(root)
        s.label(low, 'Original:').grid(row=0, column=0, sticky='w')
        s.entry(low, self.orig_var, readonly=True).grid(row=0, column=1, sticky='ew', padx=6)
        s.label(low, 'Cleaned:').grid(row=1, column=0, sticky='w', pady=(4, 0))
        s.entry(low, self.clean_var, readonly=True).grid(row=1, column=1, sticky='ew', padx=6, pady=(4, 0))
        row = tk.Frame(low, bg=GREY)
        row.grid(row=2, column=1, sticky='w', padx=6, pady=(6, 0))
        self.h_orig = s.button(row, 'Copy original', lambda: self.copy_history('original'), width=14)
        self.h_orig.pack(side='left')
        self.h_clean = s.button(row, 'Copy cleaned', lambda: self.copy_history('cleaned'), width=14)
        self.h_clean.pack(side='left', padx=6)
        s.button(row, 'Clear history', app.clear_history, width=14).pack(side='left')

        tk.Label(root, textvariable=self.status_var, relief='sunken', bd=1, anchor='w', bg=GREY,
                 padx=4).grid(row=4, column=0, sticky='ew')
        app.history.listeners.append(self.refresh_history)
        self.refresh_history()

    def set_result_buttons(self, on):
        state = 'normal' if on else 'disabled'
        self.copy_clean.configure(state=state)
        self.copy_orig.configure(state=state)

    def do_clean(self):
        result = self.app.manual_clean(self.entry.get())
        self.show_result(result)

    def show_result(self, r):
        self.last = r
        if r['status'] == 'invalid':
            self.result_var.set('')
            self.note_var.set(r['summary'])
            self.set_result_buttons(False)
            return
        self.result_var.set(r['cleaned'])
        parts = [r['summary']]
        if r['removed']:
            parts.append('Removed: ' + ', '.join(x['name'] for x in r['removed']) + '.')
        for f in r['flags']:
            parts.append(f['message'])
        self.note_var.set(' '.join(parts))
        self.set_result_buttons(True)

    def copy(self, which):
        if self.last and self.last['status'] != 'invalid':
            self.app.copy_text(self.last[which])

    def selected(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.app.history.items):
            return None
        return self.app.history.items[sel[0]]

    def show_entry(self):
        e = self.selected()
        self.orig_var.set(e['original'] if e else '')
        self.clean_var.set(e['cleaned'] if e else '')
        state = 'normal' if e else 'disabled'
        self.h_orig.configure(state=state)
        self.h_clean.configure(state=state)

    def copy_history(self, which):
        e = self.selected()
        if e:
            self.app.copy_text(e[which])

    def refresh_history(self):
        self.listbox.delete(0, 'end')
        for e in self.app.history.items:
            self.listbox.insert('end', self.app.history.label(e))
        if self.settings()['keep_history']:
            self.history_title.set('History since Link Guard started (%d)' % len(self.app.history.items))
        else:
            self.history_title.set('History is off')
        self.show_entry()

    def set_status(self, text):
        self.status_var.set(text)

    def about(self):
        messagebox.showinfo(
            'About Link Guard',
            'Link Guard %s\n\nStrips tracking junk from links. Everything happens on this computer; '
            'it never connects to the sites in your links, so it cannot unwrap short links.\n\n'
            'The history lives in memory only and disappears when Link Guard quits.' % __version__,
            parent=self.root)
