#!/bin/bash
for i in `seq 1 80`
do
ls -l /mnt/ocfs2 > /dev/null
sleep 0.1
done
