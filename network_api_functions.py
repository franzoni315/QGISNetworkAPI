# -*- coding: utf-8 -*-

# network api functions to be added to the call path registry
#
# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object.
#
# the functions should return an instance of NetworkAPIResult

from network_api_registry import networkapi, NetworkAPIResult
from qgis.core import QgsMapLayerRegistry

# TODO add simple function to simplify wrapping argument-free function calls

# http://qgis.org/api/2.18/classQgisInterface.html
@networkapi('/qgis/defaultStyleSheetOptions')
def defaultStylesheetOptions(iface, _):
    print type(iface.defaultStyleSheetOptions())
    return NetworkAPIResult(iface.defaultStyleSheetOptions())

# http://qgis.org/api/2.18/classQgsMapLayerRegistry.html
@networkapi('/qgis/mapLayers')
def mapLayers(iface, request):
    # TODO implement optional 'id' GET arg
    return NetworkAPIResult(QgsMapLayerRegistry.instance().mapLayers())

@networkapi('/qgis/mapLayers/count')
def mapLayers_count(iface, _):
    return NetworkAPIResult(QgsMapLayerRegistry.instance().count())

# helper function
def qgis_layer_by_id(id):
    layer = QgsMapLayerRegistry.instance().mapLayer(id)
    if layer == None:
        raise KeyError('No layer with id: ' + id)
    return layer

# the following paths require 'id' an argument specifying the desired layer

# TODO add support for removal of multiple layers. unwise to overload arg name?
@networkapi('/qgis/mapLayers/remove')
def mapLayers_remove(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    QgsMapLayerRegistry.instance().removeMapLayer(layer)
    # 'layer' object is already deleted at this point?
    return NetworkAPIResult(request.args['id'])

# TODO parse QgsFeatureRequest from POST body
@networkapi('/qgis/mapLayers/getFeatures')
def mapLayers_getFeatures(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.getFeatures(None))


# http://qgis.org/api/2.18/classQgsMapCanvas.html
import os
from tempfile import mkstemp
from PyQt4.QtGui import QPixmap

@networkapi('/qgis/mapCanvas')
def mapCanvas(iface, request):
    """ Return the currently visible content of the map canvas as an image.
    The 'format' argument (default 'png') can be any image format string
    supported by QGIS' saveAsImage(), with the MIME type of the HTTP response
    simply set to 'image/' + format."""
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
    return NetworkAPIResult(imagedata, content_type='image/' + ext)

@networkapi('/qgis/mapCanvas/extent')
def mapCanvas_extent(iface, _):
    return NetworkAPIResult(iface.mapCanvas().extent())

@networkapi('/qgis/mapCanvas/fullExtent')
def mapCanvas_fullExtent(iface, _):
    return NetworkAPIResult(iface.mapCanvas().fullExtent())

@networkapi('/qgis/mapCanvas/magnificationFactor')
def mapCanvas_magnificationFactor(iface, _):
    return NetworkAPIResult(iface.mapCanvas().magnificationFactor())

@networkapi('/qgis/mapCanvas/scale')
def mapCanvas_scale(iface, _):
    return NetworkAPIResult(iface.mapCanvas().scale())

    # '/qgis/mapCanvas/zoomIn': lambda iface, _: iface.mapCanvas().zoomIn(),
    # '/qgis/mapCanvas/zoomOut': lambda iface, _: iface.mapCanvas().zoomOut(),
    # '/qgis/mapCanvas/zoomScale': lambda iface, request: iface.mapCanvas().zoomScale(float(request.args['scale'])),
    # '/qgis/mapCanvas/zoomToFullExtent': lambda iface, _: iface.mapCanvas().zoomToFullExtent()

from PyQt4.QtXml import QDomDocument

# overload /xml path: POST loads layer from request, GET returns current xml
@networkapi('/qgis/mapLayers/xml')
def mapLayers_xml(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    if request.command == 'POST':
        doc = QDomDocument('xml')
        # TODO needs testing
        if doc.setContent(request.headers.get_payload()) and layer.readLayerXml(doc):
            return NetworkAPIResult()
        else:
            return NetworkAPIResult(status=418) # TODO what error to raise?
    else:
        doc = QDomDocument('xml')
        root = doc.createElement('maplayer')
        doc.appendChild(root)
        layer.writeLayerXML(root, doc, '')
        return NetworkAPIResult(doc.toString(), 'text/xml')

# same overloading for /style path
@networkapi('/qgis/mapLayers/style')
def mapLayers_style(iface, request):
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
        return NetworkAPIResult(doc.toString(), 'text/xml')

@networkapi('/qgis/addRasterLayer')
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
    return NetworkAPIResult(iface.addRasterLayer(filename, request.args.get('name', 'NetworkAPILayer')))
    # TODO temp file cleanup

@networkapi('/qgis/addVectorLayer')
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
    return NetworkAPIResult(iface.addVectorLayer(filename, request.args.get('name', 'NetworkAPILayer'), request.args.get('type', 'ogr')))
    # TODO file cleanup

from json import JSONEncoder
from qgis.core import QgsFeatureIterator, QgsMapLayer, QgsRectangle, QgsCoordinateReferenceSystem, QgsUnitTypes

# TODO: convert python-wrapped C++ enum to string:
# https://riverbankcomputing.com/pipermail/pyqt/2014-August/034630.html
# add conversion for LayerType, https://qgis.org/api/classQgsUnitTypes.html

class QGISJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, QgsMapLayer):
            return {'name': o.name(), 'type': o.type(), 'publicSource': o.publicSource(), 'crs': o.crs(), 'extent': o.extent(), 'isEditable': o.isEditable()}
        elif isinstance(o, QgsCoordinateReferenceSystem):
            return {'description': o.description(), 'srsid': o.srsid(), 'proj4': o.toProj4(), 'postgisSrid': o.postgisSrid()}
        elif isinstance(o, QgsRectangle):
            return [o.xMinimum(), o.yMinimum(), o.xMaximum(), o.yMaximum()]
#        elif isinstance(o, QgsFeatureIterator):
#            return None # TODO
        return JSONEncoder.default(self, o)
