#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
The retry decorator
When the function throw a exception, retry 10 times as default
"""
import random
import time

def retry(times=10, exceptions=None, delay=True):
    """retry decorator
    Parameters:
        times: The retry times
        exception: The exceptions that will be catched, if None, catch all
        delay: Wait 'delay' seconds when try next time
    """
    exceptions = exceptions if exceptions is not None else Exception
    def wrapper(func):
        """
        The decorator function
        """
        def wrapper(*args, **kwargs):
            """
            In order to make the decorator support functions with parameters
            """
            last_exception = Exception("retry {0} times failed".format(times))
            for _ in range(times):
                try:
                    return func(*args, **kwargs)
                except exceptions as expt:
                    last_exception = expt
                    if delay:
                        time.sleep(random.random()/10)
            raise last_exception
        return wrapper
    return wrapper
