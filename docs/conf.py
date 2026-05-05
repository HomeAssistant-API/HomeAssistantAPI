"""Configuration file for the Sphinx documentation builder."""

#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import re
import sys

sys.path.insert(0, os.path.abspath("../"))
sys.path.append(os.path.abspath("extensions"))

# -- Project information -----------------------------------------------------

project = "Homeassistant API"
copyright = "2023-2025, Nathan Larsen"  # pylint: disable=redefined-builtin
author = "Nathan Larsen"
repo_url = "https://github.com/GrandMoff100/HomeassistantAPI"

# The full version, including alpha/beta/rc tags
with open("../pyproject.toml") as f:
    pyproject = f.read()
    search_result = re.search('version = "(.+?)"', pyproject)
    assert search_result is not None
    release = version = search_result.group(1)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

branch = "dev" if re.match(r".+\.(post|pre)\d+", version) else "v" + version

extensions = [
    "sphinx.ext.autodoc",
    "resourcelinks",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
]

autodoc_pydantic_model_show_json = False

resource_links = {
    "repo": repo_url,
    "issues": f"{repo_url}/issues",
    "discussions": f"{repo_url}/discussions",
    "examples": f"{repo_url}/tree/{branch}/examples",
    "new_pr": f"{repo_url}/pulls",
    "pypi": "https://pypi.org/project/homeassistant_api",
    "fork": f"{repo_url}/fork",
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]

html_favicon = "./images/favicon.png"
autodoc_typehints = "signature"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
}
intersphinx_mapping = {
    "python": (
        "https://docs.python.org/3",
        None,
    ),
    "homeassistant_api": ("https://homeassistantapi.readthedocs.io/en/stable", None),
}
