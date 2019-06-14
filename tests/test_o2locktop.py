import sys
import os
from queue import Queue
import pytest
import config
sys.path.append("../")

PATH = os.path.dirname(os.path.abspath(__file__))
INDEX = 0

with open(os.path.join(PATH, "../o2locktop"), "r") as filp:
    RAW_FILE = filp.readlines()

with open(os.path.join(PATH, "o2locktop.py"), "w") as filp:
    for line in RAW_FILE:
        if "importsys" in line.strip().replace(" ", ""):
            filp.write(line)
            filp.write('sys.path.append("../")\n')
            continue
        if "os.kill" in line:
            if INDEX <= 2:
                filp.write(" "*line.index("os")+"queue.put('failed')\n")
                INDEX += 1
            else:
                # fd.write(" "*line.index("os")+"raise NotImplementedError\n")
                pass
        elif not "keyboard" in line:
            filp.write(line)

import o2locktop

@pytest.fixture(params=[['-n', '127.0.0.1'], \
                        ['-n', 'node1', '-n', 'node2'], \
                        ['-n', 'node1', '-n', 'node2', '-n', '127.0.0.1'], \
                        ['']
                       ])
def node(request):
    return request.param

@pytest.fixture(params=[['/mnt/ocfs2'], ['']])
def mount_point(request):
    return request.param

@pytest.fixture(params=[['-l', '10'], ['-l', 'not_num'], ['']])
def lines(request):
    return request.param

@pytest.fixture(params=[['-d'], ['--debug'], ['']])
def debug(request):
    return request.param

@pytest.fixture(params=[['-o', 'log.txt'], ['']])
def log(request):
    return request.param

@pytest.fixture(params=[['-V'], ['--version'], ['']])
def version(request):
    return request.param

@pytest.fixture(params=[[''], ['-x']])
def wrong_arg(request):
    return request.param

def test_parse_args():
    args = o2locktop.parse_args(['-n', '127.0.0.1', '/mnt/ocfs2'])
    assert list(args.keys()) == ['mode', 'mount_node',\
                                  'mount_point', 'node_list',\
                                  'log', 'display_len',\
                                  'debug']
    assert args["mode"] == 'remote' and \
           args["mount_node"] == '127.0.0.1' and \
           args["mount_point"] == '/mnt/ocfs2' and \
           args["node_list"] == ['127.0.0.1'] and \
           not args["log"] and \
           not args["display_len"]and \
           not args["debug"]

def test_parse_args_full_function(mount_point, node, lines, debug, log, version, wrong_arg):
    raw_args = mount_point + node + lines + debug + log + version + wrong_arg
    while '' in raw_args:
        raw_args.remove('')
    if not raw_args:
        with pytest.raises(SystemExit):
            args = o2locktop.parse_args(raw_args)
    if len(lines) > 1 and lines[1] == 'not_num':
        with pytest.raises(SystemExit):
            args = o2locktop.parse_args(raw_args)
    elif mount_point[0] == '' or version[0] == '-V' or version[0] == '--version' \
         or wrong_arg[0] != '':
        with pytest.raises(SystemExit):
            args = o2locktop.parse_args(raw_args)
    else:
        args = o2locktop.parse_args(raw_args)
        if log[0] != '':
            assert args["log"] == log[1], \
            "o2locktop parse_args test error"
        else:
            assert not args["log"], \
            "o2locktop parse_args test error"
        if lines[0] != '':
            assert args["display_len"] == int(lines[1]), \
            "o2locktop parse_args test error"
        else:
            assert not args["display_len"], \
            "o2locktop parse_args test error"
        if debug[0] != '':
            assert args["debug"], \
            "o2locktop parse_args test error"
        else:
            assert not args["debug"], \
            "o2locktop parse_args test error"
        if node[0] == '':
            assert args['mode'] == 'local', \
            "o2locktop parse_args test error"
            assert len(args) == 5, \
            "o2locktop parse_args test error"
        else:
            assert args['mode'] == 'remote', \
            "o2locktop parse_args test error"
            assert len(args) == 7, \
            "o2locktop parse_args test error"
            assert len(args["node_list"]) == len(node)/2, \
            "o2locktop parse_args test error"
            assert args['mount_node'] == node[1], \
            "o2locktop parse_args test error"

def test_connection_test_worker():
    queue = Queue()
    o2locktop._connection_test_worker(config.nodelist[0], config.mount_point, queue, -1)
    assert queue.get() == config.lockspace, \
    "o2locktop _test_connection_test_worker test error, may be not set ssh passwordless or \
    not match mount point or nwt condition is bad"
    o2locktop._connection_test_worker("No Connect", config.mount_point, queue, -1)
    assert queue.get(False) == 'failed', \
    "o2locktop _test_connection_test_worker test error"

def test_connection_ocfs2_debug_test_worker():
    o2locktop._connection_ocfs2_debug_test_worker(config.nodelist[1], 0)
    with pytest.raises(SystemExit):
        o2locktop._connection_ocfs2_debug_test_worker("No Connect", 0)
    "o2locktop _connection_ocfs2_debug_test_worker test error"

def test_remote_cmd_test_worker():
    o2locktop._remote_cmd_test_worker(config.nodelist[0], 0, config.lockspace)
    with pytest.raises(SystemExit):
        o2locktop._remote_cmd_test_worker("No Connect", 0, config.lockspace)
    "o2locktop _remote_cmd_test_worker test error"
    with pytest.raises(SystemExit):
        o2locktop._remote_cmd_test_worker("No Connect", 0, config.lockspace+"NoneSence")
    "o2locktop _remote_cmd_test_worker test error"

def test_local_test():
    o2locktop.local_test(config.mount_point)
    with pytest.raises(SystemExit):
        o2locktop.local_test(config.mount_point+"NoneSence")
    "o2locktop local_test test error"

if os.path.exists(os.path.join(PATH, "o2locktop.py")):
    os.remove(os.path.join(PATH, "o2locktop.py"))
