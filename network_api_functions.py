# -*- coding: utf-8 -*-

# the Network API plugin parses this dict: it maps request paths to (anonymous)
# functions called whenever the corresponding path is requested

# the functions should take three arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second are the query arguments (if
# any) as parsed from the request as a dictionary (key=value pairs), the third
# is the content body of the request

# the functions should return either None or a list of up to three elements:
# 1. the HTTP status to be sent back to the client
# 2. the response body
# 3. a list of (field, value) tuples to be added to the HTTP response header
#
# the latter two can be None, in which case only the HTTP status is sent back.
# when the function returns None instead of a list, a 200 OK status is assumed.

from qgis.core import QgsMapLayerRegistry

network_api_functions = {
    # http://qgis.org/api/classQgisInterface.html
    '/qgis/defaultStyleSheetOptions': lambda iface, _, _2: [200, str(iface.defaultStyleSheetOptions())],

    # dict comprehension syntax only from python 2.7 onwards
    # TODO convert map layer type enum in string representation?
    '/qgis/mapLayers': lambda iface, _, _2: [200, {(name, layer.type()) for (name, layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems()}],

    # http://www.qgis.org/api/classQgsMapLayer.html
    '/qgis/editableLayers': lambda iface, _, _2: [200, iface.editableLayers()],
    # the following paths require an argument specifying the desired layer
    '/qgis/editableLayers/maximumScale': lambda iface, _, _2: None,

    # http://qgis.org/api/classQgsMapCanvas.html
    '/qgis/mapCanvas/magnificationFactor': lambda iface, _, _2: iface.mapCanvas().magnificationFactor(),
    '/qgis/mapCanvas/mapUnitsPerPixel': lambda iface, _, _2: iface.mapCanvas().mapUnitsPerPixel(),
    '/qgis/mapCanvas/scale': lambda iface, _, _2: iface.mapCanvas().scale(),
    '/qgis/mapCanvas/zoomIn': lambda iface, _, _2: iface.mapCanvas().zoomIn(),
    '/qgis/mapCanvas/zoomOut': lambda iface, _, _2: iface.mapCanvas().zoomOut(),
    '/qgis/mapCanvas/zoomScale': lambda iface, args, _: iface.mapCanvas().zoomScale(float(args['scale'])),
    '/qgis/mapCanvas/zoomToFullExtent': lambda iface, _, _2: iface.mapCanvas().zoomToFullExtent()
}

import os
from tempfile import mkstemp
from PyQt4.QtGui import QPixmap

# the 'format' argument (default 'png') can be any image format string
# supported by saveAsImage(), with the MIME type of the HTTP response simply
# set to 'image/' + format
def get_canvas(iface, args, _):
    ext = args.get('format', 'png')
    tmpfile, tmpfilename = mkstemp('.' + ext)
    os.close(tmpfile)

    # if either is unspecified or otherwise invalid, QGIS display size is used
    pixmap = QPixmap(int(args.get('width', 0)), int(args.get('height', 0)))
    if pixmap.isNull():
        pixmap = None

    iface.mapCanvas().saveAsImage(tmpfilename, pixmap, ext)
    with open(tmpfilename, 'r') as content_file:
        imagedata = content_file.read()
    os.remove(tmpfilename)
    # TODO QGIS also writes a 'world file' (same filename + 'w' at the end)?
    return [200, imagedata, [('Content-Type', 'image/' + ext)]]

network_api_functions['/qgis/mapCanvas'] = get_canvas
