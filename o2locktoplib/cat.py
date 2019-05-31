#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
The library of o2locktop. The main fuction of this module is
cat the file from remote node or local file.
"""

from o2locktoplib import util

class Cat(object):
    """
    The super class that have the required interfaces
    """
    def __init__(self, lock_space):
        self._lock_space = lock_space

    def get(self):
        """
        The interface that the child class should implement
        """
        pass

class LocalCat(Cat):
    """
    The local mode class of Cat
    """
    def  __init__(self, lock_space):
        if util.PY2:
            super(LocalCat, self).__init__(lock_space)
        else:
            super().__init__(lock_space)


    def get(self):
        """
        According  the lock_sapce to get the local node's locking_state
        """
        return util.get_one_cat(self._lock_space, None)

class SshCat(Cat):
    """
    The remote mode class of Cat
    """
    def __init__(self, lock_space, node_name):
        self._node_name = node_name
        if util.PY2:
            super(SshCat, self).__init__(lock_space)
        else:
            super().__init__(lock_space)

    def get(self):
        """
        According  the lock_sapce to get the remote node's locking_state
        """
        return util.get_one_cat(self._lock_space, self._node_name)

def gen_cat(which, lock_space, *args):
    """According 'which' parameter to generate different Cat object
    Parameters:
        which(str): The mode of Cat, it can be 'local' or 'ssh'
    """
    if which == 'local':
        return LocalCat(lock_space)
    elif which == 'ssh':
        return SshCat(lock_space, *args)
    return None
