from .registry import Registry, networkapi, NetworkAPIResult
from string import join

def wrap_in_html(body):
    return '<!DOCTYPE html><html lang="en"><head><title>QGIS Network API</title><style>dt { font-family: monospace; }</style></head><body><h1>QGIS Network API plugin</h1>' + body + '</body></html>'

def wrap_command(path, function, short=False):
    if short:
        if function.__doc__:
            return '<dt><a href="/api?path=' + path + '">' + path + '</a></dt><dd>' + function.__doc__.strip().splitlines()[0] + '</dd>'
        else:
            return '<dt>' + path + '</dt><dd>not documented</dd>'
    else:
         return '<dt>' + path + '</dt><dd><pre style="max-width:80%;white-space: pre-wrap;">' + function.__doc__ + '</pre></dd><a href="' + path + '">go there</a>'

@networkapi('/api')
def api_docs(iface, request):
    """Display documentation for all API paths in human-readable HTML (i.e. the page you are currently looking at)."""
    # check 'path' arg
    path = request.args.get('path')
    if path:
        # return full documentation for specific path only
        body = '<p><a href="/api">back</a></p>' + wrap_command(path, Registry.instance().paths[path])
        # TODO if not found: look for paths that have given prefix?
    else:
        body = '<p>Documentation of all HTTP request paths currently exposed by the Network API plugin. Click on a path for details on arguments and return values.</p>' + join([wrap_command(path, cmd, True) for (path, cmd) in sorted(Registry.instance().paths.items())], sep='\n')
    return NetworkAPIResult(wrap_in_html(body), 'text/html')
