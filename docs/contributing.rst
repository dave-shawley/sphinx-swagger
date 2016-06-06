Contributing
============

Setting up your environment
---------------------------
First of all, build yourself a nice clean virtual environment using the
:mod:`venv` module (or `virtualenv`_ if you must).  Then pull in the
requirements::

   sphinx-swagger$ python3 -mvenv env
   sphinx-swagger$ env/bin/pip install -qr requires/development.txt

Then you can test the package using the embedded *sample* package starting
with the same pattern::

   sphinx-swagger$ cd sample
   sample$ python3 -mvenv env
   sample$ env/bin/python setup.py develop
   sample$ env/bin/pip install -e ..
   sample$ env/bin/sphinx-build -b swagger -d build/tmp docs sample
   sample$ env/bin/python sample/app.py

This will run the Tornado stack and serve the API definition at
``/swagger.json`` on port 8888 -- http://localhost:8888/swagger.json
You can use the Swagger UI to browse the generated documentation in a web
browser as well::

   sample$ git clone git@github.com:swagger-api/swagger-ui.git
   sample$ open swagger-ui/dist/index.html

Point it at the Tornado application on localhost and you should get a nice
way to browse the API.

Seeing Changes
--------------
If you followed the installation instructions above, then you have a locally
running Tornado application that is serving a API definition and a local
version of the Swagger UI running.  Changes to the Sphinx extension can be
easily tested by running the *sphinx-build* command in the sample directory.
The *swagger.json* file will be regenerated and picked up the next time that
it is requested from the UI.

Giving it Back
--------------
Once you have something substantial that you would like to contribute back
to the extension, push your branch up to github.com and issue a Pull Request
against the main repository.

.. _virtualenv: https://virtualenv.pypa.io/en/stable/
