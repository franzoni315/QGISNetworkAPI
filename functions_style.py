from .functions import qgis_layer_by_id
from .registry import networkapi, NetworkAPIResult, toGeoJSON

from json import loads

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

