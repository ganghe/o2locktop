## The Design Document of o2locktop

### How o2locktop work

o2locktop works in a simple way. When o2locktop starts, after finishing the initial work(include some check and parsing user's command), it will generate 2 process. One is the printer process, the other is the lock_space process.

The lock_space process is responsible for collecting lock data from all nodes and processing the data, then placing the results in a queue. The queue is shared by two child processes. The printer process gets new data from the queue, and if there is new data in the queue, the printer process will move the data and display it.

After starting the printer and lock_space processes, the parent process will set the terminal's attribute to satisfy the o2locktop's requirment and wait for the command from user, the command can be q(quit), d(detail).

### The printer process

The main job of printer process is to check for updates in the queue. If there are new messages in the queue, the printer process will display the information based on the message content.

There are three message types in the queue: "kb\_hit", "new\_content", "quit". If the printer process gets a "kb_hit" message, it will switch the display mode (switching from verbose mode to simple mode or vice versa). If the message is "new\_contains", the print process will use the new content to refresh the display. If the message is "exit", the printing process will exit.

Before exit or after crash, the process will recovery the terminal.

### The lock_space process

The lock_space process maintains several threads which keep collecting ocfs2 lock data from multiple nodes.

Once a thread gathered all lock info from one Node, it translates the raw lock string to multiple Shot(s). Shot is a python class, defined in file `o2locktoplib/dlm.py`, same as Node, Lock, LockSet, LockSetGroup. Each Shot corresponds to a dlm lock ID.

Each thread collects data from the node in a regular interval. Then according the Shot's lock id, pushing the Shots that with same id to class Lock.

We use the stack to store the Shots in a Lock, and the length of the stack is 2. Using the second Shot minus the first Shot to calculate the frequency of applying for the lock.

The class Node collects all the Lock(s) in the same node. To show the top N hottest locks in the cluster, the lock_space process integrates the same Lock in different Node to LockSet.

Then putting all the LockSet(s) to the LockSetGroup ranking the multiple LockSet(s) and putting the top N hot files to the queue. The printer process will use this information to generate the final report.
