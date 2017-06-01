# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NetworkAPI
                                 A QGIS plugin
 Remote Control Interface
                              -------------------
        begin                : 2017-05-21
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Barry Rowlingson
        email                : b.rowlingson@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from network_api_dialog import NetworkAPIDialog
import os.path


class NetworkAPI:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'NetworkAPI_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Network API')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'NetworkAPI')
        self.toolbar.setObjectName(u'NetworkAPI')

        self.serversingleton = NetworkAPIServer(self.iface)
        # to save clicks while developing: immediately start server on load
        self.serversingleton.startServer(8090)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('NetworkAPI', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = NetworkAPIDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/NetworkAPI/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Remote Control'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        self.serversingleton.stopServer()


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            self.serversingleton.startServer(8090)


# collect imports here, since this class might want to be moved to its own file
from PyQt4.QtNetwork import QTcpServer
from PyQt4.QtCore import SIGNAL

class NetworkAPIServer(QTcpServer):
    def __init__(self, iface):
        QTcpServer.__init__(self)
        self.iface = iface

    def stopServer(self):
        if self.isListening():
            print 'Stopping to listen on port', self.serverPort()
            self.close()

    def startServer(self, port):
        self.stopServer()

        self.connect(self, SIGNAL("newConnection()"), self.processRequest)
        if self.listen(port=port):
            print 'Listening for Network API requests on port', self.serverPort()
        else:
          print 'Error: failed to open socket at port', port

    def processRequest(self):
        connection = self.nextPendingConnection()

        # FIXME querying one of the connection's fields before passing it on to
        # the NetworkAPIRequest is in fact required, otherwise the content read
        # from the connection is for some reason empty? This might have to do
        # with Qt, maybe NetworkAPIRequest would have to be a QObject too?
        print 'New connection from', connection.peerAddress().toString()
        request = NetworkAPIRequest(connection)

        print 'Request path structure:', request.path_components
        # TODO find+call function corresponding to given path (from a dict?)

        # return status (and content) will come from the previous function call
        request.send_response(200)
        request.end_headers()
        request.wfile.write('Foo')

        # write response content collected in wfile StringIO to the connection
        connection.write(request.wfile.getvalue())
        # flush response and close connection (i.e. no persistent connections)
        connection.disconnectFromHost()

# request parsing
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
from urlparse import urlparse

class NetworkAPIRequest(BaseHTTPRequestHandler):

    def __init__(self, connection):
        self.server_version = 'QGISNetworkAPI/0.0 ' + self.server_version

        # mock input/output files for the BaseRequestHandler
        self.rfile = StringIO(str(connection.readAll()))
        self.raw_requestline = self.rfile.readline()
        self.wfile = StringIO()

        # client_address is really just used for logging
        self.client_address = (connection.peerAddress().toString(), connection.peerPort())

        self.error_code = self.error_message = None
        self.parse_request()

        # further parse request path
        parsed_path = urlparse(self.path)
        self.path_components = parsed_path[2][1:].split('/')
        self.query = parsed_path[4]
