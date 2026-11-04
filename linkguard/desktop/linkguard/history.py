from datetime import datetime

LIMIT = 200


class History:
    def __init__(self, limit=LIMIT):
        self.limit = limit
        self.items = []
        self.listeners = []

    def _changed(self):
        for fn in self.listeners:
            fn()

    def add(self, source, result):
        entry = {
            'time': datetime.now(),
            'source': source,
            'status': result['status'],
            'host': result['host'] or '',
            'original': result['original'],
            'cleaned': result['cleaned'],
            'removed': len(result['removed']),
            'flags': [f['code'] for f in result['flags']],
        }
        self.items.insert(0, entry)
        del self.items[self.limit:]
        self._changed()

    def clear(self):
        self.items = []
        self._changed()

    def label(self, entry):
        stamp = entry['time'].strftime('%H:%M:%S')
        what = {'cleaned': 'cleaned', 'attention': 'flagged', 'clean': 'no change'}.get(entry['status'], entry['status'])
        where = 'typed' if entry['source'] == 'manual' else 'copied'
        extra = '  (%d removed)' % entry['removed'] if entry['removed'] else ''
        return '%s  %-9s %-7s %s%s' % (stamp, what, where, entry['host'], extra)
