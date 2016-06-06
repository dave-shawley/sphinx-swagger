from docutils import nodes, writers
import copy
import json
import os.path
import re

from sphinx import addnodes


URI_TEMPLATE_RE = re.compile(r'\(\?P<([^>]*)>.*\)')
PARAMETER_RE = re.compile(r'(?P<name>[^ ]*)\s+'
                          r'(\((?P<type>[^)]*)\))?\s*'
                          r'--\s+(?P<description>.*)')


def write_swagger_file(app, exception):
    """
    :param sphinx.application.Sphinx app:
    :param Exception|NoneType exception:
    """
    if exception is not None:
        return

    if getattr(app.builder, 'swagger', None) is None:
        return

    with open(os.path.join(app.outdir, app.config.swagger_file), 'w') as f:
        json.dump(app.builder.swagger.get_document(app.config), f, indent=2)


class SwaggerWriter(writers.Writer):

    def __init__(self, *args, **kwargs):
        self.swagger_document = kwargs.pop('swagger_document')
        writers.Writer.__init__(self, *args, **kwargs)
        self.translator_class = SwaggerTranslator

    def translate(self):
        visitor = SwaggerTranslator(self.document, self.swagger_document)
        self.document.walkabout(visitor)


class SwaggerTranslator(nodes.SparseNodeVisitor):

    def __init__(self, document, output_document):
        nodes.NodeVisitor.__init__(self, document)  # assigns self.document
        self._swagger_doc = output_document
        self._current_node = None

    def warning(self, *args, **kwargs):
        self.document.reporter.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.document.reporter.error(*args, **kwargs)

    def reset_path_data(self, node):
        self._current_node = node

    def visit_desc(self, node):
        if isinstance(node, addnodes.desc) and node['domain'] == 'http':
            self.reset_path_data(node)

    def depart_desc(self, node):
        """
        :param docutils.nodes.Element node:
        """
        if node is not self._current_node:
            return

        idx = node.first_child_matching_class(addnodes.desc_signature)
        if idx is None:  # no detail about the signature, skip it
            self._current_node = None
            return

        desc_signature = node.children[idx]
        url_template = _convert_url(desc_signature['path'])
        description = ''
        responses = {}
        parameters = []

        idx = node.first_child_matching_class(addnodes.desc_content)
        if idx is None:  # no content, skip
            return

        # TODO remove this ... useful for debugging only
        # debug_name = 'out-{}.json'.format(len(self._swagger_doc._paths))
        # with open(debug_name, 'w') as f:
        #     data = _generate_debug_tree(node)
        #     data['signature'] = desc_signature['path']
        #     data['url_template'] = url_template
        #     json.dump(data, f, indent=2)
        # END TODO

        default = 'default'
        for child in node[idx].children:
            if isinstance(child, nodes.paragraph):
                p = _render_paragraph(child)
                if description:
                    description += '\n\n'
                description += p

            if isinstance(child, nodes.field_list):  # list of some sort
                for field in child.children:
                    # assumptions, assumptions, assumptions ...
                    assert isinstance(field, nodes.field)
                    assert isinstance(field[0], nodes.field_name)
                    assert isinstance(field[1], nodes.field_body)

                    name = field[0]
                    if name.astext() == 'Response JSON Object':
                        rsp = _render_response_information(field[1])
                        if rsp is not None:
                            responses.setdefault(default, {})
                            responses[default].update(rsp)

                    elif name.astext() == 'Status Codes':
                        for code, _, desc in _generate_status_codes(field[1]):
                            if default == 'default' and 200 <= int(code) < 300:
                                d = responses.pop('default', {})
                                responses[code] = d
                                default = code
                            responses.setdefault(code, {})
                            responses[code]['description'] = desc

                    elif name.astext() == 'Response Headers':
                        responses[default].setdefault('headers', {})
                        headers = responses[default]['headers']
                        for name, spec in _generate_parameters(field[1]):
                            headers[name] = spec

                    elif name.astext() == 'Request Headers':
                        for name, spec in _generate_parameters(field[1]):
                            spec['name'] = name
                            spec['in'] = 'header'
                            parameters.append(spec)

                    elif name.astext() == 'Parameters':
                        for name, spec in _generate_parameters(field[1]):
                            spec['name'] = name
                            spec['in'] = 'path'
                            spec['required'] = True
                            parameters.append(spec)

                    elif name.astext() == 'Query Parameters':
                        for name, spec in _generate_parameters(field[1]):
                            spec['name'] = name
                            spec['in'] = 'query'
                            parameters.append(spec)

        self._swagger_doc.add_path_info(
            desc_signature['method'], url_template, description,
            parameters, responses)

        self._current_node = None


def _generate_debug_tree(node):
    n = {'type': str(type(node)),
         'attributes': node.attributes if hasattr(node, 'attributes') else {},
         'children': [_generate_debug_tree(x) for x in node.children]}
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
        'description': '',
        'schema': {
            'type': 'object',
            'required': [],
            'properties': {},
        },
    }

    for list_item in bullet_list.children:
        assert isinstance(list_item, nodes.list_item)
        assert len(list_item.children) == 1

        para = list_item[0]
        assert isinstance(para, nodes.paragraph)

        obj_info = _parsed_typed_object(para)
        if obj_info:
            response_obj['schema']['required'].append(obj_info['name'])
            response_obj['schema']['properties'][obj_info['name']] = {
                'type': obj_info['type'],
                'description': obj_info['description'],
            }

    return response_obj


def _generate_status_codes(body):
    """
    :param nodes.field_body body:
    :returns: :data:`tuple` of (code, reason, description)
    :rtype: tuple
    """
    if len(body.children) > 1 or not isinstance(body[0], nodes.bullet_list):
        return

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


def _generate_parameters(body):
    """
    :param nodes.field_body body:
    :returns: :data:`tuple` of (name, dict)
    :rtype: tuple
    """
    bullet_list = body[0]

    for list_item in bullet_list.children:
        assert isinstance(list_item, nodes.list_item)
        assert len(list_item.children) == 1

        para = list_item[0]
        assert isinstance(para, nodes.paragraph)

        obj_info = _parsed_typed_object(para)
        if obj_info:
            yield obj_info['name'], {
                'type': obj_info['type'],
                'description': obj_info['description'],
            }


def _parsed_typed_object(paragraph):
    """
    Parses a typed-object description like ``name (type) -- description``.

    :param docutils.nodes.paragraph paragraph:

    :return: :class:`dict` containing the name, type, and description
        as strings or an empty :class:`dict`
    :rtype: dict

    """
    type_map = {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'object': 'object',
        'dict': 'object',
    }

    name = paragraph[0].astext()
    if paragraph[1].astext() == ' (':
        t = type_map.get(paragraph[2].astext()) or 'string'
        desc_start = 5
    else:
        t = 'string'
        desc_start = 2

    description = '\n\n'.join(n.astext() for n in paragraph[desc_start:])

    return {
        'name': name,
        'type': t,
        'description': description,
    }


def _convert_url(url):
    """
    Convert a URL regex to a URL template.

    :param str url: regular expression pattern to convert
    :return: `url` converted to a URL template

    """
    start_url = url
    for attempt in range(0, 100):
        maybe_changed = URI_TEMPLATE_RE.sub(r'{\1}', url)
        if maybe_changed == url:
            return url
        url = maybe_changed

    raise RuntimeError('failed to convert {} to a URL Template '
                       'after {} tries'.format(start_url, attempt))


class SwaggerDocument(object):

    def __init__(self):
        super(SwaggerDocument, self).__init__()
        self._paths = {}

    def get_document(self, config):
        """
        :param sphinx.config.Config config: project-level configuration
        :return: swagger document as a :class`dict`
        :rtype: dict
        """
        info = {
            'title': config.project,
            'version': config.version,
        }
        try:
            info['description'] = config.html_theme_options['description']
        except AttributeError:
            pass
        if config.swagger_license:
            info['license'] = config.swagger_license

        return {'swagger': '2.0',
                'info': info,
                'host': 'localhost:8000',
                'basePath': '/',
                'paths': copy.deepcopy(self._paths)}

    def add_path_info(self, method, url_template, description,
                      parameters, responses):
        path_info = self._paths.setdefault(url_template, {})
        path_info[method] = {'description': description,
                             'responses': {'default': {'description': ''}}}
        if parameters:
            path_info[method]['parameters'] = copy.deepcopy(parameters)
        if responses:
            path_info[method]['responses'] = copy.deepcopy(responses)
