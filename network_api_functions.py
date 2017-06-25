# -*- coding: utf-8 -*-

# network api functions to be added to the call path registry
#
# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object.
#
# the functions should return an instance of NetworkAPIResult

from network_api_registry import networkapi, NetworkAPIResult
from qgis.core import QgsMapLayerRegistry, QgsVectorFileWriter

# TODO add simple function to simplify wrapping argument-free function calls

@networkapi('/qgis/supportedFiltersAndFormats')
def supportedFiltersAndFormats(_, _2):
    """Returns a dictionary of supported vector formats with format filter string as key and OGR format key as value."""
    return NetworkAPIResult(QgsVectorFileWriter.supportedFiltersAndFormats())

# http://qgis.org/api/2.18/classQgisInterface.html
@networkapi('/qgis/defaultStyleSheetOptions')
def defaultStylesheetOptions(iface, _):
    """Return changeable options built from settings and/or defaults."""
    return NetworkAPIResult(iface.defaultStyleSheetOptions())

@networkapi('/qgis/addRasterLayer')
def addRasterLayer(iface, request):
    """
    Add a new raster layer to QGIS.

    The vector data can be provided in two ways:

    1. from an external file, by providing a WMS url as a 'url' GET argument, in combination with a valid 'providerKey'

    2. as raster data in the request body of a POST request

    GET arguments:
        name (string, optional): name for the new layer
        url (string, optional): url to WMS dataset to be added as a new layer
        providerKey (string, optional): QGIS provider key (default: 'ogr')

    Returns:
        A JSON object containing information on the layer that was just added.
    """
    if request.command == 'POST':
        # TODO check get_payload() for multipart?
        tmpfile, filename = mkstemp()
        os.write(tmpfile, request.headers.get_payload())
        os.close(tmpfile)
        return NetworkAPIResult(iface.addRasterLayer(filename, request.args.get('name', '')))
    else:
        # 3 args for WMS layer: url, name, providerkey
        return NetworkAPIResult(iface.addRasterLayer(request.args['url'], request.args.get('name', ''), request.args['providerKey']))

@networkapi('/qgis/addVectorLayer')
def addVectorLayer(iface, request):
    """
    Add a new vector layer to QGIS.

    The vector data can be provided in two ways:

    1. from an external file, by passing a QGIS provider string as a 'url' GET argument

    2. as GeoJSON data in the request body of a POST request (support for other formats to be added later)

    GET arguments:
        name (string, optional): name for the new layer
        url (string, optional): QGIS provider string to a local or external vector data source
        providerKey (string, optional): QGIS provider key (default: 'ogr')

    Returns:
        A JSON object containing information on the layer that was just added.
    """
    if request.command == 'POST':
        # TODO check get_payload() for multipart?
        tmpfile, filename = mkstemp()
        os.write(tmpfile, request.headers.get_payload())
        os.close(tmpfile)
        # TODO this file should probably not be temporary but actually stay on disk?
    else:
        # try 'url' GET arg (could actually be file:// or a web http:// url)
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/loadlayer.html#vector-layers
        filename = request.args['url']
    return NetworkAPIResult(iface.addVectorLayer(filename, request.args.get('name', ''), request.args.get('providerKey', 'ogr')))

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

# TODO add support for removal of multiple layers. unwise to overload arg name?
@networkapi('/qgis/mapLayers/removeMapLayer')
def mapLayers_removeMapLayer(iface, request):
    """
    Remove a layer from the registry by layer ID.

    The specified layer will be removed from the registry. If the registry has ownership of the layer then it will also be deleted.

    GET arguments:
        id (string): ID of the layer to be removed
    """
    layer = qgis_layer_by_id(request.args['id'])
    QgsMapLayerRegistry.instance().removeMapLayer(layer)
    # 'layer' object is already deleted at this point?
    return NetworkAPIResult(request.args['id'])

# http://qgis.org/api/2.18/classQgsMapLayer.html
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
@networkapi('/qgis/mapLayer/fields')
def mapLayer_fields(iface, request):
    """
    Returns the list of fields of a layer.

    This also includes fields which have not yet been saved to the provider.

    GET arguments:
        id (string): ID of layer whose fields to retrieve
    """
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.fields())

# TODO parse QgsFeatureRequest from POST body
@networkapi('/qgis/mapLayer/getFeatures')
def mapLayer_getFeatures(iface, request):
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.getFeatures(None))

@networkapi('/qgis/mapLayer/selectedFeatures')
def mapLayer_selectedFeatures(iface, request):
    """
    Return information about the currently selected features from the given vector layer.

    To retrieve the geometry of all selected features, see /qgis/mapLayer/selectedFeatures/geometry

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

@networkapi('/qgis/mapLayer/selectedFeatures/geometry')
def mapLayer_selectedFeatures_geometry(iface, request):
    if request.args.get('id'):
        layer = qgis_layer_by_id(request.args['id'])
    else:
        layer = iface.mapCanvas().currentLayer()
    return NetworkAPIResult([f.geometry() for f in layer.selectedFeatures()])

from PyQt4.QtXml import QDomDocument

# overload /xml path: POST loads layer from request, GET returns current xml
@networkapi('/qgis/mapLayer/xml')
def mapLayer_xml(iface, request):
    """
    Retrieve or set the definition of the layer with the given id.

    GET arguments:
        id (string): ID of layer whose definition to retrieve or set

    Returns:
        The XML definition for the layer with the given ID.
    """
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
@networkapi('/qgis/mapLayer/style')
def mapLayer_style(iface, request):
    """
    Retrieve or set the style for the layer with the given id.

    GET arguments:
        id (string): ID of layer whose stylesheet to retrieve or set

    Returns:
        The XML style definition for the layer with the given ID.
    """
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
        # TODO check return value
        layer.writeStyle(root, doc, '')
        return NetworkAPIResult(doc.toString(), 'text/xml')


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

@networkapi('/qgis/mapCanvas/center')
def mapCanvas_center(iface, _):
    """Get map center, in geographical coordinates."""
    return NetworkAPIResult(iface.mapCanvas().center())

@networkapi('/qgis/mapCanvas/extent')
def mapCanvas_extent(iface, _):
    """Returns the current zoom exent of the map canvas."""
    return NetworkAPIResult(iface.mapCanvas().extent())

@networkapi('/qgis/mapCanvas/fullExtent')
def mapCanvas_fullExtent(iface, _):
    """Returns the combined exent for all layers on the map canvas."""
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

    For *all* registered layers, see /qgis/mapLayers
    """
    return NetworkAPIResult(iface.mapCanvas().layers())

@networkapi('/qgis/mapCanvas/magnificationFactor')
def mapCanvas_magnificationFactor(iface, _):
    """Returns the magnification factor."""
    return NetworkAPIResult(iface.mapCanvas().magnificationFactor())

@networkapi('/qgis/mapCanvas/setMagnificationFactor')
def mapCanvas_setMagnificationFactor(iface, request):
    """
    Sets the factor of magnification to apply to the map canvas.

    GET arguments:
        factor (float): target magnification factor
    """
    return NetworkAPIResult(iface.mapCanvas().setMagnificationFactor(float(request.args['factor'])))

@networkapi('/qgis/mapCanvas/scale')
def mapCanvas_scale(iface, _):
    """Get the last reported scale of the canvas.

    Returns:
        The last reported scale of the canvas (a single float)
    """
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomIn')
def mapCanvas_zoomIn(iface, _):
    """
    Zoom in with fixed factor.

    Returns:
        The new scale of the canvas (a single float)
    """
    iface.mapCanvas().zoomIn()
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomOut')
def mapCanvas_zoomOut(iface, _):
    """
    Zoom out with fixed factor.

    Returns:
        The new scale of the canvas (a single float)
    """
    iface.mapCanvas().zoomOut()
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomScale')
def mapCanvas_zoomScale(iface, request):
    """
    Zoom to a specific scale.

    GET arguments:
        scale (float): target scale

    Returns:
        The new scale of the canvas (a single float)
    """
    print iface.mapCanvas().zoomScale(float(request.args['scale']))
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomToFullExtent')
def mapCanvas_zoomToFullExtent(iface, _):
    """Zoom to the full extent of all layers."""
    return NetworkAPIResult(iface.mapCanvas().zoomToFullExtent())

