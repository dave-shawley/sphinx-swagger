from docutils import nodes, writers
import json
import os.path
import re

from sphinx import addnodes


_swagger_document = {
    'swagger': '2.0',
    'info': {},
    'host': 'localhost:8000',
    'basePath': '/',
    'schemes': ['http'],
    'consumes': [],
    'produces': [],
    'paths': {},
    'definitions': {},
    'parameters': {},
    'responses': {},
    'securityDefinitions': {},
    'security': [],
    'tags': [],
}


def write_swagger_file(app, exception):
    """
    :param sphinx.application.Sphinx app:
    :param Exception|NoneType exception:
    """
    if exception is not None:
        return

    maybe_empty = [name for name in _swagger_document.keys()
                   if name not in ('swagger', 'info', 'paths')]
    for k in maybe_empty:
        if not _swagger_document[k]:
            del _swagger_document[k]

    _swagger_document['info'].setdefault('title', app.config.project)
    _swagger_document['info'].setdefault('version', app.config.version)

    with open(os.path.join(app.outdir, 'swagger.json'), 'w') as f:
        json.dump(_swagger_document, f, indent=2)


class SwaggerWriter(writers.Writer):

    def __init__(self, *args, **kwargs):
        writers.Writer.__init__(self, *args, **kwargs)
        self.translator_class = SwaggerTranslator

    def translate(self):
        visitor = SwaggerTranslator(self.document)
        self.document.walkabout(visitor)


class SwaggerTranslator(nodes.NodeVisitor):

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)  # assigns self.document
        # document.settings
        self._desc_stack = []
        self._path_data = {}

        self._current_node = None
        self._current_path_name = None
        self._current_path_data = {}

        for node_type in ('document', 'section', 'title', 'Text', 'index',
                          'signature', 'desc', 'desc_signature', 'desc_name',
                          'desc_content', 'paragraph', 'field_list',
                          'field', 'field_name', 'field_body',
                          'bullet_list', 'list_item', 'literal_strong',
                          'literal_emphasis', 'title_reference', 'reference',
                          'target', 'literal', 'emphasis', 'strong',
                          'literal_block', 'compound', 'problematic'):
            if not hasattr(self, 'visit_' + node_type):
                setattr(self, 'visit_' + node_type, self.default_visit)
            if not hasattr(self, 'depart_' + node_type):
                setattr(self, 'depart_' + node_type, self.default_depart)

    def warning(self, *args, **kwargs):
        self.document.reporter.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.document.reporter.error(*args, **kwargs)

    def reset_path_data(self, node):
        self._current_node = node
        self._current_path_name = None
        self._current_path_data = {}

    def visit_desc(self, node):
        if isinstance(node, addnodes.desc) and node['domain'] == 'http':
            self.reset_path_data(node)

    def depart_desc(self, node):
        """
        :param docutils.nodes.Element node:
        """
        if node is self._current_node:
            xlated = self.walk(node)
            with open('out.json', 'w') as f:
                json.dump(xlated, f, indent=2)

            idx = node.first_child_matching_class(addnodes.desc_signature)
            if idx is None:
                self._current_node = None
                return

            child = node.children[idx]
            path_info = {
                'description': '',
                'responses': {},
            }

            patn = re.compile(r'\(\?P<([^>]*)>.*\)')
            tpath = child['path']
            while True:
                maybe_changed = patn.sub(r'{\1}', tpath)
                if maybe_changed == tpath:
                    break
                tpath = maybe_changed
            child['path'] = tpath

            p = _swagger_document['paths'].setdefault(child['path'], {})
            p[child['method']] = path_info

            idx = node.first_child_matching_class(addnodes.desc_content)
            if idx is not None:
                default = 'default'
                for child in node.children[idx].children:
                    if isinstance(child, nodes.paragraph):  # amend description
                        p = _render_paragraph(child)
                        if path_info['description']:
                            path_info['description'] += '\n\n'
                        path_info['description'] += p

                    if isinstance(child, nodes.field_list):  # list of some sort
                        for field in child.children:
                            # assumptions ...
                            assert isinstance(field, nodes.field)
                            assert isinstance(field[0], nodes.field_name)
                            assert isinstance(field[1], nodes.field_body)

                            name = field[0]
                            if name.astext() == 'Response JSON Object':
                                rsp = _render_response_information(field[1])
                                if rsp is not None:
                                    path_info['responses']['default'] = rsp

                            elif name.astext() == 'Status Codes':
                                for code, _, description in _render_status_codes(field[1]):
                                    if default == 'default' and 200 <= int(code) < 300:
                                        d = path_info['responses']['default']
                                        path_info['responses'].pop('default')
                                        path_info['responses'][code] = d
                                        default = code
                                    path_info['responses'].setdefault(code, {})
                                    path_info['responses'][code]['description'] = description

                            elif name.astext() == 'Response Headers':
                                path_info['responses'][default].setdefault('headers', {})
                                headers = path_info['responses'][default]['headers']
                                for name, spec in _render_headers(field[1]):
                                    headers[name] = spec

                            elif name.astext() == 'Request Headers':
                                path_info.setdefault('parameters', [])
                                for name, spec in _render_headers(field[1]):
                                    spec['name'] = name
                                    spec['in'] = 'header'
                                    path_info['parameters'].append(spec)

                            elif name.astext() == 'Parameters':
                                path_info.setdefault('parameters', [])
                                for name, spec in _render_headers(field[1]):
                                    spec['name'] = name
                                    spec['in'] = 'path'
                                    spec['required'] = True
                                    path_info['parameters'].append(spec)

                            elif name.astext() == 'Query Parameters':
                                path_info.setdefault('parameters', [])
                                for name, spec in _render_headers(field[1]):
                                    spec['name'] = name
                                    spec['in'] = 'query'
                                    path_info['parameters'].append(spec)

            self._current_node = None

    def default_visit(self, node):
        print('entering', type(node))

    def default_depart(self, node):
        print('departing', type(node))

    def walk(self, node):
        n = {'type': str(type(node)),
             'attributes': node.attributes if hasattr(node, 'attributes') else {},
             'children': [self.walk(x) for x in node.children]}
        if isinstance(node, nodes.Text):
            n['value'] = str(node)
        return n


def _render_paragraph(paragraph):
    """
    :param nodes.paragraph paragraph:
    :returns: str
    """
    lines = [t.astext() for t in paragraph.children
             if isinstance(t, nodes.Text)]
    return '\n\n'.join(lines)


def _render_response_information(body):
    """
    :param nodes.field_body body:
    :rtype: dict|NoneType
    """
    if len(body.children) > 1 or not isinstance(body[0], nodes.bullet_list):
        return None

    bullet_list = body[0]

    response_obj = {
        'schema': {
            'type': 'object',
            'required': [],
            'properties': {},
        },
    }
    types = {
        'str': 'string',
        'int': 'number',
        'float': 'number',
    }

    for list_item in bullet_list.children:
        assert isinstance(list_item, nodes.list_item)
        assert len(list_item.children) == 1

        para = list_item[0]
        assert isinstance(para, nodes.paragraph)
        assert len(para.children) >= 5

        # 0: name
        # 1: '('
        # 2: type
        # 3: ')'
        # 4: ' -- '
        # 5*: description
        name = para[0].astext()
        type_ = types.get(para[2].astext(), 'string')
        descr = ''.join(segment.astext() for segment in para[5:])
        response_obj['schema']['required'].append(name)
        response_obj['schema']['properties'][name] = {'type': type_,
                                                      'description': descr}

    return response_obj


def _render_status_codes(body):
    """
    :param nodes.field_body body:
    :returns: :data:`tuple` of (code, reason, description)
    :rtype: tuple
    """
    if len(body.children) > 1 or not isinstance(body[0], nodes.bullet_list):
        return None

    bullet_list = body[0]

    for list_item in bullet_list.children:
        assert isinstance(list_item[0], nodes.paragraph)
        assert len(list_item.children) == 1

        para = list_item[0]
        assert isinstance(para, nodes.paragraph)
        assert len(para.children) >= 2

        # 0: code ' ' reason
        # 1: ' -- '
        # 2*: description
        code, _, reason = para.children[0].astext().partition(' ')
        description = ''.join(t.astext() for t in para.children[2:])
        yield code, reason or description, description


def _render_headers(body):
    """
    :param nodes.field_body body:
    :returns: :data:`tuple` of (name, dict)
    :rtype: tuple
    """
    bullet_list = body[0]

    for list_item in bullet_list.children:
        para = list_item[0]

        # 0: name
        # 1: ' -- '
        # 2*: description
        yield para[0].astext(), {
            'type': 'string',
            'description': ''.join(t.astext() for t in para[2:])
        }

"""
{"swagger":"2.0"
,"info":{"title":"Title String"
        ,"description":"in Github-Flavored Markdown"
        ,"termsOfService":"http://swagger.io/terms/"
        ,"contact":{"name":"$AUTHOR_NAME"
                   ,"email":"api@example.com"
                   ,"url":"http://api.aweber.com/"}
        ,"license":{"name":"BSD"
                   ,"url":"http://license.url"}
        ,"version":"$PROJECT_VERSION"}
,"host":"localhost:8000"
,"basePath":"/"
,"schemes":["http"]
,"consumes":["application/json"]
,"produces":["application/json"]
,"paths":{"/status":{"get":{"description":""
                           ,"responses":{"200":{"description":"the application is functional"
                                               ,"schema":{"$ref":"#/definitions/Status"}}}}}}
,"definitions":{"Status":{"type":"object"
                         ,"description":"Application status information"
                         ,"required":["application","version","status"]
                         ,"properties":{"application":{"type":"string"
                                       ,"description":"the name of the service"}
                                       ,"version":{"type":"string"
                                                  ,"description":"the deployed application version"}
                                       ,"status":{"type":"string"
                                                 ,"description":"status of the application"}}}}
,"parameters":{}
,"responses":{}
,"securityDefinitions":{}
,"security":[]
,"tags":[]}
"""
