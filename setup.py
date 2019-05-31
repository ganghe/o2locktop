#!/usr/bin/env python
"""
Setup tools for o2locktop
"""
import os
from o2locktoplib import config
from o2locktoplib import util
if not util.PY2:
    import setuptools
else:
    import distutils.core as setuptools

NAME = 'o2locktop'

DIR_PATH = os.path.abspath(os.path.dirname(__file__))
READ_PATH = os.path.join(DIR_PATH, "README.md")
with open(READ_PATH, "r") as fh:
    LONG_DESCRIPTION = fh.read()


setuptools.setup(name=NAME,
                 version=config.VERSION_SETUP,
                 author="Larry Chen, Weikai Wang, Gang He",
                 author_email="lchen@suse.com, wewang@suse.com, ghe@suse.com",
                 url="https://github.com/ganghe/o2locktop",
                 description="o2locktop is a top-like OCFS2 DLM lock monitor",
                 long_description=LONG_DESCRIPTION,
                 long_description_content_type="text/markdown",
                 license="GPL2.0",
                 packages=['o2locktoplib'],
                 scripts=[NAME],
                 include_package_data=True)
