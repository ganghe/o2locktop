## How to test

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
