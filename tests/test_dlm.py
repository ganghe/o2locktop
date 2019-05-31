"""
unit test for dlm.py
"""
import sys
import os
import pytest
import config
sys.path.append("../")
from o2locktoplib import dlm
from o2locktoplib import util
import check_env

PATH = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(PATH, "locking_state_data.txt")) as fd:
    LOCKING_STATE_STR1 = fd.readline()
    LOCKING_STATE_STR2 = fd.readline()
    LOCKING_STATE_STR0 = fd.readline()

def test_check_env_befor_test():
    """
    Check if the config file's infomation is setted
    """
    assert config.lockspace == check_env.check_env(config.nodelist[0], config.mount_point),\
    "The lockspace in config.py is wrong or the mount point is not mounted on an ocfs2 file system"

def test_check_test_env():
    """
    Check if the config file's infomation is setted
    """
    assert len(config.nodelist) >= 2
    # check if the mount point is exit
    # check if the lockspace is match to mount point on the machine

def test_class_lockname():
    """
    Test the LockName class in dlm.py
    """
    lockname = dlm.LockName("M00000000000000000000056434f530")
    assert lockname.lock_type == "M", "LockName lock_type test failed"
    assert lockname.inode_num == 5, "LockName inode_num test failed"
    assert lockname.generation == "6434f530", "LockName generation test failed"
    assert lockname.short_name.replace(' ', '') == "M5", "LockName short_name test failed"
    lockname1 = dlm.LockName("M00000000000000000000056434f530")
    assert lockname == lockname1, "LockName __eq__ test failed"

    lockname = dlm.LockName("N00000000000000050000c603")
    assert lockname.lock_type == "N", "LockName lock_type test failed"
    assert lockname.inode_num == 50691, "LockName inode_num test failed"
    assert lockname.generation == "0000c603", "LockName generation test failed"
    assert lockname.short_name.replace(' ', '') == "N50691", "LockName short_name test failed"
    lockname1 = dlm.LockName("N00000000000000050000c603")
    assert lockname == lockname1, "LockName __eq__ test failed"

def test_class_shot():
    """
    Test the Shot class in dlm.py
    """
    shot = dlm.Shot(LOCKING_STATE_STR1)
    assert shot.legal(), "got an ilegal shot"
    assert shot.inode_num == 5, "Shot inode number test failed"
    assert shot.lock_type == "M", "Shot lock_type test failed"

    shot = dlm.Shot(LOCKING_STATE_STR0)
    assert shot.legal(), "got an ilegal shot"
    assert shot.inode_num == 50690, "Shot inode number test failed"
    assert shot.lock_type == "N", "Shot lock_type test failed"


    assert shot.debug_ver == '0x4'
    assert shot.name == dlm.LockName("N00000000000000050000c602")
    assert shot.l_level == '3'
    assert shot.l_flags == '0x41'
    assert shot.l_action == '0x0'
    assert shot.l_unlock_action == '0x0'
    assert shot.l_ro_holders == '0'
    assert shot.l_ex_holders == '0'
    assert shot.l_requested == '3'
    assert shot.l_blocking == '-1'
    assert shot.lvb_64B == '0x00x00x00x00x00x00x00x00x00x00x00x0'\
                           '0x00x00x00x00x00x00x00x00x00x00x00x0'\
                           '0x00x00x00x00x00x00x00x00x00x00x00x0'\
                           '0x00x00x00x00x00x00x00x00x00x00x00x0'\
                           '0x00x00x00x00x00x00x00x00x00x00x00x0'\
                           '0x00x00x00x0'
    assert shot.lock_num_prmode == '1'
    assert shot.lock_num_exmode == '0'
    assert shot.lock_num_prmode_failed == '0'
    assert shot.lock_num_exmode_failed == '0'
    assert shot.lock_total_prmode == '21937'
    assert shot.lock_total_exmode == '0'
    assert shot.lock_max_exmode == '21'
    assert shot.lock_refresh == '0'

# In this test, I insert two diff kind of lock in Lock object
# and it should throw AssertionError
def test_class_lock():
    """
    Test the Lock class in dlm.py
    """
    lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
    node = lockspace._nodes[config.nodelist[0]]
    lock = dlm.Lock(node)
    # at this time, the lock have no data
    assert not lock.name
    assert node is lock.node
    assert lockspace is lock.lock_space
    assert not lock.inode_num
    assert not lock.lock_type
    assert not lock.has_delta()
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_EX) == (0, 0, 0)
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_PR) == (0, 0, 0)
    # at this time, the lock have one shot
    shot1 = dlm.Shot(LOCKING_STATE_STR1)
    lock.append(shot1)
    assert lock.name == shot1.name
    assert node is lock.node
    assert lockspace is lock.lock_space
    assert lock.inode_num == 5
    assert lock.lock_type == 'M'
    assert not lock.has_delta()
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_EX) == (0, 0, 0)
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_PR) == (0, 0, 0)
    # at this time, the lock also have one shot, because add an useless shot
    shot0 = dlm.Shot(LOCKING_STATE_STR0)
    with pytest.raises(AssertionError):
        lock.append(shot0)
    assert lock.name == shot1.name
    assert node is lock.node
    assert lockspace is lock.lock_space
    assert lock.inode_num == 5
    assert lock.lock_type == 'M'
    assert not lock.has_delta()
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_EX) == (0, 0, 0)
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_PR) == (0, 0, 0)

# In this test, Insert two same kind of Lock
def test_class_lock_2():
    """
    Test the Lock class in dlm.py use anthor method
    """
    lockspace = dlm.LockSpace(["127.0.0.1"], config.lockspace, 0, False, display_len=10)
    node = lockspace._nodes["127.0.0.1"]
    lock = dlm.Lock(node)

    # test for _lock_level_2_field in class Lock
    assert lock._lock_level_2_field(dlm.LOCK_LEVEL_EX) == ('lock_total_exmode', 'lock_num_exmode'),\
    "test _lock_level_2_field in class Lock failed"
    assert lock._lock_level_2_field(dlm.LOCK_LEVEL_PR) == ('lock_total_prmode', 'lock_num_prmode'),\
    "test _lock_level_2_field in class Lock failed"


    # at this time, the lock have no data
    assert not lock.name
    assert node is lock.node
    assert lockspace is lock.lock_space
    assert not lock.inode_num, "test __init__ in class Lock failed"
    assert not lock.lock_type, "test __init__ in class Lock failed"
    assert not lock.has_delta(), "test __init__ in class Lock failed"
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_EX) == (0, 0, 0),\
    "test __init__ in class Lock failed"
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_PR) == (0, 0, 0),\
    "test __init__ in class Lock failed"
    # at this time, the lock have one shot
    shot1 = dlm.Shot(LOCKING_STATE_STR1)
    lock.append(shot1)
    assert lock.name == shot1.name
    assert node is lock.node
    assert lockspace is lock.lock_space
    assert lock.inode_num == 5
    assert lock.lock_type == 'M'
    assert not lock.has_delta()
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_EX) == (0, 0, 0)
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_PR) == (0, 0, 0)

    # test get_key_index in class Lock
    assert lock.get_key_index() == 0

    # at this time, the lock have two shots
    shot2 = dlm.Shot(LOCKING_STATE_STR2)
    assert shot1.name == shot2.name
    lock.append(shot2)
    shot = lock._shots[-1]
    # 34      22      0       0           21278   15984   36      15      1       22484   22484
    assert shot.lock_num_prmode == '34'
    assert shot.lock_num_exmode == '22'
    assert shot.lock_num_prmode_failed == '0'
    assert shot.lock_num_exmode_failed == '0'
    assert shot.lock_total_prmode == '21278'
    assert shot.lock_total_exmode == '15984'
    assert shot.lock_max_exmode == '36'
    assert shot.lock_refresh == '15'
    total_time_field, total_num_field = lock._lock_level_2_field(dlm.LOCK_LEVEL_EX)
    assert total_time_field == 'lock_total_exmode'
    assert total_num_field == 'lock_num_exmode'
    assert lock._get_data_field_indexed(total_time_field, -1) == "15984"
    assert lock._get_data_field_indexed(total_num_field, -1) == "22"
    total_time_field, total_num_field = lock._lock_level_2_field(dlm.LOCK_LEVEL_PR)
    assert total_time_field == 'lock_total_prmode'
    assert total_num_field == 'lock_num_prmode'
    assert lock._get_data_field_indexed(total_time_field, -1) == "21278"
    assert lock._get_data_field_indexed(total_num_field, -1) == "34"
    #lock._get_latest_data_field_delta(total_time_field)
    assert lock.name == shot2.name
    assert node is lock.node
    assert lockspace is lock.lock_space
    assert lock.inode_num == 5
    assert lock.lock_type == 'M'
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_EX) == (100, 20, 5)
    assert lock.get_lock_level_info(dlm.LOCK_LEVEL_PR) == (100, 10, 10)
    assert lock.has_delta()


    # chage the order of shot1 and shot2, so the will get the negative data
    lock.append(shot2)
    lock.append(shot1)
    total_time_field, total_num_field = lock._lock_level_2_field(dlm.LOCK_LEVEL_PR)
    assert lock._get_latest_data_field_delta(total_time_field) == -100
    assert lock._get_latest_data_field_delta(total_num_field) == -10
    assert lock._get_latest_data_field_delta_abs(total_time_field) == \
           int(getattr(lock._shots[-1], total_time_field))
    assert lock._get_latest_data_field_delta_abs(total_num_field) == \
           int(getattr(lock._shots[-1], total_num_field))


    # test for _get_data_field_indexed in class Lock
    assert lock._get_data_field_indexed('lock_num_prmode', -2) == '34'
    assert lock._get_data_field_indexed('lock_total_exmode', -2) == '15984'
    assert lock._get_data_field_indexed('lock_total_exmode', -1) == '15884'
    assert lock._get_data_field_indexed('lock_total_exmode_suse', -1) == None
    assert lock._get_data_field_indexed('lock_total_exmode_suse', -2) == None
    assert lock._get_data_field_indexed('lock_total_exmode_suse', 100) == None

    # test get_key_index in class Lock
    assert lock.get_key_index() == 4412, "test get_key_index in class Lock failed"

@pytest.fixture
def data():
    """
    Read the fake data
    """
    path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(path, "locking_state_data.txt")) as fild:
        locking_state_str1 = fild.readline()
        locking_state_str2 = fild.readline()
        locking_state_str0 = fild.readline()
        locking_state_str3 = fild.readline()
        locking_state_str4 = fild.readline()
    return [locking_state_str1,
            locking_state_str2,
            locking_state_str0,
            locking_state_str3,
            locking_state_str4]

@pytest.fixture
def complete_lockset(data):
    """
    To get the LockSet object for net step text
    """
    lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
    node1 = lockspace._nodes[config.nodelist[0]]
    lock1 = dlm.Lock(node1)
    shot1 = dlm.Shot(data[0])
    shot2 = dlm.Shot(data[1])
    lock1.append(shot1)
    lock1.append(shot2)
    lockset = dlm.LockSet()
    lockset.append(lock1)
    node2 = lockspace._nodes[config.nodelist[1]]
    lock2 = dlm.Lock(node2)
    shot1 = dlm.Shot(data[3])
    shot2 = dlm.Shot(data[4])
    lock2.append(shot1)
    lock2.append(shot2)
    lockset.append(lock2)
    return lockset


class TestLockSet:
    """
    Test the LockSet clasin dlm.py
    """
    def test_LockSet_init(self, data):
        """
        Test the __init__ method of LockSet
        """
        # without lock_list
        lockset = dlm.LockSet()
        assert lockset.key_index == 0, "LockSet __init__ function test error"
        assert lockset.node_to_lock_dict == {}, "LockSet __init__ function test error"
        assert lockset._lock_list == [], "LockSet __init__ function test error"
        assert lockset._nodes_count == 0, "LockSet __init__ function test error"
        assert lockset.name == None, "LockSet __init__ function test error"
        assert lockset.inode_num == None, "LockSet __init__ function test error"

    def test_LockSet_append(self, data):
        """
        Test the append method of LockSet
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        node1 = lockspace._nodes[config.nodelist[0]]
        lock1 = dlm.Lock(node1)
        shot1 = dlm.Shot(data[0])
        shot2 = dlm.Shot(data[1])
        lock1.append(shot1)
        lock1.append(shot2)
        lockset = dlm.LockSet()
        lockset.append(lock1)
        assert lock1.name == lockset.name
        assert lock1.name._name == 'M000000000000000000000561bea619'
        with pytest.raises(AssertionError):
            lockset.append(lock1)
        node2 = lockspace._nodes[config.nodelist[1]]
        lock2 = dlm.Lock(node2)
        shot1 = dlm.Shot(data[3])
        shot2 = dlm.Shot(data[4])
        lock2.append(shot1)
        lock2.append(shot2)
        lockset.append(lock2)
        assert len(lockset.node_to_lock_dict) == 2, \
        "LockSet append function test error"
        assert lockset.node_to_lock_dict[lock1.node] == lock1, \
        "LockSet append function test error"
        assert lockset.node_to_lock_dict[lock2.node] == lock2, \
        "LockSet append function test error"


    def test_LockSet_report_once(self, complete_lockset):
        """
        Test the report_once method of LockSet
        """
        ret = complete_lockset.report_once()
        assert ret['simple'].replace(' ', '') == 'M5000000'
        "LockSet report_once function test error"
        assert ret['detailed'].replace(' ', '').replace('\n', '') == \
        'M5000000├─{node1}000000└─{node2}000000'.\
        format(node1=config.nodelist[0], node2=config.nodelist[1]), \
        "LockSet report_once function test error"

    def test_LockSet_get_key_index(self, complete_lockset):
        """
        Test the get_key_index method of LockSet
        """
        assert complete_lockset.get_key_index() == 5, \
        "LockSet get_key_index function test error"

    # TODO fix me
    def comm_test_LockSet_init_with_para(self, data):
        """
        Test the __init__ method of LockSet
        """
        # with lock_list
        assert len(config.nodelist) >= 2, \
               "the length of nodelist in config must greater or equal to 2, "\
               "please check and edit it"
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        node1 = lockspace._nodes[config.nodelist[0]]
        lock1 = dlm.Lock(node1)
        lock1.append(dlm.Shot(data[0]))
        lock1.append(dlm.Shot(data[1]))
        node2 = lockspace._nodes[config.nodelist[1]]
        lock2 = dlm.Lock(node2)
        lock2.append(dlm.Shot(data[3]))
        lock2.append(dlm.Shot(data[4]))
        lockset = dlm.LockSet([lock1])
        assert lockset.key_index == 0, "LockSet __init__ function test error"
        assert lockset.node_to_lock_dict == {}, "LockSet __init__ function test error"
        assert lockset._lock_list == [lock1, lock2], "LockSet __init__ function test error"
        assert lockset._nodes_count == 2, "LockSet __init__ function test error"
        assert lockset._name == lock1.name, "LockSet __init__ function test error"
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        node1 = lockspace._nodes[config.nodelist[0]]
        node1.process_one_shot(data[0])
        shot_name = dlm.Shot(data[0]).name
        #assert shot_name == ''
        lock1 = node1.locks[shot_name]
        lockset = dlm.LockSet([lock1])


class TestLockSetGroup():
    """
    Test the class LockSet in dlm.py
    """
    def test_LockSetGroup_init(self):
        """
        Test the __init__ method of LockSetGroup
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        lsg = dlm.LockSetGroup(10, lockspace, 100)
        assert len(lsg.lock_set_list) == 0, "LockSetGroup __init__ function test error"
        assert lsg._max_sys_inode_num == 10, "LockSetGroup __init__ function test error"
        assert lsg.lock_space == lockspace, "LockSetGroup __init__ function test error"
        assert lsg._debug == lockspace._debug, "LockSetGroup __init__ function test error"
        assert not lsg._sort_flag, "LockSetGroup __init__ function test error"
        assert lsg._max_length == 100, "LockSetGroup __init__ function test error"

    def test_LockSetGroup_append(self, complete_lockset):
        """
        Test the append method of LockSetGroup
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        lsg = dlm.LockSetGroup(10, lockspace, 100)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        assert len(lsg.lock_set_list) == 4, "LockSetGroup append function test error"
        assert lsg.lock_set_list[1] is complete_lockset, "LockSetGroup append function test error"

    def test_LockSetGroup_get_top_n_key_index(self, complete_lockset):
        """
        Test the get_top_n_key_index method of LockSetGroup
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        lsg = dlm.LockSetGroup(0, lockspace, 100)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        assert complete_lockset.inode_num == 5, \
        "LockSetGroup get_top_n_key_index function test error"
        assert lsg.get_top_n_key_index(1)[0] == complete_lockset, \
        "LockSetGroup get_top_n_key_index function test error"
        assert lsg.get_top_n_key_index(1)[0] is complete_lockset, \
        "LockSetGroup get_top_n_key_index function test error"
        # filted by inodenum
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        lsg = dlm.LockSetGroup(10, lockspace, 100)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        assert complete_lockset.inode_num == 5, \
        "LockSetGroup get_top_n_key_index function test error"
        assert lsg.get_top_n_key_index(1) == [], \
        "LockSetGroup get_top_n_key_index function test error"
        # filted by inodenum, but get back by debug flag
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        lsg = dlm.LockSetGroup(10, lockspace, 100)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        assert complete_lockset.inode_num == 5, \
        "LockSetGroup get_top_n_key_index function test error"
        assert lsg.get_top_n_key_index(1, debug=True) == [complete_lockset], \
        "LockSetGroup get_top_n_key_index function test error"

    def test_LockSetGroup_report_once(self, complete_lockset):
        """
        Test the report_once method of LockSetGroup
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
        lsg = dlm.LockSetGroup(0, lockspace, 100)
        lsg.append(complete_lockset)
        lsg.append(complete_lockset)
        ret = lsg.report_once(1)
        assert ret['simple'].strip().replace(' ', '').replace('\n', '')[18:] == \
        "lockacquisitions:total0,EX0,PR0lockresources:"\
        "total0TYPEINOEXNUMEXTIME(us)EXAVG(us)PRNUMPRTIME(us)PRAVG(us)M5000000"
        assert ret['detailed'].strip().replace(' ', '').replace('\n', '')[18:] == \
        "lockacquisitions:total0,EX0,PR0lockresources:"\
        "total0TYPEINOEXNUMEXTIME(us)EXAVG(us)PRNUMPRTIME(us)PRAVG(us)M5000000├─" in \
        ret['detailed'].strip().replace(' ', '').replace('\n', '')[18:]


@pytest.fixture(params=[config.nodelist[0], None])
def node(request):
    """
    To get the Node object for next step test
    """
    lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 0, False, display_len=10)
    node = dlm.Node(lockspace, request.param)
    return {"node":node, "lockspace":lockspace, "param":request.param}

class TestNode():
    """
    Test class Node in dlm.py
    """
    def test_init(self, node):
        """
        Test the __init__ method of Node
        """
        assert not node["node"]._locks,\
        "Node __init__ function test error"
        assert node["node"]._lock_space is node["lockspace"],\
        "Node __init__ function test error"
        assert node["node"]._lock_space == node["lockspace"],\
        "Node __init__ function test error"
        assert node["node"]._node_name == node["param"],\
        "Node __init__ function test error"

    def test_is_local_node(self, node):
        """
        Test the is_local_node method of Node
        """
        if node["param"] == None:
            assert node["node"].is_local_node(),\
            "Node is_local_node test error"
        if node["param"] != None:
            assert not node["node"].is_local_node(),\
            "Node is_local_node test error"

    def test_name(self, node):
        """
        Test the name method of Node
        """
        if node["param"] == None:
            assert node["node"].name == None,\
            "Node name test error, when init node_name not set"
        if node["param"] != None:
            assert node["node"].name == node["param"],\
            "Node name test error, when init node_name is set"


    def test_str(self, node):
        """
        Test the __str__ method of Node
        """
        assert str(node["node"]) == "lock space: {0}\n mount point: {1}"\
                                    .format(config.lockspace, config.mount_point),\
                                    "Node __str__ method test error"

    def test_process_one_shot(self, node, data):
        """
        Test the process_one_shot method of Node
        """
        node["node"].process_one_shot(data[0])
        assert len(node["node"]._locks) == 1,\
        "Node process_one_shot method test error"
        shot = dlm.Shot(data[0])
        assert node["node"]._locks[shot.name] != None,\
        "Node process_one_shot method test error"
        assert len(node["node"]._lock_space._lock_names) == 1,\
        "Node process_one_shot method test error"
        assert len(node["node"]._lock_space._lock_types) == 1,\
        "Node process_one_shot method test error"
        node["node"].process_one_shot(data[0])
        assert len(node["node"]._locks) == 1,\
        "Node process_one_shot method test error"
        assert len(node["node"]._lock_space._lock_names) == len(config.nodelist),\
        "Node process_one_shot method test error"
        assert len(node["node"]._lock_space._lock_types) == 1,\
        "Node process_one_shot method test error"
        node["node"]._lock_space.reduce_lock_name()
        assert len(node["node"]._lock_space._lock_names) == 1,\
        "LockSpace reduce_lock_name method test error"

    def test_contains(self, node, data):
        """
        Test the __contains__ method of Node
        """
        node["node"].process_one_shot(data[0])
        shot = dlm.Shot(data[0])
        assert shot.name in node["node"],\
        "Node __contains__ method test error"

    def test_gettitem(self, node, data):
        """
        Test the __getitem__ method of Node
        """
        node["node"].process_one_shot(data[0])
        shot = dlm.Shot(data[0])
        assert node["node"][shot.name] != None,\
        "Node __getitem__ method test error"

    def test_get_lock_names(self, node, data):
        """
        Test the get_lock_names method of Node
        """
        node["node"].process_one_shot(data[0])
        assert len(node["node"].get_lock_names()) == 1,\
        "Node get_lock_names method test error"
        assert list(node["node"].get_lock_names())[0]._name[0] == 'M',\
        "Node get_lock_names method test error"


class TestLockSpace:
    """
    Test the class LockSpace in dlm.py
    """
    def test_init(self):
        """
        Test the __init__ method of LockSpace
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 10, True, 100)
        assert lockspace._max_sys_inode_num == 10,\
        "LockSpace __init__ method test error"
        assert lockspace._debug,\
        "LockSpace __init__ method test error"
        assert lockspace._display_len == 100,\
        "LockSpace __init__ method test error"
        assert lockspace._name == config.lockspace,\
        "LockSpace __init__ method test error"
        assert lockspace.name == config.lockspace,\
        "LockSpace name method test error"
        assert not lockspace._lock_names,\
        "LockSpace __init__ method test error"
        assert not lockspace._lock_types,\
        "LockSpace __init__ method test error"
        assert not lockspace.should_stop,\
        "LockSpace __init__ method test error"
        assert lockspace.first_run,\
        "LockSpace __init__ method test error"
        assert len(lockspace._nodes) == len(config.nodelist),\
        "LockSpace __init__ method test error"

        lockspace = dlm.LockSpace(None, config.lockspace, 10, True, 100)
        assert len(lockspace._nodes) == 1,\
        "LockSpace __init__ method test error"
        assert lockspace._nodes['local'].is_local_node(),\
        "LockSpace __init__ method test error"

    def test_stop(self):
        """
        Test the __init__ method of LockSpace
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 10, True, 100)
        assert not lockspace.should_stop
        lockspace.stop()
        assert lockspace.should_stop,\
        "LockSpace __init__ method test error"

    def test_node_name_list(self):
        """
        Test the node_name_list method of LockSpace
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 10, True, 100)
        assert list(lockspace.node_name_list) == config.nodelist,\
        "LockSpace node_name_list method test error"

    def test_node_name(self):
        """
        Test the node_name method of LockSpace
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 10, True, 100)
        assert len(lockspace.node_list) == len(config.nodelist),\
        "LockSpace node_list method test error"

    def test_gettitem(self):
        """
        Test the __getitem__ method of LockSpace
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 10, True, 100)
        assert lockspace[config.nodelist[0]] != None,\
        "Node __getitem__ method test error"

    def test_lock_name_to_lock_set(self, data):
        """
        Test the lock_name_to_lock_set method of LockSpace
        """
        lockspace = dlm.LockSpace(config.nodelist, config.lockspace, 10, True, 100)
        for node in config.nodelist:
            node = lockspace[node]
            node.process_one_shot(data[0])
            node.process_one_shot(data[1])
        lockset = lockspace.lock_name_to_lock_set(dlm.Shot(data[0]).name)
        assert lockset.name == dlm.Shot(data[0]).name
        assert len(lockset._lock_list) == len(config.nodelist)
