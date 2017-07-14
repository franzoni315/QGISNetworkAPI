QGIS Desktop Network API and remote control plugin
==================================================

This plugin provides a web service API that exposes QGIS' data processing and canvas drawing functionalities. The plugin provides a way to include QGIS in the data processing workflow of other (‘mapping-deficient’) programming languages over a HTTP interface which mirrors the existing QGIS API, without precluding the ability to make use of its interactive editing components. It is currently under development as part of [this Google Summer of Code 2017 project](https://summerofcode.withgoogle.com/projects/#5197021490184192).

Testing
-------

The plugin is currently under development so there is not a whole lot of (reliable) documentation. You can nevertheless try out and help test the current development version of the plugin:

1.  Install the plugin into your $QGIS\_HOME/plugins/ folder, either by `git clone`ing this repository or by downloading the latest snapshot as a [zip file](https://gitlab.com/qgisapi/networkapi/repository/archive.zip?ref=master).
2.  In QGIS (2.\*), activate the plugin under Plugins &gt; Manage and Install Plugins &gt; 'Network API'
3.  Once activated, the plugin will automatically start listening for (and accept all) connections on port 8090. (The plugin dialog is currently just a mockup, it is not configurable yet.)
4.  Access the web service API, currently implemented requests/paths can be found [here](https://gitlab.com/qgisapi/networkapi/blob/master/functions.py). Some example commands that can be run from your console:

``` bash
# make sure QGIS Desktop 2.* is running with the Network Plugin enabled, then:
curl --silent http://localhost:8090/qgis/mapLayers
```

    ## {}

``` bash
# start a new blank project
curl --silent http://localhost:8090/qgis/newProject
```

    ## null

``` bash
# add some vector data from the web
curl --silent 'http://localhost:8090/qgis/addVectorLayer?url=https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson&name=url-layer'
```

    ## {
    ##   "crs": {
    ##     "postgisSrid": 4326, 
    ##     "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##     "srsid": 3452, 
    ##     "description": "WGS 84"
    ##   }, 
    ##   "valid": true, 
    ##   "name": "url-layer OGRGeoJSON Point", 
    ##   "extent": [
    ##     -175.22056447761656, 
    ##     -89.99999981438727, 
    ##     179.21664709402887, 
    ##     78.21668438639699
    ##   ], 
    ##   "publicSource": "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson", 
    ##   "type": 0, 
    ##   "id": "url_layer20170714133749574", 
    ##   "isEditable": false
    ## }

``` bash
# add another layer as POST data
if [ ! -f "ne_50m_populated_places.geojson" ]; then
  wget --no-verbose https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson
fi
curl --silent -d @ne_50m_populated_places.geojson http://localhost:8090/qgis/addVectorLayer?name=geojson-layer
```

    ## {
    ##   "crs": {
    ##     "postgisSrid": 4326, 
    ##     "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##     "srsid": 3452, 
    ##     "description": "WGS 84"
    ##   }, 
    ##   "valid": true, 
    ##   "name": "geojson-layer OGRGeoJSON Point", 
    ##   "extent": [
    ##     -175.22056447761656, 
    ##     -89.99999981438727, 
    ##     179.21664709402887, 
    ##     78.21668438639699
    ##   ], 
    ##   "publicSource": "/tmp/tmpapFUHl", 
    ##   "type": 0, 
    ##   "id": "geojson_layer20170714133805931", 
    ##   "isEditable": false
    ## }

``` bash
# retrieve layer information
curl --silent http://localhost:8090/qgis/mapLayers
```

    ## {
    ##   "url_layer20170714133749574": {
    ##     "crs": {
    ##       "postgisSrid": 4326, 
    ##       "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##       "srsid": 3452, 
    ##       "description": "WGS 84"
    ##     }, 
    ##     "valid": true, 
    ##     "name": "url-layer OGRGeoJSON Point", 
    ##     "extent": [
    ##       -175.22056447761656, 
    ##       -89.99999981438727, 
    ##       179.21664709402887, 
    ##       78.21668438639699
    ##     ], 
    ##     "publicSource": "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_populated_places.geojson", 
    ##     "type": 0, 
    ##     "id": "url_layer20170714133749574", 
    ##     "isEditable": false
    ##   }, 
    ##   "geojson_layer20170714133805931": {
    ##     "crs": {
    ##       "postgisSrid": 4326, 
    ##       "proj4": "+proj=longlat +datum=WGS84 +no_defs", 
    ##       "srsid": 3452, 
    ##       "description": "WGS 84"
    ##     }, 
    ##     "valid": true, 
    ##     "name": "geojson-layer OGRGeoJSON Point", 
    ##     "extent": [
    ##       -175.22056447761656, 
    ##       -89.99999981438727, 
    ##       179.21664709402887, 
    ##       78.21668438639699
    ##     ], 
    ##     "publicSource": "/tmp/tmpapFUHl", 
    ##     "type": 0, 
    ##     "id": "geojson_layer20170714133805931", 
    ##     "isEditable": false
    ##   }
    ## }

``` bash
curl --silent http://localhost:8090/qgis/mapCanvas/extent
```

    ## [
    ##   -284.4320441859037, 
    ##   -94.20541691940687, 
    ##   288.428126802316, 
    ##   82.42210149141658
    ## ]

``` bash
# adjust view
curl --silent http://localhost:8090/qgis/mapCanvas/zoomToFullExtent
```

    ## 204741060.76927844

``` bash
# read current canvas content
wget --no-verbose http://127.0.0.1:8090/qgis/mapCanvas/saveAsImage
file "saveAsImage"
```

    ## 2017-07-14 13:38:07 URL:http://127.0.0.1:8090/qgis/mapCanvas/saveAsImage [2313] -> "saveAsImage" [1]
    ## saveAsImage: PNG image data, 1093 x 337, 8-bit/color RGBA, non-interlaced

``` bash
wget --no-verbose http://127.0.0.1:8090/qgis/mapCanvas/saveAsImage?format=jpeg
file "saveAsImage?format=jpeg"
```

    ## 2017-07-14 13:38:07 URL:http://127.0.0.1:8090/qgis/mapCanvas/saveAsImage?format=jpeg [6699] -> "saveAsImage?format=jpeg" [1]
    ## saveAsImage?format=jpeg: JPEG image data, JFIF standard 1.01, resolution (DPI), density 96x96, segment length 16, baseline, precision 8, 1093x337, frames 3

``` bash
# retrieve current scale
curl --silent http://localhost:8090/qgis/mapCanvas/scale
```

    ## 204741060.76927844

``` bash
# some more canvas manipulation
curl --silent http://localhost:8090/qgis/mapCanvas/zoomIn
```

    ## 102370530.38463922

``` bash
curl --silent http://localhost:8090/qgis/mapCanvas/zoomScale?scale=1234567.8
```

    ## 1234567.8000000003

Related projects
----------------

The motivation behind this plugin is to make QGIS interface components available and scriptable from other mapping-averse programming language such as R. Development versions of the corresponding R package making use of this Network API can be found [here](https://gitlab.com/qgisapi/rqgisapi).

For using QGIS processing routines from R (geared towards performing large scale data mangling without making use of QGIS UI components, with a significant overhead per processing invocation), have a look at the [RQGIS package](https://github.com/jannes-m/RQGIS).
