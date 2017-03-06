# ============================================================================
# FILE: mpc.py
# AUTHOR: Rafael Bodill <justRafi at gmail.com>
# License: MIT license
# ============================================================================

import os
import re

from .base import Base
from denite.socket import Socket


class Source(Base):
    """ MPD client source for Denite.nvim """

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'mpc'
        self.kind = 'mpc'
        self.syntax_name = 'deniteSource_mpc'
        self.matchers = ['matcher_fuzzy']
        self.sorters = ['sorter_mpc']
        self.__cache = {}

        self.vars = {
            'host': os.environ.get('MPD_HOST', 'localhost'),
            'port': os.environ.get('MPD_PORT', 6600),
            'min_cache_files': 5000,
            'timeout': 2.0,
            'default_view': 'artist',
            'tags': [
                'date', 'genre', 'title', 'album',
                'track', 'artist', 'albumartist', 'pos'
            ],
            'formats': {
                'date': '{date}',
                'genre': '{genre}',
                'artist': '{artist}',
                'album': '{albumartist} - {album} ({date})',
                'albumartist': '{albumartist} - {album} ({date})',
                'title': '{track} {artist} - {title}',
                'playlist': '{artist:19.19} {track:4.4} {title:25.25} '
                            '{album:>20.20} {date:^4.4} {genre}'
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
        if len(context['args']) > 0:
            self.__entity = context['args'].pop(0)
        else:
            self.__entity = self.vars['default_view']

        self.__current = {}
        self.__status = context.get('__status', {})
        self.__hash = '{} {}'.format(
            self.__entity, ' '.join(context['args'])).__hash__()

        context['__sock'] = None
        context['__status'] = self.__status
        context['__entity'] = self.__entity

    def on_close(self, context):
        """ Kill the socket when source's window closes """
        if context['__sock']:
            context['__sock'].kill()
            context['__sock'] = None

    def highlight_syntax(self):
        self.vim.command(
            'syntax region ' + self.syntax_name + ' start=// end=/$/ '
            'contains=deniteMatched contained')
        self.vim.command(
            'syntax match deniteSource_mpcCurrent /^\s*▶.*/ '
            ' contains=deniteSource_mpcMark containedin=' + self.syntax_name)
        self.vim.command(
            'syntax match deniteSource_mpcMark /^\s*▶/ conceal contained')
        self.vim.command(
            'highlight default link deniteSource_mpcCurrent Todo')

    def gather_candidates(self, context):
        """ Initiate socket communicate """
        if context['__sock']:
            return self.__async_gather_candidates(context, 0.03)

        if context['is_redraw']:
            self.__status = {}
            self.__cache = {}

        # Use cache if hash exists
        elif self.__hash in self.__cache:
            return self.__cache[self.__hash]

        # Concat command
        self.__formatter = self.vars['formats'].get(self.__entity)
        if self.__entity == 'playlist':
            command = 'playlistinfo'
        else:
            # Find which tags we need according to the formatter string
            pattern = re.compile(r'{([\w]*)}')
            for field_name in re.findall(pattern, self.__formatter):
                if field_name != self.__entity:
                    context['args'] += ['group', field_name]

            # Concat command to be sent to socket
            command = 'list "{}" {}'.format(
                self.__entity,
                ' '.join(['"{}"'.format(a.replace('"', '\\"'))
                         for a in context['args']])).strip()

        commands = []
        if not self.__status:
            commands.append('status')
        commands.append(command)

        # Open socket and send command
        self.__current_candidates = []
        context['__sock'] = Socket(
            self.vars['host'],
            self.vars['port'],
            commands,
            context,
            self.vars['timeout'])

        return self.__async_gather_candidates(context, self.vars['timeout'])

    def __async_gather_candidates(self, context, timeout):
        """ Collect all candidates from socket communication """
        lines = context['__sock'].communicate(timeout=timeout)
        context['is_async'] = not context['__sock'].eof()

        if context['__sock'].eof():
            context['__sock'] = None
        if not lines:
            return []

        # Parse the socket output lines according to mpd's protocol
        candidates = []
        current = {}
        separator = 'file' if self.__entity == 'playlist' else self.__entity
        status_consumed = bool(self.__status)
        for line in lines:
            if line == 'OK' and not status_consumed:
                status_consumed = True
                continue

            parts = line.split(': ', 1)
            if len(parts) < 2 or not parts[1]:
                continue
            key = parts[0].lower()
            val = parts[1]

            # Set current playing song info
            if self.__status and self.__status.get('state') == 'play' and \
               'id' in current and current['id'] == self.__status['songid']:
                self.__current = current

            # Parse status and object metadata
            if not status_consumed:
                self.__status[key] = val
                continue
            elif key == separator and current:
                candidates.append(self._parse_candidate(current))
                current = {}

            if key in current:
                if isinstance(current[key], str):
                    current[key] = [current[key]]
                current[key].append(val)
            else:
                current[key] = val

        if current:
            candidates.append(self._parse_candidate(current))

        if candidates:
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
        # - If current candidate is playing, mark 'current'
        meta = {x: item.get(x, '') for x in self.vars['tags']}

        if 'albumartist' in meta and not meta.get('albumartist'):
            meta['albumartist'] = item.get('artist')

        if self.__entity != 'playlist' and meta['track']:
            track = meta['track']
            total = None
            if meta['track'].find('/') > -1:
                track, total = track.split('/', 1)
            meta['track'] = track.zfill(len(total or '10'))

        if self.__formatter:
            formatter = self._calc_percentage(self.__formatter)
            word = formatter.format(**{k: str(v) for k, v in meta.items()})
        else:
            word = item.get(self.__entity, '')

        if self.__current and \
           {str(self.__current.get(x)) for x in ['artist', 'title', 'track']} \
           == {str(meta.get(x)) for x in ['artist', 'title', 'track']}:
            word = '▶' + word

        candidate = {'meta__{}'.format(x): item.get(x)
                     for x in self.vars['tags'] if item.get(x)}

        candidate.update({'word': word})
        return candidate

    def _calc_percentage(self, format):
        """ Compiles sizes from numbers in format, handled as percentage """
        winwidth = self.vim.call('winwidth', 0)
        pattern = r'([\<\>\.\:\^])(\d+)'

        def calc_percent(obj):
            percent = round(winwidth * (int(obj.group(2)) / 100))
            return obj.group(1) + str(percent)

        return re.sub(pattern, calc_percent, self.__formatter)
