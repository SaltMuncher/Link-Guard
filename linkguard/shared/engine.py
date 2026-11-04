import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

WS = re.compile(r'[\u0000-\u0020\u007f-\u00a0\u1680\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]')
URL_RE = re.compile(r'^([A-Za-z][A-Za-z0-9+.\-]*)://([^/?#]*)([^?#]*)(?:\?([^#]*))?(?:#(.*))?$')
SCHEME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*://')
BAD_PCT = re.compile(r'%(?![0-9a-fA-F]{2})')
CANON_IPV4 = re.compile(r'^(0|[1-9][0-9]{0,2})(\.(0|[1-9][0-9]{0,2})){3}$')
NUMERIC_LABEL = re.compile(r'^(0x[0-9a-f]*|[0-9]+)$')
LIST_KEYS = ('global_params', 'global_prefixes', 'shorteners', 'redirect_path_hints')
MAX_DEPTH = 3
MAX_STR = 200
MAX_ITEMS = 2000

MESSAGES = {
    'shortener': 'This is a URL shortener. Link Guard does not contact it, so the destination cannot be confirmed.',
    'redirect_param': 'This link redirects to another site named in its parameters ({host}). The destination was not verified.',
    'punycode': 'The host name uses international characters or punycode and can imitate another site.',
    'ip_host': 'The link points to an IP address instead of a host name.',
    'userinfo': 'The link contains a user name before the host, which can disguise the real destination.',
    'encoded_host': 'The host name contains percent-encoded characters.',
}


def load_rules(path=None):
    if path:
        path = Path(path)
    elif getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        path = Path(sys._MEIPASS) / 'rules.json'
    else:
        path = Path(__file__).with_name('rules.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _strings(name, value, nonempty=False):
    if (not isinstance(value, list) or (nonempty and not value) or len(value) > MAX_ITEMS
            or not all(isinstance(x, str) and 0 < len(x) <= MAX_STR for x in value)):
        raise ValueError(name + ' must be a list of non-empty strings')


def validate_custom(custom):
    if not isinstance(custom, dict):
        raise ValueError('custom rules must be an object')
    for key in LIST_KEYS + ('keep_params',):
        _strings(key, custom.get(key, []))
    domains = custom.get('domains', [])
    if not isinstance(domains, list) or len(domains) > MAX_ITEMS:
        raise ValueError('domains must be a list')
    for d in domains:
        if not isinstance(d, dict):
            raise ValueError('each domain entry must be an object')
        _strings('hosts', d.get('hosts'), nonempty=True)
        for key in ('strip', 'strip_prefixes', 'path_strip'):
            _strings(key, d.get(key, []))
        u = d.get('unwrap')
        if u is not None:
            if not isinstance(u, dict) or not isinstance(u.get('path_prefix'), str):
                raise ValueError('unwrap needs a path_prefix')
            _strings('unwrap params', u.get('params'), nonempty=True)


def merge_rules(base, custom):
    validate_custom(custom)
    out = dict(base)
    for key in LIST_KEYS:
        out[key] = list(base.get(key, [])) + [x.lower() for x in custom.get(key, [])]
    out['keep_params'] = list(base.get('keep_params', [])) + [x.lower() for x in custom.get('keep_params', [])]
    out['domains'] = list(base.get('domains', [])) + list(custom.get('domains', []))
    return out


def normalize_slashes(s):
    """Browsers treat backslash as a slash in http(s) URLs, up to the query or fragment."""
    m = re.search(r'[?#]', s)
    i = m.start() if m else len(s)
    return s[:i].replace('\\', '/') + s[i:]


def decode_name(s):
    s = s.replace('+', ' ')

    def sub(m):
        n = int(m.group(1), 16)
        return chr(n) if n < 128 else m.group(0)
    return re.sub(r'%([0-9a-fA-F]{2})', sub, s)


def decode_value(v):
    if BAD_PCT.search(v):
        return None
    try:
        return unquote(v, errors='strict')
    except UnicodeDecodeError:
        return None


def host_matches(host, pattern):
    pattern = pattern.lower()
    if pattern.endswith('.*'):
        base = re.escape(pattern[:-2])
        return re.search(r'(^|\.)' + base + r'\.[a-z]{2,3}(\.[a-z]{2})?$', host) is not None
    return host == pattern or host.endswith('.' + pattern)


def split_authority(auth):
    userinfo = None
    hostport = auth
    if '@' in auth:
        userinfo, _, hostport = auth.rpartition('@')
    if hostport.startswith('['):
        end = hostport.find(']')
        if end < 0:
            return None
        host = hostport[:end + 1]
        rest = hostport[end + 1:]
        if rest and not re.match(r'^:[0-9]*$', rest):
            return None
    else:
        host, _, port = hostport.partition(':')
        if port and not re.match(r'^[0-9]+$', port):
            return None
    host = host.lower().rstrip('.')
    if not host or '\\' in host:
        return None
    return {'host': host, 'userinfo': userinfo}


def parse(url):
    m = URL_RE.match(url)
    if not m:
        return None
    scheme, auth, path, query, fragment = m.groups()
    if scheme.lower() not in ('http', 'https'):
        return None
    a = split_authority(auth)
    if not a:
        return None
    return {'scheme': scheme, 'auth': auth, 'path': path, 'query': query, 'fragment': fragment,
            'host': a['host'], 'userinfo': a['userinfo']}


def is_private_ipv4(host):
    p = [int(x) for x in host.split('.')]
    if any(x > 255 for x in p):
        return False
    return (p[0] in (10, 127) or (p[0] == 192 and p[1] == 168) or
            (p[0] == 172 and 16 <= p[1] <= 31) or (p[0] == 169 and p[1] == 254))


def host_flags(parts, rules):
    host = parts['host']
    flags = []
    if parts['userinfo'] is not None:
        flags.append('userinfo')
    if host.startswith('xn--') or '.xn--' in host or re.search(r'[^\x00-\x7f]', host):
        flags.append('punycode')
    if '%' in host:
        flags.append('encoded_host')
    if host.startswith('['):
        if host != '[::1]':
            flags.append('ip_host')
    elif CANON_IPV4.match(host):
        if not is_private_ipv4(host):
            flags.append('ip_host')
    elif NUMERIC_LABEL.match(host.rsplit('.', 1)[-1]):
        flags.append('ip_host')
    for s in rules.get('shorteners', []):
        if host_matches(host, s):
            flags.append('shortener')
            break
    return flags


def segments(query):
    return [] if query is None else query.split('&')


def seg_name(seg):
    return decode_name(seg.split('=', 1)[0])


def find_redirect_param(parts, rules):
    hints = set(rules.get('redirect_path_hints', []))
    segs = [s for s in parts['path'].lower().split('/') if s]
    if not any(s in hints for s in segs):
        return None
    for seg in segments(parts['query']):
        if '=' not in seg:
            continue
        value = decode_value(seg.split('=', 1)[1])
        if value is None:
            continue
        target = parse(normalize_slashes(value)) if re.match(r'^https?:', value, re.I) else None
        if target and target['host'] != parts['host']:
            return target['host']
    return None


def find_unwrap(parts, rules):
    path = parts['path'].lower()
    for d in rules.get('domains', []):
        u = d.get('unwrap')
        if not u or not any(host_matches(parts['host'], h) for h in d['hosts']):
            continue
        if not path.startswith(u['path_prefix'].lower()):
            continue
        for name in u['params']:
            for seg in segments(parts['query']):
                if '=' in seg and seg_name(seg).lower() == name.lower():
                    value = decode_value(seg.split('=', 1)[1])
                    if value is not None and re.match(r'^https?:', value, re.I):
                        return value, parts['host']
    return None


def build_strip(parts, rules):
    exact = {}
    prefixes = []
    for p in rules.get('global_params', []):
        exact[p.lower()] = 'Known tracking parameter'
    for p in rules.get('global_prefixes', []):
        prefixes.append((p.lower(), 'Tracking parameter prefix ' + p))
    path_strip = []
    for d in rules.get('domains', []):
        hit = next((h for h in d['hosts'] if host_matches(parts['host'], h)), None)
        if hit is None:
            continue
        for p in d.get('strip', []):
            exact[p.lower()] = 'Tracking parameter for ' + hit
        for p in d.get('strip_prefixes', []):
            prefixes.append((p.lower(), 'Tracking parameter for ' + hit))
        path_strip.extend(d.get('path_strip', []))
    for p in rules.get('keep_params', []):
        exact.pop(p.lower(), None)
    keep = set(rules.get('keep_params', []))
    return exact, prefixes, path_strip, keep


def strip_reason(name, exact, prefixes, keep):
    n = name.lower()
    if n in keep:
        return None
    if n in exact:
        return exact[n]
    for prefix, reason in prefixes:
        if n.startswith(prefix):
            return reason
    return None


def result(status, original, cleaned, host, removed, flags, summary):
    return {'status': status, 'original': original, 'cleaned': cleaned, 'host': host,
            'removed': removed, 'flags': flags, 'summary': summary}


def invalid(original, reason):
    return result('invalid', original, original, None, [], [], reason)


def safe_analyze(text, rules, assume_https=False):
    """Use this from the GUI and clipboard watcher: a bad rule can never crash or hang the caller."""
    try:
        return analyze(text, rules, assume_https)
    except Exception:
        return invalid(text if isinstance(text, str) else '', 'This link could not be analysed.')


def analyze(text, rules, assume_https=False, _depth=0):
    s = text.strip() if isinstance(text, str) else ''
    if not s:
        return invalid(s, 'No URL was provided.')
    if WS.search(s):
        return invalid(s, 'The URL contains spaces or control characters.')
    s = normalize_slashes(s)
    if assume_https and not SCHEME_RE.match(s):
        s = 'https://' + s
    parts = parse(s)
    if parts is None:
        if re.match(r'^[A-Za-z][A-Za-z0-9+.\-]*:', s) and not re.match(r'^https?:', s, re.I) and '://' in s:
            return invalid(s, 'Only http and https links are supported.')
        return invalid(s, 'The URL is malformed or has no valid host.')

    flags = [{'code': c, 'message': MESSAGES[c]} for c in host_flags(parts, rules)]

    if _depth < MAX_DEPTH:
        unwrapped = find_unwrap(parts, rules)
        if unwrapped:
            inner = analyze(normalize_slashes(unwrapped[0]), rules, False, _depth + 1)
            if inner['status'] != 'invalid':
                removed = [{'name': 'redirect wrapper (' + unwrapped[1] + ')',
                            'reason': 'Replaced by the destination encoded in the link'}] + inner['removed']
                status = 'attention' if inner['flags'] else 'cleaned'
                summary = inner['summary'] if inner['flags'] else 'Redirect wrapper replaced by its encoded destination.'
                return result(status, s, inner['cleaned'], inner['host'], removed, inner['flags'], summary)

    exact, prefixes, path_strip, keep = build_strip(parts, rules)
    removed = []
    seen = set()

    def note(name, reason):
        k = name.lower()
        if k not in seen:
            seen.add(k)
            removed.append({'name': name, 'reason': reason})

    path = parts['path']
    for prefix in path_strip:
        segs = path.split('/')
        idx = len(segs) - 1
        if segs[idx] == '' and idx > 0:
            idx -= 1
        if idx > 0 and segs[idx].lower().startswith(prefix.lower()):
            note('path ' + segs[idx], 'Tracking path segment')
            del segs[idx]
            path = '/'.join(segs)

    query = parts['query']
    changed_query = False
    if query is not None:
        kept = []
        for seg in segments(query):
            name = seg_name(seg)
            reason = strip_reason(name, exact, prefixes, keep)
            if reason:
                note(name, reason)
                changed_query = True
            else:
                kept.append(seg)
        if changed_query:
            query = '&'.join(kept)

    if not flags:
        host = find_redirect_param(parts, rules)
        if host:
            flags.append({'code': 'redirect_param', 'message': MESSAGES['redirect_param'].format(host=host)})

    cleaned = parts['scheme'] + '://' + parts['auth'] + path
    if query is not None and not (changed_query and query == ''):
        cleaned += '?' + query
    if parts['fragment'] is not None:
        cleaned += '#' + parts['fragment']

    if flags:
        status = 'attention'
        summary = 'This link needs your attention.'
    elif removed:
        status = 'cleaned'
        summary = 'Removed %d tracking item(s).' % len(removed)
    else:
        status = 'clean'
        summary = 'No known tracking parameters found. This does not mean the link is safe.'
    return result(status, s, cleaned, parts['host'], removed, flags, summary)