# ============================================================================
# FILE: mpc.py
# AUTHOR: Rafael Bodill <justRafi at gmail.com>
# License: MIT license
# ============================================================================

import re
from operator import itemgetter
from time import sleep

from .base import Base
from denite.socket import Socket


class Source(Base):
    """ MPD client source for Denite.nvim """

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'mpc'
        self.kind = 'command'
        self.__cache = {}
        self.vars = {
            'host': 'localhost',
            'port': 6600,
            'min_cache_files': 5000,
            'timeout': 5.0,
            'default_view': 'date',
            'tags': [
                'date', 'genre', 'title', 'album',
                'track', 'artist', 'albumartist'
            ],
            'formats': {
                'date': '{date}',
                'genre': '{genre}',
                'artist': '{artist}',
                'album': '{albumartist} - {album} ({date})',
                'title': '{track} {artist} - {title}',
            },
            'targets': {
                'date': 'album',
                'genre': 'album',
                'artist': 'album',
                'album': 'title',
                'title': None
            }
        }

    def on_init(self, context):
        self.__sock = None
        if len(context['args']) > 0:
            self.__entity = context['args'].pop(0)
        else:
            self.__entity = self.vars['default_view']

        self.__hash = '{} {}'.format(
            self.__entity, ' '.join(context['args'])).__hash__()

    def on_close(self, context):
        """ Kill the socket when source's window closes """
        if self.__sock:
            self.__sock.kill()
            self.__sock = None

    def gather_candidates(self, context):
        """ Initiate socket communicate """
        if self.__sock:
            return self.__async_gather_candidates(context, 1.0)

        if context['is_redraw']:
            self.__cache = {}

        # Find which tags we need according to the formatter string
        pattern = re.compile(r'{([\w]*)}')
        self.__formatter = self.vars['formats'].get(self.__entity)
        for field_name in re.findall(pattern, self.__formatter):
            if field_name != self.__entity:
                context['args'] += ['group', field_name]

        # Concat command to be sent to socket
        command = 'list "{}" {}'.format(
            self.__entity,
            ' '.join(['"{}"'.format(self._escape(a)) for a in context['args']]))

        # Use cache if hash exists
        if self.__hash in self.__cache:
            return self.__cache[self.__hash]

        # Open socket and send command
        self.__current_candidates = []
        self.__sock = Socket(
            self.vars['host'],
            self.vars['port'],
            command,
            context,
            self.vars['timeout'])

        return self.__async_gather_candidates(context, 2.0)

    def __async_gather_candidates(self, context, timeout):
        """ Collect all candidates from socket communication """

        lines = self.__sock.communicate(timeout=timeout)
        context['is_async'] = not self.__sock.eof()
        if self.__sock.eof():
            self.__sock = None
        if not lines:
            return []

        # Parse the socket output lines according to mpd's protocol
        candidates = []
        current = {}
        for line in lines:
            parts = line.split(': ', 1)
            if len(parts) < 2 or not parts[1]:
                continue

            key = parts[0].lower()
            val = parts[1]
            if key == self.__entity and current:
                candidates.append(self._parse_candidate(current))
                current = {}
            elif key in current:
                if isinstance(current[key], str):
                    current[key] = [current[key]]
                current[key].append(val)

            current[key] = val

        if current:
            candidates.append(self._parse_candidate(current))

        # Sort candidates if applicable, and add to the global collection
        candidates = self._apply_filters(candidates)
        self.__current_candidates += candidates

        # Cache items if there are more than the cache threshold
        if len(self.__current_candidates) >= self.vars['min_cache_files']:
            self.__cache[self.__hash] = self.__current_candidates
        return candidates

    def _escape(self, s):
        """ Escape certain characters with backslash """
        if s:
            s = re.sub(r'(\\)', r'\\\\\\\1', s)
            s = re.sub(r'([:"\ ])', r'\\\1', s)
        return s

    def _parse_candidate(self, item):
        """ Returns a dict representing the item's candidate schema """
        # Collect a metadata dict to be used for custom formatting.
        # - Artists displayed using 'Albumartist' or if empty, use 'Artist'
        # - Track number receives a leading-zero
        meta = {x: item.get(x) for x in self.vars['tags']}

        if 'albumartist' in meta and not meta.get('albumartist'):
            meta['albumartist'] = item.get('artist')

        if meta['track']:
            meta['track'] = meta['track'].split('/')[0].zfill(2)

        # Format the candidate human-friendly output
        if self.__formatter:
            word = self.__formatter.format(**meta)
        else:
            word = item.get(self.__entity, '')

        # Escape the meta key value to be sent later
        # to Denite, if candidate selected.
        value = self._escape(meta.get(self.__entity, ''))

        # Concat the candidate's command executed when selected
        source = ''
        target = self.vars['targets'].get(self.__entity)
        if target:
            source = 'Denite mpc:{}:{}:{}'.format(target, self.__entity, value)

        return {'word': word, 'action__command': source}

    def _apply_filters(self, items):
        """ Sort dates with newer first and track title numbers """
        if self.__entity == 'date':
            return sorted(items, key=itemgetter('word'), reverse=True)
        elif self.__entity == 'title':
            return sorted(items, key=itemgetter('word'))
        else:
            return items
