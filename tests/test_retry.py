import pytest
from o2locktoplib.retry import retry

def test_retry():
    a = 0
    @retry(15)
    def add_a():
        nonlocal a
        a += 1
        raise Exception("test run time error")
    with pytest.raises(Exception):
        add_a()
    assert a == 15, "decorator retry test faild"

def test_retry_with_other_Exception():
    a = 0
    @retry(exceptions = ZeroDivisionError)
    def add_a():
        nonlocal a
        a += 1
        raise ZeroDivisionError("test run time error")
    with pytest.raises(ZeroDivisionError):
        add_a()
    assert a == 10, "decorator retry test faild"

def test_retry_with_out_delay():
    a = 0
    @retry(exceptions = ZeroDivisionError, delay = False)
    def add_a():
        nonlocal a
        a += 1
        raise ZeroDivisionError("test run time error")
    with pytest.raises(ZeroDivisionError):
        add_a()
    assert a == 10, "decorator retry test faild"


# a more flexibility way to test more parameters
@pytest.fixture(params=[1,2,3,4,5,6,7,8,9,10,11,12])
def value1(request):
    return request.param

@pytest.fixture(params=[True, False])
def value2(request):
    return request.param

def test_retry_with_auto_params(value1, value2):
    a = []
    a.append(0)
    @retry(value1, delay=value2)
    def add_a():
        #nonlocal a
        a[0] += 1
        raise Exception("test run time error")
    with pytest.raises(Exception):
        add_a()
    assert a[0] == value1, "decorator retry test faild"
