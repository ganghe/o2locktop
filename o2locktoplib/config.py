"""
The config file of o2locktop
"""
VERSION = "o2locktop 1.0.10"
VERSION_SETUP = "1.0.10"
ROWS = 0
COLUMNS = 93
CMDS = ["uname", "grep", "cat", "lsblk", "dlm_tool", "o2info", "blkid", "mount", "debugfs.ocfs2"]

DEBUG = False
if DEBUG:
    CLEAR = False
else:
    CLEAR = True
INTERVAL = 5
pr_locks = 0
ex_locks = 0
UUID = ""
