sphinx-swagger
==============

Generates a swagger API definition directly from `httpdomain`_ based
documentation.

Usage
-----

1. Enable the extension in your *conf.py* by adding ``'sphinxswagger'``
   to the ``extensions`` list
2. Run the ``swagger`` builder (e.g., ``setup.py swagger``)
3. Use the generated *swagger.json*

Setuptools Command
------------------
This library installs a new command named **swagger** that is available
from the *setup.py* utility.  It runs sphinx to generate the swagger
output file.  It is similar to running ``sphinx-build -b swagger`` except
that it has access to your packages metadata so you don't have to
configure it in two places!

**This is the recommend approach for using this package.**

You can configure the output file name in your project's *setup.cfg* in
the ``[swagger]`` section::

   [swagger]
   output-file = static/swagger.json

This makes it easier to include it directly into your built artifact
by adding it as ``package_data`` in *setup.py*.  Remember to add it to
your *MANIFEST.in* as well.

Configuration
-------------
This extension contains a few useful configuration values that can be
set from within the sphinx configuration file.

:swagger_description:
   Sets the description of the application in the generated swagger file.
   If this is not set, then the "description" value in ``html_theme_options``
   will be used if it is set.

:swagger_file:
   Sets the name of the generated swagger file.  The file is always
   generated in the sphinx output directory -- usually *build/sphinx/swagger*.
   The default file name is *swagger.json*.

:swagger_license:
   A dictionary that describes the license that governs the API.  This
   is written as-is to the `License`_ section of the API document.  It should
   contain two keys -- **name** and **url**.

.. _httpdomain: https://pythonhosted.org/sphinxcontrib-httpdomain/
.. _License: https://github.com/OAI/OpenAPI-Specification/blob/master/
   versions/2.0.md#licenseObject
