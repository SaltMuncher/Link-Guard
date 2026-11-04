import json
import os
import secrets
import threading
from multiprocessing.connection import AuthenticationError, Client, Listener
from pathlib import Path

from . import paths

MAX_MESSAGE = 65536


class AlreadyRunning(Exception):
    pass


def family():
    return 'AF_PIPE' if paths.IS_WINDOWS else 'AF_UNIX'


def address():
    override = os.environ.get('LINKGUARD_IPC_ADDRESS')
    if override:
        return override
    if paths.IS_WINDOWS:
        return r'\\.\pipe\linkguard-' + (os.environ.get('USERNAME') or 'user')
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    base = Path(runtime) if runtime and os.path.isdir(runtime) else paths.config_dir()
    return str(base / 'linkguard.sock')


def authkey():
    path = paths.config_dir() / 'ipc.key'
    try:
        data = path.read_bytes()
        if len(data) >= 16:
            return data
    except OSError:
        pass
    data = secrets.token_bytes(32)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data)
    return data


def request(message, timeout=5.0):
    try:
        conn = Client(address(), family(), authkey=authkey())
    except (OSError, EOFError, AuthenticationError):
        return None
    try:
        conn.send_bytes(json.dumps(message).encode('utf-8'))
        if timeout is not None and not conn.poll(timeout):
            return None
        return json.loads(conn.recv_bytes(MAX_MESSAGE))
    except (OSError, EOFError, ValueError):
        return None
    finally:
        conn.close()


def ping(timeout=2.0):
    reply = request({'type': 'ping'}, timeout)
    return bool(reply and reply.get('ok'))


class Server:
    def __init__(self, handler):
        self.handler = handler
        self.listener = None
        self.closed = False

    def start(self):
        addr = address()
        if family() == 'AF_UNIX' and os.path.exists(addr):
            if ping():
                raise AlreadyRunning()
            os.unlink(addr)
        self.listener = Listener(addr, family(), authkey=authkey())
        if family() == 'AF_UNIX':
            os.chmod(addr, 0o600)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def close(self):
        self.closed = True
        if self.listener is not None:
            try:
                self.listener.close()
            except OSError:
                pass

    def _accept_loop(self):
        while not self.closed:
            try:
                conn = self.listener.accept()
            except AuthenticationError:
                continue
            except (OSError, EOFError):
                if self.closed:
                    return
                continue
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        try:
            if not conn.poll(5):
                return
            message = json.loads(conn.recv_bytes(MAX_MESSAGE))
            if not isinstance(message, dict):
                reply = {'ok': False, 'error': 'bad_request'}
            else:
                reply = self.handler(message)
            conn.send_bytes(json.dumps(reply).encode('utf-8'))
        except (OSError, EOFError):
            pass
        except Exception:
            try:
                conn.send_bytes(b'{"ok": false, "error": "internal"}')
            except (OSError, EOFError):
                pass
        finally:
            conn.close()
