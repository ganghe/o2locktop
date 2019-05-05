#!/usr/bin/env python
#-*- coding: utf-8 -*-


from multiprocessing.dummy import Pool as ThreadPool
import multiprocessing
import sys
import signal
import threading
import time
import os
from o2locktoplib import util
from o2locktoplib import config
from o2locktoplib import keyboard
from o2locktoplib import cat

# cat  -----  output of one time execution of "cat locking_stat"
                # one cat contains multiple Shot(es)
# Shot -----  lockinfo for one lockres at one time of cat
# Lock   ---- a list of Shot for a typical lockres
# Node --- LockSpace on one node, which contains multiple Lock(s)
# LockSpace ---- A Lock should only belongs to one LockSpace
#

_debug = False

LOCK_LEVEL_PR = 0
LOCK_LEVEL_EX = 1
KEEP_HISTORY_CNT = 2


class LockName:
    """
    M    000000 0000000000000005        6434f530
    type  PAD   blockno(hex)            generation(hex)
    [0:1][1:1+6][1+6:1+6+16]            [1+6+16:]
    not for dentry
    """

    def __init__(self, lock_name):
        self._name = lock_name

    @property
    def lock_type(self):
        lock_name = self._name
        return lock_name[0]

    @property
    def inode_num(self):
        if self._name[0] != "N":
            start, end = 7, 7+16
            lock_name = self._name
            return int(lock_name[start : end], 16)
        # dentry lock
        else:
            return int(self._name[-8:], 16)

    @property
    def generation(self):
        return self._name[-8:]

    @property
    def short_name(self):
        if util.PY2:
            return "{0:4} {1:12}".format(self.lock_type, str(self.inode_num))
        else:
            return "{:4} {:12}".format(self.lock_type, str(self.inode_num))

    def __str__(self):
        return self._name

    def __eq__(self, other):
        return self._name == other._name

    def __hash__(self):
        return hash(self._name)

class Shot:
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
        ("lock_max_exmode", 1), #unit ns
        ("lock_refresh", 1),
    )

    def __init__(self, source_str):
        self.source = source_str.strip()
        strings = source_str.strip().split()
        debug_ver = int(strings[0].lstrip("0x"))
        assert(debug_ver == 3 or debug_ver == 4)
        i = 0
        for item in Shot.debug_format_v3:
            k, v = item[0], item[1]
            var_name = k
            var_len = v
            value = "".join(strings[i: i + var_len])
            setattr(self, var_name, value)
            i += var_len
        self.name = LockName(self.name)

    def __str__(self):
        ret = []
        keys = [i[0] for i in Shot.debug_format_v3]
        for k in keys:
            v = getattr(self, k)
            ret.append("{0} : {1}".format(k, v))
        return "\n".join(ret)

    def legal(self):
        if 0 == self.name.inode_num:
            return False
        return True

    @property
    def inode_num(self):
        return self.name.inode_num

    @property
    def inode_type(self):
        return self.name.inode_type

class Lock():
    def __init__(self, node):
        self._node = node
        self._shots= [None, None]
        self.keep_history_cnt = KEEP_HISTORY_CNT
        self.refresh_flag = False

    @property
    def shot_count(self):
        return len(self._shots)

    @property
    def name(self):
        return getattr(self, "_name", None)

    @property
    def node(self):
        return self._node

    @property
    def lock_space(self):
        return self._node.lock_space

    @property
    def inode_num(self):
        if not hasattr(self, "_name"):
            return None
        return self._name.inode_num

    @property
    def lock_type(self):
        if not hasattr(self, "_name"):
            return None
        return self._name.lock_type

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
        if delta_time and delta_num:
            return delta_time, delta_num, delta_time//delta_num
        return 0, 0, 0

    def has_delta(self):
        return self._shots[0] != None and self._shots[1] != None

    def append(self, shot):
        if not hasattr(self, "_name"):
            self._name = shot.name
        else:
            assert(self._name == shot.name)

        if self._shots[0] == None:
            self._shots[0] = shot
            return
        if self._shots[1] == None:
            self._shots[1] = shot
        else:
            #del self._shots[0]
            self._shots[0] = self._shots[1]
            self._shots[1] = shot
        self.refresh_flag = True

        if not _debug:
            return
        print(self.node.name, self.name, self.get_key_index())
        for level in [LOCK_LEVEL_PR, LOCK_LEVEL_EX]:
            total_time_field, total_num_field = self._lock_level_2_field(level)
            time_line =self.get_line(total_time_field)
            num_line = self.get_line(total_num_field)
            if num_line[-1] - num_line[0] == 0:
                return
            print(self.name.short_name, "level=", level)
            print("total time line")
            print(time_line)
            print("total num line")
            print(num_line)

    def get_line(self, data_field, delta=False):
        data_list = [int(getattr(i, data_field)) for i in self._shots]
        if not delta:
            return data_list

        if self.has_delta():
            ret = [data_list[i] - data_list[i-1] for i in \
                range(1, len(data_list))]
            return ret

        return None

    def get_key_index(self):
        if not self.has_delta():
            return 0
        avg_key_index = 0
        for level in [LOCK_LEVEL_PR, LOCK_LEVEL_EX]:
            # could use unit='us' to match the output and make the output more significant
            key_index = self.get_lock_level_info(level, unit='ns')[-1]
            #*_, key_index= self.get_lock_level_info(level)
            avg_key_index += key_index
        return avg_key_index//2


    def _get_data_field_indexed(self, data_field, index = -1):
        try:
            ret = getattr(self._shots[index], data_field)
            if ret != None:
                return ret
            return 0
        except:
            return None

    def _get_latest_data_field_delta(self, data_field):
        if not self.has_delta():
            if self._shots[0] != None:
                return self._shots[0]
            return 0
        latter = self._get_data_field_indexed(data_field, -1)
        former = self._get_data_field_indexed(data_field, -2)
        return int(latter) - int(former)

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
        if lock_level == LOCK_LEVEL_PR:
            total_time_field = "lock_total_prmode"
            total_num_field =  "lock_num_prmode"
        elif lock_level == LOCK_LEVEL_EX:
            total_time_field = "lock_total_exmode"
            total_num_field = "lock_num_exmode"
        else:
            return None, None
        return total_time_field, total_num_field

class LockSet():
    # locks which has the same name but on different node
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
            assert(i.name == name)

        self._lock_list = lock_list
        self._nodes_count = len(lock_list)
        self._name = self._lock_list[0].name
        for i in self._lock_list:
            self.append(i)


    @property
    def name(self):
        if hasattr(self, "_name"):
            return self._name
        return None
    
    @property
    def inode_num(self):
        if hasattr(self, "_name"):
            return self._lock_list[0].inode_num
        return None

    '''
    @property
    def key_index(self):
        return self.get_key_index()
    '''

    def append(self, lock):
        if self._name is None:
            self._name = lock.name

        self._lock_list.append(lock)
        self._nodes_count += 1
        assert lock.node not in self.node_to_lock_dict
        self.node_to_lock_dict[lock.node] = lock

    def report_once(self, detail=False):
        if len(self.node_to_lock_dict) == 0:
            return

        ret = ""
        res_ex = {"total_time":0,"total_num":0, "key_index":0}
        res_pr = {"total_time":0,"total_num":0, "key_index":0}
        body = ""

        node_to_lock_dict_len = len(self.node_to_lock_dict)
        temp_index = 0
        for _node, _lock in self.node_to_lock_dict.items():

            ex_total_time, ex_total_num, ex_key_index = \
                    _lock.get_lock_level_info(LOCK_LEVEL_EX, unit='us')

            res_ex["total_time"] += ex_total_time
            res_ex["total_num"] += ex_total_num
            config.ex_locks += ex_total_num


            pr_total_time, pr_total_num, pr_key_index = \
                    _lock.get_lock_level_info(LOCK_LEVEL_PR, unit='us')

            res_pr["total_time"] += pr_total_time
            res_pr["total_num"] += pr_total_num
            config.pr_locks += pr_total_num

            if util.PY2:
                node_detail_format = "{0:25}{1:<12}{2:<12}{3:<12}{4:<12}{5:<12}{6:<12}"
            else:
                node_detail_format = "{0:21}{1:<12}{2:<12}{3:<12}{4:<12}{5:<12}{6:<12}"
            temp_index += 1
            node_name = util.get_hostname() if not _node.name else _node.name
            if temp_index < node_to_lock_dict_len:
                node_detail_str = node_detail_format.format(
                        "├─"+node_name,
                        ex_total_num, ex_total_time, ex_key_index,
                        pr_total_num, pr_total_time, pr_key_index)
            else:
                node_detail_str = node_detail_format.format(
                        "└─"+node_name,
                        ex_total_num, ex_total_time, ex_key_index,
                        pr_total_num, pr_total_time, pr_key_index)

            if body == "":
                body = node_detail_str
            else:
                body = "\n".join([body, node_detail_str])

        if res_ex["total_num"] != 0:
            res_ex["key_index"] = res_ex["total_time"]//res_ex["total_num"]
        if res_pr["total_num"] != 0:
            res_pr["key_index"] = res_pr["total_time"]//res_pr["total_num"]



        title_format = LockSetGroup.DATA_FORMAT
        title = title_format.format(
                self.name.short_name,
                res_ex["total_num"], res_ex["total_time"], res_ex["key_index"],
                res_pr["total_num"], res_pr["total_time"], res_pr["key_index"])
        lock_set_summary = '\n'.join([title, body])

        return {'simple':title, "detailed":lock_set_summary}

    def get_key_index(self):
        if len(self._lock_list) == 0:
            return 0

        key_index = 0
        for i in self._lock_list:
            key_index += i.get_key_index()

        self.key_index = key_index//len(self._lock_list)
        return self.key_index

class LockSetGroup():
    TITLE_FORMAT = "{0:21}{1:12}{2:12}{3:12}{4:12}{5:12}{6:12}"
    DATA_FORMAT = "{0:21}{1:<12}{2:<12}{3:<12}{4:<12}{5:<12}{6:<12}"

    def __init__(self, max_sys_inode_num, lock_space, max_length = 600):
        self.lock_set_list = []
        self._max_sys_inode_num = max_sys_inode_num 
        self.lock_space = lock_space
        self._debug = self.lock_space._debug
        self._sort_flag = False
        self._max_length = max_length

    def append(self, lock_set):
        lock_set.get_key_index()
        if len(self.lock_set_list) >= self._max_length:
            new_key_index = lock_set.key_index
            if new_key_index == 0:
                return
            if self._sort_flag == False:
                self.lock_set_list.sort(key=lambda x:x.key_index, reverse=True)
                self._sort_flag = True
            begin = 0
            end = len(self.lock_set_list) - 1 
            while begin <= end:
                middle = (begin + end)//2
                if self.lock_set_list[middle].key_index == new_key_index:
                    self.lock_set_list.insert(middle,lock_set)
                    del self.lock_set_list[-1]
                    break
                elif end - begin == 1:
                    if begin == 0 and self.lock_set_list[begin].key_index < new_key_index:
                        self.lock_set_list.insert(begin,lock_set)
                    elif end == len(self.lock_set_list)-1 and self.lock_set_list[end].key_index > new_key_index:
                        break
                    else:
                        self.lock_set_list.insert(end,lock_set)
                    del self.lock_set_list[-1]
                    break
                elif self.lock_set_list[middle].key_index > new_key_index:
                    if begin == end and begin != len(self.lock_set_list)-1:
                        self.lock_set_list.insert(middle+1,lock_set)
                        del self.lock_set_list[-1]
                        break
                    else:
                        begin = middle
                elif self.lock_set_list[middle].key_index < new_key_index:
                    if begin == end:
                        self.lock_set_list.insert(begin,lock_set)
                        del self.lock_set_list[-1]
                        break
                    else:
                        end = middle
        else:
            self.lock_set_list.append(lock_set)

    def get_top_n_key_index(self, n, debug=False):
        if n == None:
            rows, cols = os.popen('stty size', 'r').read().split()
            if int(cols) < config.COLUMNS:
                n = (int(rows)//2 - 4)
            else:
                n = (int(rows) - 6)
            config.ROWS = n
        if self._sort_flag == False:
            self.lock_set_list.sort(key=lambda x:x.key_index, reverse=True)
        if debug:
            if len(self.lock_set_list) > n:
                return self.lock_set_list[:n]
            return self.lock_set_list
        ret = []
        for i in self.lock_set_list:
            if int(i.inode_num) > self._max_sys_inode_num:
                ret.append(i)
                if len(ret) == n:
                    return ret
        return ret

    def report_once(self, top_n):
        self.sort_flag = False
        time_stamp = str(util.now())
        if '.' in time_stamp:
            time_stamp = time_stamp.split('.')[0]
        top_n_lock_set = self.get_top_n_key_index(top_n, debug=self._debug)
        what = LockSetGroup.TITLE_FORMAT.format(
            "TYPE INO  ", "EX NUM", "EX TIME(us)", "EX AVG(us)",
            "PR NUM", "PR TIME(us)", "PR AVG(us)")
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
        for key,value in sorted(self.lock_space._lock_types.items(),key = lambda x:x[1], reverse = True):
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
        shot  = Shot(raw_string)
        if not shot.legal():
            return
        shot_name = shot.name
        if shot_name not in self._locks:
            lock_tmp = Lock(self)
            lock_tmp.append(shot)
            self._locks[shot_name] = lock_tmp
        else:
            self._locks[shot_name].append(shot)
        self._lock_space.add_lock_name(shot_name)
        self._lock_space.add_lock_type(shot_name)

    def del_unfreshed_node(self):
        for key in self._locks.keys():
            if self._locks[key].refresh_flag == False:
                self._locks.pop(key)
            else:
                self._locks[key].refresh_flag = False

    def add_last_slot_to_unfreshed_node(self):
        for key in self._locks.keys():
            if self._locks[key].refresh_flag == False: 
                if len(self._locks[key]._shots) > 0:
                    self._locks[key].append(self._locks[key]._shots[-1])
                else:
                    self._locks.pop(key)
            self._locks[key].refresh_flag = False

    def process_all_slot_worker(self, raw_slot_strs, run_once_finished_semaphore):
        for i in raw_slot_strs:
            self.process_one_shot(i)
        run_once_finished_semaphore.release()

    def run_once_consumer(self, sort_finished_semaphore, run_once_finished_semaphore):
        while True:
            # the next line must before semaphore,
            (raw_slot_strs, sleep_time) = yield ''
            sort_finished_semaphore.acquire()
            if not raw_slot_strs:
                run_once_finished_semaphore.release()
                continue
            if config.debug:
                print("[DEBUG] got the data on node {0}".format(self._node_name))
            consumer_process = threading.Thread(target=self.process_all_slot_worker, args=(raw_slot_strs, run_once_finished_semaphore))
            consumer_process.daemon = True
            consumer_process.start()
            if sleep_time > 0:
                time.sleep(sleep_time)


    def run_once(self, consumer):
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
            if config.debug:
                print("[DEBUG] cat takes {0}s on node {1}".format(cat_time, self._node_name))
            if self._lock_space.first_run:
                consumer.send((raw_slot_strs, 1-cat_time-cat_time))
            else:
                consumer.send((raw_slot_strs, config.interval-cat_time-cat_time))
        consumer.close()
        

    def __contains__(self, item):
        return item in self._locks

    def __getitem__(self, key):
        return self._locks.get(key, None)

    def get_lock_names(self):
        return self._locks.keys()

class LockSpace:
    "One lock space on multiple node"
    def __init__(self, node_name_list, lock_space, max_sys_inode_num, debug, display_len = 10):
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
        self.should_stop = True

    def run(self, printer_queue, interval=5, ):
        self._lock_names = []
        self._thread_list = []
        self.run_once_finished_semaphore = []
        self.sort_finished_semaphore = []
        for node_name, node in self._nodes.items():
            temp_run_once_finished_semaphore = threading.Semaphore(0)
            self.run_once_finished_semaphore.append(temp_run_once_finished_semaphore)
            temp_sort_finished_semaphore = threading.Semaphore(1)
            self.sort_finished_semaphore.append(temp_sort_finished_semaphore)
            th = threading.Thread(target=node.run_once, args=(node.run_once_consumer(temp_sort_finished_semaphore, temp_run_once_finished_semaphore),))
            self._thread_list.append(th)
        for th in self._thread_list:
            th.start()
        if config.debug:
            print("[DEBUG] the length of thread list is {0}".format(len(self._thread_list)))
        while not self.should_stop:
            start = time.time()
            if config.debug:
                print("[DEBUG] the length of semaphore list is {0}".format(len(self.run_once_finished_semaphore)))
            for semaphore in self.run_once_finished_semaphore:
                semaphore.acquire()
            lock_space_report = self.report_once()
            printer_queue.put(
                            {'msg_type':'new_content',
                            'simple':lock_space_report['simple'],
                            'detailed':lock_space_report['detailed'],
                            'rows':config.ROWS}
                            )
            if config.debug:
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
        lock_set = LockSet()
        for node in self.node_list:
            lock = node[lock_name]
            if lock is not None:
                lock_set.append(lock)
        return lock_set

    def add_lock_name(self, lock_name):
        with self._mutex:
            self._lock_names.append(lock_name)

    def reduce_lock_name(self):
        self._lock_names = list(set(self._lock_names))

    def add_lock_type(self, lock_name):
        with self._mutex:
            if lock_name.lock_type in self._lock_types.keys():
                self._lock_types[lock_name.lock_type] += 1
            else:
                self._lock_types[lock_name.lock_type] = 1


    def report_once(self):
        if config.debug:
            print("[DEBUG] in LockSpace.report_once, befor reduce_lock_name, the length of lock_name is {0}".format(len(self._lock_names)))
        self.reduce_lock_name()
        if config.debug:
            print("[DEBUG] in LockSpace.report_once, after reduce_lock_name, the length of lock_name is {0}".format(len(self._lock_names)))
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
        lock_space = LockSpace(nodes, lock_space_str, max_sys_inode_num, debug, display_len=display_len)
        lock_space.run(printer_queue, interval=config.interval)
    except KeyboardInterrupt:
        #keyboard.reset_terminal()
        pass
    except:
        import traceback
        print(traceback.format_exc())
        exit(0)

