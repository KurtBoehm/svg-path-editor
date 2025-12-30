# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from datetime import datetime

from svg_path_editor import __version__ as version

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "svg-path-editor"
author = "Kurt Böhm"
copyright = f"{datetime.now().year}, {author}"
release = version

# -- General configuration ---------------------------------------------------
extensions = [
    "autoapi.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",  # Links to source
]

templates_path = ["_templates"]
exclude_patterns = []

# autodoc options
autodoc_member_order = "bysource"
autodoc_typehints = "description"

autoapi_dirs = ['../../src']
autoapi_add_toctree_entry = False

python_use_unqualified_type_names = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"  # alternatives: "alabaster" "sphinx_rtd_theme"
html_static_path = ["_static"]
