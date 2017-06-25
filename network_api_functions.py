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
    """Return changeable options built from settings and/or defaults."""
    return NetworkAPIResult(iface.defaultStyleSheetOptions())


# http://qgis.org/api/2.18/classQgsMapLayerRegistry.html
@networkapi('/qgis/mapLayers/count')
def mapLayers_count(iface, _):
    """Returns the total number of registered layers, visible or not."""
    return NetworkAPIResult(QgsMapLayerRegistry.instance().count())

@networkapi('/qgis/mapLayers')
def mapLayers(iface, request):
    """
    Returns information about all registered layers by layer ID.

    For information on the currently visible layers and their ordering, see /qgis/mapCanvas/layers

    Returns:
        A JSON object containing id : layer pairs.
    """
    return NetworkAPIResult(QgsMapLayerRegistry.instance().mapLayers())

# helper function
def qgis_layer_by_id(id):
    layer = QgsMapLayerRegistry.instance().mapLayer(id)
    if layer == None:
        raise KeyError('No layer with id: ' + id)
    return layer

@networkapi('/qgis/mapLayer')
def mapLayer(iface, request):
    """
    Return information about the layer with the given ID.

    For information about all registered layers and their IDs, see /qgis/mapLayers

    GET arguments:
        id (string): ID of layer to retrieve

    Returns:
        A JSON object containing information on the layer with the given ID.
    """
    return NetworkAPIResult(qgis_layer_by_id(request.args['id']))

# the following paths require 'id' an argument specifying the desired layer
@networkapi('/qgis/mapLayers/fields')
def mapLayers_fields(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.fields())

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

@networkapi('/qgis/mapLayers/selectedFeatures')
def mapLayers_selectedFeatures(iface, request):
    """
    Return information about the currently selected features from the given vector layer.

    To retrieve the geometry of all selected features, see /qgis/mapLayers/selectedFeatures/geometry

    GET arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

    Returns:
        A list of all currently selected features in JSON format, where each feature is an object specifying the feature's 'id' and all its 'attributes'.
    """
    # if 'id' arg was not passed, default to currentLayer()
    if request.args.get('id'):
        layer = qgis_layer_by_id(request.args['id'])
    else:
        layer = iface.mapCanvas().currentLayer()
    # FIXME this sometimes returns empty attributes and id of 0 for some
    # elements, maybe retrieve features via their id instead?
    return NetworkAPIResult(layer.selectedFeatures())

@networkapi('/qgis/mapLayers/selectedFeatures/geometry')
def mapLayers_selectedFeatures_geometry(iface, request):
    if request.args.get('id'):
        layer = qgis_layer_by_id(request.args['id'])
    else:
        layer = iface.mapCanvas().currentLayer()
    return NetworkAPIResult([f.geometry() for f in layer.selectedFeatures()])

# http://qgis.org/api/2.18/classQgsMapCanvas.html
import os
from tempfile import mkstemp
from PyQt4.QtGui import QPixmap

@networkapi('/qgis/mapCanvas')
def mapCanvas(iface, request):
    """
    Return information about the map canvas, such as visible area, projection etc.
    """
    return NetworkAPIResult(iface.mapCanvas())

# overload with POST?
# @networkapi('/qgis/mapCanvas/xml')
# def mapCanvas_xml(iface, request):
#     doc = QDomDocument('xml')
#     iface.mapCanvas().writeProject(doc)
#     return NetworkAPIResult(doc.toString(), 'text/xml')

@networkapi('/qgis/mapCanvas/image')
def mapCanvas_image(iface, request):
    """
    Return the currently visible content of the map canvas as an image.

    GET arguments:
        format (optional): any image format string supported by QGIS' saveAsImage() (default: 'png', other options e.g. 'jpeg')

    Returns:
        An image the same size as the currently visible map canvas. The content-type of the response is set to 'image/' + format.
    """
    ext = request.args.get('format', 'png')
    tmpfile, tmpfilename = mkstemp('.' + ext)
    os.close(tmpfile)

    # if either is unspecified or otherwise invalid, QGIS display size is used
    pixmap = QPixmap(int(request.args.get('width', 0)), int(request.args.get('height', 0)))
    if pixmap.isNull():
        pixmap = None

    # doesn't provide status information about success of writing, have to
    # check file size below
    iface.mapCanvas().saveAsImage(tmpfilename, pixmap, ext)

    with open(tmpfilename, 'r') as content_file:
        imagedata = content_file.read()
    os.remove(tmpfilename)
    # TODO QGIS also writes a 'world file' (same filename + 'w' at the end)?

    if len(imagedata) == 0:
        raise IOError('Failed to write canvas contents in format ' + ext)

    # FIXME format = 'jpg' generates image correctly but has incorrect MIMEtype
    return NetworkAPIResult(imagedata, content_type='image/' + ext.lower())

@networkapi('/qgis/mapCanvas/extent')
def mapCanvas_extent(iface, _):
    return NetworkAPIResult(iface.mapCanvas().extent())

@networkapi('/qgis/mapCanvas/fullExtent')
def mapCanvas_fullExtent(iface, _):
    return NetworkAPIResult(iface.mapCanvas().fullExtent())

@networkapi('/qgis/mapCanvas/layer')
def mapCanvas_layer(iface, request):
    """
    Return the map layer at position index in the layer stack.

    GET arguments:
        index (int): position index in the layer stack, between 0 and layerCount-1
    """
    return NetworkAPIResult(iface.mapCanvas().layer(int(request.args['index'])))

@networkapi('/qgis/mapCanvas/layerCount')
def mapCanvas_layerCount(iface, _):
    """
    Return number of layers on the map that are set visible.

    For the total number of registered layers, see /qgis/mapLayers/count
    """
    return NetworkAPIResult(iface.mapCanvas().layerCount())

@networkapi('/qgis/mapCanvas/layers')
def mapCanvas_layers(iface, _):
    """
    Return list of layers within map canvas that are set visible.

    For all registered layers, see /qgis/mapLayers
    """
    return NetworkAPIResult(iface.mapCanvas().layers())

@networkapi('/qgis/mapCanvas/magnificationFactor')
def mapCanvas_magnificationFactor(iface, _):
    """Returns the magnification factor."""
    return NetworkAPIResult(iface.mapCanvas().magnificationFactor())

@networkapi('/qgis/mapCanvas/scale')
def mapCanvas_scale(iface, _):
    """Get the last reported scale of the canvas."""
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomIn')
def mapCanvas_zoomIn(iface, _):
    """Zoom in with fixed factor."""
    return NetworkAPIResult(iface.mapCanvas().zoomIn())

@networkapi('/qgis/mapCanvas/zoomOut')
def mapCanvas_zoomOut(iface, _):
    """Zoom out with fixed factor."""
    return NetworkAPIResult(iface.mapCanvas().zoomOut())

@networkapi('/qgis/mapCanvas/zoomScale')
def mapCanvas_zoomScale(iface, request):
    """
    Zoom to a specific scale.

    GET arguments:
        scale (float): target scale
    """
    return NetworkAPIResult(iface.mapCanvas().zoomScale(float(request.args['scale'])))

@networkapi('/qgis/mapCanvas/zoomToFullExtent')
def mapCanvas_zoomToFullExtent(iface, _):
    """Zoom to the full extent of all layers."""
    return NetworkAPIResult(iface.mapCanvas().zoomToFullExtent())



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
            return NetworkAPIResult(status=NetworkAPIResult.INVALID_ARGUMENTS)
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
            return NetworkAPIResult()
        else:
            return NetworkAPIResult(status=NetworkAPIResult.INVALID_ARGUMENTS)
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
    return NetworkAPIResult(iface.addRasterLayer(filename, request.args.get('name', '')))
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
    return NetworkAPIResult(iface.addVectorLayer(filename, request.args.get('name', ''), request.args.get('type', 'ogr')))
    # TODO file cleanup
