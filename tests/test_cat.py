from o2locktoplib import cat
import o2locktoplib.util as util
import config

def test_gen_cat():
    if config.test_local:
        if config.mount_point == "" or config.mount_point == None:
            assert 0
        else:
            lock_space = util.get_dlm_lockspace_mp(None, config.mount_point)
            print(len(cat.gen_cat('local', lock_space).get()))
            assert len(cat.gen_cat('local', lock_space).get()) > 0 
