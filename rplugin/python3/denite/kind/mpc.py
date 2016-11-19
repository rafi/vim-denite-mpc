# ============================================================================
# FILE: mpc.py
# AUTHOR: Rafael Bodill <justRafi at gmail.com>
# License: MIT license
# ============================================================================

import re
from .base import Base
from ..source.mpc import Source
from ..socket import Socket
from ..util import error


class Kind(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'mpc'
        self.default_action = 'list'

    def action_list(self, context):
        self._get_vars(context)
        for candidate in context['targets']:
            mpc_kind = candidate.get('mpc__kind')
            target_kind = self._vars['targets'].get(mpc_kind)
            if mpc_kind == 'title':
                self.action_play(context)
                continue

            args = []
            for key, value in self._metadata(candidate).items():
                args.append(key)
                args.append(self._escape(value))
            if args:
                # Concat the candidate's command to be executed
                cmd = 'Denite mpc:{}:{}'.format(target_kind, ':'.join(args))
                self.vim.command(cmd)
                continue
            self.error('Candidate is missing metadata: {}'.format(candidate))

    def action_play(self, context):
        self._get_vars(context)
        cmds = self._get_commands('findadd', context)
        self._send(cmds, context)
        next = len(self._playlist())
        self._send(['play {}'.format(next)], context)
        self._kill()

    def action_add(self, context):
        self._get_vars(context)
        cmds = self._get_commands('findadd', context)
        self._send(cmds, context)
        self._kill()

    def action_replace(self, context):
        self._get_vars(context)
        cmds = ['clear'] + self._get_commands('findadd', context) + ['play']
        self._send(cmds, context)
        self._kill()

    def _get_vars(self, context):
        # FIXME: Find a better way to get the full source vars
        custom = context['custom']['source'].get('mpc', {}).get('vars', {})
        self._vars = Source(self.vim).vars.copy()
        self._vars.update(custom)

    def _get_commands(self, command, context):
        cmds = []
        for candidate in context['targets']:
            args = [command]
            for key, value in self._metadata(candidate).items():
                args.append(key)
                args.append('"{}"'.format(self._escape(value)))
            cmds.append(' '.join(args))

        return cmds

    def _metadata(self, candidate):
        return {key[5:]: value for key, value in candidate.items()
                if value and key.startswith('meta_')}

    def _playlist(self):
        return self.vim.vars.get('denite_mpc_playlist', [])

    def _escape(self, s):
        """ Escape certain characters with backslash """
        if s:
            s = re.sub(r'(\\)', r'\\\\\\\1', s)
            s = re.sub(r'([:"\ ])', r'\\\1', s)
        return s

    def error(self, err):
        error(self.vim, err)

    def _send(self, commands, context):
        self.__sock = Socket(
            self._vars['host'],
            self._vars['port'],
            commands,
            context,
            self._vars['timeout'])

        return self.__sock.communicate(2.0)

    def _kill(self):
        self.vim.vars['denite_mpc_playlist'] = []
        self.vim.vars['denite_mpc_status'] = {}
        self.__sock.kill()
        self.__sock = None
