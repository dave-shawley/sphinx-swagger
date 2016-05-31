from __future__ import print_function

import docutils.io
import json
import os.path

from sphinx import builders

from . import writer


class SwaggerBuilder(builders.Builder):
    name = 'swagger'
    allow_parallel = False

    def init(self):
        """Sub-class hook called from __init__"""
        self.writer = None

    def prepare_writing(self, docnames):
        """Called before :meth:`write_doc`"""
        self.swagger = writer.SwaggerDocument()
        self.writer = writer.SwaggerWriter(swagger_document=self.swagger)

    def write_doc(self, docname, doctree):
        """Write a doc to the filesystem."""
        destination = docutils.io.NullOutput()
        self.writer.write(doctree, destination)

    def get_outdated_docs(self):
        """List of docs that we need to write or just a file name."""
        return 'swagger.json'

    def get_target_uri(self, docname, typ=None):
        return ''  # No clue what to return here :/

    def finish(self):
        """Called after write() has completed."""
        pass
