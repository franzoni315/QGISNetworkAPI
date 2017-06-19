from network_api_registry import Registry, networkapi, NetworkAPIResult
from string import join
# 
def wrap_in_html(definitions):
    return '<!DOCTYPE html><html lang="en"><head><title>QGIS Network API</title></head><body><h1>QGIS Network API plugin</h1><dl>' + join(definitions, sep='\n') + '</dl></body></html>'

def wrap_command(path, function):
    return '<dt><a href="/api?path=' + path + '">' + path + '</a></dt><dd>' + str(function.__doc__) + '</dd>'

@networkapi('/api')
def api_docs(iface, request):
    """"""
    # check 'path' arg
    path = request.args.get('path')
    if path:
        # return documentation for specific path only
        doc = [wrap_command(path, Registry.instance().paths[path])]
        # if not found: look for paths that have given prefix?
    else:
        doc = [wrap_command(path, cmd) for (path, cmd) in sorted(Registry.instance().paths.items())]
    return NetworkAPIResult(wrap_in_html(doc), 'text/html')
