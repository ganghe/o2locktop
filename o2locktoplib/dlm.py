#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
The most important library of o2locktop
The main fuction of this file is to collect
classify and statistics the locks of the cluster
"""

import threading
import time
import os
import decimal
import math
from o2locktoplib import util
from o2locktoplib import config
from o2locktoplib import cat

# cat  -----  output of one time execution of "cat locking_stat"
                # one cat contains multiple Shot(es)
# Shot -----  lockinfo for one lockres at one time of cat
# Lock   ---- a list of Shot for a typical lockres
# Node --- LockSpace on one node, which contains multiple Lock(s)
# LockSpace ---- A Lock should only belongs to one LockSpace
#

_DEBUG = False

LOCK_LEVEL_PR = 0
LOCK_LEVEL_EX = 1
KEEP_HISTORY_CNT = 2


class LockName:
    """
    The Lock format is as follows
    M    000000 0000000000000005        6434f530
    type  PAD   blockno(hex)            generation(hex)
    [0:1][1:1+6][1+6:1+6+16]            [1+6+16:]
    not for dentry
    """

    def __init__(self, lock_name):
        self._name = lock_name

    @property
    def lock_type(self):
        """
        Return the lock type of the lock, e.g M
        """
        lock_name = self._name
        return lock_name[0]

    @property
    def inode_num(self):
        """
        Return the inode number of the lock
        If the lock type is 'N', use the short inode format,
        else use the normal inode format.(You can refer ocfs2 source code)
        """
        if self._name[0] != "N":
            start, end = 7, 7+16
            lock_name = self._name
            return int(lock_name[start : end], 16)
        # dentry lock
        return int(self._name[-8:], 16)

    @property
    def generation(self):
        """
        Return the generation of the lock, not used in the new version
        """
        return self._name[-8:]

    @property
    def short_name(self):
        """
        Return the short format of a lock, just use lock type and inode number
        to represent a lock
        """
        if util.PY2:
            return "{0:4} {1:12}".format(self.lock_type, str(self.inode_num))
        return "{:4} {:12}".format(self.lock_type, str(self.inode_num))

    def __str__(self):
        return self._name

    def __eq__(self, other):
        # add to compare with None
        if not other:
            return False
        return self._name == str(other)

    def __hash__(self):
        return hash(self._name)

class Shot:
    """
    The Shot class represent a complete line in the locking_stat file
    The line includes all the information of the lock
    Support the ocfs2 debug info version3 and version4
    """
    debug_format_v3 = (
        ("debug_ver", 1),
        ("name", 1),
        ("l_level", 1),
        ("l_flags", 1),
        ("l_action", 1),
        ("l_unlock_action", 1),
        ("l_ro_holders", 1),
        ("l_ex_holders", 1),
        ("l_requested", 1),
        ("l_blocking", 1),
        ("lvb_64B", 64),
        ("lock_num_prmode", 1),
        ("lock_num_exmode", 1),
        ("lock_num_prmode_failed", 1),
        ("lock_num_exmode_failed", 1),
        ("lock_total_prmode", 1), #unit ns
        ("lock_total_exmode", 1), #unit ns
        ("lock_max_prmode", 1), #unit ns
        ("lock_max_exmode", 1), #unit ns
        ("lock_refresh", 1),
    )

    debug_format_v4 = debug_format_v3 + (
        ("lock_last_prmode", 1),
        ("lock_last_exmode", 1),
        ("lock_wait", 1),
    )

    def __init__(self, source_str):
        self.source = source_str.strip()
        strings = source_str.strip().split()
        self.debug_ver = int(strings[0].lstrip("0x"))
        assert(self.debug_ver == 3 or self.debug_ver == 4)
        self.debug_format = Shot.debug_format_v3 if self.debug_ver == 3 else Shot.debug_format_v4
        i = 0
        for item in self.debug_format:
            # key, value = item[0], item[1]
            var_name = item[0]
            var_len = item[1]
            value = "".join(strings[i: i + var_len])
            setattr(self, var_name, value)
            i += var_len
        self.name = LockName(self.name)
        self.check_hang()

    def check_hang(self):
        """
        According current timestamp to judge if the lock is hanged
        If hanged, set the lock_total_prmode and lock_total_exmode to inf
        """
        if self.lock_wait == '0':
            return
        hang_time = int(time.time()) - int(self.lock_wait)/1000000
        if hang_time > config.INTERVAL:
            if self.l_requested == '3':
                self.lock_total_prmode = float('inf')
                self.lock_prmode_hang_time = hang_time
            if self.l_requested == '5':
                self.lock_total_exmode = float('inf')
                self.lock_exmode_hang_time = hang_time

    def __str__(self):
        """
        Put the shot by a friendly format
        """
        ret = []
        keys = [i[0] for i in self.debug_format]
        for k in keys:
            value = getattr(self, k)
            ret.append("{0} : {1}".format(k, value))
        return "\n".join(ret)

    def legal(self):
        """
        Check if the inode number that decoded from the input raw string is legal
        """
        if self.name.inode_num == 0:
            return False
        return True

    @property
    def inode_num(self):
        """
        Return the inode number of the input raw string
        """
        return self.name.inode_num

    @property
    def lock_type(self):
        """
        Return the type of the input raw string
        """
        return self.name.lock_type

class Lock():
    def __init__(self, node):
        self._node = node
        self._shots = [None, None]
        # In the ocfs2 debug v4, if the lock is nit fresh, we shoule delete it
        self._fresh = 1
        self.keep_history_cnt = KEEP_HISTORY_CNT
        self.refresh_flag = False

    @property
    def shot_count(self):
        return len(self._shots)

    @property
    def name(self):
        """
        Return the name of the lock, It is same as the slot name in the lock
        """
        return getattr(self, "_name", None)

    @property
    def node(self):
        """
        Return the node that this lock belong to
        """
        return self._node

    @property
    def lock_space(self):
        """
        Return the lockspace that this lock belong to
        """
        return self._node.lock_space

    @property
    def inode_num(self):
        """
        Return the inode number of the lock
        """
        if not hasattr(self, "_name"):
            return None
        return self._name.inode_num

    @property
    def lock_type(self):
        """
        Return the lock type of this lock
        """
        if not hasattr(self, "_name"):
            return None
        return self._name.lock_type

    def fresh_lock(self):
        """
        If there is a new shot add to the lock,
        then use this function tofresh the lock
        """
        self._fresh = 1

    def un_fresh_lock(self):
        """
        Every time get raw string from nodes, unfresh the lock
        """
        if self._fresh > 0:
            self._fresh -= 1
        else:
            self._fresh = -1

    def is_fresh_lock(self):
        """
        To judge if the lock is fresh acorrding to self._fresh
        """
        if self._fresh < 0:
            return False
        return True

    def get_lock_level_info(self, lock_level, unit='ns'):
        """
        return delta_time, delta_num and key_index
        """
        #pdb.set_trace()
        if not self.has_delta():
            return 0, 0, 0

        if unit == 'ns':
            ratio = 1
        elif unit == 'us':
            ratio = 1000
        elif unit == 'ms':
            ratio = 1000000


        total_time_field, total_num_field = self._lock_level_2_field(lock_level)

        delta_time = self._get_latest_data_field_delta(total_time_field)//ratio
        delta_num = self._get_latest_data_field_delta(total_num_field)
        #(total_time, total_num, key_indexn)
        if delta_time < 0 or delta_num < 0:
            delta_time = self._get_latest_data_field_delta_abs(total_time_field)//ratio
            delta_num = self._get_latest_data_field_delta_abs(total_num_field)
        if math.isnan(delta_time):
            hang_type = self._lock_level_2_hang_field(lock_level)
            hang_time = self._get_data_field_indexed(hang_type, -1)
            return float('inf'), delta_num, float(hang_time)
        if delta_time and delta_num:
            return delta_time, delta_num, delta_time//delta_num
        return 0, 0, 0

    def has_delta(self):
        """
        If one of the slot in self._slots is None, then return False
        """
        return self._shots[0] != None and self._shots[1] != None

    def append(self, shot):
        """
        Append a shot to the lock, if the para is None, it plant to set the lock invalid
        """
        if shot == None:
            self._shots[0] = None
            self._shots[1] = None
            return
        if not hasattr(self, "_name"):
            self._name = shot.name
        else:
            assert self._name == shot.name

        self.fresh_lock()
        if not self._shots[0]:
            self._shots[0] = shot
            return
        if not self._shots[1]:
            self._shots[1] = shot
        else:
            #del self._shots[0]
            self._shots[0] = self._shots[1]
            self._shots[1] = shot
        self.refresh_flag = True

        if not _DEBUG:
            return
        print(self.node.name, self.name, self.get_key_index())
        for level in [LOCK_LEVEL_PR, LOCK_LEVEL_EX]:
            total_time_field, total_num_field = self._lock_level_2_field(level)
            time_line = self.get_line(total_time_field)
            num_line = self.get_line(total_num_field)
            if num_line[-1] - num_line[0] == 0:
                return
            print(self.name.short_name, "level=", level)
            print("total time line")
            print(time_line)
            print("total num line")
            print(num_line)

    def get_line(self, data_field, delta=False):
        """
        Get the the two latest shot according to para data_field
        """
        data_list = [int(getattr(i, data_field)) for i in self._shots]
        if not delta:
            return data_list

        if self.has_delta():
            ret = [data_list[i] - data_list[i-1] for i in \
                range(1, len(data_list))]
            return ret

        return None

    def get_key_index(self):
        """
        We will accoring the return of this function to sort all the lock
        """
        if not self.has_delta():
            return 0
        avg_key_index = 0
        for level in [LOCK_LEVEL_PR, LOCK_LEVEL_EX]:
            # could use unit='us' to match the output and make the output more significant
            key_index = self.get_lock_level_info(level, unit='ns')[-1]
            #*_, key_index= self.get_lock_level_info(level)
            avg_key_index += key_index
        return avg_key_index/2


    def _get_data_field_indexed(self, data_field, index=-1):
        """
        Get the shot info according to para data_field and index
        """
        try:
            ret = getattr(self._shots[index], data_field)
            if ret != None:
                return ret
            return 0
        except:
            return None

    def _get_latest_data_field_delta(self, data_field):
        """
        Get the subtraction of the two latest shot according to para data_field
        """
        if not self.has_delta():
            if self._shots[0] != None:
                return self._shots[0]
            return 0
        latter = self._get_data_field_indexed(data_field, -1)
        former = self._get_data_field_indexed(data_field, -2)
        if math.isinf(float(latter)) or math.isinf(float(former)):
            return float('inf')
        return float(latter) - float(former)

    def _get_latest_data_field_delta_abs(self, data_field):
        '''
        if not self.has_delta():
            return 0
        '''
        ret = self._get_data_field_indexed(data_field, -1)
        if ret != None:
            return int(ret)
        return 0

    def _lock_level_2_field(self, lock_level):
        """
        According the lock_level return two relative strings
        lock_level include 2 type, ex lock and pr lock
        """
        if lock_level == LOCK_LEVEL_PR:
            total_time_field = "lock_total_prmode"
            total_num_field = "lock_num_prmode"
        elif lock_level == LOCK_LEVEL_EX:
            total_time_field = "lock_total_exmode"
            total_num_field = "lock_num_exmode"
        else:
            return None, None
        return total_time_field, total_num_field

    def _lock_level_2_hang_field(self, lock_level):
        """
        According the lock_level return lock_prmode_hang_time
        or lock_exmode_hang_time
        """
        if lock_level == LOCK_LEVEL_PR:
            return 'lock_prmode_hang_time'
        elif lock_level == LOCK_LEVEL_EX:
            return 'lock_exmode_hang_time'
        else:
            return None

class LockSet():
    """
    locks which has the same name but on different node
    """
    def __init__(self, lock_list=None):
        self.key_index = 0
        self.node_to_lock_dict = {}

        if lock_list is None:
            self._lock_list = []
            self._nodes_count = 0
            self._name = None
            return

        name = lock_list[0].name
        for i in lock_list:
            assert i.name == name

        self._lock_list = lock_list
        self._nodes_count = len(lock_list)
        self._name = self._lock_list[0].name
        for i in self._lock_list:
            self.append(i)


    @property
    def name(self):
        """
        Return the name that same as all the Lock of the lockset
        """
        if hasattr(self, "_name"):
            return self._name
        return None

    @property
    def inode_num(self):
        if hasattr(self, "_name") and self._name != None:
            return self._lock_list[0].inode_num
        return None

    '''
    @property
    def key_index(self):
        return self.get_key_index()
    '''

    def append(self, lock):
        """
        Add the lock that has same name but on the diff node to the set
        """
        if self._name is None:
            self._name = lock.name

        self._lock_list.append(lock)
        self._nodes_count += 1
        assert lock.node not in self.node_to_lock_dict
        self.node_to_lock_dict[lock.node] = lock

    def _change_float_to_str(self, total_time, total_num, key_index, inf_str):
        """
        This function is to change the three mian number that will be showed on screen
        to int type str, and if some of the three number is inf, it represent there is
        a hang in the lock, then chang the inf to the inf_str string.
        """
        if math.isinf(total_time):
            total_time_str = str(decimal.Decimal(key_index).quantize(decimal.Decimal('0.')))+inf_str
            total_num_str = str(decimal.Decimal(total_num).quantize(decimal.Decimal('0.')))
            key_index_str = inf_str
        else:
            total_time_str = str(decimal.Decimal(total_time).quantize(decimal.Decimal('0.')))
            total_num_str = str(decimal.Decimal(total_num).quantize(decimal.Decimal('0.')))
            key_index_str = str(decimal.Decimal(key_index).quantize(decimal.Decimal('0.')))
        return total_time_str, total_num_str, key_index_str

    def report_once(self):
        """
        According to self.node_to_lock_dict splice the simple and detailed string
        """
        if not self.node_to_lock_dict:
            return None

        res_ex = {"total_time":0, "total_num":0, "key_index":0}
        res_pr = {"total_time":0, "total_num":0, "key_index":0}
        body = ""

        node_to_lock_dict_len = len(self.node_to_lock_dict)
        #temp_index = 0
        hang_time = 0
        pr_hang_flag = False
        ex_hang_flag = False
        for _node, _lock in self.node_to_lock_dict.items():

            ex_total_time, ex_total_num, ex_key_index = \
                    _lock.get_lock_level_info(LOCK_LEVEL_EX, unit='ns')
            ex_total_time_str, ex_total_num_str, ex_key_index_str = \
                self._change_float_to_str(ex_total_time, ex_total_num, ex_key_index, '(hang)')

            if math.isinf(ex_total_time):
                hang_type = _lock._lock_level_2_hang_field(LOCK_LEVEL_EX)
                hang_time += _lock._get_data_field_indexed(hang_type, -1)
                ex_hang_flag = True
            res_ex["total_time"] += ex_total_time
            res_ex["total_num"] += ex_total_num
            config.ex_locks += ex_total_num


            pr_total_time, pr_total_num, pr_key_index = \
                    _lock.get_lock_level_info(LOCK_LEVEL_PR, unit='ns')
            pr_total_time_str, pr_total_num_str, pr_key_index_str = \
                self._change_float_to_str(pr_total_time, pr_total_num, pr_key_index, '(hang)')

            if math.isinf(pr_total_time):
                hang_type = _lock._lock_level_2_hang_field(LOCK_LEVEL_PR)
                hang_time += _lock._get_data_field_indexed(hang_type, -1)
                pr_hang_flag = True
            res_pr["total_time"] += pr_total_time
            res_pr["total_num"] += pr_total_num
            config.pr_locks += pr_total_num
            node_name = util.get_hostname() if not _node.name else _node.name

            if util.PY2:
                node_detail_format = "{0:25}{1:<12}{2:<12}{3:<12}{4:<12}{5:<12}{6:<12}"
            else:
                node_detail_format = "{0:21}{1:<12}{2:<12}{3:<12}{4:<12}{5:<12}{6:<12}"
            #temp_index += 1
            node_detail_str = ""
            if ex_total_num != 0 or pr_total_num != 0:
                node_detail_str = node_detail_format.format(
                    "├─"+node_name,
                    ex_total_num_str, ex_total_time_str, ex_key_index_str,
                    pr_total_num_str, pr_total_time_str, pr_key_index_str)
                '''
                node_detail_str = node_detail_format.format(
                    "└─"+node_name,
                    ex_total_num, ex_total_time, ex_key_index,
                    pr_total_num, pr_total_time, pr_key_index)
                '''

            tmp_index = node_detail_str.rfind("├─")
            if node_detail_str != "":
                node_detail_str = node_detail_str[:tmp_index] + "└─" + node_detail_str[tmp_index+6:]
                if body == "":
                    body = node_detail_str
                else:
                    body = "\n".join([body, node_detail_str])

        if res_ex["total_num"] != 0:
            res_ex["key_index"] = res_ex["total_time"]//res_ex["total_num"]
        if res_pr["total_num"] != 0:
            res_pr["key_index"] = res_pr["total_time"]//res_pr["total_num"]



        title_format = LockSetGroup.DATA_FORMAT
        ex_total_time_str, ex_total_num_str, ex_key_index_str = \
            self._change_float_to_str(res_ex["total_time"], res_ex["total_num"],
                                      hang_time if ex_hang_flag else res_ex["key_index"], '(hang)')
        pr_total_time_str, pr_total_num_str, pr_key_index_str = \
            self._change_float_to_str(res_pr["total_time"] , res_pr["total_num"],
                                      hang_time if pr_hang_flag else res_pr["key_index"], '(hang)')
        title = title_format.format(
            self.name.short_name,
            ex_total_num_str, ex_total_time_str, ex_key_index_str,
            pr_total_num_str, pr_total_time_str, pr_key_index_str)
        lock_set_summary = '\n'.join([title, body])

        return {'simple':title, "detailed":lock_set_summary}

    def get_key_index(self):
        """
        We use the return of the fuction to sort in o2locktop
        """
        if not self._lock_list:
            return 0

        key_index = 0
        for i in self._lock_list:
            key_index += i.get_key_index()

        # self.key_index = key_index//len(self._lock_list)
        # use the lock num in all node to sort
        self.key_index = key_index
        return self.key_index

class LockSetGroup():
    """
    The group of LockSet, It contains all the infomation that get form all the nodes
    """
    TITLE_FORMAT = "{0:21}{1:12}{2:12}{3:12}{4:12}{5:12}{6:12}"
    DATA_FORMAT = "{0:21}{1:<12}{2:<12}{3:<12}{4:<12}{5:<12}{6:<12}"

    def __init__(self, max_sys_inode_num, lock_space, max_length=600):
        self.lock_set_list = []
        self._max_sys_inode_num = max_sys_inode_num
        self.lock_space = lock_space
        self._debug = self.lock_space._debug
        self._sort_flag = False
        self._max_length = max_length

    def append(self, lock_set):
        """
        Append lockset to this group, If the length of self.lock_set_list is more than self._max_length,
        We use a elimination algorithm to eliminate the smallest lock_set in self.lock_set_list,
        and keep the length of self.lock_set_list always self._max_length
        """
        lock_set.get_key_index()
        if len(self.lock_set_list) >= self._max_length:
            new_key_index = lock_set.key_index
            if new_key_index == 0:
                return
            if not self._sort_flag:
                self.lock_set_list.sort(key=lambda x: x.key_index, reverse=True)
                self._sort_flag = True
            begin = 0
            end = len(self.lock_set_list) - 1
            while begin <= end:
                middle = (begin + end)//2
                if self.lock_set_list[middle].key_index == new_key_index:
                    self.lock_set_list.insert(middle, lock_set)
                    del self.lock_set_list[-1]
                    break
                elif end - begin == 1:
                    if begin == 0 and self.lock_set_list[begin].key_index < new_key_index:
                        self.lock_set_list.insert(begin, lock_set)
                    elif end == len(self.lock_set_list) - 1 \
                         and self.lock_set_list[end].key_index > new_key_index:
                        break
                    else:
                        self.lock_set_list.insert(end, lock_set)
                    del self.lock_set_list[-1]
                    break
                elif self.lock_set_list[middle].key_index > new_key_index:
                    if begin == end and begin != len(self.lock_set_list)-1:
                        self.lock_set_list.insert(middle+1, lock_set)
                        del self.lock_set_list[-1]
                        break
                    else:
                        begin = middle
                elif self.lock_set_list[middle].key_index < new_key_index:
                    if begin == end:
                        self.lock_set_list.insert(begin, lock_set)
                        del self.lock_set_list[-1]
                        break
                    else:
                        end = middle
        else:
            self.lock_set_list.append(lock_set)

    def filter_zero(self, index_list):
        """
        Filter the zero line in index_list
        We use it befor display
        """
        ret_list = []
        if not index_list:
            return index_list
        if index_list[-1].key_index > 0:
            return index_list
        for i in index_list:
            if i.key_index != 0:
                ret_list.append(i)
        return ret_list

    def get_top_n_key_index(self, top_n, debug=False):
        """
        According LockSet method get_key_index to sort the group,
        and return the top n lock set
        """
        if not top_n:
            rows, cols = os.popen('stty size', 'r').read().split()
            if int(cols) < config.COLUMNS:
                top_n = (int(rows)//2 - 4)
            else:
                top_n = (int(rows) - 6)
            config.ROWS = top_n
        if not self._sort_flag:
            self.lock_set_list.sort(key=lambda x: x.key_index, reverse=True)
        if debug:
            if len(self.lock_set_list) > top_n:
                return self.filter_zero(self.lock_set_list[:top_n])
            return self.filter_zero(self.lock_set_list)
        ret = []
        for i in self.lock_set_list:
            if int(i.inode_num) > self._max_sys_inode_num:
                ret.append(i)
                if len(ret) == top_n:
                    return self.filter_zero(ret)
        return self.filter_zero(ret)

    def report_once(self, top_n):
        """
        Accordng the para top_n, splice the "simple" and "detailed" format string
        """
        self.sort_flag = False
        time_stamp = str(util.now())
        if '.' in time_stamp:
            time_stamp = time_stamp.split('.')[0]
        top_n_lock_set = self.get_top_n_key_index(top_n, debug=self._debug)
        what = LockSetGroup.TITLE_FORMAT.format(
            "TYPE INO  ", "EX NUM", "EX TIME(ns)", "EX AVG(ns)",
            "PR NUM", "PR TIME(ns)", "PR AVG(ns)")
        lsg_report_simple = ""
        lsg_report_simple += time_stamp + " lock acquisitions: total {0}, EX {1}, PR {2}\n"
        lsg_report_simple += "lock resources: {3}\n\n"
        lsg_report_simple += what + "\n"

        lsg_report_detailed = lsg_report_simple

        for lock_set in top_n_lock_set:
            lock_set_report = lock_set.report_once()
            lsg_report_simple += lock_set_report['simple'] + '\n'
            lsg_report_detailed += lock_set_report['detailed'] + '\n'
        types = ""
        lsg_report_simple = lsg_report_simple[:-1]
        lsg_report_detailed = lsg_report_detailed[:-1]
        total_value = 0
        for key, value in sorted(self.lock_space._lock_types.items(),
                                 key=lambda x: x[1],
                                 reverse=True):
            types += "{0} {1}, ".format(key, value)
            total_value += value
        types = "total {0}, ".format(total_value) + types
        types = types[:-2]
        lsg_report_simple = lsg_report_simple.format(config.ex_locks + config.pr_locks,
                                                     config.ex_locks,
                                                     config.pr_locks,
                                                     types)
        lsg_report_detailed = lsg_report_detailed.format(config.ex_locks + config.pr_locks,
                                                         config.ex_locks,
                                                         config.pr_locks,
                                                         types)
        self.lock_space._lock_types = {}
        config.ex_locks = 0
        config.pr_locks = 0

        return {"simple": lsg_report_simple, "detailed": lsg_report_detailed}

class Node:
    def __init__(self, lock_space, node_name=None):
        self._lock_space = lock_space
        self._locks = {}
        self.major, self.minor, self.mount_point = \
            util.lockspace_to_device(self._lock_space.name, node_name)
        self._node_name = node_name


    def is_local_node(self):
        return self.name is None

    @property
    def name(self):
        return self._node_name

    @property
    def locks(self):
        return self._locks

    def __str__(self):
        ret = "lock space: {0}\n mount point: {1}".format(
            self._lock_space.name, self.mount_point)
        return ret

    @property
    def lock_space(self):
        return self._lock_space

    def process_one_shot(self, raw_string):
        """
        Trun the raw_string to a Shot object
        parameters:
            raw_string: is a line form file locking_state
        """
        shot = Shot(raw_string)
        if not shot.legal():
            return
        shot_name = shot.name
        if shot_name not in self._locks:
            lock_tmp = Lock(self)
            lock_tmp.append(shot)
            self._locks[shot_name] = lock_tmp
        else:
            self._locks[shot_name].append(shot)
            if self._locks[shot_name].get_key_index() > 0:
                self._lock_space.add_lock_type(shot_name)
        self._lock_space.add_lock_name(shot_name)
        # self._lock_space.add_lock_type(shot_name)

    def del_unfreshed_node(self):
        for key in self._locks.keys():
            if self._locks[key].refresh_flag == False:
                self._locks.pop(key)
            else:
                self._locks[key].refresh_flag = False

    def add_last_slot_to_unfreshed_node(self):
        for key in self._locks.keys():
            if not self._locks[key].refresh_flag:
                if self._locks[key]._shots:
                    self._locks[key].append(self._locks[key]._shots[-1])
                else:
                    self._locks.pop(key)
            self._locks[key].refresh_flag = False

    def process_all_slot_worker(self, raw_slot_strs, run_once_finished_semaphore):
        """
        The worker that process the file locking state, the method will be use as a thread method
        """
        for i in raw_slot_strs:
            self.process_one_shot(i)
        for lock_name, lock_obj in self._locks.items():
            lock_obj.un_fresh_lock()
            if not lock_obj.is_fresh_lock():
                    lock_obj.append(None)
                #del self._locks[lock_name]
        run_once_finished_semaphore.release()

    def run_once_consumer(self, sort_finished_semaphore, run_once_finished_semaphore):
        """
        The concumer of the productor-consumer module, it get the raw_date form productor
        and use a thread to process the raw string.
        """
        while True:
            # the next line must before semaphore,
            (raw_slot_strs, sleep_time) = yield ''
            sort_finished_semaphore.acquire()
            if not raw_slot_strs:
                run_once_finished_semaphore.release()
                continue
            if config.DEBUG:
                print("[DEBUG] got the data on node {0}".format(self._node_name))
            consumer_process = threading.Thread(target=self.process_all_slot_worker,
                                                args=(raw_slot_strs, run_once_finished_semaphore))
            consumer_process.daemon = True
            consumer_process.start()
            if sleep_time > 0:
                time.sleep(sleep_time)


    def run_once(self, consumer):
        """
        The productor of the productor and consumer module, it get the raw string by _cat,
        and sent the raw string to consumer
        """
        if util.PY2:
            consumer.next()
        else:
            consumer.__next__()
        while True:
            start = time.time()
            if self.is_local_node():
                _cat = cat.gen_cat('local', self.lock_space.name)
            else:
                _cat = cat.gen_cat('ssh', self.lock_space.name, self.name)
            raw_slot_strs = _cat.get()
            cat_time = time.time() - start
            if config.DEBUG:
                print("[DEBUG] cat takes {0}s on node {1}".format(cat_time, self._node_name))
            if self._lock_space.first_run:
                consumer.send((raw_slot_strs, 1-cat_time-cat_time))
            else:
                #consumer.send((raw_slot_strs, config.INTERVAL-cat_time-cat_time))
                consumer.send((raw_slot_strs, config.INTERVAL-cat_time-cat_time))
        consumer.close()


    def __contains__(self, item):
        return item in self._locks

    def __getitem__(self, key):
        return self._locks.get(key, None)

    def get_lock_names(self):
        return self._locks.keys()

class LockSpace:
    """
    One lock space on multiple node
    """
    def __init__(self, node_name_list, lock_space, max_sys_inode_num, debug, display_len=10):
        #pdb.set_trace()
        self._mutex = threading.Lock()
        self._max_sys_inode_num = max_sys_inode_num
        self._debug = debug
        self._display_len = display_len
        self._name = lock_space
        self._nodes = {} #node_list[i] : Node
        self._lock_names = []
        self._lock_types = {}
        self.should_stop = False
        self._thread_list = []
        self.first_run = True
        if node_name_list is None:
            # node name None means this is a local node
            self._nodes['local'] = Node(self, None)
        else:
            for node in node_name_list:
                self._nodes[node] = Node(self, node)


    def stop(self):
        """
        Using this function can stop this process
        """
        self.should_stop = True

    def run(self, printer_queue, interval=5, ):
        """
        The main code of o2locktop
        """
        self._lock_names = []
        self._thread_list = []
        self.run_once_finished_semaphore = []
        self.sort_finished_semaphore = []
        for _, node in self._nodes.items():
            temp_run_once_finished_semaphore = threading.Semaphore(0)
            self.run_once_finished_semaphore.append(temp_run_once_finished_semaphore)
            temp_sort_finished_semaphore = threading.Semaphore(1)
            self.sort_finished_semaphore.append(temp_sort_finished_semaphore)
            thread = threading.Thread(
                target=node.run_once,
                args=(node.run_once_consumer(temp_sort_finished_semaphore,
                                             temp_run_once_finished_semaphore),))
            self._thread_list.append(thread)
        for thread in self._thread_list:
            thread.start()
        if config.DEBUG:
            print("[DEBUG] the length of thread list is {0}".format(len(self._thread_list)))
        while not self.should_stop:
            start = time.time()
            if config.DEBUG:
                print("[DEBUG] the length of semaphore list is {0}"
                      .format(len(self.run_once_finished_semaphore)))
            for semaphore in self.run_once_finished_semaphore:
                semaphore.acquire()
            lock_space_report = self.report_once()
            printer_queue.put({'msg_type':'new_content',
                               'simple':lock_space_report['simple'],
                               'detailed':lock_space_report['detailed'],
                               'rows':config.ROWS})
            if config.DEBUG:
                num_of_len = len(self._nodes)
                print("[DEBUG] the num of locke to release is {0}".format(num_of_len))
            for semaphore in self.sort_finished_semaphore:
                semaphore.release()
            end = time.time()
            if not self.first_run:
                new_interval = interval - (end - start)
                if new_interval > 0:
                    util.sleep(new_interval)
            else:
                new_interval = 1 - (end - start)
                if new_interval > 0:
                    util.sleep(new_interval)
                self.first_run = False

    @property
    def name(self):
        return self._name

    @property
    def node_name_list(self):
        return self._nodes.keys()

    @property
    def node_list(self):
        return self._nodes.values()

    def __getitem__(self, key):
        return self._nodes.get(key, None)

    def name_to_locks(self, lock_name):
        lock_on_cluster = []
        for node in self.node_list:
            lock = node[lock_name]
            if lock is not None:
                lock_on_cluster.append(lock)
        return lock_on_cluster

    def lock_name_to_lock_set(self, lock_name):
        """
        According the lock_name generate a LockSet object,
        collect the lock with para lock_name on different nodes,
        and push them in a LockSet object. 
        """
        lock_set = LockSet()
        for node in self.node_list:
            lock = node[lock_name]
            if lock is not None:
                lock_set.append(lock)
        return lock_set

    def add_lock_name(self, lock_name):
        """
        self._lock_names contains all the lock name on the lockspace(all the node),
        This function update self._lock_names
        """
        with self._mutex:
            self._lock_names.append(lock_name)

    def reduce_lock_name(self):
        """
        Delete duplicate locks in self._lock_names
        """
        self._lock_names = list(set(self._lock_names))

    def add_lock_type(self, lock_name):
        """
        self._lock_types contains all the lock types and the number of each type on the lockspace(all the node),
        This function update self._lock_types
        """
        with self._mutex:
            if lock_name.lock_type in self._lock_types.keys():
                self._lock_types[lock_name.lock_type] += 1
            else:
                self._lock_types[lock_name.lock_type] = 1


    def report_once(self):
        if config.DEBUG:
            print("[DEBUG] in LockSpace.report_once, befor reduce_lock_name, "
                  "the length of lock_name is {0}"
                  .format(len(self._lock_names)))
        self.reduce_lock_name()
        if config.DEBUG:
            print("[DEBUG] in LockSpace.report_once, after reduce_lock_name, "
                  "the length of lock_name is {0}"
                  .format(len(self._lock_names)))
        lock_names = self._lock_names
        lsg = LockSetGroup(self._max_sys_inode_num, self)
        for lock_name in lock_names:
            lock_set = self.lock_name_to_lock_set(lock_name)
            # change append method
            lsg.append(lock_set)

        return lsg.report_once(self._display_len)

def worker(lock_space_str, max_sys_inode_num, debug, display_len, nodes, printer_queue):
    # nodes == None : local mode
    # else remote mode
    try:
        lock_space = LockSpace(nodes,
                               lock_space_str,
                               max_sys_inode_num,
                               debug,
                               display_len=display_len)
        lock_space.run(printer_queue, interval=config.INTERVAL)
    except KeyboardInterrupt:
        #keyboard.reset_terminal()
        pass
    except:
        import traceback
        print(traceback.format_exc())
        exit(0)
