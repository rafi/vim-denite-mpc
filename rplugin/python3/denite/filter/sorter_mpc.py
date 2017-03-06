# ============================================================================
# FILE: sorter_mpc.py
# AUTHOR: Rafael Bodill <justRafi at gmail.com>
# License: MIT license
# ============================================================================

from operator import itemgetter
from .base import Base


class Filter(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'sorter_mpc'
        self.description = 'unite-mpc sorter'

    def filter(self, context):
        if context['__entity'] == 'playlist':
            # Skip sort for playlist display
            return context['candidates']

        # Sort alphabetically, and reverse list for dates
        return sorted(
            context['candidates'],
            key=itemgetter('word'),
            reverse=context['__entity'] == 'date')
