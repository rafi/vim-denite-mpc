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
        self.kind = 'mpc'
        self.__cache = {}
        self.vars = {
            'host': 'localhost',
            'port': 6600,
            'min_cache_files': 5000,
            'timeout': 2.0,
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
                'albumartist': '{albumartist} - {album} ({date})',
                'title': '{track} {artist} - {title}',
            },
            'targets': {
                'date': 'album',
                'genre': 'album',
                'artist': 'album',
                'albumartist': 'album',
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

        self.__status = self.vim.vars.get('denite_mpc_status', {})
        self.__playlist = self.vim.vars.get('denite_mpc_playlist', [])
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
            return self.__async_gather_candidates(context, 0.5)

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
            ' '.join(['"{}"'.format(a.replace('"', '\\"'))
                      for a in context['args']])).strip()

        # Use cache if hash exists
        if self.__hash in self.__cache:
            return self.__cache[self.__hash]

        commands = [command]
        if not self.__playlist:
            commands.insert(0, 'playlist')
        if not self.__status:
            commands.insert(0, 'status')

        # Open socket and send command
        self.__current_candidates = []
        self.__sock = Socket(
            self.vars['host'],
            self.vars['port'],
            commands,
            context,
            self.vars['timeout'])

        sleep(0.1)
        return self.__async_gather_candidates(context, self.vars['timeout'])

    def _sort(self, items):
        """ Sort dates with newer first and track title numbers """
        return sorted(
            items,
            key=itemgetter('word'),
            reverse=self.__entity == 'date')

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
        status_consumed = bool(self.__status)
        for line in lines:
            if line == 'OK' and not status_consumed:
                self.vim.vars['denite_mpc_status'] = self.__status
                status_consumed = True
                continue

            parts = line.split(': ', 1)
            if len(parts) < 2 or not parts[1]:
                continue
            key = parts[0].lower()
            val = parts[1]

            # Parse status and playlist
            if not status_consumed:
                self.__status[key] = val
                continue
            elif key.endswith(':file'):
                self.__playlist.append(val)
                continue

            # Parse object metadata
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

        if self.__playlist:
            self.vim.vars['denite_mpc_playlist'] = self.__playlist

        # Sort candidates if applicable, and add to the global collection
        if candidates:
            candidates = self._sort(candidates)
            self.__current_candidates += candidates

        # Cache items if there are more than the cache threshold
        if len(self.__current_candidates) >= self.vars['min_cache_files']:
            self.__cache[self.__hash] = self.__current_candidates
        return candidates

    def _parse_candidate(self, item):
        """ Returns a dict representing the item's candidate schema """
        # Collect a metadata dict to be used for customizable formatting.
        # - If 'Albumartist' is empty, use 'Artist' instead
        # - Track number receives a leading-zero
        meta = {x: item.get(x, '') for x in self.vars['tags']}

        if 'albumartist' in meta and not meta.get('albumartist'):
            meta['albumartist'] = item.get('artist')

        if meta['track']:
            meta['track'] = meta['track'].split('/')[0].zfill(2)

        if self.__formatter:
            word = self.__formatter.format(**meta)
        else:
            word = item.get(self.__entity, '')

        candidate = {'meta__{}'.format(x): item.get(x)
                     for x in self.vars['tags'] if item.get(x)}
        candidate.update({'word': word, 'mpc__kind': self.__entity})
        return candidate
