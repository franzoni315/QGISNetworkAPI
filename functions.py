# -*- coding: utf-8 -*-

# network api functions to be added to the call path registry
#
# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object.
#
# the functions should return an instance of NetworkAPIResult

from .registry import networkapi, NetworkAPIResult, parseCRS, toGeoJSON
from distutils.util import strtobool
from qgis.core import QgsExpression, QgsFeatureRequest, QgsMapLayerRegistry, QgsPoint, QgsRectangle, QgsVectorFileWriter

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

    1. by providing a WMS url as a 'url' GET argument, in combination with a valid 'providerKey'

    2. as raster data in the request body of a POST request

    3. from a file readable by QGIS, by giving the file name as a 'rasterLayerPath' GET argument. If you are accessing the API from your local machine, this approach saves you from creating a redundant copy of the raster file on disk.

    HTTP query arguments:
        layerName (string, optional): name for the new layer
        rasterLayerPath (string, optional): file name of a locally readable raster data set to be added as a new layer
        url (string, optional): url of WMS service to be added as a new layer
        providerKey (string, only required together with url argument): QGIS provider key (default: 'ogr')

    Returns:
        A JSON object containing information on the layer that was just added.
    """
    if request.command == 'POST':
        # TODO check get_payload() for multipart?
        tmpfile, filename = mkstemp()
        os.write(tmpfile, request.headers.get_payload())
        os.close(tmpfile)
        return NetworkAPIResult(iface.addRasterLayer(filename, request.args.get('layerName', '')))
    else:
        if request.args.get('rasterLayerPath'):
            # 2 args for local file: rasterLayerPath, layerName
            return NetworkAPIResult(iface.addRasterLayer(request.args['rasterLayerPath'], request.args.get('layerName', '')))
            # 3 args for WMS layer: url, name, providerkey
        else:
            return NetworkAPIResult(iface.addRasterLayer(request.args['url'], request.args.get('layerName', ''), request.args['providerKey']))

@networkapi('/qgis/addVectorLayer')
def addVectorLayer(iface, request):
    """
    Add a new vector layer to QGIS.

    The vector data can be provided in two ways:

    1. from an external file, by passing a QGIS provider string as a 'vectorLayerPath' query argument

    2. as GeoJSON data in the request body of a POST request (support for other formats to be added later)

    HTTP query arguments:
        baseName (string, optional): name for the new layer
        vectorLayerPath (string, optional): QGIS provider string to a local or external vector data source
        providerKey (string, optional): QGIS provider key (default: 'ogr')
        crs (string, optional): specification for a coordinate reference system understandable by QGIS, such as a 'EPSG:...' or WKT definition string. This argument is really only useful for the case of adding GeoJSON data (via a POST request), since this is the only format which does not contain information on the coordinate system of the data.

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
        # try 'vectorLayerPath' GET arg (could actually be file:// or a web http:// url)
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/loadlayer.html#vector-layers
        filename = request.args['vectorLayerPath']
    layer = iface.addVectorLayer(filename, request.args.get('baseName', ''), request.args.get('providerKey', 'ogr'))

    if request.args.get('crs'):
        # FIXME what about error handling in such a case? parsing the CRS might
        # fail which means the API will return an error, without communicating
        # information on the successfully added layer...
        layer.setCrs(parseCRS(request.args['crs']))

    return NetworkAPIResult(layer)

@networkapi('/qgis/newProject')
def mapLayers_count(iface, _):
    """Start a blank project. Warning: does *not* prompt to save changes to the currently open project!"""
    return NetworkAPIResult(iface.newProject())


# http://qgis.org/api/2.18/classQgsMapLayerRegistry.html
@networkapi('/qgis/mapLayers/count')
def mapLayers_count(iface, _):
    """Returns the total number of registered layers, visible or not."""
    return NetworkAPIResult(QgsMapLayerRegistry.instance().count())

@networkapi('/qgis/mapLayers')
def mapLayers(iface, request):
    """
    Returns information about all registered layers.

    For information on the currently visible layers and their ordering, see /qgis/mapCanvas/layers

    Returns:
        A JSON object containing id : layer pairs.
    """
    return NetworkAPIResult(QgsMapLayerRegistry.instance().mapLayers())

# helper function
def qgis_layer_by_id(id):
    layer = QgsMapLayerRegistry.instance().mapLayer(str(id))
    if layer == None:
        raise KeyError('No layer with id: ' + str(id))
    return layer

def qgis_layer_by_id_or_current(iface, request):
    if request.args.get('id'):
        return qgis_layer_by_id(request.args['id'])

    if iface.mapCanvas().currentLayer() == None:
        raise ValueError('No layer selected in QGIS')

    return iface.mapCanvas().currentLayer()

# TODO add support for removal of multiple layers. unwise to overload arg name?
@networkapi('/qgis/mapLayers/removeMapLayer')
def mapLayers_removeMapLayer(iface, request):
    """
    Remove a layer from the registry by layer ID.

    The specified layer will be removed from the registry. If the registry has ownership of the layer then it will also be deleted.

    HTTP query arguments:
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

    HTTP query arguments:
        id (string): ID of layer to retrieve

    Returns:
        A JSON object containing information on the layer with the given ID.
    """
    return NetworkAPIResult(qgis_layer_by_id(request.args['id']))

@networkapi('/qgis/mapLayer/crs')
def mapLayer_crs(iface, request):
    """Get or set the layer's spatial reference system.

    On receiving a POST request, attempts to set the layer's CRS to the content of the request body, which can be any specification for a coordinate reference system understandable by QGIS, such as a 'EPSG:...' or a WKT definition string.

    HTTP query arguments:
        id (optional): ID of the desired layer.

    Returns:
        A JSON object representing the layer's spatial reference system (after setting)
    """
    layer = qgis_layer_by_id(request.args['id'])
    if request.command == 'POST':
        layer.setCrs(parseCRS(request.headers.get_payload()))
    return NetworkAPIResult(layer.crs())

@networkapi('/qgis/mapLayer/featureCount')
def mapLayer_featureCount(iface, request):
    """
    Return feature count of the given vector layer.

    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

    Returns:
    Feature count of the given vector layer, including changes which have not yet been committed to this layer's provider.
    """
    layer = qgis_layer_by_id_or_current(iface, request)
    return NetworkAPIResult(layer.featureCount())

# the following paths require 'id' an argument specifying the desired layer
@networkapi('/qgis/mapLayer/fields')
def mapLayer_fields(iface, request):
    """
    Returns the list of fields of a layer.

    This also includes fields which have not yet been saved to the provider.

    HTTP query arguments:
        id (string): ID of layer whose fields to retrieve
    """
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.fields())

@networkapi('/qgis/mapLayer/getFeatures')
def mapLayer_getFeatures(iface, request):
    """
    Return information about features of the given vector layer.

    Retrieve information about (and, optionally, geometry of) features of the given vector layer by querying the underlying datasource programmatically. To retrieve features that were manually selected by the user within QGIS, see /qgis/mapLayer/selectedFeatures


    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

        geometry (optional, default false): if true, returns all feature information including their geometry in GeoJSON format. Accepts several string representations of booleans (e.g. 1, 0, true, false, yes, no, ...).

        orderBy (optional): expression that the results should be ordered by. If you want to order by a field, you'll have to give its name in quotes, e.g. ?orderBy="length"

        ascending (optional, default true): whether the results should be listen in ascending or descending order. Accepts several string representations of booleans (e.g. 1, 0, true, false, yes, no, ...).

        nullsfirst (optional): how null values should be treated in the ordering. Accepts several string representations of booleans (e.g. 1, 0, true, false, yes, no, ...).


    The different ways to filter features follow the different constructor signatures defined by the QgsFeatureRequest class, in particular:

        If the request is a HTTP POST request, the request body is treated as a QGIS filter expression, and the result of applying that filter is returned.

        If the request is a HTTP GET request, the following query arguments are considered in order, and the first one provided is applied:

            fid (integer): Construct a request with a QGIS feature ID filter

            rect (string): Construct a request with a rectangle filter. The rectangle should be specified as four numbers in the format "xmin,ymin,xmax,ymax".

            A GET request in which none of the arguments are specified returns ALL features of the given vector layer, which can produce very large results.


    Returns:
        If the 'geometry' argument was passed: a GeoJSON FeatureCollection with complete attribute and geometry data for all features of the layer.
        If the 'geometry' argument was not passed: a list of all features of the vector layer in JSON format, where each feature is an object specifying the feature's 'id' and all its 'attributes'.
    """
    layer = qgis_layer_by_id_or_current(iface, request)

    # construct and run QgsFeatureRequest depending on arguments

    featurerequest = QgsFeatureRequest()
    featurerequest.addOrderBy(request.args.get('orderBy', ''), strtobool(request.args.get('ascending', 'y')), strtobool(request.args.get('nullsfirst', 'n')))

    if request.command == 'POST':
        # POST request: complex QgsExpression passed as string
        featurerequest.setFilterExpression(QgsExpression(request.headers.get_payload()))
    else:
        if request.args.get('fid'):
            # query by feature id
            featurerequest.setFilterFid(int(request.args['fid']))
        elif request.args.get('rect'):
            # query by rectangle
            r = [float(x) for x in request.args['rect'].split(',')]
            if len(r) != 4:
                raise ValueError('"rect" argument to getFeatures requires exactly four floats in the format "xmin,ymin,xmax,ymax"')
            featurerequest.setFilterRect(QgsRectangle(r[0], r[1], r[2], r[3]))

    result = layer.getFeatures(featurerequest)

    if strtobool(request.args.get('geometry', 'n')):
        return NetworkAPIResult(toGeoJSON(layer, result), 'application/geo+json')
    else:
        # note that the lazy QgsFeatureIterator returned here is currently
        # turned into a full in-memory list during conversion to JSON
        return NetworkAPIResult(result)

@networkapi('/qgis/mapLayer/selectedFeatureCount')
def mapLayer_selectedFeatureCount(iface, request):
    """
    Return the number of features that are selected in the given vector layer.

    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

    Returns:
        An integer indicating the number of items that would be returned by the corresponding call to /qgis/mapLayer/selectedFeatures
    """
    layer = qgis_layer_by_id_or_current(iface, request)
    return NetworkAPIResult(layer.selectedFeatureCount())


from qgis.core import QgsVectorLayer

@networkapi('/qgis/mapLayer/selectedFeatures')
def mapLayer_selectedFeatures(iface, request):
    """
    Return information about the currently selected features from the given vector layer.

    Returns ids and attributes of the features only. In order to also retrieve the geometry as well as layer information of the features (in proper GeoJSON), see /qgis/mapLayer/selectedFeatures/geometry

    To retrieve *all* features of the layer that are available from its provider, see /qgis/mapLayer/getFeatures

    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

    Returns:
        A list of all currently selected features in JSON format, where each feature is an object specifying the feature's 'id' and all its 'attributes'.
    """
    layer = qgis_layer_by_id_or_current(iface, request)
    # FIXME this sometimes returns empty attributes and id of 0 for some
    # elements, maybe retrieve features via their id instead?
    return NetworkAPIResult(layer.selectedFeatures())

@networkapi('/qgis/mapLayer/selectedFeatures/geometry')
def mapLayer_selectedFeatures_geometry(iface, request):
    """
    Return attributes and geometry of the currently selected features from the given vector layer.

    To inspect the feature ids and attributes only, see /qgis/mapLayer/selectedFeatures

    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

    Returns:
        A GeoJSON FeatureCollection with complete data of all selected features of the given vector layer.
    """
    layer = qgis_layer_by_id_or_current(iface, request)
    return NetworkAPIResult(toGeoJSON(layer, layer.selectedFeatures()), 'application/geo+json')

@networkapi('/qgis/mapLayer/setAttribution')
def mapLayer_setAttribution(iface, request):
    """Set the attribution of the layer used by QGIS Server in GetCapabilities request.

    Attribution indicates the provider of a Layer or collection of Layers.

    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.
        attrib (string): the desired attribution for the layer

    Returns:
        NULL
    """
    layer = qgis_layer_by_id_or_current(iface, request)
    return NetworkAPIResult(layer.setAttribution(request.args['attrib']))

@networkapi('/qgis/mapLayer/subLayers')
def mapLayer_subLayers(iface, request):
    """Returns the sublayers of this layer (Useful for providers that manage their own layers, such as WMS)

    HTTP query arguments:
        id (optional): ID of layer from which selected features should be retrieved. If not specified, defaults to the currently active layer.

    Returns:
        A list of sublayer ids
    """
    layer = qgis_layer_by_id_or_current(iface, request)
    return NetworkAPIResult(layer.subLayers())


from PyQt4.QtXml import QDomDocument

# overload /xml path: POST loads layer from request, GET returns current xml
@networkapi('/qgis/mapLayer/xml')
def mapLayer_xml(iface, request):
    """
    Retrieve or set the definition of the layer with the given id.

    HTTP query arguments:
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


# http://qgis.org/api/2.18/classQgsMapCanvas.html
import os
from tempfile import mkstemp
from PyQt4.QtGui import QPixmap


@networkapi('/qgis/mapCanvas')
def mapCanvas(iface, _):
    """
    Return configuration and properties used for map rendering, such as visible area, projection etc.

    To obtain the XML specification of the configurable map canvas settings, see /qgis/mapCanvas/xml

    Unlike the XML configuration, this path also returns information about properties of the canvas which are to do with the underlying layers or are incidental to the current session (such as 'fullExtent' and 'visibleExtent').

    Returns:
        The contents of the canvas' QgsMapSettings object in JSON format.
    """
    # TODO implement access to specific fields via GET arg?
    return NetworkAPIResult(iface.mapCanvas().mapSettings())

@networkapi('/qgis/mapCanvas/xml')
def mapCanvas_xml(iface, _):
    """
    Return XML configuration used for map rendering.

    To obtain a JSON specification of the current map canvas settings, see /qgis/mapCanvas

    Returns:
        The XML serialisation of the canvas' QgsMapSettings object.
    """
    # TODO implement POST command
    doc = QDomDocument('xml')
    root = doc.createElement('mapcanvas')
    doc.appendChild(root)
    iface.mapCanvas().mapSettings().writeXML(root, doc)
    return NetworkAPIResult(doc.toString(), 'text/xml')

@networkapi('/qgis/mapCanvas/saveAsImage')
def mapCanvas_saveAsImage(iface, request):
    """
    Return the currently visible content of the map canvas as an image.

    HTTP query arguments:
        format (optional): any image format string supported by QGIS' (default: 'png', other options e.g. 'jpeg')

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

    # FIXME if the canvas has been modified very recently, it might not be done
    # re-rendering yet...
    # from QGIS 3 we could simply use: iface.mapCanvas().waitWhileRendering()

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

@networkapi('/qgis/mapCanvas/setCenter')
def mapCanvas_setCenter(iface, request):
    """Set the center of the map canvas, in geographical coordinates.

    HTTP query arguments:
        x (float): new x coordinate of the map canvas center
        y (float): new y coordinate of the map canvas center
    """
    center = QgsPoint(float(request.args['x']), float(request.args['y']))
    iface.mapCanvas().setCenter(center)
    return NetworkAPIResult(iface.mapCanvas().center())

@networkapi('/qgis/mapCanvas/setCrsTransformEnabled')
def mapCanvas_setCrsTransformEnabled(iface, request):
    """Set whether on-the-fly reprojection is enabled or disabled.

    HTTP query arguments:
        enabled: whether on-the-fly reprojection should be turned on or off. Accepts several string representations of booleans (e.g. 1, 0, true, false, yes, no, ...).
    """
    iface.mapCanvas().setCrsTransformEnabled(strtobool(request.args['enabled']))
    return NetworkAPIResult()

from qgis.core import QgsCoordinateReferenceSystem

@networkapi('/qgis/mapCanvas/setDestinationCrs')
def mapCanvas_setDestinationCrs(iface, request):
    """Set the map canvas' destination coordinate reference system.

    HTTP query arguments:
        crs: specification for a coordinate reference system understandable by QGIS, such as a 'EPSG:...' or WKT definition string.

    Returns:
        A JSON object representing the map canvas' coordinate reference system after applying the given definition string.
    """
    crs = parseCRS(request.args['crs'])
    # TODO is there a difference between this and the mapSettings.set() method?
    iface.mapCanvas().setDestinationCrs(crs)
    return NetworkAPIResult(iface.mapCanvas().mapSettings().destinationCrs())

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

    HTTP query arguments:
        index (int): position index in the layer stack, between 0 and layerCount-1
    """
    layer = iface.mapCanvas().layer(int(request.args['index']))
    if layer:
      return NetworkAPIResult(layer)
    else:
      raise KeyError('Invalid layer index: ' + str(int(request.args['index'])))

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

    HTTP query arguments:
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

    HTTP query arguments:
        scale (float): target scale

    Returns:
        The new scale of the canvas (a single float)
    """
    iface.mapCanvas().zoomScale(float(request.args['scale']))
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/setExtent')
def mapCanvas_setExtent(iface, request):
    """
    Zoom to feature extent and redraw map canvas.

    Adds a small margin around the extent and does a pan if rect is empty (point extent).

    HTTP query arguments:
        rect (string): Feature extent, specified as four numbers in the format "xmin,ymin,xmax,ymax".

    Returns:
        The new scale of the canvas (a single float)
    """
    ext = [float(x) for x in request.args['rect'].split(',')]
    iface.mapCanvas().setExtent(QgsRectangle(ext[0], ext[1], ext[2], ext[3]))
    # force redraw
    iface.mapCanvas().refresh()
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomToFullExtent')
def mapCanvas_zoomToFullExtent(iface, _):
    """
    Zoom to the full extent of all layers.

    Returns:
        The new scale of the canvas (a single float)
    """
    iface.mapCanvas().zoomToFullExtent()
    return NetworkAPIResult(iface.mapCanvas().scale())

@networkapi('/qgis/mapCanvas/zoomToSelected')
def mapCanvas_zoomToSelected(iface, request):
    """
    Zoom to the extent of the selected features of current (vector) layer.

    HTTP query arguments:
        layer (string): optionally specify different than current layer

    Returns:
        The new scale of the canvas (a single float)
    """
    if request.args.get('layer'):
        iface.mapCanvas().zoomToSelected(qgis_layer_by_id(request.args['layer']))
    else:
        iface.mapCanvas().zoomToSelected()
    return NetworkAPIResult(iface.mapCanvas().scale())
