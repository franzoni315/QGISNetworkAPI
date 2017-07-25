from json import dump
from PyQt4.QtCore import pyqtSignal, QTimer
from PyQt4.QtNetwork import QHostAddress, QTcpServer
from network_api_dialog import NetworkAPIDialog
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar

from .registry import QGISJSONEncoder, Registry

from . import doc
from . import functions
from . import functions_processing
from . import functions_style

class NetworkAPIServer(QTcpServer):

    # signal emitted whenever the server changes state
    # int argument: 0 = stopped, 1 = listening, 2 = waiting for data,
    # 3 = processing request (busy/blocking)
    status_changed = pyqtSignal(int, str)

    def emitStatusSignal (self, status, message = None):
        # fill in default paused/running messages for status 0+1
        if message == None:
            if status == 0:
                message = 'Network API disabled'
            elif status == 1:
                message = 'Listening on port ' + str(self.serverPort())
        self.log(message)
        self.status_changed.emit(status, message)

    def __init__(self, iface):
        QTcpServer.__init__(self)
        self.iface = iface

        # TODO trigger different method which checks project-specific settings
#        self.iface.newProjectCreated.connect(self.stopServer)
        self.iface.projectRead.connect(self.stopServer)

        # timer for interrupting open connections on inactivity
        self.timer = QTimer()
        self.timer.setInterval(3000) # 3 seconds, worth making configurable?
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timeout)

        # TODO: read project-specific on/off setting, start server if desired
#        self.startServer(NetworkAPIDialog.settings.port())

    def log(self, message, level=QgsMessageLog.INFO):
        "Print a message to QGIS' Log Messages Panel"
        QgsMessageLog.logMessage(message, 'NetworkAPI', level=level)

    def showMessage(self, message, level=QgsMessageBar.INFO):
        "If enabled by the config, display a log message in QGIS' message bar"
        # always log
        # the message bar and log panel have different message status ranges -
        # the modulo (%) merely maps the messages' SUCCESS status to the log
        # panel's INFO
        self.log(message, level % 3)
        if NetworkAPIDialog.settings.log():
            # TODO make message timeout configurable? 
            self.iface.messageBar().pushMessage('Network API', message, level, 5)

    def stopServer(self):
        if self.isListening():
            self.log('Stopping to listen on port ' + str(self.serverPort()))
            # open/running requests are automatically wrapped up through their
            # 'disconnect' signal triggering finishConnection()
            self.close()
            self.emitStatusSignal(0)

    def startServer(self, port):
        self.stopServer()
        # process one connection/request at a time
        self.connection = None
        self.request = None
        self.nrequests = 0

        self.newConnection.connect(self.acceptConnection)
        if self.listen(QHostAddress.Any, port):
            self.emitStatusSignal(1)
        else:
            self.showMessage('Failed to open socket on port ' + str(port), QgsMessageBar.CRITICAL)
            self.emitStatusSignal(0, 'Error: failed to open socket on port ' + str(port))

    def acceptConnection(self):
        """Accept a new incoming connection request. If the server is still
        busy processing an earlier request, the function returns immediately and the new incoming connection will be taken care of when the current
        request is finished (see the call to hasPendingConnections() in
        finishConnection() below)"""
        if self.connection == None:
            cxn = self.nextPendingConnection()
            if not NetworkAPIDialog.settings.remote_connections() and cxn.peerAddress() != QHostAddress.LocalHost: # FIXME .LocalHostIPv6?
                self.showMessage('Refusing remote connection from ' + cxn.peerAddress().toString(), QgsMessageBar.WARNING)
                cxn.close()
                return
            self.connection = cxn
            self.nrequests = self.nrequests + 1
            self.log('Processing connection #' + str(self.nrequests) + ' (' + self.connection.peerAddress().toString() + ')')
            self.connection.disconnected.connect(self.finishConnection)
            self.connection.readyRead.connect(self.readFromConnection)
            self.readFromConnection()
        else:
            self.log('Still busy with #' + str(self.nrequests) + ', putting incoming connection on hold...')

    def readFromConnection(self):
        # readAll() doesn't guarantee that there isn't any more data still
        # incoming before reaching the 'end' of the input stream (which, for
        # network connections, is ill-defined anyway). in order to be able to
        # parse incoming requests incrementally, we store the parse request
        # header in a class variable.

        # (re)set connection timeout
        self.timer.start()

        if self.request == None:
            self.emitStatusSignal(2, 'Connection opened...')
            if not self.connection.canReadLine():
                self.log('Warning: readyRead() was signalled before full HTTP request line was available for reading (' + str(self.connection.bytesAvailable()) + ' bytes in buffer)', QgsMessageLog.WARNING)
                return
            # new request, parse header
            self.request = NetworkAPIRequest(self.connection)
        else:
            # additional data for previous request, append to payload. the loop
            # is necessary to work around a race condition where data is added
            # after readAll() but, because the present function is still busy,
            # readyRead is not emitted again.
            while True:
                self.request.headers.set_payload(self.request.headers.get_payload() + self.connection.readAll())
                if not self.connection.waitForReadyRead(0):
                    break
        # respond to request or -- if data is still incomplete -- do nothing
        self.processRequest()

    def processRequest(self):
        if NetworkAPIDialog.settings.security():
            if request.headers['Authorization'] != NetworkAPIDialog.settings.auth():
                # TODO log/message?
                self.sendError(401)
                return

        # find+call function corresponding to given path
        qgis_call = Registry.get(self.request.path)

        if qgis_call == None:
            self.sendError(404)
            return

        # if some path that only processes GET requests was submitted with a
        # POST body, we receive + accept it anyway instead of throwing a 405...
        if self.request.command == 'POST':
            self.emitStatusSignal(2, 'Processing request: received ' + str(len(self.request.headers.get_payload())) + ' of ' + str(self.request.content_length))

            if len(self.request.headers.get_payload()) < self.request.content_length:
                # request body incomplete, wait for more data to arrive --
                # timeout is controlled by the lower-level readFromConnection()
                return

        # looks like we have all the data, execute call
        self.timer.stop()
        self.emitStatusSignal(3, 'Executing request...')
        # response is written and connection closed in executeRequest()
        self.executeRequest(qgis_call)

    def sendResponse(self):
        # pass output generated by BaseHTTPRequestHandler on to the QTcpSocket
        self.connection.write(self.request.wfile.getvalue())
        # flush response and close connection (i.e. no persistent connections)
        # calling this will cause a signal to trigger finishConnection() for
        # actual connection cleanup
        self.connection.disconnectFromHost()

    def sendError(self, status):
        self.request.send_http_error(status)
        self.sendResponse()

    def timeout(self):
        if self.connection:
            self.showMessage('Connection timed out after ' + str(self.timer.interval()) + 'ms', QgsMessageBar.WARNING)
            self.finishConnection()

    def finishConnection(self):
        """Gracefully disconnect a peer and clean up the network connection."""
        self.log('Disconnecting #' + str(self.nrequests) + ' (' + self.connection.peerAddress().toString() + ')')
        self.connection.readyRead.disconnect(self.readFromConnection)
        self.connection.disconnected.disconnect(self.finishConnection)
        self.request = None
        self.connection = None
        # process waiting connections
        if self.hasPendingConnections():
            self.log('Found pending connection, processing..')
            self.acceptConnection()
        else:
            # back to listening
            self.emitStatusSignal(1)

    def executeRequest(self, qgis_call):
        """Execute a command retrieved from the registry"""
        try:
            result = qgis_call(self.iface, self.request)
            self.request.send_response(result.status)
            if result.content_type:
                self.request.send_header('Content-Type', result.content_type)
                self.request.end_headers()
                self.request.wfile.write(result.body)
            else:
                # autoconvert python classes using JSONEncoder below.
                # note that GeoJSON results are NOT handled here!
                self.request.send_header('Content-Type', 'application/json')
                self.request.end_headers()
                dump(result.body, self.request.wfile, cls=QGISJSONEncoder, indent=2)
            # connection will be closed by parent function
        except Exception as e:
            self.request.send_http_error(500, str(e))
            # TODO if request failed, add link to docs at /api?path=... ?
        self.showMessage('Executed request #' + str(self.nrequests) + ': ' + self.request.log_string)#, QgsMessageBar.SUCCESS)
        self.sendResponse()

# request parsing
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
from email import message_from_file # TODO replace by _from_string
from urlparse import parse_qsl, urlparse

class NetworkAPIRequest(BaseHTTPRequestHandler):

    # default mimetools.Message is deprecated and removed in Python 3. instead,
    # mock function signature for MessageClass(self.rfile, 0) call to email.*

    # this currently loads the entire body of the message into memory, could
    # do incremental parsing instead and pass the network-inputstream?
    MessageClass = lambda self, fp, _: message_from_file(fp)

    def __init__(self, connection):
        self.server_version = 'QGISNetworkAPI/0.0 ' + self.server_version

        # mock input/output files for the BaseRequestHandler
        self.rfile = StringIO(str(connection.readAll()))
        self.wfile = StringIO()

        self.raw_requestline = self.rfile.readline()

        # client_address is really just used for logging
        self.client_address = (connection.peerAddress().toString(), connection.peerPort())

        if self.parse_request():
            # class fields now populated: command, path, headers
            if self.command == 'POST':
                self.content_length = int(self.headers['Content-Length'])

            # further parse request path: detach GET arguments
            parsed_path = urlparse(self.path)
            self.path = parsed_path[2].rstrip('/')
            # parse key=value pairs, keep keys with blank values
            self.args = dict(parse_qsl(parsed_path[4], True))
        else:
            self.showMessage('Invalid request, should probably force disconnect?', QgsMessageBar.WARNING)
            # TODO throw exception

    def send_http_error(self, code, message=None):
        if message == None:
           self.error_message_format = '%(code)d %(message)s: %(explain)s\n'
        else:
           self.error_message_format = '%(code)d: ' + message + '\n'
        self.error_content_type = 'text/plain'
        self.send_error(code)

    def log_message(self, format, *args):
        self.log_string = self.client_address[0] + ' ' + format%args
