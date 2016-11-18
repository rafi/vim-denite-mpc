# ============================================================================
# FILE: mpc.py
# AUTHOR: Rafael Bodill <justRafi at gmail.com>
# License: MIT license
# ============================================================================

from time import sleep
from .base import Base
from ..source.mpc import Source
from ..socket import Socket


class Kind(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'mpc'
        self.default_action = 'list'

    def action_list(self, context):
        target = context['targets'][0]
        self.vim.command(target['action__list'])

    def action_play(self, context):
        commands = self._parse_targets(context) + ['play']
        self._send(commands, context)
        self._kill()

    def action_add(self, context):
        commands = self._parse_targets(context)
        self._send(commands, context)
        self._kill()

    def action_replace(self, context):
        commands = ['clear'] + self._parse_targets(context)
        commands.append('play')
        self._send(commands, context)
        self._kill()

    def _parse_targets(self, context):
        commands = []
        for target in context['targets']:
            command = 'findadd'
            for key, value in target.items():
                if value and key.startswith('meta_'):
                    command += ' {} "{}"'.format(key[5:], value)

            commands.append(command)
        return commands

    def _send(self, commands, context):
        custom = context['custom']['source'].get('mpc', {}).get('vars', {})
        self._vars = Source(self.vim).vars.copy()
        self._vars.update(custom)

        self.__sock = Socket(
            self._vars['host'],
            self._vars['port'],
            commands,
            context,
            self._vars['timeout'])

        return self.__sock.communicate(timeout=self._vars['timeout'])

    def _kill(self):
        self.__sock.kill()
        self.__sock = None
