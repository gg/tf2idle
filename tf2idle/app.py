# coding: utf-8

import concurrent.futures
from functools import partial
import os
import re
import shutil
import subprocess
import tempfile
import time

import psutil
import sandboxie

from tf2idle.steam import SteamClient, Tf2Installation, LinkedTf2Installation
from tf2idle.util import get_process_windows, tail


class Tf2IdleApp(object):
    DEFAULT_WORKING_DIR = 'C:\\tf2idle'
    DEFAULT_STEAM_BASE_DIR = 'C:\\Program Files\\Steam'

    DEFAULT_SANDBOX_OPTIONS = {
        'AutoDelete': 'y',
        'Enabled': 'y',
        'ConfigLevel': '7',
        'AutoRecover': 'n',
    }

    DEFAULT_LAUNCH_OPTIONS = ('-textmode -sw -low -w 640 -h 480 -novid '
                              '-nosound -nomouse -noipx -nopreload '
                              '-nopreloadmodels -nod3d9ex -nodev -nodns '
                              '-nohltv -nojoy -nomessagebox -nominidumps '
                              '+clientport 27100 +hostport 27400 '
                              '-steamport 27700 +map itemtest')

    def __init__(self, steam_base_dir=None, working_dir=None,
                 sandboxie_install_dir=None):
        self.steam_base_dir = steam_base_dir or self.DEFAULT_STEAM_BASE_DIR
        self.base_installation = Tf2Installation(self.steam_base_dir)
        self.working_dir = working_dir or self.DEFAULT_WORKING_DIR
        self.sbie = sandboxie.Sandboxie(install_dir=sandboxie_install_dir)

    def __run_async(self, tasks):
        results = {}
        jobs = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for taskid, task_func in enumerate(tasks):
                job = executor.submit(task_func)
                jobs[job] = taskid

            for job in concurrent.futures.as_completed(jobs):
                results[jobs[job]] = job.result()

        return results

    def _create_tf2_installation(self, username):
        installation = LinkedTf2Installation(os.path.join(self.working_dir,
                                                          username))
        installation.link(self.base_installation)
        return installation

    def _create_sandbox(self, username):
        options = dict(self.DEFAULT_SANDBOX_OPTIONS)
        options['OpenFilePath'] = os.path.splitdrive(self.steam_base_dir)[0]
        options['OpenPipePath'] = os.path.splitdrive(self.working_dir)[0]
        self.sbie.create_sandbox(username, options)

    def _get_tf2installation(self, username):
        tf2_installation = self._create_tf2_installation(username)
        return tf2_installation

    def _get_steam_client(self, username):
        self._create_sandbox(username)
        tf2_installation = self._get_tf2installation(username)
        return SteamClient(tf2_installation,
                           shell_executer=partial(self.sbie.start,
                                                  box=username, wait=False))

    def login(self, accounts):
        tasks = [partial(self._get_steam_client(account.username).login,
                         account.username, account.password)
                 for account in accounts]
        return self.__run_async(tasks)

    def logout(self, accounts):
        tasks = [partial(self._get_steam_client(account.username).logout)
                 for account in accounts]
        logout_results = self.__run_async(tasks)
        for account in accounts:
            self.cleanup(account.username)
        return logout_results

    def launch_tf2(self, accounts, launch_options=None, autoexec_cfg=None):
        launch_options = launch_options or self.DEFAULT_LAUNCH_OPTIONS
        launch_options = launch_options.split(' ')
        tasks = [partial(self._get_steam_client(account.username).launch_tf2,
                         account.username, launch_options, autoexec_cfg)
                 for account in accounts]
        return self.__run_async(tasks)

    def close_tf2(self, accounts):
        tasks = [partial(self._get_steam_client(account.username).close_tf2)
                 for account in accounts]
        return self.__run_async(tasks)

    def cleanup(self, username):
        tf2_installation = self._get_tf2installation(username)
        self.sbie.terminate_processes(box=username)
        self.sbie.destroy_sandbox(box=username)
        tf2_installation.unlink()
