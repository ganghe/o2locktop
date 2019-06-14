#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
The utility function collection for o2locktop
"""

from __future__ import print_function
import datetime
import time
import os
import sys
import signal
import socket
import platform
from o2locktoplib import config
from o2locktoplib import shell

PY2 = (sys.version_info[0] == 2)
LINUX = True if "linux" in platform.system().lower() else False

def check_support_debug_v4_and_get_interval(lockspace, ip_addr):
    """Check if the node support ocfs2 debug information version4
    Parameters:
        lockspace(str): the ocfs2 file system uuid
        ip_addr(str): The node's ip that to be tested
    """
    prefix = "ssh root@{0} ".format(ip_addr)
    cmd = "cat /sys/kernel/debug/ocfs2/{lockspace}/locking_filter".format(
        lockspace=lockspace)
    shell_obj = shell.shell(prefix + cmd)
    ret = shell_obj.output()
    return ret

def set_debug_v4_interval(lockspace, ip_addr, interval=0):
    """Set ocfs2 filter interval
    Parameters:
        lockspace(str): the ocfs2 file system uuid
        ip_addr(str): The node's ip that to be tested
        interval(int): The ocfs2 filter interval(will be wrote to locking_filter)
    """
    prefix = "ssh root@{0} ".format(ip_addr)
    cmd = r"echo {interval} \> /sys/kernel/debug/ocfs2/{lockspace}/locking_filter".format(
        lockspace=lockspace,
        interval=interval)
    shell_obj = shell.shell(prefix + cmd)
    shell_obj.output()

def is_passwdless_ssh_set(ip_addr, user="root"):
    """Check if the remote host is set sshpasswordless for localhost
    Parameters:
        ip_addr(str): The node's ip that to be tested
        user(str): The username for the remote node
    """
    prefix = "ssh -oBatchMode=yes {user}@{ip_addr} ".format(user=user, ip_addr=ip_addr)
    shell_obj = shell.shell(prefix + "uname")
    ret = shell_obj.output()
    return len(ret) != 0

def get_remote_path(ip_addr):
    """
    Get the remote node's environmet variable PATH
    """
    prefix = "ssh root@{0} ".format(ip_addr)
    cmd = "echo '$PATH'"
    shell_obj = shell.shell(prefix + cmd)
    ret = shell_obj.output()
    return ret

def get_remote_cmd_list(ip_addr):
    """
    Split the remote node's environmet variable PATH to list array
    """
    path = get_remote_path(ip_addr)
    prefix = "ssh root@{0} ".format(ip_addr)
    ret = []
    #cmd = 'for i in `echo $PATH|sed "s/:/ /g"`; do ls $i | grep -v "^d"; done'
    if not path:
        return []
    for i in path[0].split(':'):
        cmd = 'ls {0}'.format(i)
        shell_obj = shell.shell(prefix + cmd)
        ret = ret + shell_obj.output()
    return ret

def cmd_is_exist(cmd_list, ip_addr=None):
    """Check if the commands required is installed on the remote node
    Parameters:
        cmd_list(list): The command that required
        ip_addr(str): The node's ip that to be tested, if None, test the localhost
    """
    assert type(isinstance(cmd_list, list))
    if not ip_addr:
        cmds = []
        cmdpaths = os.environ['PATH'].split(':')
        for cmdpath in cmdpaths:
            if os.path.isdir(cmdpath):
                cmds += os.listdir(cmdpath)
    else:
        cmds = get_remote_cmd_list(ip_addr)
    for cmd in cmd_list:
        if cmd not in cmds:
            return False, cmd
    return True, None

def get_hostname():
    """
    Return the hostname(str) of localhost
    """
    return socket.gethostname()

def now():
    """
    Get the current time
    """
    return datetime.datetime.now()

def sleep(interval):
    """
    Sleep interval seconds
    """
    return time.sleep(interval)

def uname_r(ip_addr=None):
    """
    Get the result of command "uname -r" on remote node
    """
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "uname -r"
    shell_obj = shell.shell(prefix + cmd)
    ret = shell_obj.output()
    return ret

def is_kernel_ocfs2_fs_stats_enabled(ip_addr=None):
    """
    Check if the CONFIG_OCFS2_FS_STATS macro is set on remote node
    """
    uname = uname_r(ip_addr)
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "grep \"CONFIG_OCFS2_FS_STATS=y\" /boot/config-{uname}".format(
        uname=" ".join(uname))
    shell_obj = shell.shell(prefix + cmd)
    ret = shell_obj.output()
    if not ret:
        return False
    if ret[0] == "CONFIG_OCFS2_FS_STATS=y":
        return True
    return False

def prompt_sshkey_copy_id():
    """
    Prompt the user to copy ssh public key to the ip
    """
    answer = input("Did you run ssh-copy-id to the remote node?[Y/n]")
    return answer in ['Y', 'y']


def get_one_cat(lockspace, ip_addr=None):
    """
    Cat the locking_state according to the fs uuid(lockspace) and ip
    """
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "cat /sys/kernel/debug/ocfs2/{lockspace}/locking_state".format(
        lockspace=lockspace)
    shell_obj = shell.shell(prefix + cmd)
    ret = shell_obj.output()
    if not ret and config.DEBUG:
        eprint("[DEBUG] {cmd} on {ip_addr} return len=0".format(cmd=cmd, ip_addr=ip_addr))
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
def major_minor_to_device_path(major, minor, ip_addr=None):
    """
    Trans the major,minor pair to the device path
    """
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "lsblk -o MAJ:MIN,KNAME,MOUNTPOINT -l | grep '{major}:{minor}'".format(
        major=major, minor=minor)
    output = shell.shell(prefix + cmd).output()
    #output should be like
    """
    MAJ:MIN KNAME
    253:0   vda
    253:1   vda1
    253:2   vda2
    253:16  vdb
    """
    assert output
    device_name = output[0].split()[1]
    return device_name

def eprint(msg):
    """
    Print message to the stdout
    """
    print(msg, file=sys.stdout)
    # print(msg, file=sys.stderr)

def lockspace_to_device(uuid, ip_addr=None):
    """
    According the uuid to get the major, minor and mount point of the device
    """
    cmd = "cat /sys/kernel/debug/ocfs2/{uuid}/fs_state | grep 'Device =>'"\
            .format(uuid=uuid)
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    shell_obj = shell.shell(prefix + cmd)
    output = shell_obj.output()
    if not output:
        err_msg = "\nError while detecting the mount point {uuid} on {ip_addr}\n".format(
            uuid=uuid, ip_addr=ip_addr)
        eprint(err_msg)
        sys.exit(0)
        # os._exit(0)
        # return None, None, None
    #output should be like
    """
    Device => Id: 253,16  Uuid: 7635D31F539A483C8E2F4CC606D5D628  Gen: 0x6434F530  Label:
    """
    dev_major, dev_minor = output[0].split()[3].split(",")
    # the space must be required
    cmd = "lsblk -o MAJ:MIN,KNAME,MOUNTPOINT -l | grep '{major}:{minor} '"\
          .format(major=dev_major, minor=dev_minor)
    shell_obj = shell.shell(prefix + cmd)
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
    output = shell_obj.output()
    assert output
    # device_name, mount_point = output[0].split()[1:]
    _, mount_point = output[0].split()[1:]
    return dev_major, dev_minor, mount_point
    #device_name = major_minor_to_device_path(dev_major, dev_minor)
    #return device_name

def get_dlm_lockspaces(ip_addr=None):
    """
    Get the dlm lockspace(fs uuid) of remote ip
    """
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "dlm_tool ls | grep ^name"
    shell_obj = shell.shell(prefix + cmd)
    output = shell_obj.output()
    lockspace_list = [i.split()[1] for i in output]
    if lockspace_list:
        return lockspace_list
    return None

def get_dlm_lockspace_mp(ip_addr, mount_point):
    """
    According the mount point get the lockspace info of remote host
    and check if the ssh-copy-id is set to the remote node
    """
    prefix = "ssh -oBatchMode=yes -oConnectTimeout=6 root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "o2info --volinfo {0} | grep UUID".format(mount_point)
    shell_obj = shell.shell(prefix + cmd)
    output = shell_obj.output()
    if len(output) == 1:
        if (not config.UUID) or (not config.UUID):
            config.UUID = output[0].split()[1]
        return output[0].split()[1]
    return None

def _trans_uuid(uuid):
    """
    Trans uuid form to 9062CAE6-F179-479C-9678-1F4EF2CFDED5 like format to
    9062cae6-f179-479c-9678-1f4ef2cfded5 format
    """
    if not uuid:
        return None
    uuid = uuid.lower()
    return "{0}-{1}-{2}-{3}-{4}".format(uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:])

def get_dlm_lockspace_max_sys_inode_number(ip_addr, mount_point):
    """
    Return the max inode number of the file system that mounted on the "mount_point"
    """
    uuid = _trans_uuid(get_dlm_lockspace_mp(ip_addr, mount_point))
    if not uuid:
        eprint("\no2locktop: error: can't find the mount point: {0}, please cheack and retry\n"
               .format(mount_point))
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "blkid  | grep {0}".format(uuid)
    output = shell.shell(prefix + cmd).output()

    if len(output) == 1:
        filesystem = output[0].split()[0].strip()[:-1]
        if filesystem[-1] == '/':
            filesystem = filesystem[:-1]
    else:
        return None
    if ip_addr != None:
        prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
        cmd = "'debugfs.ocfs2 -R \"ls //\" {0}'".format(filesystem)
        output = shell.shell(prefix + cmd).output()
    else:
        cmd = "debugfs.ocfs2 -R \"ls //\" {0}".format(filesystem)
        output = os.popen(cmd).readlines()
    if output:
        return int(output[-1].split()[0])
    return None

"""
lchen-vanilla-node1:~/code # mount | grep "type ocfs2" | cut -f1
/dev/vdb on /mnt/ocfs2 type ocfs2 (rw,relatime,heartbeat=none,nointr,data=ordered,errors=remount-ro,atime_quantum=60,cluster_stack=pcmk,coherency=full,user_xattr,acl)
/dev/vdb on /mnt/ocfs2-1 type ocfs2 (rw,relatime,heartbeat=none,nointr,data=ordered,errors=remount-ro,atime_quantum=60,cluster_stack=pcmk,coherency=full,user_xattr,acl)
"""
def device_to_mount_points(device, ip_addr=None):
    """
    According the device get the mount point, the fs on the device must be ocfs2
    /dev/sda => /mnt/ocfs2
    """
    prefix = "ssh root@{0} ".format(ip_addr) if ip_addr else ""
    cmd = "mount | grep 'type ocfs2'"
    shell_obj = shell.shell(prefix + cmd)
    output = shell_obj.output()
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
    """
    Clear the screen
    """
    os.system("clear")


def kill():
    """
    Kill the current process group
    """
    os.killpg(os.getpgid(0), signal.SIGKILL)
