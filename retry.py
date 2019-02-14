#!/usr/bin/env python
#-*- coding: utf-8 -*-

import random
import time

def retry(times=10, exceptions=None, delay=True):
    exceptions = exceptions if exceptions is not None else Exception
    def wrapper(func):
        def wrapper(*args,**kwargs):
            last_exception = None
            for _ in range(times):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if delay:
                        time.sleep(random.random()/10)
            raise last_exception
        return wrapper
    return wrapper

