version_info = (0, 0, 1)
__version__ = '.'.join(str(v) for v in version_info)


def setup(app):
    """
    Called by Sphinx to initialize the extension.

    :param sphinx.application.Sphinx app: sphinx instance that is running
    :return: a :class:`dict` of extension metadata -- ``version`` is the
        only required key
    :rtype: dict

    """
    from . import builder, writer

    app.add_builder(builder.SwaggerBuilder)
    app.add_config_value('swagger_file', 'swagger.json', True)
    app.add_config_value('swagger_license', {'name': 'Proprietary'}, True)
    app.connect('build-finished', writer.write_swagger_file)

    return {'version': __version__}
