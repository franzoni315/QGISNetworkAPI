# -*- coding: utf-8 -*-

# the Network API plugin parses this dict: it maps request paths to (anonymous)
# functions called whenever the corresponding path is requested

# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object

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
    '/qgis/defaultStyleSheetOptions': lambda iface, _: [200, str(iface.defaultStyleSheetOptions())],

    # dict comprehension syntax only from python 2.7 onwards
    # TODO convert map layer type enum in string representation?
    '/qgis/mapLayers': lambda iface, _: [200, {(name, layer.type()) for (name, layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems()}],
    # addVectorLayer below

    # http://www.qgis.org/api/classQgsMapLayer.html
    '/qgis/editableLayers': lambda iface, _: [200, iface.editableLayers()],
    # the following paths require an argument specifying the desired layer
    '/qgis/editableLayers/maximumScale': lambda iface, _: None,

    # http://qgis.org/api/classQgsMapCanvas.html
    '/qgis/mapCanvas/magnificationFactor': lambda iface, _: iface.mapCanvas().magnificationFactor(),
    '/qgis/mapCanvas/mapUnitsPerPixel': lambda iface, _: iface.mapCanvas().mapUnitsPerPixel(),
    '/qgis/mapCanvas/scale': lambda iface, _: [200, iface.mapCanvas().scale()],
    '/qgis/mapCanvas/zoomIn': lambda iface, _: iface.mapCanvas().zoomIn(),
    '/qgis/mapCanvas/zoomOut': lambda iface, _: iface.mapCanvas().zoomOut(),
    '/qgis/mapCanvas/zoomScale': lambda iface, request: iface.mapCanvas().zoomScale(float(request.args['scale'])),
    '/qgis/mapCanvas/zoomToFullExtent': lambda iface, _: iface.mapCanvas().zoomToFullExtent()
}

import os
from tempfile import mkstemp
from PyQt4.QtGui import QPixmap

# the 'format' argument (default 'png') can be any image format string
# supported by saveAsImage(), with the MIME type of the HTTP response simply
# set to 'image/' + format
def get_canvas(iface, request):
    ext = request.args.get('format', 'png')
    tmpfile, tmpfilename = mkstemp('.' + ext)
    os.close(tmpfile)

    # if either is unspecified or otherwise invalid, QGIS display size is used
    pixmap = QPixmap(int(request.args.get('width', 0)), int(request.args.get('height', 0)))
    if pixmap.isNull():
        pixmap = None

    iface.mapCanvas().saveAsImage(tmpfilename, pixmap, ext)
    with open(tmpfilename, 'r') as content_file:
        imagedata = content_file.read()
    os.remove(tmpfilename)
    # TODO QGIS also writes a 'world file' (same filename + 'w' at the end)?
    return [200, imagedata, [('Content-Type', 'image/' + ext)]]

network_api_functions['/qgis/mapCanvas'] = get_canvas

def add_vector_layer(iface, request):
    if request.command == 'POST':
        # TODO check get_payload() for multipart?
        tmpfile, filename = mkstemp('.geojson')
        os.write(tmpfile, request.headers.get_payload())
        os.close(tmpfile)
    else:
        # try 'file' GET arg (could actually be file:// or a web http:// url)
        # TODO implement provider string URI options (from POST arguments?)
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/loadlayer.html#vector-layers
        filename = request.args['file']
    [200, iface.addVectorLayer(filename, 'newvectorlayer', 'ogr')]
    # TODO file cleanup

network_api_functions['/qgis/addVectorLayer'] = add_vector_layer
