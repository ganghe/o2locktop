import sys
sys.path.append("../")
from o2locktoplib import util

def check_env(ip, mount_point):
    uuid = util.get_dlm_lockspace_mp(ip, mount_point)
    return uuid

if __name__ == "__main__":
    check_env('127.0.0.1', '/mnt/ocfs2')
