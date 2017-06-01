# -*- coding: utf-8 -*-

# the Network API plugin parses this dict: it maps request paths to (anonymous)
# functions called whenever the corresponding path is requested

# the functions should take three arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second are the query arguments (if
# any) as parsed from the request, the third is the content body of the request

# the functions should return either None or a list of three elements:
# 1. the HTTP status to be sent back to the client
# 2. the response body
# 3. a list of (field, value) tuples to be added to the HTTP response header

# the latter two can be None, in which case only the HTTP status is sent back.
# when the function returns None instead of a list, a 200 OK status is assumed.

network_api_functions = {
    # http://qgis.org/api/classQgisInterface.html
    '/qgis/defaultStyleSheetOptions': lambda iface, _, _2: [200, str(iface.defaultStyleSheetOptions())],
    # http://qgis.org/api/classQgsMapCanvas.html
    '/qgis/mapCanvas/zoomIn': lambda iface, _, _2: iface.mapCanvas().zoomIn(),
    '/qgis/mapCanvas/zoomOut': lambda iface, _, _2: iface.mapCanvas().zoomOut(),
    '/qgis/mapCanvas/zoomScale': lambda iface, args, _: iface.mapCanvas().zoomScale(float(args['scale'])),
    '/qgis/mapCanvas/zoomToFullExtent': lambda iface, _, _2: iface.mapCanvas().zoomToFullExtent()
}

import os
from tempfile import mkstemp
from PyQt4.QtGui import QPixmap

# the 'format' argument (default)
def get_canvas(iface, args, _):
    ext = args.get('format', 'png')
    tmpfile, tmpfilename = mkstemp('.' + ext)
    os.close(tmpfile)
    # if either argument is 
    pixmap = QPixmap(int(args.get('width', 0)), int(args.get('height', 0)))
    iface.mapCanvas().saveAsImage(tmpfilename, pixmap, ext)
    with open(tmpfilename, 'r') as content_file:
        imagedata = content_file.read()
#    os.remove(tmpfilename)
    return [200, imagedata, [('Content-Type', 'image/' + ext)]]

network_api_functions['/qgis/mapCanvas'] = get_canvas
