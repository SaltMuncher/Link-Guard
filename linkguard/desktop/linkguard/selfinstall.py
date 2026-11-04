import os
import shutil
import stat
import subprocess
from pathlib import Path

from . import autostart, ipc, paths

ICON_NAME = 'linkguard'


def installed_path():
    return paths.data_dir() / 'LinkGuard.AppImage'


def home():
    return Path(os.environ.get('HOME') or Path.home())


def entry_file():
    return home() / '.local' / 'share' / 'applications' / 'linkguard.desktop'


def icon_file():
    return home() / '.local' / 'share' / 'icons' / 'hicolor' / '256x256' / 'apps' / (ICON_NAME + '.png')


def running_from_installed():
    current = os.environ.get('APPIMAGE')
    return bool(current) and os.path.realpath(current) == os.path.realpath(str(installed_path()))


def install(appimage):
    target = installed_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.path.realpath(appimage) != os.path.realpath(str(target)):
        tmp = target.with_suffix('.tmp')
        shutil.copy2(appimage, tmp)
        tmp.chmod(tmp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(tmp, target)
    icon = paths.resource('assets/linkguard.png')
    if icon.exists():
        icon_file().parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon, icon_file())
    entry_file().parent.mkdir(parents=True, exist_ok=True)
    entry_file().write_text(
        '[Desktop Entry]\nType=Application\nName=Link Guard\n'
        'Comment=Strips tracking junk from links\n'
        'Exec=' + autostart.desktop_exec([str(target)]) + '\n'
        'Icon=' + ICON_NAME + '\nTerminal=false\nCategories=Utility;Network;\n',
        encoding='utf-8')
    autostart.enable([str(target), '--background'])
    return target


def uninstall():
    ipc.request({'type': 'quit'}, 2)
    autostart.disable()
    for f in (entry_file(), icon_file(), installed_path()):
        try:
            f.unlink()
        except FileNotFoundError:
            pass


def start_installed():
    subprocess.Popen([str(installed_path())], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
