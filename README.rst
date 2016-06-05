sphinx-swagger
==============

Generates a swagger API definition directly from `httpdomain`_ based
documentation.

Usage
-----

1. Enable the extension in your *conf.py* by adding ``'sphinxswagger'``
   to the ``extensions`` list
2. Run the ``swagger`` builder (e.g., ``setup.py build_sphinx -b swagger``)
3. Use the generated *swagger.json*

Configuration
-------------
This extension contains a few useful configuration values:

:swagger_file:
   Sets the name of the generated swagger file.  The file is always
   generated in the sphinx output directory -- usually *build/sphinx/swagger*.
   The default file name is *swagger.json*.

.. _httpdomain: https://pythonhosted.org/sphinxcontrib-httpdomain/
