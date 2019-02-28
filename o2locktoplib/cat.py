#!/usr/bin/env python
#-*- coding: utf-8 -*-

from o2locktoplib import util


def gen_cat(which, lock_space, *args):
    if which == 'local':
        return LocalCat(lock_space)
    elif which == 'ssh':
        return SshCat(lock_space, *args)


class Cat(object):
    def __init__(self, lock_space):
        self._lock_space = lock_space

    def get():
        pass

class LocalCat(Cat):
    def  __init__(self, lock_space):
        if util.PY2:
            super(LocalCat, self).__init__(lock_space)
        else:
            super().__init__(lock_space)


    def get(self):
        return util.get_one_cat(self._lock_space, None)

class SshCat(Cat):
    def __init__(self, lock_space, node_name):
        self._node_name = node_name
        if util.PY2:
            super(SshCat, self).__init__(lock_space)
        else:
            super().__init__(lock_space)

    def get(self):
        return util.get_one_cat(self._lock_space, self._node_name)
