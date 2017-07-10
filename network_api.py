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

from PyQt4.QtCore import QSettings, Qt, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QCheckBox, QIcon
from PyQt4.Qt import QPalette
# Initialize Qt resources from file resources.py
import resources

# Import the code for the dialog
from network_api_dialog import NetworkAPIDialog
from .server import NetworkAPIServer
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
        text,
        callback,
        icon=QIcon(':/plugins/NetworkAPI/icon.png'),
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
        self.add_action(
            text=self.tr(u'Configure Network API'),
            callback=self.showConfigDialog,
            parent=self.iface.mainWindow())

        self.statusbutton = QCheckBox()
        # replace checkbox with icon that is b/w when button is not checked
#        self.statusbutton.setStyleSheet('QCheckBox::icon::checked { image: url(:/plugins/NetworkAPI/icon.png);} QCheckBox::icon::unchecked { image: url(:/plugins/NetworkAPI/icon-bw.png);}')
        self.statusbutton.setText('Network API plugin')
        # TODO set initial tooltip?

        self.statusbutton.clicked.connect(self.toggleServer)
        self.dlg.toggle.clicked.connect(self.toggleServer)
        self.dlg.server_port_changed.connect(self.serverConfigChanged)

        self.iface.mainWindow().statusBar().addPermanentWidget(self.statusbutton)

        # connect server signals to update status button etc
        self.serversingleton.status_changed.connect(self.serverStatusChanged)

    def toggleServer(self, toggled):
        if toggled:
            self.serversingleton.startServer(NetworkAPIDialog.settings.port())
        else:
            self.serversingleton.stopServer()

    def serverConfigChanged(self):
        if self.serversingleton.isListening():
            self.toggleServer(True)

    def serverStatusChanged(self, status, description):
        # only 0 = off
        self.statusbutton.setChecked(bool(status))
        self.statusbutton.setToolTip(description)
        self.dlg.status.setText(description)
        self.dlg.toggle.setChecked(bool(status))
        self.dlg.toggle.setText('Disable API' if bool(status) else 'Enable API')

        if status == 2: # receiving data
            self.statusbutton.setStyleSheet('background-color: yellow;')
        elif status == 3: # processing request (blocking)
            self.statusbutton.setStyleSheet('background-color: red;')
        elif status == 1: # listening
            self.statusbutton.setStyleSheet('')
        else: # off
            self.statusbutton.setStyleSheet('')


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.serversingleton.stopServer()
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        self.iface.mainWindow().statusBar().removeWidget(self.statusbutton)
        del self.statusbutton


    def showConfigDialog(self):
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # no need to check the result -- the dialog itself takes care of
        # restarting the server in case of port/config changes etc.
