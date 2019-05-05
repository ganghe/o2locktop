#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
import datetime
import time
import pdb
import os
import sys
import signal
import socket
import platform
from o2locktoplib import config
from o2locktoplib import shell

PY2 = (sys.version_info[0] == 2)
if "linux" in platform.system().lower():
    LINUX = True
else:
    LINUX = False

def check_support_debug_v4_and_get_interval(lockspace, ip):
    prefix = "ssh root@{0} ".format(ip)
    cmd = "cat /sys/kernel/debug/ocfs2/{lockspace}/locking_filter".format(
            lockspace=lockspace)
    sh = shell.shell(prefix + cmd)
    ret = sh.output()
    return ret

def set_debug_v4_interval(lockspace, ip, interval=0):
    prefix = "ssh root@{0} ".format(ip)
    cmd = "echo {interval} \> /sys/kernel/debug/ocfs2/{lockspace}/locking_filter".format(
            lockspace=lockspace,
            interval=interval)
    sh = shell.shell(prefix + cmd)
    ret = sh.output()

def is_passwdless_ssh_set(ip):
    prefix = "ssh -oBatchMode=yes root@{0} ".format(ip)
    sh = shell.shell(prefix + "uname")
    ret = sh.output()
    return (len(ret) != 0)

def get_remote_path(ip):
    prefix = "ssh root@{0} ".format(ip)
    cmd = "echo '$PATH'"
    sh = shell.shell(prefix + cmd)
    ret = sh.output()
    return ret

def get_remote_cmd_list(ip):
    path = get_remote_path(ip)
    prefix = "ssh root@{0} ".format(ip)
    ret = []
    #cmd = 'for i in `echo $PATH|sed "s/:/ /g"`; do ls $i | grep -v "^d"; done'
    if len(path) == 0:
        return []
    for i in path[0].split(':'):
        cmd = 'ls {0}'.format(i)
        sh = shell.shell(prefix + cmd)
        ret = ret + sh.output()
    return ret

def cmd_is_exist(cmd_list, ip=None):
    assert type(isinstance(cmd_list,list))
    if not ip:
        cmds = []
        cmdpaths = os.environ['PATH'].split(':')
        for cmdpath in cmdpaths:
            if os.path.isdir(cmdpath):
                cmds += os.listdir(cmdpath)
    else:
        cmds = get_remote_cmd_list(ip)
    for cmd in cmd_list:
        if cmd not in cmds:
            return False, cmd
    return True, None

def get_hostname():
    return socket.gethostname()

def now():
    return datetime.datetime.now()

def sleep(interval):
    return time.sleep(interval)

def uname_r(ip=None):
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "uname -r"
    sh = shell.shell(prefix + cmd)
    ret = sh.output()
    return ret

def is_kernel_ocfs2_fs_stats_enabled(ip=None):
    uname = uname_r(ip)
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "grep \"CONFIG_OCFS2_FS_STATS=y\" /boot/config-{uname}".format(
                uname=" ".join(uname))
    sh = shell.shell(prefix + cmd)
    ret = sh.output()
    if len(ret) == 0:
        return False
    if ret[0] == "CONFIG_OCFS2_FS_STATS=y":
        return True
    return False

def prompt_sshkey_copy_id(ip=None):
    answer = input("Did you run ssh-copy-id to the remote node?[Y/n]")
    return answer in ['Y', 'y']


def get_one_cat(lockspace, ip=None):
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "cat /sys/kernel/debug/ocfs2/{lockspace}/locking_state".format(
                lockspace=lockspace)
    sh = shell.shell(prefix + cmd)
    ret = sh.output()
    if len(ret) == 0 and config.debug:
        eprint("[DEBUG] {cmd} on {ip} return len=0".format(cmd=cmd, ip=ip))
    return ret

# fs_stat
"""
    Device => Id: 253,16  Uuid: 7635D31F539A483C8E2F4CC606D5D628  Gen: 0x6434F530  Label:
    Volume => State: 2  Flags: 0x0
     Sizes => Block: 4096  Cluster: 4096
  Features => Compat: 0x3  Incompat: 0xB7D0  ROcompat: 0x1
     Mount => Opts: 0x104  AtimeQuanta: 60
   Cluster => Stack: pcmk  Name: 7635D31F539A483C8E2F4CC606D5D628  Version: 1.0
  DownCnvt => Pid: 3802  Count: 0  WakeSeq: 707  WorkSeq: 707
  Recovery => Pid: -1  Nodes: None
    Commit => Pid: 3810  Interval: 0
   Journal => State: 1  TxnId: 2  NumTxns: 0
     Stats => GlobalAllocs: 0  LocalAllocs: 0  SubAllocs: 0  LAWinMoves: 0  SAExtends: 0
LocalAlloc => State: 1  Descriptor: 0  Size: 27136 bits  Default: 27136 bits
     Steal => InodeSlot: -1  StolenInodes: 0, MetaSlot: -1  StolenMeta: 0
OrphanScan => Local: 117  Global: 248  Last Scan: 5 seconds ago
     Slots => Num     RecoGen
            *   0           1
                1           0
                2           0
                3           0
                4           0
                5           0
                6           0
                7           0
"""
def major_minor_to_device_path(major, minor, ip=None):
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "lsblk -o MAJ:MIN,KNAME,MOUNTPOINT -l | grep '{major}:{minor}'"\
        .format( major=major,minor=minor)
    output = shell.shell(prefix + cmd)
    #output should be like
    """
    MAJ:MIN KNAME
    253:0   vda
    253:1   vda1
    253:2   vda2
    253:16  vdb
    """
    assert(len(output) > 0)
    device_name = output[0].split()[1]
    return device_name

def eprint(msg):
    print(msg, file=sys.stdout)
    # print(msg, file=sys.stderr)

def lockspace_to_device(uuid, ip=None):
    cmd = "cat /sys/kernel/debug/ocfs2/{uuid}/fs_state | grep 'Device =>'"\
            .format(uuid=uuid)
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    sh = shell.shell(prefix + cmd)
    output = sh.output()
    if len(output) == 0:
        err_msg = "\nError while detecting the mount point {uuid} on {ip}\n".format(
                        uuid=uuid, ip=ip)
        eprint(err_msg)
        os._exit(0)
        #return None, None, None
    #output should be like
    """
    Device => Id: 253,16  Uuid: 7635D31F539A483C8E2F4CC606D5D628  Gen: 0x6434F530  Label:
    """
    dev_major, dev_minor = output[0].split()[3].split(",")
    # the space must be required
    cmd = "lsblk -o MAJ:MIN,KNAME,MOUNTPOINT -l | grep '{major}:{minor} '" \
                .format(major=dev_major,minor=dev_minor)
    sh = shell.shell(prefix + cmd)
    #before grep output should be like
    """
    MAJ:MIN KNAME MOUNTPOINT
    253:0   vda
    253:1   vda1  [SWAP]
    253:2   vda2  /
    253:16  vdb   /mnt/ocfs2-1
    """
    #after grep
    """
    253:16  vdb   /mnt/ocfs2-1
    """
    output = sh.output()
    assert(len(output) > 0)
    device_name, mount_point = output[0].split()[1:]
    return dev_major, dev_minor, mount_point
    #device_name = major_minor_to_device_path(dev_major, dev_minor)
    #return device_name

def get_dlm_lockspaces(ip=None):
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "dlm_tool ls | grep ^name"
    sh = shell.shell(prefix + cmd)
    output = sh.output()
    lockspace_list = [i.split()[1] for i in output]
    if len(lockspace_list):
        return lockspace_list
    return None

def get_dlm_lockspace_mp(ip, mount_point):
    prefix = "ssh -oBatchMode=yes -oConnectTimeout=6 root@{0} ".format(ip) if ip else ""
    cmd = "o2info --volinfo {0} | grep UUID".format(mount_point)
    sh = shell.shell(prefix + cmd)
    output = sh.output()
    if (len(output) == 1):
        if config.UUID == None or config.UUID == "":
            config.UUID = output[0].split()[1]
        return output[0].split()[1]
    return None

def _trans_uuid(uuid):
    if not uuid:
        return None
    uuid = uuid.lower()
    return "{0}-{1}-{2}-{3}-{4}".format(uuid[:8],uuid[8:12],uuid[12:16],uuid[16:20],uuid[20:])

def get_dlm_lockspace_max_sys_inode_number(ip, mount_point):
    uuid = _trans_uuid(get_dlm_lockspace_mp(ip, mount_point))
    if not uuid:
        eprint("\no2locktop: error: can't find the mount point: {0}, please cheack and retry\n".format(mount_point))
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "blkid  | grep {0}".format(uuid)
    output = shell.shell(prefix + cmd).output()
    
    if (len(output) == 1):
        filesystem = output[0].split()[0].strip()[:-1]
        if filesystem[-1] == '/':
            filesystem = filesystem[:-1]    
    else:
        return None
    # TODO:fix shell
    if ip != None:
        prefix = "ssh root@{0} ".format(ip) if ip else ""
        cmd = "'debugfs.ocfs2 -R \"ls //\" {0}'".format(filesystem)
        output = shell.shell(prefix + cmd).output()
    else:
        cmd = "debugfs.ocfs2 -R \"ls //\" {0}".format(filesystem)
        output = os.popen(cmd).readlines()
    if len(output) > 0:
        return int(output[-1].split()[0])
    return None

"""
lchen-vanilla-node1:~/code # mount | grep "type ocfs2" | cut -f1
/dev/vdb on /mnt/ocfs2 type ocfs2 (rw,relatime,heartbeat=none,nointr,data=ordered,errors=remount-ro,atime_quantum=60,cluster_stack=pcmk,coherency=full,user_xattr,acl)
/dev/vdb on /mnt/ocfs2-1 type ocfs2 (rw,relatime,heartbeat=none,nointr,data=ordered,errors=remount-ro,atime_quantum=60,cluster_stack=pcmk,coherency=full,user_xattr,acl)
"""
def device_to_mount_points(device, ip=None):
    prefix = "ssh root@{0} ".format(ip) if ip else ""
    cmd = "mount | grep 'type ocfs2'"
    sh = shell.shell(prefix + cmd)
    output = sh.output()
    dev_stat = os.stat(device)
    dev_num = dev_stat.st_rdev

    ret = []
    for i in output:
        i = i.split()
        _dev = i[0]
        if os.stat(_dev).st_rdev == dev_num:
            ret.append(i[2])
    return list(set(ret))

def clear_screen():
    os.system("clear")



def kill():
    os.killpg(os.getpgid(0), signal.SIGKILL)
