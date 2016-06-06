import inspect
import json

from tornado import web


class CORSAllowAll(object):

    def __init__(self, *args, **kwargs):
        self._supported_methods = []
        super(CORSAllowAll, self).__init__(*args, **kwargs)

    def set_default_headers(self):
        super(CORSAllowAll, self).set_default_headers()
        self.set_header('Access-Control-Allow-Origin', '*')

    def options(self, *args):
        self.set_header('Access-Control-Allow-Methods',
                        ','.join(self._get_supported_methods()))
        self.set_status(204)
        self.finish()

    def _get_supported_methods(self):
        if not self._supported_methods:
            self._supported_methods = []
            for method in self.SUPPORTED_METHODS:
                method_instance = getattr(self, method.lower(), None)
                if method_instance:
                    for cls in inspect.getmro(self.__class__):
                        if method_instance.__name__ in cls.__dict__:
                            if cls is not web.RequestHandler:
                                self._supported_methods.append(method)
        return self._supported_methods


class JSONHandlerMixin(object):

    def write_json(self, obj):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(
            json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8'))


class IPHandler(CORSAllowAll, JSONHandlerMixin, web.RequestHandler):

    def get(self):
        """
        Simply return the requesting IP address.

        :>json str origin: the requesting IP address in canonical string
            form.  For example ``::1`` in the case of IPv6 localhost.

        """
        self.write_json({'origin': self.request.remote_ip})


class MethodHandler(CORSAllowAll, JSONHandlerMixin, web.RequestHandler):

    def _get_response_body(self):
        return {
            'args': dict(
                (name, ','.join(v.decode('ascii') for v in vals))
                for name, vals in self.request.query_arguments.items()),
            'headers': dict(self.request.headers),
            'origin': self.request.remote_ip,
            'url': '{}://{}{}'.format(self.request.protocol,
                                      self.request.host, self.request.uri)
        }

    def get(self):
        """
        Return the request details.

        :>json object args: mapping of query parameter names to values
        :>json object headers: mapping of normalized header names to values
        :>json str origin: requesting IP address
        :>json str url: requested URL

        """
        self.write_json(self._get_response_body())

    def post(self):
        """
        Return the request details.

        :>json object args: mapping of query parameter names to values
        :>json object headers: mapping of normalized header names to values
        :>json str body: the raw request body
        :>json object json: request body decoded as JSON if the request
            content type is compatible, ``null`` otherwise
        :>json str origin: requesting IP address
        :>json str url: requested URL

        """
        response = self._get_response_body()
        response.update({
            'data': self.request.body.decode('utf-8'),
            'json': None,
        })
        if self.request.headers['Content-Type'].startswith('application/json'):
            try:
                response['json'] = json.loads(
                    self.request.body.decode('utf-8'))
            except:
                pass
        self.write_json(response)

    def put(self):
        """
        Return the request details.

        :>json object args: mapping of query parameter names to values
        :>json object headers: mapping of normalized header names to values
        :>json str body: the raw request body
        :>json object json: request body decoded as JSON if the request
            content type is compatible, ``null`` otherwise
        :>json str origin: requesting IP address
        :>json str url: requested URL

        """
        response = self._get_response_body()
        response.update({
            'data': self.request.body.decode('utf-8'),
            'json': None,
        })
        if self.request.headers['Content-Type'].startswith('application/json'):
            try:
                response['json'] = json.loads(
                    self.request.body.decode('utf-8'))
            except:
                pass
        self.write_json(response)
