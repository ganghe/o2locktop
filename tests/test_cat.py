import pytest
from o2locktoplib import cat
import o2locktoplib.util as util
import config

@pytest.fixture
def lockspace():
    return util.get_dlm_lockspace_mp(None, config.mount_point)

@pytest.fixture(params = config.mode)
def mode(request):
    return request.param

def test_gen_cat(lockspace, mode):
    if mode == 'local':
        if config.mount_point == "" or config.mount_point == None:
            assert 0, "test get_cat remote mode faild"
        else:
            assert len(cat.gen_cat('local', lockspace).get()) > 0, "test get_cat remote mode faild" 
    elif mode == 'remote':
        if config.mount_point == "" or config.mount_point == None:
            assert 0, "test get_cat remote mode faild"
        else:
            assert len(cat.gen_cat('local', lockspace).get()) > 0, "test get_cat remote mode faild" 


def test_cat(lockspace, mode):
    if mode == 'local':
        if config.mount_point == "" or config.mount_point == None:
            assert 0, "test LocalCat faild"
        else:
            cat_with_mode = cat.LocalCat(lockspace)
            assert len(cat_with_mode.get()) > 0, "test LocalCat faild" 
    elif mode == 'remote':
        if config.mount_point == "" or config.mount_point == None:
            assert 0, "test SshCat faild"
        else:
            cat_with_mode = cat.SshCat(lockspace, '127.0.0.1')
            assert len(cat.gen_cat('local', lockspace).get()) > 0, "test SshCat faild" 

    
