VERSION = "o2locktop 1.0.10"
VERSION_SETUP = "1.0.10"
ROWS = 0
COLUMNS = 93
CMDS = ["uname", "grep", "cat", "lsblk", "dlm_tool", "o2info", "blkid", "mount", "debugfs.ocfs2"]

debug = False
if debug:
    clear = False
else:
    clear = True
interval = 5
del_unfreshed_node = False
pr_locks = 0
ex_locks = 0
UUID = ""
