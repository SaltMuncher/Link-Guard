import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform.startswith('win')
FROZEN = bool(getattr(sys, 'frozen', False))


def _private_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    if not IS_WINDOWS:
        os.chmod(path, 0o700)
    return path


def config_dir():
    override = os.environ.get('LINKGUARD_CONFIG_DIR')
    if override:
        return _private_dir(Path(override))
    if IS_WINDOWS:
        base = os.environ.get('APPDATA') or str(Path.home() / 'AppData' / 'Roaming')
        return _private_dir(Path(base) / 'LinkGuard')
    base = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return _private_dir(Path(base) / 'linkguard')


def data_dir():
    if IS_WINDOWS:
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        return Path(base) / 'LinkGuard'
    base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / 'linkguard'


def root_dir():
    if FROZEN:
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def resource(name):
    if FROZEN and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / name
    return Path(__file__).resolve().parents[2] / name
