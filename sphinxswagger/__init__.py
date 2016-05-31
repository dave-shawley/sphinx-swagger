version_info = (0, 0, 0)
__version__ = '.'.join(str(v) for v in version_info)


def setup(app):
    from . import builder, writer

    app.add_builder(builder.SwaggerBuilder)
    app.add_config_value('swagger_file', 'swagger.json', 'html')
    app.connect('build-finished', writer.write_swagger_file)

    return {'version': __version__}
