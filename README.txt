# QGIS Desktop Network API and remote control plugin

This plugin provides a web service API that exposes QGIS' data processing and canvas drawing functionalities. The plugin provides a way to include QGIS in the data processing workflow of other (‘mapping-deficient’) programming languages over a HTTP interface which mirrors the existing QGIS API, without precluding the ability to make use of its interactive editing components. It is currently under development as part of [this Google Summer of Code 2017 project](https://summerofcode.withgoogle.com/projects/#5197021490184192).

## Testing

The plugin is currently under development so there is not a whole lot of (reliable) documentation. You can nevertheless try out and help test the current development version of the plugin:

1. Install the plugin into your $QGIS_HOME/plugins/ folder, either by `git clone`ing this repository or by downloading the latest snapshot as a [zip file](https://gitlab.com/qgisapi/networkapi/repository/archive.zip?ref=master).
2. In QGIS (2.*), activate the plugin under Plugins > Manage and Install Plugins > 'Network API'
3. Once activated, the plugin will automatically start listening for (and accept all) connections on port 8090. (The plugin dialog is currently just a mockup, it is not configurable yet.)
4. Access the web service API, currently implemented requests/paths can be found [here](https://gitlab.com/qgisapi/networkapi/blob/master/network_api_functions.py). Some example commands that can be run from your console:

```{bash}
# add some vector data from the web
curl http://localhost:8090/qgis/addVectorLayer?file=https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson

# add another layer as POST data (currently only reliable for small files!)
wget https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson
curl -d @ne_50m_populated_places.geojson http://localhost:8090/qgis/addVectorLayer

# adjust view
curl http://localhost:8090/qgis/mapCanvas/zoomToFullExtent

# retrieve current scale
curl http://localhost:8090/qgis/mapCanvas/scale

# read current canvas content
# these two urls also work in a browser (although currently not under Chrome)
wget http://localhost:8090/qgis/mapCanvas
wget http://localhost:8090/qgis/mapCanvas?format=jpg

# some more canvas manipulation
curl http://localhost:8090/qgis/mapCanvas/zoomIn
curl http://localhost:8090/qgis/mapCanvas/zoomScale?scale=12345.6
```

### Test data

http://blog.mastermaps.com/2011/02/natural-earth-vectors-in-cloud.html
