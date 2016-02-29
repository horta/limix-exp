from __future__ import absolute_import
import os
from tabulate import tabulate
from limix_misc.pickle_ import pickle, unpickle, pickle_merge
from limix_misc.pickle_ import SlotPickleMixin
from limix_misc.pickle_ import PickleByName
from limix_misc.report import BeginEnd
from limix_misc.scalar import isfloat
from limix_misc.str_ import summarize

def extract_successes_and_failures(tasks):
    methods = tasks[0].get_result().methods

    nsucs = {m:0 for m in methods}
    nfails = {m:0 for m in methods}

    for task in tasks:
        tr = task.get_result()
        for m in methods:
            if tr.error_status(m) == 0:
                nsucs[m] += 1
            else:
                nfails[m] += 1

    return dict(nsucs=nsucs, nfails=nfails)

class TaskArgs(SlotPickleMixin):
    def __init__(self):
        super(TaskArgs, self).__init__()
        self._names = []

    def add(self, name):
        self._names.append(name)

    def get_names(self):
        return self._names

class Task(PickleByName):
    def __init__(self, workspace_id, experiment_id, task_id):
        super(Task, self).__init__()
        self.task_id = int(task_id)
        self.workspace_id = workspace_id
        self.experiment_id = experiment_id

    def run(self):
        from .workspace import get_experiment
        e = get_experiment(self.workspace_id, self.experiment_id)
        return e.do_task(self)

    @property
    def finished(self):
        return self.get_result() is not None

    def get_result(self):
        from .workspace import get_experiment
        e = get_experiment(self.workspace_id, self.experiment_id)
        if e is None:
            return None

        return e.get_task_result(self.task_id)

class TaskResult(SlotPickleMixin):
    __slots__ = ['total_elapsed', 'workspace_id', 'experiment_id', 'task_id',
                 '_elapsed', '_error_status', '_error_msg', '_methods']

    def __init__(self, workspace_id, experiment_id, task_id):
        super(TaskResult, self).__init__()
        self.total_elapsed = float('nan')
        self.workspace_id = workspace_id
        self.experiment_id = experiment_id
        self.task_id = int(task_id)
        self._elapsed = dict()
        self._error_status = dict()
        self._error_msg = dict()
        self._methods = set()

    def get_task(self):
        from .workspace import get_experiment
        e = get_experiment(self.workspace_id, self.experiment_id)
        return e.get_task(self.task_id)

    def elapsed(self, method):
        return self._elapsed[method]

    def error_status(self, method):
        return self._error_status[method]

    def error_msg(self, method):
        return self._error_msg[method]

    @property
    def methods(self):
        return list(self._methods)

    def set_error_status(self, method, error_status):
        self._add_method(method)
        self._error_status[method] = int(error_status)

    def set_error_msg(self, method, error_msg):
        self._add_method(method)
        self._error_msg[method] = str(error_msg)

    def set_elapsed(self, method, elapsed):
        self._add_method(method)
        self._elapsed[method] = float(elapsed)

    def _add_method(self, method):
        self._methods.add(method)

def load_tasks(fpath, verbose=True):
    with BeginEnd('Loading tasks', silent=not verbose):
        if os.path.exists(fpath):
            if verbose:
                print "Exist %s" % fpath
        else:
            print "Does not exist %s" % fpath
        tasks = unpickle(fpath)
        if verbose:
            print('   %d tasks found  ' % len(tasks))
    return tasks

def store_tasks(tasks, fpath):
    if os.path.exists(fpath):
        return
    pickle({t.task_id:t for t in tasks}, fpath)

def load_task_args(fpath):
    return unpickle(fpath)

def store_task_args(task_args, fpath):
    if os.path.exists(fpath):
        return
    pickle(task_args, fpath)

def collect_task_results(folder, force_cache=False):
    if force_cache:
        fpath = os.path.join(folder, 'all.pkl')
    else:
        with BeginEnd('Merging task results'):
            fpath = pickle_merge(folder)
    if fpath is None:
        return fpath
    with BeginEnd('Unpickling merged task results'):
        out = unpickle(fpath)
    return out

def store_task_results(task_results, fpath):
    with BeginEnd('Storing task results'):
        pickle({tr.task_id:tr for tr in task_results}, fpath)
        print('   %d task results stored   ' % len(task_results))

def tasks_summary(tasks):
    from collections import OrderedDict
    from .workspace import get_experiment

    if len(tasks) == 0:
        return ''

    wid = tasks[0].workspace_id
    eid = tasks[0].experiment_id

    e = get_experiment(wid, eid)

    args = e.get_task_args().get_names()

    args.sort()
    d = OrderedDict([(k, set()) for k in args])

    for task in tasks:
        for a in args:
            d[a].add(getattr(task, a))

    for a in args:
        d[a] = list(d[a])
        d[a].sort(key= lambda x: float(x) if isfloat(x) else x)

    table = zip(d.keys(), [summarize(v) for v in d.values()])
    return '*** Task summary ***\n' + tabulate(table)
