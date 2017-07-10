from PyQt4.QtCore import QSettings

class NetworkAPISettings(QSettings):
    """A QSettings object wrapped into its own class to provide type-specific get accessors with correct default values"""

    def __init__(self):
        # on Linux, this will be $HOME/.config/QGIS/NetworkAPI.ini
        QSettings.__init__(self, QSettings.IniFormat, QSettings.UserScope, 'QGIS', 'NetworkAPI')

    def port(self):
        return self.value('port', 8090, int)

    def remote_connections(self):
        # allow only local (IPv4) connections by default
        return self.value('remote_connections', False, bool)

    def security(self):
        # no security an ok default if only local connections are allowed anyway
        return self.value('security', 0, int)

    def auth(self):
        return self.value('auth', '', unicode)

    def log(self):
        return self.value('log', True, bool)
