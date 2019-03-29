#!/usr/bin/env python

from o2locktoplib import util
if not util.PY2:
    import setuptools
else:
    import distutils.core as setuptools
from o2locktoplib import config
import os

name = 'o2locktop'

dir_path = os.path.abspath(os.path.dirname(__file__))
read_path = os.path.join(dir_path, "README.md")
with open(read_path, "r") as fh:
    long_description = fh.read()


setuptools.setup(name=name,
    version = config.VERSION_SETUP,
    author = "Larry Chen, Weikai Wang, Gang He",
    author_email = "lchen@suse.com, wewang@suse.com, ghe@suse.com",
    url = "https://github.com/ganghe/o2locktop",
    description = "o2locktop is a top-like OCFS2 DLM lock monitor",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    license = "GPL2.0",
    packages = ['o2locktoplib'],
    scripts = [name],
    include_package_data=True
)
