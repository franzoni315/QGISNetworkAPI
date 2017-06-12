# -*- coding: utf-8 -*-

# the Network API plugin parses this dict: it maps request paths to (anonymous)
# functions called whenever the corresponding path is requested

# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object

# the functions should return either None or a list of up to three elements:
# 1. the HTTP status to be sent back to the client
# 2. the response body (optional: either missing or None)
# 3. the HTTP Content-Type of the response body (also optional)
#
# when the function returns None instead of a list, a 200 OK status is assumed.
# when the Content-Type is not specified, defaults to plain/text for string
# responses and application/json for other data structures, which are
# automatically converted using json.dump()

from qgis.core import QgsMapLayerRegistry

# dict comprehension syntax only from python 2.7 onwards
# TODO convert map layer type enum in string representation?
#def layerslots(layer):
#    {s: getattr(layer, s) for s in ['id', 'name', 'type']}

network_api_functions = {
    # http://qgis.org/api/2.18/classQgisInterface.html
    '/qgis/defaultStyleSheetOptions': lambda iface, _: [200, str(iface.defaultStyleSheetOptions())],

    # http://qgis.org/api/2.18/classQgsMapLayerRegistry.html
    # can't seem to find a way to autoconvert QMaps to JSON...
    # TODO implement optional 'id' GET arg
    '/qgis/mapLayers': lambda iface, _: [200, {name: layer for (name, layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems()}],
    '/qgis/mapLayers/count': lambda iface, _: [200, QgsMapLayerRegistry.instance().count()],
    # see below for: /addRasterLayer, /addVectorLayer,
    # /mapLayers/remove?id=, /mapLayers/xml?id=
    '/qgis/editableLayers': lambda iface, _: [200, iface.editableLayers()],
    # the following paths require an argument specifying the desired layer
    '/qgis/editableLayers/maximumScale': lambda iface, _: None,

    # http://qgis.org/api/2.18/classQgsMapCanvas.html
    '/qgis/mapCanvas/extent': lambda iface, _: [200, iface.mapCanvas().extent()],
    '/qgis/mapCanvas/fullExtent': lambda iface, _: [200, iface.mapCanvas().fullExtent()],
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
    return [200, imagedata, 'image/' + ext]

network_api_functions['/qgis/mapCanvas'] = get_canvas

def qgis_layer_by_id(id):
    layer = QgsMapLayerRegistry.instance().mapLayer(id)
    if layer == None:
        raise KeyError('No layer with id: ' + id)
    return layer

# TODO add support for removal of multiple layers. unwise to overload arg name?
def remove_layers(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    QgsMapLayerRegistry.instance().removeMapLayer(layer)
    return [200, request.args['id']] #'layer' already deleted at this point

network_api_functions['/qgis/mapLayers/remove'] = remove_layers

from PyQt4.QtXml import QDomDocument

# overload /xml path: POST loads layer from request, GET returns current xml
def layer_xml(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    if request.command == 'POST':
        doc = QDomDocument('xml')
        # TODO needs testing
        if doc.setContent(request.headers.get_payload()) and layer.readLayerXml(doc):
            return None
        else:
            return [418] # TODO what error to raise?
    else:
        doc = QDomDocument('xml')
        root = doc.createElement('maplayer')
        doc.appendChild(root)
        layer.writeLayerXML(root, doc, '')
        return [200, doc.toString(), 'text/xml']

network_api_functions['/qgis/mapLayers/xml'] = layer_xml

# same overloading for /style path
def layer_style(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    if request.command == 'POST':
        doc = QDomDocument('xml')
        # TODO needs testing (second argument to readStyle?)
        if doc.setContent(request.headers.get_payload()) and layer.readStyle(doc):
            return None
        else:
            return [418] # TODO what error to raise?
    else:
        doc = QDomDocument('xml')
        root = doc.createElement('maplayer')
        doc.appendChild(root)
        # FIXME 'QgsVectorLayer' object has no attribute 'writeStyle' ??
        # cf. http://qgis.org/api/2.18/classQgsVectorLayer.html#aca70632c28ef4e5075784e16f4be8efa
        layer.writeStyle(root, doc, '')
        return [200, doc.toString(), 'text/xml']

network_api_functions['/qgis/mapLayers/style'] = layer_style

def add_raster_layer(iface, request):
    if request.command == 'POST':
        # TODO check get_payload() for multipart?
        tmpfile, filename = mkstemp('.geojson')
        os.write(tmpfile, request.headers.get_payload())
        os.close(tmpfile)
    else:
        # try 'uri' GET arg (could actually be file:// or a web http:// url)
        # TODO implement provider string URI options (from POST arguments?)
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/loadlayer.html#vector-layers
        filename = request.args['uri']
    # 2 args for local file, 3 args for WMS layer
    return [200, iface.addRasterLayer(filename, request.args.get('name', 'NetworkAPILayer'))]
    # TODO temp file cleanup

network_api_functions['/qgis/addRasterLayer'] = add_raster_layer

def add_vector_layer(iface, request):
    if request.command == 'POST':
        # TODO check get_payload() for multipart?
        tmpfile, filename = mkstemp('.geojson')
        os.write(tmpfile, request.headers.get_payload())
        os.close(tmpfile)
    else:
        # try 'uri' GET arg (could actually be file:// or a web http:// url)
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/loadlayer.html#vector-layers
        filename = request.args['uri']
    return [200, iface.addVectorLayer(filename, request.args.get('name', 'NetworkAPILayer'), request.args.get('type', 'ogr'))]
    # TODO file cleanup

network_api_functions['/qgis/addVectorLayer'] = add_vector_layer



from json import JSONEncoder
from qgis.core import QgsMapLayer, QgsRectangle, QgsCoordinateReferenceSystem, QgsUnitTypes

# TODO: convert python-wrapped C++ enum to string:
# https://riverbankcomputing.com/pipermail/pyqt/2014-August/034630.html
# add conversion for LayerType, https://qgis.org/api/classQgsUnitTypes.html

class QGISJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, QgsMapLayer):
            return {'name': o.name(), 'type': o.type(), 'publicSource': o.publicSource(), 'crs': o.crs(), 'extent': o.extent(), 'isEditable': o.isEditable()}
        elif isinstance(o, QgsCoordinateReferenceSystem):
            return {'description': o.description(), 'srsid': o.srsid(), 'proj4': o.toProj4(), 'wkt': o.toWkt(), 'postgisSrid': o.postgisSrid()}
        elif isinstance(o, QgsRectangle):
            return [o.xMinimum(), o.yMinimum(), o.xMaximum(), o.yMaximum()]
        return JSONEncoder.default(self, o)
