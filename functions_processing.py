# -*- coding: utf-8 -*-

# network api functions to be added to the call path registry
#
# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object.
#
# the functions should return an instance of NetworkAPIResult

from .registry import networkapi, NetworkAPIResult

# mock Python 3.4's contextlib.redirect_stdout()
from StringIO import StringIO
import sys

class GetStdOut(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout

# FIXME importing processing from within the plugin does not currently work
# loading the plugin after manually calling 'import processing' in the QGIS
# python console *does* work

from processing.core.Processing import Processing
# TODO check if initialisation succeeds, if not maybe plugin is not enabled, in
# which case these API paths should NOT be exposed by the plugin (but what if
# processing is enabled by the user later...?)
Processing.initialize()
import processing

import re
def parse_processing_algorithms(arg=None):
    """Parse available processing algorithms from alglist()'s console output"""
    with GetStdOut() as algs:
        processing.alglist(arg)
    # FIXME algorithms might have a -> sequence in their description
    # (grass:v.out.pov and grass7:v.out.pov in particular)
    algs = [re.split('-+>', alg, maxsplit=1) for alg in algs if alg]
    return { a[1]: a[0] for a in algs }

@networkapi('/processing/alglist')
def processing_alglist(_, request):
    """Retrieve names and descriptions of available Processing algorithms"""
    # the optional argument filters algorithms based on their description
    return NetworkAPIResult(parse_processing_algorithms(request.args.get('search')))

@networkapi('/processing/alghelp')
def processing_alghelp(_, request):
    with GetStdOut() as alghelp:
        processing.alghelp(request.args['alg'])
    return NetworkAPIResult([ line.strip() for line in alghelp if line])
