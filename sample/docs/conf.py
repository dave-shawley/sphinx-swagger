#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import alabaster
import sample


project = 'sample'
copyright = '2016, Dave Shawley.'
version = sample.__version__
release = '.'.join(str(x) for x in sample.version_info[:2])

needs_sphinx = '1.0'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinxcontrib.autohttp.tornado',
    'sphinxswagger',
]
templates_path = []
source_suffix = '.rst'
source_encoding = 'utf-8-sig'
master_doc = 'index'
pygments_style = 'sphinx'
html_theme = 'alabaster'
html_theme_path = [alabaster.get_path()]
html_static_path = []
html_sidebars = {
    '**': [
        'about.html',
    ],
}
html_theme_options = {
    'description': 'Sample HTTP API',
    'github_banner': False,
    'github_button': False,
    'travis_button': False,
}

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'tornado': ('http://tornadoweb.org/en/latest/', None),
}

swagger_license = {'name': 'BSD 3-clause',
                   'url': 'https://opensource.org/licenses/BSD-3-Clause'}
