# How to test

## unit test
### requirement
- The ha cluster envirment is required, at least 2 nodes, and you must write the node in config.py
- You must be the root

- Edit the config, replace the MOUNT_POINT in your env
- Make sure the UUID is the UUID of ocfs2 in the cluster

- The unit test only support python3
- You must install pytest

### test command
- `# cd tests`
- `# pytest`

## CI

### requirement
- Python3 only
- The ha cluster is required
- You must install the packages in requirement.txt

### test command
- for example<br>
 `root@tests # ../o2locktop -l 10 /mnt/ocfs2 -d | ./test.py -l 10 /mnt/ocfs2/ -o test.log`<br>
 The command above that will test the local mode of o2locktop, and you must assign the lines of o2locktop's output, so the -l parameter is required. o2locktop and test.py must have the same -l parameter.<br>
- The -o parameter in test.py assign a log file of test.py's result. If not assign -o parameter, the log file will be `/tmp/log/o2locktop/test.log` as default.
- For more information, you can see by -h parameter.

 Use the follow command to test the o2locktop remote mode<br>
 `root@tests # ../o2locktop -l 10 /mnt/ocfs2 -d -n node1 | ./test.py -l 10 /mnt/ocfs2/ -o test.log -n node1`<br>
 Use the follow command to test the o2locktop remote mode with mulity nodes<br>
 `root@tests # ../o2locktop -l 10 /mnt/ocfs2 -d -n node1 -n node2| ./test.py -l 10 /mnt/ocfs2/ -o test.log -n node1 -n node2`<br>

- And maybe you need to chang the `sshd_config` file on remote cluster node, change the max connection number. For example, change `# MaxSessions 10` the line in `sshd_config` to `MaxSessions 100`. After that, you need restart the sshd service. 
