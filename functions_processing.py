# -*- coding: utf-8 -*-

# network api functions to be added to the call path registry
#
# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object.
#
# the functions should return an instance of NetworkAPIResult

from .functions import qgis_layer_by_id
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
    # parse string into description/name pairs and remove blank lines
    # FIXME algorithms might have a -> sequence in their description
    # (grass:v.out.pov and grass7:v.out.pov in particular)
    algs = [re.split('-+>', alg, maxsplit=1) for alg in algs if alg]
    # turn into dictionary
    return { a[1]: a[0] for a in algs }

@networkapi('/qgis/processing/alglist')
def processing_alglist(_, request):
    """Retrieve names and descriptions of available Processing algorithms.

    HTTP query arguments:
        search (optional): if provided, results are limited to algorithms whose name or description contains the given string

    Returns:
        A JSON object with a name: description pair for every algorithm
    """
    # the optional argument filters algorithms based on their description
    return NetworkAPIResult(parse_processing_algorithms(request.args.get('search')))

@networkapi('/qgis/processing/alghelp')
def processing_alghelp(_, request):
    """Retrieve arguments and usage information of a Processing algorithm.

    HTTP query arguments:
        alg (string): the name of the algorithm for which to show the help

    Returns:
        An array of strings describing the algorithm as well as its arguments.
    """
    with GetStdOut() as alghelp:
        processing.alghelp(request.args['alg'])
    # strip parameter-initial tabs and remove blank lines
    return NetworkAPIResult([ line.strip() for line in alghelp if line])

@networkapi('/qgis/processing/algoptions')
def processing_algoptions(_, request):
    """Retrieve arguments and usage information of a Processing algorithm.

    HTTP query arguments:
        alg (string): the name of the algorithm for which to show the options

    Returns:
        An array of strings describing the algorithm as well as its arguments.
    """
    with GetStdOut() as algoptions:
        processing.algoptions(request.args['alg'])
    # strip parameter-initial tabs and remove blank lines
    return NetworkAPIResult([ line.strip() for line in algoptions if line])

# for layer arguments, processing only accepts the actual layer objects,
# references to the file or other layer source provider strings. therefore,
# if any of the arguments passed is a valid qgis layer id, resolve to the
# actual layer object (but revert to the string if non-existent)
def possible_qgis_layer(arg):
    try:
        return qgis_layer_by_id(arg)
    except KeyError:
        return arg

@networkapi('/qgis/processing/runalg')
def processing_runalg(_, request):
    """Run a Processing algorithm

    The arguments to the processing algorithm should be passed in JSON format in the POST body of the request, and the request MUST specify 'Content-Type: application/json' in its header. The body should either be a simple JSON array (passed to the algorithm as positional arguments in that order) or as a JSON object containing all desired arguments as 'name: value' pairs.

    Arguments which refer to input data sets can either be specified by their QGIS provider string, or also by passing their QGIS layer id.

    HTTP query arguments:
        alg (string): the name of the algorithm to run

    Returns:
        The result of invoking the processing algorithm with the given arguments
    """
    with GetStdOut() as algoutput:
        # JSON POST body is automatically parsed by server
        # check if arguments are given as a simple array, or with their
        # argument names in a JSON object (which arrives here as a dict)

        # for how to pass the different argument types, see:
        # https://docs.qgis.org/2.2/en/docs/user_manual/processing/console.html#calling-algorithms-from-the-python-console
        if isinstance(request.headers.get_payload(), dict):
            args = {k: possible_qgis_layer(v) for k, v in request.headers.get_payload().iteritems()}
            # pass named argument dict to make use of default values
            result = processing.runalg(request.args['alg'], args)

        else:
            args = [possible_qgis_layer(arg) for arg in request.headers.get_payload()]
            # variable length argument list gets unpacked with *
            result = processing.runalg(request.args['alg'], *args)

    # if result is None, processing has probably written some error message to stdout
    return NetworkAPIResult(result or algoutput)
