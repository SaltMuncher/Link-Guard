import json
import os
import tempfile

import engine
from . import paths

DEFAULTS = {
    'clipboard_monitor': True,
    'autostart': True,
    'warn_clipboard': True,
    'keep_history': True,
    'always_on_top': True,
    'diagnostic_log': False,
    'first_run': True,
}

_rules_cache = {'mtime': None, 'rules': None}


def _settings_path():
    return paths.config_dir() / 'config.json'


def load():
    data = dict(DEFAULTS)
    try:
        with open(_settings_path(), encoding='utf-8') as f:
            stored = json.load(f)
        for key, default in DEFAULTS.items():
            if isinstance(stored.get(key), bool):
                data[key] = stored[key]
    except (OSError, ValueError, AttributeError):
        pass
    return data


def save(settings):
    target = _settings_path()
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump({k: bool(settings[k]) for k in DEFAULTS}, f, indent=2)
    os.replace(tmp, target)


def custom_rules_path():
    return paths.config_dir() / 'custom_rules.json'


def get_rules():
    base = _rules_cache.get('base')
    if base is None:
        base = engine.load_rules()
        _rules_cache['base'] = base
    path = custom_rules_path()
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        mtime = None
    if _rules_cache['rules'] is not None and _rules_cache['mtime'] == mtime:
        return _rules_cache['rules']
    rules = base
    if mtime is not None:
        try:
            with open(path, encoding='utf-8') as f:
                rules = engine.merge_rules(base, json.load(f))
        except (OSError, ValueError):
            rules = base
    _rules_cache['mtime'] = mtime
    _rules_cache['rules'] = rules
    return rules
