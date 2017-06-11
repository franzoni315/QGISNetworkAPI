QGIS Desktop Network API and remote control plugin
==================================================

This plugin provides a web service API that exposes QGIS' data processing and canvas drawing functionalities. The plugin provides a way to include QGIS in the data processing workflow of other (‘mapping-deficient’) programming languages over a HTTP interface which mirrors the existing QGIS API, without precluding the ability to make use of its interactive editing components. It is currently under development as part of [this Google Summer of Code 2017 project](https://summerofcode.withgoogle.com/projects/#5197021490184192).

Testing
-------

The plugin is currently under development so there is not a whole lot of (reliable) documentation. You can nevertheless try out and help test the current development version of the plugin:

1.  Install the plugin into your $QGIS\_HOME/plugins/ folder, either by `git clone`ing this repository or by downloading the latest snapshot as a [zip file](https://gitlab.com/qgisapi/networkapi/repository/archive.zip?ref=master).
2.  In QGIS (2.\*), activate the plugin under Plugins &gt; Manage and Install Plugins &gt; 'Network API'
3.  Once activated, the plugin will automatically start listening for (and accept all) connections on port 8090. (The plugin dialog is currently just a mockup, it is not configurable yet.)
4.  Access the web service API, currently implemented requests/paths can be found [here](https://gitlab.com/qgisapi/networkapi/blob/master/network_api_functions.py). Some example commands that can be run from your console:

``` bash
# make sure QGIS Desktop 2.* is running with the Network Plugin enabled, then:
curl --silent http://localhost:8090/qgis/mapLayers
```

    ## {}

``` bash
# add some vector data from the web
curl --silent 'http://localhost:8090/qgis/addVectorLayer?uri=https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson&name=uri-layer'
```

    ## {
    ##   "crs": {
    ##     "postgisSrid": 4326, 
    ##     "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##     "srsid": 3452, 
    ##     "description": "WGS 84", 
    ##     "wkt": "GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]]"
    ##   }, 
    ##   "name": "uri-layer", 
    ##   "isEditable": false, 
    ##   "publicSource": "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson", 
    ##   "extent": [
    ##     -175.22056447761656, 
    ##     -89.99999981438727, 
    ##     179.21664709402887, 
    ##     78.21668438639699
    ##   ], 
    ##   "type": 0
    ## }

``` bash
# add another layer as POST data
if [ ! -f "ne_50m_populated_places.geojson" ]; then
  wget https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson
fi
curl --silent -d @ne_50m_populated_places.geojson http://localhost:8090/qgis/addVectorLayer?name=geojson-layer
```

    ## {
    ##   "crs": {
    ##     "postgisSrid": 4326, 
    ##     "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##     "srsid": 3452, 
    ##     "description": "WGS 84", 
    ##     "wkt": "GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]]"
    ##   }, 
    ##   "name": "geojson-layer", 
    ##   "isEditable": false, 
    ##   "publicSource": "/tmp/tmplhLaBv.geojson", 
    ##   "extent": [
    ##     -175.22056447761656, 
    ##     -89.99999981438727, 
    ##     179.21664709402887, 
    ##     78.21668438639699
    ##   ], 
    ##   "type": 0
    ## }

``` bash
# retrieve layer information
curl --silent http://localhost:8090/qgis/mapLayers
```

    ## {
    ##   "uri_layer20170611151337103": {
    ##     "crs": {
    ##       "postgisSrid": 4326, 
    ##       "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##       "srsid": 3452, 
    ##       "description": "WGS 84", 
    ##       "wkt": "GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]]"
    ##     }, 
    ##     "name": "uri-layer", 
    ##     "isEditable": false, 
    ##     "publicSource": "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson", 
    ##     "extent": [
    ##       -175.22056447761656, 
    ##       -89.99999981438727, 
    ##       179.21664709402887, 
    ##       78.21668438639699
    ##     ], 
    ##     "type": 0
    ##   }, 
    ##   "geojson_layer20170611151340105": {
    ##     "crs": {
    ##       "postgisSrid": 4326, 
    ##       "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##       "srsid": 3452, 
    ##       "description": "WGS 84", 
    ##       "wkt": "GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]]"
    ##     }, 
    ##     "name": "geojson-layer", 
    ##     "isEditable": false, 
    ##     "publicSource": "/tmp/tmplhLaBv.geojson", 
    ##     "extent": [
    ##       -175.22056447761656, 
    ##       -89.99999981438727, 
    ##       179.21664709402887, 
    ##       78.21668438639699
    ##     ], 
    ##     "type": 0
    ##   }
    ## }

``` bash
curl --silent http://localhost:8090/qgis/mapCanvas/extent
```

    ## [
    ##   -287.00476950471307, 
    ##   -94.20541691940687, 
    ##   291.0008521211254, 
    ##   82.42210149141658
    ## ]

``` bash
# adjust view
curl --silent http://localhost:8090/qgis/mapCanvas/zoomToFullExtent
curl --silent http://localhost:8090/qgis/mapCanvas/extent
```

    ## [
    ##   -287.00476950471307, 
    ##   -94.20541691940687, 
    ##   291.0008521211254, 
    ##   82.42210149141658
    ## ]

``` bash
# read current canvas content
wget --no-verbose http://127.0.0.1:8090/qgis/mapCanvas
file "mapCanvas"
```

    ## 2017-06-11 15:13:41 URL:http://127.0.0.1:8090/qgis/mapCanvas [68643] -> "mapCanvas" [1]
    ## mapCanvas: PNG image data, 1093 x 334, 8-bit/color RGBA, non-interlaced

``` bash
wget --no-verbose http://127.0.0.1:8090/qgis/mapCanvas?format=jpg
file "mapCanvas?format=jpg"
```

    ## 2017-06-11 15:13:42 URL:http://127.0.0.1:8090/qgis/mapCanvas?format=jpg [49932] -> "mapCanvas?format=jpg" [1]
    ## mapCanvas?format=jpg: JPEG image data, JFIF standard 1.01, resolution (DPI), density 96x96, segment length 16, baseline, precision 8, 1093x334, frames 3

``` bash
# retrieve current scale
curl --silent http://localhost:8090/qgis/mapCanvas/scale
```

    ## 206580052.33307433

``` bash
# some more canvas manipulation
curl --silent http://localhost:8090/qgis/mapCanvas/zoomIn
curl --silent http://localhost:8090/qgis/mapCanvas/scale
```

    ## 103290026.16653717

``` bash
curl --silent http://localhost:8090/qgis/mapCanvas/zoomScale?scale=1234567.8
curl --silent http://localhost:8090/qgis/mapCanvas/scale
```

    ## 1234567.800000001

### Test data

<http://blog.mastermaps.com/2011/02/natural-earth-vectors-in-cloud.html>

Related projects
----------------

The motivation behind this plugin is to make QGIS interface components available and scriptable from other mapping-averse programming language such as R. See <https://gitlab.com/b-rowlingson/pqgisr>

For using QGIS processing routines from R (geared towards performing large scale data mangling without making use of QGIS UI components, with a significant overhead per processing invocation), have a look at the [RQGIS package](https://github.com/jannes-m/RQGIS).
