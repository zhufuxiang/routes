import threading

class _RequestConfig(object):
    """RequestConfig thrad-local singleton"""
    __shared_state = threading.local()

    def __getattr__(self, name):
        return getattr(self.__shared_state, name)

    def __setattr__(self, name, value):
        if name == 'environ':
            self.load_wsgi_environ(value)
            return self.__shared_state.__setattr__(name, value)
        return self.__shared_state.__setattr__(name, value)

    def __delattr__(self, name):
        delattr(self.__shared_state, name)

    def load_wsgi_environ(self, environ):
        if 'HTTPS' in environ or environ.get('wsgi.url_scheme') == 'https' \
           or environ.get('HTTP_X_FORWARDED_PROTO') == 'https':
            self.__shared_state.protocol = 'https'
        else:
            self.__shared_state.protocol = 'http'
        try:
            self.mapper.environ = environ
        except AttributeError:
            pass

        # Wrap in try/except as common case is that there is a mapper
        # attached to self
        try:
            if 'PATH_INFO' in environ:
                mapper = self.mapper
                path = environ['PATH_INFO']
                result = mapper.routematch(path)
                if result is not None:
                    self.__shared_state.mapper_dict = result[0]
                    self.__shared_state.route = result[1]
                else:
                    self.__shared_state.mapper_dict = None
                    self.__shared_state.route = None
        except AttributeError:
            pass

        if 'HTTP_X_FORWARDED_HOST' in environ:
            # Apache will add multiple comma separated values to
            # X-Forwarded-Host if there are multiple reverse proxies
            self.__shared_state.host = \
                environ['HTTP_X_FORWARDED_HOST'].split(', ', 1)[0]
        elif 'HTTP_HOST' in environ:
            self.__shared_state.host = environ['HTTP_HOST']
        else:
            self.__shared_state.host = environ['SERVER_NAME']
            if environ['wsgi.url_scheme'] == 'https':
                if environ['SERVER_PORT'] != '443':
                    self.__shared_state.host += ':' + environ['SERVER_PORT']
            else:
                if environ['SERVER_PORT'] != '80':
                    self.__shared_state.host += ':' + environ['SERVER_PORT']


def request_config(original=False):
    obj = _RequestConfig()
    try:
        if obj.request_local and original is False:
            return getattr(obj, 'request_local')()
    except AttributeError:
            obj.request_local = False
            obj.using_request_local = False
    return _RequestConfig()


from routes.mapper import Mapper
from routes.util import redirect_to, url_for, URLGenerator

__all__ = ['Mapper', 'url_for', 'URLGenerator', 'redirect_to',
           'request_config']

