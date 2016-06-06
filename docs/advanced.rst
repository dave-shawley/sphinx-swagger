Advanced Usage
==============

Including your definition in a package
--------------------------------------
The goal is to generate a *swagger.json* file and include it into your
source distribution.  There are a few reasons for doing this but the most
obvious is to serve this file from a endpoint within your application.
I do this in the example project by embedding the JSON file in a package
data directory as shown in the following tree::

   <project-root>/
   |-- docs/
   |   |-- conf.py
   |   `-- index.rst
   |-- MANIFEST.in
   |-- README.rst
   |-- sample/
   |   |-- __init__.py
   |   |-- app.py
   |   |-- simple_handlers.py
   |   `-- swagger.json
   `-- setup.py

The *MANIFEST.in* controls which files are included in a source distribution.
Since you will be generating the API definition when you build your package,
you aren't required to include the definition in the source distribution but
you should.  This is pretty simple::

   graft docs
   recursive-include sample *.json

That takes care of the source distributions.  The API definition also needs
to be added to binary distributions if you want to serve it from within an
application.  You need to modify your *setup.py* for this:

.. code-block:: python

   import setuptools

   setuptools.setup(
      name='sample',
      # ...
      packages=['sample'],
      package_data={'': ['**/*.json']},
      include_package_data=True,
   )

This tells the ``setuptools`` machinery to include any JSON files that
it finds in a package directory in the binary distribution.

Now for the awful part... there is no easy way to do this using the standard
``setup.py build_sphinx`` command.  It will always generate the ``swagger``
directory and does not let you customize the location of the doctrees.  Use
the **sphinx-build** utility instead::

   $ sphinx-build -b swagger -d build/tmp docs sample

That will generate the *swagger.json* directly into the ``sample`` package.
Alternatively, you can use ``setup.py build_sphinx`` and copy the API
definition into the package before generating the distribution.

Serving the API definition
--------------------------
The `Swagger UI`_ allows you to browse an API by pointing at it's API
definition file.  Once the API definition is packaged into your application
as described above, it is relatively easy to write a handler to serve the
document.  The following snippet implements one such handler in the
`Tornado`_ web framework.

.. literalinclude:: ../sample/sample/app.py
   :pyobject: SwaggerHandler

.. _Swagger UI: http://swagger.io/swagger-ui/
.. _Tornado: https://tornadoweb.org/
