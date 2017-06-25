from functools import wraps

class Registry:
    __singleton = None
    paths = {}

    @staticmethod
    def instance():
        if Registry.__singleton == None:
            Registry()
        return Registry.__singleton

    def __init__(self):
        if Registry.__singleton == None:
            Registry.__singleton = self

    @staticmethod
    def add_path(path, handler_function):
        Registry.instance().paths[path.rstrip('/')] = handler_function

    @staticmethod
    def get(path):
        return Registry.instance().paths.get(path)

# @networkapi decorator for functions processing iface and request
def networkapi(path):
    def register(handler_function):
        Registry.add_path(path, handler_function)
        def func_wrapper(request):
            return handler_function(request)
        return wraps(handler_function)(func_wrapper)
    return register

class NetworkAPIResult:
    # TODO what status to send in case of invalid/malformed request arguments?
    INVALID_ARGUMENTS = 418

    def __init__(self, body = None, content_type = None, status = 200):
        self.body = body
        self.content_type = content_type
        self.status = status
# response body can be of any type and will be automatically converted using
# json.dump() based on the following encoder:

from json import JSONEncoder
from PyQt4.QtCore import QPyNullVariant
from qgis.core import QgsFeature, QgsFeatureIterator, QgsFields, QgsGeometry, QgsMapLayer, QgsPoint, QgsRectangle, QgsCoordinateReferenceSystem, QgsUnitTypes
from qgis.gui import QgsMapCanvas

# TODO: convert python-wrapped C++ enum to string:
# https://riverbankcomputing.com/pipermail/pyqt/2014-August/034630.html
# add conversion for LayerType, https://qgis.org/api/classQgsUnitTypes.html

class QGISJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, QgsFeature):
            return {'id': o.id(), 'attributes': dict(zip([field.name() for field in o.fields().toList()], o.attributes())) }
        elif isinstance(o, QgsFields): # 'isNumeric': f.isNumeric(),  from 2.18
            return [{'name': f.name(), 'comment': f.comment(), 'length': f.length() } for f in o.toList()]
#        elif isinstance(o, QgsGeometry):
            # FIXME this actually returns a string, not a json structure...
            #return o.exportToGeoJSON()
        elif isinstance(o, QgsMapCanvas):
            return {'extent': o.extent(), 'crs': o.mapSettings().destinationCrs(), 'mapUnits': 0 } # TODO
        elif isinstance(o, QgsMapLayer):
            return {'id': o.id(), 'name': o.name(), 'type': o.type(), 'publicSource': o.publicSource(), 'crs': o.crs(), 'extent': o.extent(), 'isEditable': o.isEditable()}
        elif isinstance(o, QgsCoordinateReferenceSystem):
            return {'description': o.description(), 'srsid': o.srsid(), 'proj4': o.toProj4(), 'postgisSrid': o.postgisSrid()}
        elif isinstance(o, QgsPoint):
            return [o.x(), o.y()]
        elif isinstance(o, QgsRectangle):
            return [o.xMinimum(), o.yMinimum(), o.xMaximum(), o.yMaximum()]
        elif isinstance(o, QPyNullVariant):
            # Qt's very own 'null'
            return None
        return JSONEncoder.default(self, o)
