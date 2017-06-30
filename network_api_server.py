from json import dump
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtNetwork import QHostAddress, QTcpServer
from network_api_dialog import NetworkAPIDialog
from network_api_registry import QGISJSONEncoder, Registry
from qgis.core import QgsMessageLog
from qgis.gui import QgsMessageBar

# TODO how to run the two files without actually importing anything?
import network_api_functions
import network_api_doc

class NetworkAPIServer(QTcpServer):

    # signal emitted whenever the server changes state
    # int argument: 0 = stopped, 1 = listening, 2 = waiting for data,
    # 3 = processing request (busy/blocking)
    status_changed = pyqtSignal(int, str)

    def signal_status (self, status, message = ''):
        # TODO fill in default paused/running messages for status 0+1
        self.status_changed.emit(status, message)

    def __init__(self, iface):
        QTcpServer.__init__(self)
        self.iface = iface

        self.iface.newProjectCreated.connect(self.stopServer)
        self.iface.projectRead.connect(self.stopServer)

        # TODO: read project-specific on/off setting, start server if desired
#        self.startServer(NetworkAPIDialog.settings.port())

    def log(self, message, level=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(message, 'NetworkAPI', level=level)

    def status(self, message, level=QgsMessageBar.INFO):
        # always log
        self.log(message, level % 3) # map SUCCESS to INFO
        if NetworkAPIDialog.settings.log():
            self.iface.messageBar().pushMessage('Network API', message, level)

    def stopServer(self):
        if self.isListening():
            self.log('Stopping to listen on port ' + str(self.serverPort()))
            self.close()
            self.signal_status(0, 'Server stopped')

    def startServer(self, port):
        self.stopServer()
        # process one connection/request at a time
        self.connection = None
        self.request = None
        self.nrequests = 0

        self.newConnection.connect(self.new_connection)
        if self.listen(QHostAddress.Any, port):
            self.signal_status(1, 'Listening on port ' + str(self.serverPort()))
            self.log('Listening for Network API requests on port ' + str(self.serverPort()))
        else:
            self.status('Error: failed to open socket on port ' + str(port), QgsMessageBar.CRITICAL)

    def new_connection(self):
        # only accept connection if we're not still busy processing the
        # previous one (in which case the new one will be taken care of when
        # current one finishes, see call to hasPendingConnections() in
        # connection_ended() below)
        if self.connection == None:
            cxn = self.nextPendingConnection()
            if not NetworkAPIDialog.settings.remote_connections() and cxn.peerAddress() != QHostAddress.LocalHost: # FIXME .LocalHostIPv6?
                self.status('Refusing remote connection from ' + cxn.peerAddress().toString(), QgsMessageBar.WARNING)
                cxn.close()
                return
            self.connection = cxn
            self.nrequests = self.nrequests + 1
            self.log('Processing connection #' + str(self.nrequests) + ' (' + self.connection.peerAddress().toString() + ')')
            self.connection.disconnected.connect(self.connection_ended)
            self.connection.readyRead.connect(self.process_data)
            self.process_data()
        else:
            self.log('Still busy with #' + str(self.nrequests) + ', putting incoming connection on hold...')

    def connection_ended(self):
        self.log('Disconnecting #' + str(self.nrequests) + ' (' + self.connection.peerAddress().toString() + ')')
        self.connection.readyRead.disconnect(self.process_data)
        self.request = None
        self.connection = None
        # process waiting connections
        if self.hasPendingConnections():
            self.log('Found pending connection, processing..')
            self.new_connection()

    def process_data(self):
        self.signal_status(2, 'Receiving data...')
        # readAll() doesn't guarantee that there isn't any more data still
        # incoming before reaching the 'end' of the input stream (which, for
        # network connections, is ill-defined anyway). in order to be able to
        # parse incoming requests incrementally, we store the parse request
        # header in a class variable.
        if self.request == None:
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
            while self.connection.waitForReadyRead(0):
                self.request.headers.set_payload(self.request.headers.get_payload() + self.connection.readAll())
        # respond to request or -- if data is still incomplete -- do nothing
        self.process_request()

    def process_request(self):
        self.signal_status(3, 'Processing request...')
        # TODO check authorisation, send 401
        # inspect request.headers['Authorization']

        # find+call function corresponding to given path
        qgis_call = Registry.get(self.request.path)

        if qgis_call == None:
            self.request.send_http_error(404)
        else:
            # TODO do we care about whether correct HTTP method was used (405)?

            if self.request.command == 'POST':
                self.status('POST data: received ' + str(len(self.request.headers.get_payload())) + ' of ' + str(self.request.content_length))

                if len(self.request.headers.get_payload()) < self.request.content_length:
                    # request body incomplete, wait for more data to arrive.
                    return
                    # TODO maybe implement a timeout using QTimer so that
                    # malformed/incomplete requests which keep their
                    # connections open do not block the plugin?

            # looks like we have all the data, execute call
            self.perform_request(qgis_call)

        self.status('Processed request #' + str(self.nrequests) + ': ' + self.request.log_string)#, QgsMessageBar.SUCCESS)
        # pass output generated by BaseHTTPRequestHandler on to the QTcpSocket
        self.connection.write(self.request.wfile.getvalue())
        # flush response and close connection (i.e. no persistent connections)
        self.connection.disconnectFromHost()
        self.signal_status(1)

    def perform_request(self, qgis_call):
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
            self.status('Invalid request, should probably force disconnect?', QgsMessageBar.WARNING)

    def send_http_error(self, code, message=None):
        if message == None:
           self.error_message_format = '%(code)d %(message)s: %(explain)s\n'
        else:
           self.error_message_format = '%(code)d: ' + message + '\n'
        self.error_content_type = 'text/plain'
        self.send_error(code)

    def log_message(self, format, *args):
        self.log_string = self.client_address[0] + ' ' + format%args
