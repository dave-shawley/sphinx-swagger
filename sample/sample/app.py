import datetime
import hashlib
import json
import logging
import os.path
import pkg_resources
import signal

from tornado import ioloop, web

from sample import simple_handlers


class SwaggerHandler(web.RequestHandler):
    """Tornado request handler for serving a API definition."""

    def initialize(self, swagger_path):
        super(SwaggerHandler, self).initialize()
        self.swagger_path = swagger_path
        self.application.settings.setdefault('swagger_state', {
            'document': None,
            'last-read': None,
        })

    def set_default_headers(self):
        super(SwaggerHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Origin', '*')

    def options(self, *args):
        self.set_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.set_status(204)
        self.finish()

    def head(self):
        """Retrieve API definition metadata."""
        last_modified = datetime.datetime.utcfromtimestamp(
            self.swagger_state['last-modified'])
        self.set_header('Last-Modified',
                        last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT'))
        self.set_header('Content-Type', 'application/json')
        self.set_header('ETag', self.compute_etag())
        self.set_status(204)
        self.finish()

    def get(self):
        """Retrieve the API definition."""
        try:
            if self.request.headers['If-None-Match'] == self.compute_etag():
                self.set_status(304)
                return
        except KeyError:
            pass

        self.swagger_state['document']['host'] = self.request.host
        last_modified = datetime.datetime.utcfromtimestamp(
            self.swagger_state['last-modified'])
        self.set_header('Content-Type', 'application/json')
        self.set_header('Last-Modified',
                        last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT'))
        self.write(self.swagger_state['document'])

    @property
    def swagger_state(self):
        """
        Returns a :class:`dict` containing the cached state.

        :return: :class:`dict` containing the following keys: ``document``,
            ``last-modified``, and ``digest``.
        :rtype: dict
        """
        self.refresh_swagger_document()
        return self.application.settings['swagger_state']

    def compute_etag(self):
        """Return the digest of the document for use as an ETag."""
        return self.swagger_state['digest']

    def refresh_swagger_document(self):
        state = self.application.settings['swagger_state']
        last_modified = os.path.getmtime(self.swagger_path)
        if state['document']:
            if last_modified <= state['last-modified']:
                return

        with open(self.swagger_path, 'rb') as f:
            raw_data = f.read()
            state['document'] = json.loads(raw_data.decode('utf-8'))
        state['last-modified'] = last_modified
        state['digest'] = hashlib.md5(raw_data).hexdigest()


class Application(web.Application):

    def __init__(self, io_loop=None, **kwargs):
        self.io_loop = kwargs.pop('io_loop', ioloop.IOLoop.current())
        swagger_path = pkg_resources.resource_filename('sample',
                                                       'swagger.json')
        super(Application, self).__init__(
            [web.url('/ip', simple_handlers.IPHandler),
             web.url('/echo', simple_handlers.MethodHandler),
             web.url('/swagger.json', SwaggerHandler,
                     {'swagger_path': swagger_path})],
            **kwargs)

        self.logger = logging.getLogger(self.__class__.__name__)
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signo, frame):
        self.io_loop.add_callback_from_signal(self.io_loop.stop)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)1.1s - %(name)s: %(message)s')
    iol = ioloop.IOLoop.current()
    app = Application(io_loop=iol, debug=True)
    app.listen(8888)
    iol.start()
