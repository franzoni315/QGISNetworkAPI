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
from PyQt4.QtCore import QDate, QDateTime, QPyNullVariant, QSize, QTime, Qt
from qgis.core import QgsFeature, QgsFeatureIterator, QgsFields, QgsGeometry, QgsMapLayer, QgsMapSettings, QgsPoint, QgsRectangle, QgsCoordinateReferenceSystem, QgsUnitTypes
from qgis.gui import QgsMapCanvas

# TODO: convert python-wrapped C++ enum to string:
# https://riverbankcomputing.com/pipermail/pyqt/2014-August/034630.html
# add conversion for LayerType, https://qgis.org/api/classQgsUnitTypes.html

class QGISJSONEncoder(JSONEncoder):
    def default(self, o):

        ### Qt types (in alphabetical order)
        if isinstance(o, QDate) or isinstance(o, QDateTime) or isinstance(o, QTime):
            # there is not actual date/time type in JSON, so convert to string
            return o.toString(Qt.ISODate)
        elif isinstance(o, QPyNullVariant):
            # Qt's very own 'null'
            return None
        elif isinstance(o, QSize):
            return [o.width(), o.height()]


        ### QGIS types (in alphabetical order)
        elif isinstance(o, QgsCoordinateReferenceSystem):
            return {'description': o.description(), 'srsid': o.srsid(), 'proj4': o.toProj4(), 'postgisSrid': o.postgisSrid()}
        elif isinstance(o, QgsFeature):
            return {'id': o.id(), 'attributes': dict(zip([field.name() for field in o.fields().toList()], o.attributes())) }
        elif isinstance(o, QgsFeatureIterator):
            return list(o)
        elif isinstance(o, QgsFields): # 'isNumeric': f.isNumeric(),  from 2.18
            return [{'name': f.name(), 'comment': f.comment(), 'length': f.length() } for f in o.toList()]
        #elif isinstance(o, QgsGeometry):
          # use QgsVectorFileWriter instead (see below)
        elif isinstance(o, QgsMapSettings):
            return { 'destinationCrs': o.destinationCrs(), 'extent': o.extent(), 'fullExtent': o.fullExtent(), 'layers': o.layers(), 'mapUnits': o.mapUnits(), 'mapUnitsPerPixel': o.mapUnitsPerPixel(), 'outputSize': o.outputSize(), 'rotation': o.rotation(), 'scale': o.scale(), 'visibleExtent': o.visibleExtent()}
        elif isinstance(o, QgsMapLayer):
            return {'id': o.id(), 'valid': o.isValid(), 'name': o.name(), 'type': o.type(), 'publicSource': o.publicSource(), 'crs': o.crs(), 'extent': o.extent(), 'isEditable': o.isEditable()}
        elif isinstance(o, QgsPoint):
            return [o.x(), o.y()]
        elif isinstance(o, QgsRectangle):
            # same order as e.g. sf's 'bbox' class
            return [o.xMinimum(), o.yMinimum(), o.xMaximum(), o.yMaximum()]

        # default encoding -- prints a conversion error in the middle of the
        # HTTP response if the structure is not a primitive
        return JSONEncoder.default(self, o)

def parseCRS(spec):
    crs = QgsCoordinateReferenceSystem(spec) # string or numeric
    if not crs.isValid():
        # check if it's proj4
        if not crs.createFromProj4(str(spec)):
            raise ValueError("Can't process CRS specification: " + str(spec))
    return crs

import os
from tempfile import mkstemp
from qgis.core import QgsVectorFileWriter

def toGeoJSON(layer, features):
    """
    Convert a list of QgsFeatures including their geometries to GeoJSON.
    """
    tmpfile, tmpfilename = mkstemp('.geojson')
    os.close(tmpfile)
    # supporting arbitrary output formats would be great but unfortunately
    # the QgsVectorFileWriter adds an extension to the supplied filename if
    # it doesn't have the correct one already. so in order to robustly
    # support all formats we'd have to create the temporary filename
    # according to QgsVectorFileWriter.supportedFiltersAndFormats()
    # (there's still more added complexity from the fact that some formats
    # are spread across more than one file...)
    writer = QgsVectorFileWriter(tmpfilename, None, layer.fields(), layer.wkbType(), layer.crs(), 'GeoJSON')

    for f in features:
        # TODO check returned boolean?
        writer.addFeature(f)

    if writer.hasError():
        msg = writer.errorMessage()
        del writer
        os.remove(tmpfilename)
        raise IOError(msg)

    # flush to file
    del writer

    with open(tmpfilename, 'r') as content_file:
        content = content_file.read()
    os.remove(tmpfilename)
    return content
