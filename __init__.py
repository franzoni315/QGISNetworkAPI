# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NetworkAPI
                                 A QGIS plugin
 Remote Control Interface
                             -------------------
        begin                : 2017-05-21
        copyright            : (C) 2017 by Barry Rowlingson
        email                : b.rowlingson@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load NetworkAPI class from file NetworkAPI.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .network_api import NetworkAPI
    return NetworkAPI(iface)
