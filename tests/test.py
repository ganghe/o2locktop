#!/usr/bin/env python
#encoding:utf-8
import sys
import os
import argparse
import logging

DEBUG = True

if not os.path.exists('/tmp/log/o2locktop'):
    os.system("mkdir -p /tmp/log/o2locktop")
logging.basicConfig(filename='/tmp/log/o2locktop/test.log', filemode='w', format='%(levelname)s - %(message)s', 
                    level=logging.DEBUG)


locktype=['M', 'W', 'O', 'N', 'S']


def use_logging():
    def decorator(func):
        def wrapper(*args, **kwargs):
            if DEBUG:
                print(args[0])
            return func(*args)
        return wrapper
    return decorator


@use_logging()
def log_err(msg):
    logging.error(msg)


@use_logging()
def log_info(msg):
    logging.info(msg)


def create_file(mount_point, creat_file_num = 1000):
    for i in range(1000):
        newfile = "{0}.test".format(i)
        filepath = os.path.join(mount_point, newfile)
        if not os.path.exists(filepath):
            os.system("touch {}".format(filepath))


def parse_args():
    parser = argparse.ArgumentParser(usage=None, prog='o2locktop_test', add_help=True)
    parser.add_argument('-l', metavar='the output length of o2loctop', dest='length', 
                        type=int, required = True,
                        action='store',
                        help='number of the entry that o2locktop output')
    parser.add_argument('mount_point', nargs='?',
                        help='mount point like /mnt')
    args = parser.parse_args()
    if args.mount_point == None:
        print("you must input the mount point")
        sys.exit(0)
    if args.mount_point[-1] == '/':
        args.mount_point = args.mount_point[:-1]
    return {'length': args.length,
            'mount_point': args.mount_point}


def init():
    args = parse_args()
    create_file(args.mount_point)
    

def get_max_inode(mount_point):
    cmd = 'df -i | grep "{0}$"'.format(mount_point)
    with os.popen(cmd) as fs_info_fp:
        fs_info = fs_info_fp.read()
        if len(fs_info) == 0:
            log_err("can't get the max inode according to the mount_point")
            sys.exit(0)
        else:
            return int(fs_info.strip().split()[1]) 
    
def get_uuid(mount_point):
    with os.popen("o2info --volinfo {0} | grep UUID".format(mount_point)) as fp:
        info = fp.read()
        if len(info) == 0:
            log_err("can't get the uuid according to the mount_point")
            sys.exit(0)
        return info.strip().split()[1]
         
        


def remove_clear(line):
    #return line.replace("^[[H^[[2J^[[3J", "")
    return line.replace("\x1b[H\x1b[2J\x1b[3J", "")


def not_negative(num):
    try:
        flag = int(num) >= 0
        if flag == False:
            log_err("got a negative number in the output, the negative number is {0}".format(str(num)))
    except ValueError as e:
        log_err("got a wrong format of lock number in the output, the wrong format number is {0}".format(num))
        return False


def test_line(key_word):
    def test(line, key_word = key_word):
        return key_word in line
    return test


is_first_line = test_line('o2locktop')
is_second_line = test_line('acquisitions')
is_third_line = test_line('resources')
is_head_line = test_line('TIME(us)')


def handle_first_line(uuid):
    raw_line = raw_input()
    line = remove_clear(raw_line)
    line = line.strip().split()
    if len(line) != 5:
        log_err("the first line format is wrong, the elements of the line shoule be 5, but is {0}".format(len(line)))
    if uuid != line[-1]:
        log_err("the uuid not match, should be {0}, but {1}".format(uuid, line[-1]))

def handle_second_line():
    raw_line = raw_input()
    line = remove_clear(raw_line)
    line = line.strip().split()
    if len(line) != 10:
        log_err("the second line format is wrong, the elements of the line shoule be 10, but is {0}".format(len(line)))
    return int(line[5].replace(",",""))


def handle_third_line():
    raw_line = raw_input()
    line = remove_clear(raw_line)
    line = line.strip().split()
    if len(line) == 0:
        log_err("can't get the third line")
    if len(line) < 4:
        log_err("the second line format is wrong, the elements of the line shoule be bigger than 4, but is {0}".format(len(line)))
    return int(line[3].replace(",","")) 


def handle_blank_space():
    raw_line = raw_input()
    line = remove_clear(raw_line)
    line = line.strip().split()
    if len(line) != 0:
        log_err("get blank space erong")


def handle_one_line(max_inode):
    raw_line = raw_input()
    line = remove_clear(raw_line)
    line = line.strip().split()
    if len(line) != 8:
        log_err("the out put line format is wrong, the elements of the line shoule be 8, but is {0}".format(len(line)))
    type = line[0]
    inode = int(line[1])
    locks = line[2:]
    if False in map(not_negative, locks):
        log_err("have negative or ileagall data in the data, the wrong line is :\n{0}".format(raw_line))
    if inode > max_inode:
        log_err("the inode is too big : {0}, the max inode should be {1}".format(inode, max_inode))
    if inode <= 0:
        log_err("the inode is illegal(too small): {0}".format(inode))
     

def test_one_fram(length, mount_point):
    uuid = get_uuid(mount_point) 
    max_inode = get_max_inode(mount_point)
    handle_first_line()
    total = handle_second_line()
    handle_second_line()
    handle_third_line()
    handle_blank_space()
    for i in range(length):
        handle_one_line(max_inode)


def run():
    init()



#print(get_max_inode(parse_args()['mount_point']))
#a = "M    16123071        0           0   [H[2J[3J        0           0           0           0           "
#print(is_negative(a))


#print(has_negative(10))
#args = parse_args()
#test_one_fram(args['length'], args['mount_point'])
#create_file("/mnt/shared")
