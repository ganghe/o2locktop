"""
Unit test for printer.py
"""
import sys
sys.path.append("../")
import pytest
from o2locktoplib.printer import Printer
from o2locktoplib.printer import SIMPLE_DISPLAY
from o2locktoplib.printer import DETAILED_DISPLAY
import config
import check_env

@pytest.fixture(params=["test.log", None])
def init_params(request):
    return request.param

def test_check_env_befor_test():
    assert config.lockspace == check_env.check_env(config.nodelist[0], config.mount_point),\
    "The lockspace in config.py is wrong or the mount point is not mounted on an ocfs2 file system"

class TestPrinter():
    def test_init(self, init_params):
        printer = Printer(init_params)
        assert not printer.content,\
        "Printer __init__ method test error"
        assert printer.display_mode == SIMPLE_DISPLAY,\
        "Printer __init__ method test error"
        assert not printer.should_stop,\
        "Printer __init__ method test error"
        if init_params == None:
            assert not printer.log,\
            "Printer __init__ method test error"
        else:
            assert printer.log,\
            "Printer __init__ method test error"

    def test_active(self):
        printer = Printer(None)
        printer.activate("simple", "detail")
        assert printer.content == ("simple", "detail"),\
        "Printer activate method test error"

    def test_toggle_display_mode(self):
        printer = Printer(None)
        assert printer.display_mode == SIMPLE_DISPLAY
        printer.toggle_display_mode()
        assert printer.display_mode == DETAILED_DISPLAY,\
        "Printer toggle_display_mode method test error"
        printer.toggle_display_mode()
        assert printer.display_mode == SIMPLE_DISPLAY,\
        "Printer toggle_display_mode method test error"

    def test_set_display_mode(self):
        printer = Printer(None)
        assert printer.display_mode == SIMPLE_DISPLAY
        printer.set_display_mode(DETAILED_DISPLAY)
        assert printer.display_mode == DETAILED_DISPLAY,\
        "Printer set_display_mode method test error"
        printer.set_display_mode(SIMPLE_DISPLAY)
        assert printer.display_mode == SIMPLE_DISPLAY,\
        "Printer set_display_mode method test error"
        with pytest.raises(AssertionError):
            printer.set_display_mode(3)
