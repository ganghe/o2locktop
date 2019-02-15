
# o2locktop - a top-like OCFS2 DLM lock monitor

## Introduction

OCFS2 is a shared disk cluster file system, that means the files and directies on the shard disk are accessed from the different nodes simultaneously. To protect the data consistency among the cluster, the file access is coordinated through Distributed Lock Manager(DLM). For example, OCFS2 uses Meta DLM lock per inode to protect file meta data change, OCFS2 uses Write DLM lock per inode to protect file data write, OCFS2 uses Open DLM lock per inode to implement that a opened file which was deleted from another node can still be accessed, OCFS2 also uses other types of DLM lock to protect directory related consistency and file system meta files, etc.  
o2locktop is a top-like OCFS2 DLM lock monitor, it displays DLM lock usages via querying OCFS2 file system statistics from the specified nodes. Therefore, OCFS2 kernel modules must enable OCFS2_FS_STATS configuration option when compiling. If you want to know if the current OCFS2 kernel modules enable OCFS2_FS_STATS setting, you can refer to /boot/config-\`uname -r\` file.  
You can utilize o2locktop to detect the hot files/directories, whose DLM locks are frequently referenced among the cluster.  
You can get the maximal wait time per DLM lock, this helps you identify which hot files/directories should be decoupled for improving file access performance.  

## How to use

Login one node of the OCFS2 cluster, get the o2locktop scripts from https://github.com/ganghe/o2locktop.  
Make sure passwordless SSH access between the nodes is set up, and Python interpreter is installed.  
Launch o2locktop script via the command line, e.g. "o2locktop -n node1 -n node2 -n node3 /mnt/shared".  
Type "d" to diplay DLM lock statistics for each node.
Type "Ctrl+C" or "q" to end o2locltop process.  
For more information, please see o2locktop help via the command line "o2locktop --help".

## Columns description

o2locktop displays columns for number of lock acquisition and wait time by each inode during the sampling period, the output is refreshed every 5 seconds, the records are sorted according to DLM EX/PR lock wait time.  
TYPE column represents which DLM lock type, e.g. 'M' -> inode meta data lock, 'W' -> inode file data write lock, 'O' -> inode file open lock, etc.  
INO column lists inode number.  
EX NUM column represents number of EX(write) lock acquisition.  
EX TIME column represents the maximal wait time before get EX lock.  
EX AVG column represents the average wait time before get EX lock.  
PR NUM column represents number of PR(read) lock acquisition.  
PR TIME column represents the maximal wait time before get PR lock.  
PR AVG column represents the average wait time before get PR lock.  

## OCFS2 file system

OCFS2 is a general purpose extent based shared disk cluster file system with many similarities to ext3. If you want to know more about how OCFS2 works with DLM, please refer to the following web sites.  

Project web page (old): http://oss.oracle.com/projects/ocfs2  
Project web page (new): https://ocfs2.wiki.kernel.org  
Tools web page (old): http://oss.oracle.com/projects/ocfs2-tools  
Tools web page (new): https://github.com/markfasheh/ocfs2-tools  
OCFS2 mailing lists: http://oss.oracle.com/projects/ocfs2/mailman  

## Known limitations

Since OCFS2 file system statistics in kernel records the relevant data when applying for DLM lock and getting DLM lock, if a thread can't get a DLM lock all the time, it is called entering the deadlock state, o2locktop does not reflect this situation.  

## To do list

Add switch to hide/display system file inodes.  
Replay o2locktop log file.  
Simplify o2locktop options, make it more easier to use.  
