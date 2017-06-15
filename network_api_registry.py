from functools import wraps

class Registry:
    __singleton = None
    paths = {}

    @staticmethod
    def instance():
        if Registry.__singleton == None:
            Registry()
        return Registry.__singleton

    def __init__(self):
        if Registry.__singleton == None:
            Registry.__singleton = self

    @staticmethod
    def add_path(path, handler_function):
        Registry.instance().paths[path] = handler_function

    @staticmethod
    def get(path):
        return Registry.instance().paths.get(path)

# @networkapi decorator
def networkapi(path):
    def register(handler_function):
        Registry.add_path(path, handler_function)
        def func_wrapper(request):
            return handler_function(request)
        return wraps(handler_function)(func_wrapper)
    return register

class NetworkAPIResult:
    def __init__(self, body = None, content_type = None, status = 200):
        self.body = body
        self.content_type = content_type
        self.status = status
# response body can be of any type and will be automatically converted using json.dump()
