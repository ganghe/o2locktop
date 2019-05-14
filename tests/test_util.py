import sys
sys.path.append("../")
import os
from o2locktoplib import util
from o2locktoplib import shell
import config
import pytest

def test_check_support_debug_v4_and_get_interval():
    lockspace = config.lockspace
    ip = "127.0.0.1"
    ret = util.check_support_debug_v4_and_get_interval(lockspace, ip)
    cmd = "cat /sys/kernel/debug/ocfs2/{lockspace}/locking_filter".format(
            lockspace=lockspace)
    tmp_str = os.popen(cmd).read()
    if tmp_str == '':
        assert len(ret) == 0, "check_support_debug_v4_and_get_interval failed, the version should be 3"
    else:
        assert ret[0] == tmp_str.strip(), "check_support_debug_v4_and_get_interval failed, the version should be 4, but get the wrong filter value"

def test_set_debug_v4_interval():
    interval = util.check_support_debug_v4_and_get_interval(config.lockspace, "127.0.0.1")
    if len(interval) == 0:
        return
    else:
        util.set_debug_v4_interval(config.lockspace, "127.0.0.1", interval="1"+interval[0])
        assert "1"+interval[0] == util.check_support_debug_v4_and_get_interval(config.lockspace, '127.0.0.1')[0]
        util.set_debug_v4_interval(config.lockspace, "127.0.0.1", interval=interval[0])

def test_is_passwdless_ssh_set():
    ret = util.is_passwdless_ssh_set("127.0.0.1")
    assert ret == True or ret == False, "is_passwdless_ssh_set test failed"
    ret = util.is_passwdless_ssh_set("127.0.0.1", "theUserIsARandomString76892891")
    assert ret == False, "is_passwdless_ssh_set test failed"

def test_get_remote_path():
    ret = util.get_remote_path("127.0.0.1")
    assert "/bin" in ret[0] and "/sbin" in ret[0], "get_remote_path test error"


def test_cmd_is_exist():
    assert util.cmd_is_exist(['ls'])[0], "cmd_is_exit test faild"
    assert not util.cmd_is_exist(['cd'])[0], "cmd_is_exit test faild"
    assert util.cmd_is_exist(["uname"])[0]
    assert util.cmd_is_exist(["grep","cat","mount"])[0]

    assert util.cmd_is_exist(['ls'], '127.0.0.1')[0], "cmd_is_exit test faild"
    assert not util.cmd_is_exist(['cd'], '127.0.0.1')[0], "cmd_is_exit test faild"
    assert util.cmd_is_exist(["uname"], '127.0.0.1')[0]
    assert util.cmd_is_exist(["grep","cat","mount"], '127.0.0.1')[0]

def test_get_hostname():
    with os.popen('hostname') as fp:
        hostname = fp.read()
    assert hostname.strip() == util.get_hostname(), "get_hostname test faild"


def test_uname_r():
    with os.popen('uname -r') as fp:
        uname_r = fp.read()
    for i, j in zip(uname_r.strip().split(), util.uname_r()):
        assert i == j, "uname_r test faild in local branch"
    for i, j in zip(uname_r.strip().split(), util.uname_r('127.0.0.1')):
        assert i == j, "uname_r test faild in remote branch"
    
def test_is_kernel_ocfs2_fs_stats_enabled():
    with os.popen('grep "CONFIG_OCFS2_FS_STATS=y" /boot/config-$(uname -r)') as fp:
        ocfs_debuf_enable = fp.read()
    if ocfs_debuf_enable.strip() == "":
        assert util.is_kernel_ocfs2_fs_stats_enabled() == False, "is_kernel_ocfs2_fs_stats_enabled test faild"
    else:
        assert util.is_kernel_ocfs2_fs_stats_enabled() == True, "is_kernel_ocfs2_fs_stats_enabled test faild"

def test_lockspace_to_device():
    ret = util.lockspace_to_device(config.lockspace, "127.0.0.1")
    assert config.mount_point in ret, "lockspace_to_device test failed"

def test_get_dlm_lockspaces():
    lockspaces = util.get_dlm_lockspaces()
    with os.popen("dlm_tool ls | grep ^name") as fp:
        UUID = fp.read()
    if UUID.strip() == "":
        assert lockspaces == None, "get_dlm_lockspace test faild"
    else:
        assert len(UUID.strip().split('\n')) == len(lockspaces), "get_dlm_lockspace test faild"
        for i, j in zip([lockspace.split()[1] for lockspace in (UUID.strip().split('\n'))], lockspaces):
            assert i == j, "get_dlm_lockspace test faild"

def test_get_dlm_lockspace_mp():
    if config.mount_point == "" or config.mount_point == None:
        assert 0, "you must give a value of mount_point in file config.py"
    lockspace = util.get_dlm_lockspace_mp(None, config.mount_point)
    with os.popen("o2info --volinfo {0} | grep UUID".format(config.mount_point)) as fp:
        UUID = fp.read()
    if UUID.strip() == "":
        assert lockspace == None, "get_dlm_lockspace_mp test faild"
    else:
        assert UUID.strip().split()[1] == lockspace, "get_dlm_lockspace_mp test faild"

@pytest.fixture
def lockspace():
    return util.get_dlm_lockspace_mp(None, config.mount_point)

def test_get_one_cat(lockspace):
    cat_ret = util.get_one_cat(lockspace)
    with os.popen("cat /sys/kernel/debug/ocfs2/{lockspace}/locking_state".format(lockspace=lockspace)) as fp:
        cat_cmd_ret = fp.read()
    if cat_cmd_ret.strip() == "":
        assert cat_cmd_ret == "", "get_one_cat test faild"
    else:
        for i, j in zip(cat_ret, cat_cmd_ret.split('\n')):
            assert i == j, "get_one_cat test faild"


def test_trans_uuid():
    assert "daf3f5b6-f1c0-4b15-b9ed-8faaf109e895" == util._trans_uuid("DAF3F5B6F1C04B15B9ED8FAAF109E895"), "get_one_cat test faild" 
    assert None == util._trans_uuid(""), "get_one_cat test faild in None branch" 


