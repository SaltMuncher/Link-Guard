import argparse
import os
import sys

from . import ipc


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog='linkguard', description='Link Guard')
    parser.add_argument('--background', action='store_true', help='start without showing the window')
    parser.add_argument('--quit', action='store_true', help='ask a running Link Guard to quit')
    parser.add_argument('--check-clipboard', action='store_true', help='print clipboard diagnostics')
    parser.add_argument('--run', action='store_true', help='AppImage: run in place without installing')
    parser.add_argument('--uninstall', action='store_true', help='AppImage: remove the installed copy')
    args = parser.parse_args(argv)

    if args.quit:
        ipc.request({'type': 'quit'}, 2)
        return 0

    appimage = os.environ.get('APPIMAGE')
    if appimage:
        from . import selfinstall
        if args.uninstall:
            selfinstall.uninstall()
            print('Link Guard was removed.')
            return 0
        if not args.run and not selfinstall.running_from_installed():
            if selfinstall.old_version_present():
                if not selfinstall.ask_remove_old():
                    return 0
                selfinstall.remove_old()
            selfinstall.install(appimage)
            selfinstall.start_installed()
            return 0

    if args.check_clipboard:
        import tkinter
        from . import clipboardio
        root = tkinter.Tk()
        root.withdraw()
        print(clipboardio.check(root))
        return 0

    if ipc.ping():
        if not args.background:
            ipc.request({'type': 'show'}, 2)
        return 0

    try:
        from .app import App
    except ImportError as exc:
        sys.stderr.write('Link Guard needs Tk for Python (%s).\n'
                         'Fedora: sudo dnf install python3-tkinter\n' % exc)
        return 1
    try:
        App(background=args.background).run()
    except ipc.AlreadyRunning:
        return 0
    return 0
