import alabaster
import sphinxswagger


project = 'sphinx-swagger'
copyright = '2016, Dave Shawley'
release = '.'.join(str(v) for v in sphinxswagger.version_info[:2])
version = sphinxswagger.__version__
needs_sphinx = '1.0'
extensions = []

master_doc = 'index'
html_theme = 'alabaster'
html_theme_path = [alabaster.get_path()]
html_sidebars = {
    '**': ['about.html',
           'navigation.html'],
}
html_theme_options = {
    'description': 'Generate swagger definitions',
    'github_user': 'dave-shawley',
    'github_repo': 'sphinx-swagger',
}
