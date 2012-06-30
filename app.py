# coding: utf-8

import concurrent.futures
from functools import partial
import os

import sandboxie

from tf2idle.steam import SteamClient, Tf2Installation, LinkedTf2Installation


def create_app(config, steam_base_dir=None, working_dir=None):
    steam_base_dir = steam_base_dir or config['core']['steam_base_dir']
    if not steam_base_dir:
        raise Exception('steam_base_dir must be specified.')

    working_dir = working_dir or config['core']['working_dir'] or os.getcwd()

    return Tf2IdleApp(steam_base_dir, working_dir)


class Tf2IdleApp(object):
    def __init__(self, config, steam_base_dir=None, working_dir=None):
        self.config = config
        self.steam_base_dir = (steam_base_dir or
                               config['core']['steam_base_dir'])
        self.base_installation = Tf2Installation(self.steam_base_dir)
        self.working_dir = working_dir or config['core']['working_dir']
        self.sbie = sandboxie.Sandboxie(
            install_dir=self.config['core']['sandboxie_dir'])

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
        options = dict(self.config['sandbox_options'])
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
        launch_options = launch_options or ' '.join(
            self.config['tf2']['launch_options'].splitlines())
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
