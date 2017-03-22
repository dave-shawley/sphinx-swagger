try:
    import http.client as http_client
except ImportError:
    import httplib as http_client


class SwaggerDocument(object):

    def __init__(self):
        super(SwaggerDocument, self).__init__()
        self._paths = {}

    def get_document(self, config):
        """
        :param sphinx.config.Config config: project level configuration
        :return: the swagger document as a :class:`dict`
        :rtype: dict
        """
        info = {'title': config.project,
                'description': config.swagger_description,
                'license': config.swagger_license,
                'version': config.version}
        if not info['description'] and hasattr(config, 'html_theme_options'):
            info['description'] = config.html_theme_options.get('description')

        return {'swagger': '2.0',
                'info': info,
                'host': 'localhost:80',
                'basePath': '/',
                'paths': self._paths}

    def add_endpoint(self, endpoint, debug_info=None):
        """
        Add a swagger endpoint document.

        :param SwaggerEndpoint endpoint: the endpoint to add
        :param dict debug_info: optional debug information to include
            in the swagger definition

        """
        path_info = self._paths.setdefault(endpoint.uri_template, {})
        if endpoint.method in path_info:
            pass  # already gots this ... good this isn't
        path_info[endpoint.method] = endpoint.generate_swagger()
        if debug_info:
            path_info[endpoint.method]['x-debug-info'] = debug_info


class SwaggerEndpoint(object):

    def __init__(self):
        self.method = None
        self.uri_template = None
        self.summary = ''
        self.description = ''
        self.parameters = []
        self.responses = {}
        self.default_response_schema = None
        self.response_headers = None

    def set_default_response_structure(self, properties, is_array=False):
        schema = {'type': 'object', 'properties': {}, 'required': []}
        for prop in properties:
            name = prop.pop('name')
            schema['properties'][name] = prop.copy()
            schema['required'].append(name)
        if is_array:
            schema = {'type': 'array', 'items': schema}
        self.default_response_schema = schema

    def add_request_headers(self, headers):
        for name, description in headers.items():
            self.parameters.append({
                'name': name,
                'description': description,
                'in': 'header',
                'type': 'string',
            })

    def add_response_headers(self, headers):
        self.response_headers = {
            name: {'description': description, 'type': 'string'}
            for name, description in headers.items()
        }

    def add_response_codes(self, status_dict):
        for code, info in status_dict.items():
            swagger_rsp = self.responses.setdefault(code, {})
            if not info['reason']:
                try:
                    code = int(code)
                    info['reason'] = http_client.responses[code]
                except (KeyError, TypeError, ValueError):
                    info['reason'] = 'Unknown'

            tokens = info['description'].split(maxsplit=2)
            if tokens:
                tokens[0] = tokens[0].title()
            swagger_rsp['description'] = '{}\n\n{}'.format(
                info['reason'], ' '.join(tokens)).strip()

    def generate_swagger(self):
        swagger = {'summary': self.summary, 'description': self.description}
        if self.parameters:
            swagger['parameters'] = self.parameters

        if self.responses:
            swagger['responses'] = self.responses
        else:  # swagger requires at least one response
            swagger['responses'] = {'default': {'description': ''}}

        # Figure out where to put the response schema and response
        # header details.  This is probably going to change in the
        # future since it is `hinky' at best.
        default_code = 'default'
        status_codes = sorted(int(code)
                              for code in swagger['responses']
                              if code.isdigit())
        for code in status_codes:
            if 200 <= code < 400:
                default_code = str(code)
                break

        if default_code in swagger['responses']:
            if self.default_response_schema:
                swagger['responses'][default_code]['schema'] = \
                    self.default_response_schema
            if self.response_headers:
                swagger['responses'][default_code]['headers'] = \
                    self.response_headers

        return swagger
