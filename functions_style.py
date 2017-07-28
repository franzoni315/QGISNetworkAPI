# -*- coding: utf-8 -*-

# network api functions to be added to the call path registry
#
# the functions should take two arguments: the first is the 'iface' variable
# which gives access to QGIS components, the second a NetworkAPIRequest object.
#
# the functions should return an instance of NetworkAPIResult

from .functions import qgis_layer_by_id
from .registry import networkapi, NetworkAPIResult, toGeoJSON

from PyQt4.QtXml import QDomDocument

# GET/POST overloading for reading/writing style XML
@networkapi('/qgis/mapLayer/style')
def mapLayer_style(iface, request):
    """
    Retrieve or set the style for the layer with the given id.

    If the request is a HTTP POST request, attempts to set the XML style description of the given layer to the value of the request body. In all cases, the response will contain the XML style definition for the layer after applying the change (which might be the same as the request body if applying the new style was unsuccessful).

    HTTP query arguments:
        id (string): ID of layer whose stylesheet to retrieve or set

    Returns:
        The XML style definition for the layer with the given ID.
    """
    layer = qgis_layer_by_id(request.args['id'])
    if request.command == 'POST':
        doc = QDomDocument('xml')
        # FIXME it appears that layer.readStyle() ALWAYS return True (at least
        # for VectorLayers) -- error messages are written into the second
        # (string pointer) argument of the method, which I'm not sure how to
        # access from Python...
        # Another workaround would be to re-retrieve the XML style after
        # setting it and flagging up if there is a difference between the two
        # (i.e. if the change was not applied)
        if not doc.setContent(request.headers.get_payload()) or not layer.readStyle(doc, None):
            return NetworkAPIResult(status=NetworkAPIResult.INVALID_ARGUMENTS)

    doc = QDomDocument('xml')
    root = doc.createElement('maplayer')
    doc.appendChild(root)
    # TODO check return value (although this really shouldn't fail..)
    layer.writeStyle(root, doc, '')
    return NetworkAPIResult(doc.toString(), 'text/xml')

@networkapi('/qgis/mapLayer/styleURI')
def mapLayer_styleURI(iface, request):
    """Retrieve the style URI for a layer."""
    location = qgis_layer_by_id(request.args['id']).styleURI()
    # TODO check if file exists, if so transfer content
    return NetworkAPIResult(location)

@networkapi('/qgis/mapLayer/loadDefaultStyle')
def mapLayer_loadDefaultStyle(iface, request):
    """Retrieve the default style for this layer if one exists.

    Retrieve the default style for this layer if one exists, either as a .qml file on disk or as a record in the users style table in their personal qgis.db.

    HTTP query arguments:
        id (string): ID of the layer whose default style to load

    Returns:
        A string with any status messages
    """
    return NetworkAPIResult(qgis_layer_by_id(request.args['id']).loadDefaultStyle(None))

@networkapi('/qgis/mapLayer/loadNamedStyle')
def mapLayer_loadNamedStyle(iface, request):
    """Retrieve a named style for this layer.

    Retrieve a named style for this layer if one exists (either as a .qml file on disk or as a record in the users style table in their personal qgis.db)

    HTTP query arguments:
        id (string): ID of the layer whose style to load
        uri (string): the file name or other URI for the style file. First an attempt will be made to see if this is a file and load that, if that fails the qgis.db styles table will be consulted to see if there is a style who's key matches the URI.

    Returns:
        A string with any status messages
    """
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.loadNamedStyle(request.args['uri'], None))

@networkapi('/qgis/mapLayer/saveNamedStyle')
def mapLayer_saveNamedStyle(iface, request):
    """Save the properties of this layer as a named style (either as a .qml file on disk or as a record in the users style table in their personal qgis.db)

    HTTP query arguments:
        id (string): ID of the layer whose style to save
        uri (string): the file name or other URI for the style file. First an attempt will be made to see if this is a file and save to that, if that fails the qgis.db styles table will be used to create a style entry who's key matches the URI.

    Returns:
        A string with any status messages
    """
    layer = qgis_layer_by_id(request.args['id'])
    return NetworkAPIResult(layer.saveNamedStyle(request.args['uri'], None))
