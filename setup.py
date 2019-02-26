#!/usr/bin/env python

import distutils.core

name = 'o2locktop'

distutils.core.setup(name=name,
    version = '1.0.0',
    author = "Larry Chen, Weikai Wang, Gang He",
    author_email = "lchen@suse.com, wewang@suse.com, ghe@suse.com",
    url = "https://github.com/ganghe/o2locktop",
    description = "o2locktop is a top-like OCFS2 DLM lock monitor",
    long_description = \
"""
    OCFS2 is a shared disk cluster file system, that means the files and directies on the shard disk are accessed from the different nodes simultaneously. To protect the data consistency among the cluster, the file access is coordinated through Distributed Lock Manager(DLM). For example, OCFS2 uses Meta DLM lock per inode to protect file meta data change, OCFS2 uses Write DLM lock per inode to protect file data write, OCFS2 uses Open DLM lock per inode to implement that a opened file which was deleted from another node can still be accessed, OCFS2 also uses other types of DLM lock to protect directory related consistency and file system meta files, etc.
o2locktop is a top-like OCFS2 DLM lock monitor, it displays DLM lock usages via querying OCFS2 file system statistics from the specified nodes. Therefore, OCFS2 kernel modules must enable OCFS2_FS_STATS configuration option when compiling. If you want to know if the current OCFS2 kernel modules enable OCFS2_FS_STATS setting, you can refer to /boot/config-`uname -r` file.
You can utilize o2locktop to detect the hot files/directories, whose DLM locks are frequently referenced among the cluster.
You can get the maximal wait time per DLM lock, this helps you identify which hot files/directories should be decoupled for improving file access performance
""",
    license = "GPL2.0",
    packages = ['o2locklib'],
    scripts = [name],
)
