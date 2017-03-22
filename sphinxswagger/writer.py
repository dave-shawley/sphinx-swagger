from docutils import nodes, writers
import json
import os.path
import re

from sphinxswagger import document


URI_TEMPLATE_RE = re.compile(r'\(\?P<([^>]*)>.*\)')


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
        """
        :param docutils.nodes.document document:
        :param sphinxswagger.document.Document output_document:
        """
        nodes.NodeVisitor.__init__(self, document)  # assigns self.document
        self.document = document  # tells pycharm the attributes type
        document.reporter.report_level = document.reporter.DEBUG_LEVEL
        self._swagger_doc = output_document

        self._current_node = None
        self._endpoint = None

    def debug(self, message, *args, **kwargs):
        self.document.reporter.debug(message.format(*args, **kwargs),
                                     base_node=self._current_node)

    def info(self, message, *args, **kwargs):
        self.document.reporter.info(message.format(*args, **kwargs),
                                    base_node=self._current_node)

    def warning(self, message, *args, **kwargs):
        self.document.reporter.warning(message.format(*args, **kwargs),
                                       base_node=self._current_node)

    def error(self, message, *args, **kwargs):
        self.document.reporter.error(message.format(*args, **kwargs),
                                     base_node=self._current_node)

    def _start_new_path(self, node):
        """
        :param sphinx.addnodes.desc node:
        """
        self._current_node = node
        self._endpoint = document.SwaggerEndpoint()
        self._endpoint.method = node['desctype']
        self.info('processing {}', node['desctype'])

    def _complete_current_path(self, node):
        """
        :param sphinx.addnodes.desc node:
        """
        assert self._current_node is node
        self._swagger_doc.add_endpoint(self._endpoint,
                                       _generate_debug_tree(node))
        self._endpoint = None
        self._current_node = None

    def visit_desc(self, node):
        if node['domain'] == 'http':
            self._start_new_path(node)

        if not self._endpoint:
            raise nodes.SkipNode

    def depart_desc(self, node):
        """
        :param docutils.nodes.Element node:
        """
        if self._current_node is node:
            self._complete_current_path(node)
            return

    def visit_desc_signature(self, node):
        """
        Process a method signature.

        :param sphinx.addnodes.desc_signature node:

        """
        self.debug('visiting {}: {!r}', node.__class__, node.attributes)
        if node.parent is self._current_node:
            # signature of the endpoint itself
            self._endpoint.uri_template = _convert_url(node['path'])

    def visit_desc_content(self, node):
        """
        Process the method's description.

        :param sphinx.addnodes.desc_content node:

        """
        self.debug('visiting {}: {!r}', node.__class__, node.attributes)
        if node.parent is self._current_node:
            # description of the endpoint itself
            walker = EndpointVisitor(self.document, self._endpoint)
            node.walkabout(walker)
            self._endpoint.description = '\n\n'.join(walker.description)


class EndpointVisitor(nodes.SparseNodeVisitor):
    """Visits the content for a single endpoint."""

    def __init__(self, document, endpoint):
        """
        :param docutils.nodes.document document:
        :param sphinxswagger.document.SwaggerEndpoint endpoint:
        """
        nodes.SparseNodeVisitor.__init__(self, document)
        self.document = document
        self.endpoint = endpoint
        self.description = []

    def visit_paragraph(self, node):
        """
        :param docutils.nodes.paragraph node:
        """
        if not self.endpoint.summary:  # first paragraph is the summary
            self.endpoint.summary = node.astext()
        else:  # others are description
            visitor = ParagraphVisitor(self.document)
            node.walkabout(visitor)
            self.description.append(visitor.get_paragraph())

    def visit_field(self, node):
        """
        :param docutils.nodes.field node:
        """
        idx = node.first_child_matching_class(nodes.field_name)
        if idx is not None:
            name_node = node[idx]
            idx = node.first_child_matching_class(nodes.field_body)
            value_node = node[idx]
            name = name_node.astext()
            if name == 'Status Codes':
                visitor = StatusVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.add_response_codes(visitor.status_info)
            elif name == 'Request Headers':
                visitor = HeaderVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.add_request_headers(visitor.headers)
            elif name == 'Response Headers':
                visitor = HeaderVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.add_response_headers(visitor.headers)
            elif name == 'Parameters':
                visitor = ParameterVisitor(self.document,
                                           {'in': 'path', 'required': True})
                value_node.walkabout(visitor)
                self.endpoint.parameters.extend(visitor.parameters)
            elif name == 'Request JSON Object':
                visitor = ParameterVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.parameters.append({
                    'name': 'request-body', 'in': 'body', 'required': True,
                    'schema': visitor.get_schema()})
            elif name == 'Request JSON Array of Objects':
                visitor = ParameterVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.parameters.append({
                    'name': 'request-body', 'in': 'body', 'required': True,
                    'schema': {'type': 'array', 'items': visitor.get_schema()}
                })
            elif name == 'Response JSON Object':
                visitor = ParameterVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.set_default_response_structure(visitor.parameters)
            elif name == 'Response JSON Array of Objects':
                visitor = ParameterVisitor(self.document)
                value_node.walkabout(visitor)
                self.endpoint.set_default_response_structure(
                    visitor.parameters, is_array=True)
            else:
                self.document.reporter.warning(
                    'unhandled field type: {}'.format(name), base_node=node)
            raise nodes.SkipChildren


class ParameterVisitor(nodes.SparseNodeVisitor):
    """Visit a list of parameters and format them."""

    def __init__(self, document, parameter_attributes=None):
        nodes.SparseNodeVisitor.__init__(self, document)
        self.parameters = []
        self._fixed_attributes = (parameter_attributes or {}).copy()

    def get_schema(self):
        schema = {'type': 'object', 'properties': {}, 'required': []}
        for param in self.parameters:
            name = param['name']
            schema['properties'][name] = param.copy()
            del schema['properties'][name]['name']
            schema['required'].append(name)
        return schema

    def visit_list_item(self, node):
        """
        :param docutils.nodes.list_item node:
        """
        type_map = {
            'str': 'string',
            'int': 'number',
            'float': 'number',
            'object': 'object',
            'dict': 'object',
        }

        visitor = ParagraphVisitor(self.document)
        node[0].walkabout(visitor)
        tokens = visitor.get_paragraph().split()

        # name (type) -- description
        idx = tokens.index('--')
        try:
            s, e = tokens.index('(', 0, idx), tokens.index(')', 0, idx)
            name = ' '.join(tokens[:s])
            type = type_map.get(tokens[s+1]) or 'string'
        except ValueError:
            name = ' '.join(tokens[:idx])
            type = 'string'

        description = ' '.join(tokens[idx + 1:]).strip()
        description = description[0].upper() + description[1:]

        param_info = self._fixed_attributes.copy()
        param_info.update({'name': name,
                           'type': type,
                           'description': description})
        self.parameters.append(param_info)


class StatusVisitor(nodes.SparseNodeVisitor):
    """Visit HTTP status codes and render them."""

    def __init__(self, document):
        nodes.SparseNodeVisitor.__init__(self, document)
        self.status_info = {}

    def visit_list_item(self, node):
        """
        :param docutils.nodes.list_item node:
        """
        # 0: code (' ' reason)?
        # 1: ' -- '
        # 2+: description
        visitor = ParagraphVisitor(self.document)
        node[0].walkabout(visitor)
        tokens = visitor.get_paragraph().split()
        if tokens[0].startswith('['):  # have a link, protect it
            code = tokens[0][1:]
            tokens[1] = '[' + tokens[1]
        else:
            code = tokens[0]
        idx = tokens.index('--')
        reason = ' '.join(tokens[1:idx])
        description = ' '.join(tokens[idx+1:])
        self.status_info[code] = {'reason': reason, 'description': description}

        raise nodes.SkipChildren


class ParagraphVisitor(nodes.SparseNodeVisitor):
    """
    Renders a paragraph node into GitHub-Flavoured Markdown.

    The result is a list of formatted chunks that you can retrieve
    from :meth:`get_paragraph`.

    """

    def __init__(self, document):
        nodes.SparseNodeVisitor.__init__(self, document)
        self.chunks = []
        self._stack = []

    def get_paragraph(self):
        """
        Retrieve the formatted chunks of text.

        :return: the formatted text as a :class:`str`
        :rtype: str

        """
        return ' '.join(' '.join(chunk.strip().split())
                        for chunk in self.chunks
                        if chunk.strip())

    def _push_position(self):
        """Push the current position onto the stack."""
        self._stack.append(len(self.chunks))

    def _pop_saved_chunks(self):
        """
        Pop the chunks that have been collected since the last push.

        :return: the chunks joined as a string
        :rtype: str

        """
        start = self._stack.pop()
        content = ' '.join(self.chunks[start:])
        del self.chunks[start:]
        return content

    def visit_Text(self, node):
        self.chunks.append(node.astext())
        raise nodes.SkipChildren

    def visit_reference(self, _):
        self._push_position()

    def depart_reference(self, node):
        if 'refuri' in node.attributes:
            content = self._pop_saved_chunks()
            self.chunks.append('[{}]({})'.format(content,
                                                 node.attributes['refuri']))
        else:
            self._stack.pop()

    def visit_literal(self, _):
        self._push_position()

    def depart_literal(self, _):
        self.chunks.append('`{}`'.format(self._pop_saved_chunks()))

    def visit_emphasis(self, _):
        self._push_position()

    def depart_emphasis(self, _):
        self.chunks.append('*{}*'.format(self._pop_saved_chunks()))

    def visit_strong(self, _):
        self._push_position()

    def depart_strong(self, _):
        self.chunks.append('**{}**'.format(self._pop_saved_chunks()))


class HeaderVisitor(nodes.SparseNodeVisitor):
    """Visit HTTP headers and collect them."""

    def __init__(self, document):
        nodes.SparseNodeVisitor.__init__(self, document)
        self.headers = {}

    def visit_list_item(self, node):
        """
        :param docutils.nodes.list_item node:
        """
        # 0: name
        # 1: ' -- '
        # 2: description
        content = node[0]  # paragraph node
        # normalize the header name so that words are upper-cased
        normalized = ' '.join('-'.join(elm.title() for elm in word.split('-'))
                              for word in content[0].astext().split())
        if len(content) > 2:
            first_para = content[2].astext()
            words = first_para.split()
            words[0] = words[0].title()
            paragraphs = [' '.join(words)]
            paragraphs.extend(t.astext().replace('\n', ' ').strip()
                              for t in content[3:])
            description = ' '.join(paragraphs)
        else:
            description = ''

        self.headers[normalized] = description


def _generate_debug_tree(node):
    n = {'type': node.__class__.__name__,
         # 'attributes': node.attributes if hasattr(node, 'attributes') else {},
         'children': [_generate_debug_tree(x) for x in node.children]}
    if isinstance(node, nodes.Text):
        n['value'] = str(node)
    return n


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

    description = '\n\n'.join(n.astext().replace('\n', ' ')
                              for n in paragraph[desc_start:])

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
