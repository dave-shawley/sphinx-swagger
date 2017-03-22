from distutils import cmd, log
import os.path

from sphinx import application


class BuildSwagger(cmd.Command):
    description = 'Build a swagger definition from Sphinx docs'
    user_options = [
        ('config-dir=', 'c', 'configuration directory'),
        ('output-file=', 'o', 'output file name'),
        ('ignore-distinfo', 'u', 'ignore distribution metadata'),
    ]
    boolean_options = ['ignore-distinfo']

    def initialize_options(self):
        self.config_dir = None
        self.output_file = None
        self.ignore_distinfo = False

    def finalize_options(self):
        if self.config_dir is None:
            self.config_dir = 'docs'
        self.ensure_dirname('config_dir')
        if self.config_dir is None:
            self.config_dir = os.curdir
            self.warning('Using {} as configuration directory',
                         self.source_dir)
        self.config_dir = os.path.abspath(self.config_dir)

        if self.output_file is not None:
            self.output_file = os.path.abspath(self.output_file)

    def run(self):
        build_cmd = self.get_finalized_command('build')
        build_dir = os.path.join(os.path.abspath(build_cmd.build_base),
                                 'swagger')
        self.mkpath(build_dir)
        doctree_dir = os.path.join(build_dir, 'doctrees')
        self.mkpath(doctree_dir)

        overrides = {}
        if self.output_file is not None:
            overrides['swagger_file'] = self.output_file

        if not self.ignore_distinfo:
            if self.distribution.get_description():
                overrides['swagger_description'] = \
                    self.distribution.get_description()
            if self.distribution.get_license():
                overrides['swagger_license.name'] = \
                    self.distribution.get_license()
            if self.distribution.get_version():
                overrides['version'] = self.distribution.get_version()

        app = application.Sphinx(
            self.config_dir, self.config_dir, build_dir, doctree_dir,
            'swagger', confoverrides=overrides)
        app.build()

    def warning(self, msg, *args):
        self.announce(msg.format(*args), level=log.WARNING)

    def info(self, msg, *args):
        self.announce(msg.format(*args), level=log.INFO)

    def debug(self, msg, *args):
        self.announce(msg.format(*args), level=log.DEBUG)
