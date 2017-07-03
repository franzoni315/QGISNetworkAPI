# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NetworkAPIDialog
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

import os

from PyQt4 import uic
from PyQt4.QtGui import QDialog, QDialogButtonBox, QIntValidator
from .settings import NetworkAPISettings

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'network_api_dialog_base.ui'))


class NetworkAPIDialog(QDialog, FORM_CLASS):

    settings = NetworkAPISettings()

    def __init__(self, parent=None):
        """Constructor."""
        super(NetworkAPIDialog, self).__init__(parent)
        self.setupUi(self)
        # After setupUI you can access any designer object by doing
        # self.<objectname>

        self.port.setValidator(QIntValidator(0, 65536))
        self.buttons.clicked.connect(self.handleButtonClick)
        self.loadSettings()

    def loadSettings(self):
        self.port.setText(str(NetworkAPIDialog.settings.port()))
        self.remote_connections.setChecked(NetworkAPIDialog.settings.remote_connections())
        self.security.setCurrentIndex(NetworkAPIDialog.settings.security())
        self.auth.setText(NetworkAPIDialog.settings.auth())
        self.log.setChecked(NetworkAPIDialog.settings.log())

    def saveSettings(self):
        NetworkAPIDialog.settings.setValue('port', self.port.text())
        NetworkAPIDialog.settings.setValue('remote_connections', self.remote_connections.isChecked())
        NetworkAPIDialog.settings.setValue('security', self.security.currentIndex())
        NetworkAPIDialog.settings.setValue('auth', self.auth.text())
        NetworkAPIDialog.settings.setValue('log', self.log.isChecked())

    def handleButtonClick(self, button):
        sb = self.buttons.standardButton(button)
        # this could be more elegant by conditioning on button *roles*..
        if sb == QDialogButtonBox.Apply or sb == QDialogButtonBox.Ok:
            # TODO check if port, remote_connections or auth changed, if so
            # trigger server restart after saving
            self.saveSettings()
        else: # Reset or Cancel
            self.loadSettings()
