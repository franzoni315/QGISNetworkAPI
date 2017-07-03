from PyQt4.QtCore import QSettings

# a QSettings object wrapped into its own class to provide type-specific
# get accessors with correct default values 
class NetworkAPISettings(QSettings):
    def __init__(self):
        # on Linux, this will be $HOME/.config/QGIS/NetworkAPI.ini
        QSettings.__init__(self, QSettings.IniFormat, QSettings.UserScope, 'QGIS', 'NetworkAPI')

    def port(self):
        return self.value('port', 8090, int)

    def remote_connections(self):
        return self.value('remote_connections', False, bool)

    def security(self):
        return self.value('security', 0, int) # no security a good default?

    def auth(self):
        return self.value('auth', '', unicode)

    def log(self):
        return self.value('log', True, bool)
