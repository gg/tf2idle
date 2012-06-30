import collections
import fnmatch
import functools
import os
import re
import shutil
import subprocess
import tempfile
import time

import psutil

from tf2idle.util import get_process_windows, tail


SteamAccount = collections.namedtuple('SteamAccount', 'username password')


class LoginResult(object):
    LOGIN_SUCCEEDED = 0x1
    LOGIN_FAILED = 0x2
    LOGIN_CANCELED = 0x3
    ACCOUNT_SUSPENDED = 0x4


class Tf2LaunchResult(object):
    LAUNCH_SUCCEEDED = 0x1
    LAUNCH_FAILED = 0x2
    NOT_LOGGED_IN = 0x3
    LAUNCH_CANCELED = 0x4
    UNKNOWN_VIDEO_CARD = 0x5
    FATAL_ERROR = 0x6


class SteamClient(object):
    def __init__(self, tf2_installation, shell_executer):
        self.tf2_installation = tf2_installation
        self.shell_executer = shell_executer

    def _run_steam_command(self, *args):
        command = '"{steam_exe}" -silent {args}'.format(
            steam_exe=self.tf2_installation.steam_exe_path,
            args=' '.join(args))
        self.shell_executer(command)

    def get_steam_process(self, default=None):
        for process in psutil.process_iter():
            if (process.name == 'steam.exe' and
                    process.getcwd() == self.tf2_installation.steam_dir):
                return process
        return default

    def get_hl2_process(self, default=None):
        steam_process = self.get_steam_process()
        if steam_process is not None:
            for child_process in steam_process.get_children():
                if child_process.name == 'hl2.exe':
                    return child_process
        return None

    def login(self, username, password=None):
        def wait_for_steam_process(timeout=10, poll_interval=1):
            endtime = time.time() + timeout
            while True:
                steam_process = self.get_steam_process()
                if steam_process is not None:
                    break

                if time.time() > endtime:
                    raise Exception('Could not launch steam.exe.')
                time.sleep(poll_interval)
            return steam_process

        steam_process = self.get_steam_process()

        if steam_process is None:
            login_command = '-login "{}" "{}"'.format(username, password)
            self._run_steam_command(login_command)
            steam_process = wait_for_steam_process()

        try:
            steam_process.nice = psutil.BELOW_NORMAL_PRIORITY_CLASS
            # set affinity too?

            is_update = steam_guard_required = False

            # Consider the login to be successful if the following Steam
            # windows exist: 'Steam', 'Friends', 'Servers'.
            while True:
                windows = {window.title: window for window in
                           get_process_windows(steam_process.pid)}

                if any(title.startswith('Steam - Updating')
                       for title in windows) and not is_update:
                    print('Steam update detected.')
                    is_update = True

                # If there are no Steam windows and an update was detected,
                # assume the Steam client has been updated and restarted.
                if not windows and is_update:
                    print('Waiting for Steam to restart after update...')
                    steam_process = wait_for_steam_process(timeout=30)

                error = None
                if any(title in windows for title in ('Steam - Error',
                                                      'Steam - Warning')):
                    print('Login failed.')
                    error = LoginResult.LOGIN_FAILED

                if 'Steam - Contact us' in windows:
                    print('Steam account suspended!')
                    error = LoginResult.ACCOUNT_SUSPENDED

                if ('Steam Guard - Computer Authorization Required' in windows
                        and not steam_guard_required):
                    print('Steam Guard Authorization required.')
                    steam_guard_required = True

                if error:
                    steam_process.terminate()
                    return error

                if all(title in windows
                       for title in ('Steam', 'Friends', 'Servers')):
                    print('Login succeeded.')
                    return LoginResult.LOGIN_SUCCEEDED

                if not steam_process.is_running():
                    return LoginResult.LOGIN_CANCELED

                time.sleep(1)
        except psutil.NoSuchProcess:
            return LoginResult.LOGIN_CANCELED

    def logout(self):
        steam_process = self.get_steam_process()
        try:
            if steam_process is not None:
                self._run_steam_command('-shutdown')
                steam_process.wait(30)
        except psutil.TimeoutExpired:
            steam_process.terminate()
        except psutil.NoSuchProcess:
            pass

        return True

    def _apply_tf2_registry_settings(self):
        # apply registry settings to minimize resource consumption
        tf2idle_reg = '''\
        REGEDIT4

        [HKEY_CURRENT_USER\\Software\\Valve\\Source\\tf\\Settings]
        "AutoConfigVersion"="dword:00000001"
        "DXLevel_V1"="dword:00000051"
        "mat_aaquality"="dword:00000000"
        "mat_antialias"="dword:00000000"
        "mat_bumpmap"="dword:00000000"
        "mat_colorcorrection"="dword:00000000"
        "mat_forceaniso"="dword:00000000"
        "mat_forcehardwaresync"="dword:00000000"
        "mat_hdr_level"="dword:00000000"
        "mat_parallaxmap"="dword:00000000"
        "mat_picmip"="dword:00000002"
        "mat_reducefillrate"="dword:00000001"
        "mat_specular"="dword:00000000"
        "mat_trilinear"="dword:00000000"
        "mat_vsync"="dword:00000000"
        "MotionBlur"="dword:00000000"
        "r_rootlod"="dword:00000002"
        "r_shadowrendertotexture"="dword:00000000"
        "r_waterforceexpensive"="dword:00000000"
        "r_waterforcereflectentities"="dword:00000000"
        "ScreenHeight"="dword:00000258"
        "ScreenMonitorGamma"="2.2""
        "ScreenMSAA"="dword:00000000"
        "ScreenMSAAQuality"="dword:00000000"
        "ScreenWidth"="dword:00000320"
        "ScreenWindowed"="dword:00000001"
        "ShadowDepthTexture"="dword:00000000"
        "User Token 2"=""
        "User Token 3"=""'''
        with tempfile.NamedTemporaryFile('wt', suffix='.reg',
                                         delete=False) as temp:
            temp.write(tf2idle_reg)
            temp.close()
            self.shell_executer(' '.join(['regedit', '/s', temp.name]))
            try:
                os.unlink(temp.name)
            except OSError:
                pass

    def launch_tf2(self, username, launch_options, autoexec_cfg=None):
        steam_process = self.get_steam_process()
        if steam_process is None:
            print('Not logged in.')
            return Tf2LaunchResult.NOT_LOGGED_IN

        tf2_dir = os.path.join(self.tf2_installation.steam_dir,
                               'steamapps', username, 'team fortress 2')
        tf2_console_log = os.path.join(tf2_dir, 'tf', 'console.log')

        hl2_process = self.get_hl2_process()
        if hl2_process is None:
            self._apply_tf2_registry_settings()

            if autoexec_cfg is not None and os.path.exists(autoexec_cfg):
                cfg_dir = os.path.join(tf2_dir, 'tf', 'cfg')
                try:
                    os.makedirs(cfg_dir)
                except OSError:
                    pass
                shutil.copy(autoexec_cfg, os.path.join(cfg_dir,
                                                       'autoexec.cfg'))

            # TF2 console output will be logged to
            # steam_dir/steamapps/username/team fortress 2/tf2/console.log
            if '-condebug' not in launch_options:
                launch_options.append('-condebug')

            # Remove a pre-existing console.log
            try:
                os.unlink(tf2_console_log)
            except OSError:
                pass

            self._run_steam_command('-applaunch 440', *launch_options)

        # Wait for hl2.exe to launch.
        while True:
            try:
                windows = {window.title: window for window in
                           get_process_windows(steam_process.pid)}

                if 'Unknown Video Card' in windows:
                    print('Unknown video card')
                    windows['Unknown Video Card'].close()
                    return Tf2LaunchResult.UNKNOWN_VIDEO_CARD

                for title in ['Steam - Error', 'Steam - Warning',
                              'Ready - Team Fortress 2']:
                    if title in windows:
                        windows[title].close()
                        print('Launch error:', title)
                        return Tf2LaunchResult.LAUNCH_FAILED

                if 'Team Fortress 2 - Steam' in windows:
                    print('Preparing to launch TF2...')

                if 'Updatng Team Fortress 2' in windows:
                    print('Updating TF2...')

                hl2_process = self.get_hl2_process()
                if hl2_process is not None:
                    break

                time.sleep(5)
            except psutil.NoSuchProcess:
                return Tf2LaunchResult.NOT_LOGGED_IN

        print('hl2.exe launched')
        try:
            hl2_process.nice = psutil.BELOW_NORMAL_PRIORITY_CLASS
            # set affinity too?
        except psutil.NoSuchProcess:
            return Tf2LaunchResult.LAUNCH_CANCELED

        # Tail the console.log to obtain the server IP, server port, and client
        # port. Stop when a "connected" string is found.
        ip = server_port = client_port = None
        connected = False
        while not connected:
            try:
                windows = {window.title: window for window in
                           get_process_windows(hl2_process.pid)}
                if any(title in windows for title in
                       ['Error!', 'ERROR',
                        'Microsoft Visual C++ Runtime Library']):
                    print('Fatal error')
                    return Tf2LaunchResult.FATAL_ERROR

                with open(tf2_console_log) as console_log:
                    for line in tail(console_log, start=os.SEEK_CUR):
                        if ip is None:
                            regex = ('IP ([0-9.]+|unknown), .+, '
                                     'ports (\d+) SV / (\d+) CL')
                            match = re.search(regex, line)
                            if match:
                                ip, server_port, client_port = match.groups()
                        elif 'connected' in line:
                            connected = True
                            break
            except IOError:
                pass
            except psutil.NoSuchProcess:
                return Tf2LaunchResult.LAUNCH_CANCELED
            time.sleep(1)

        if ip == 'unknown':
            ip = None
        print('Tf2 launch succeeded:', ip, server_port, client_port)
        return Tf2LaunchResult.LAUNCH_SUCCEEDED, ip, server_port, client_port

    def close_tf2(self):
        hl2_process = self.get_hl2_process()
        try:
            if hl2_process is not None:
                hl2_process.terminate()
        except psutil.NoSuchProcess:
            pass

        # Free up ~800MB of disk space by removing the tf2 directory.
        tf2_dir = os.path.join(self.tf2_installation.steam_dir, 'steamapps',
                               username, 'team fortress 2')
        try:
            shutil.rmtree(tf2_dir)
        except OSError:
            pass

        return True


class LinkedInstallationError(Exception):
    pass


class LinkRules(object):
    def __init__(self, symlinks=set(), copy_dirs=set(), copy_files=set()):
        self.symlinks = set(symlinks)
        self.copy_dirs = set(copy_dirs)
        self.copy_files = set(copy_files)


class SteamInstallation(object):
    def __init__(self, steam_dir):
        self.steam_dir = steam_dir
        self.steamapps_dir = os.path.join(steam_dir, 'steamapps')
        self.steam_exe_path = os.path.join(steam_dir, 'steam.exe')

    def installed(self):
        return os.path.exists(self.steam_exe_path)


class Tf2Installation(SteamInstallation):
    REQUIRED_GCFS = ('multiplayer ob binaries.gcf',
                     'orangebox media.gcf',
                     'source 2007 shared materials.gcf',
                     'source 2007 shared models.gcf',
                     'source 2007 shared sounds.gcf',
                     'source materials.gcf',
                     'source models.gcf',
                     'source sounds.gcf',
                     'team fortress 2 client content.gcf',
                     'team fortress 2 content.gcf',
                     'team fortress 2 materials.gcf')

    def installed(self):
        for gcf in self.REQUIRED_GCFS:
            gcf_path = os.path.join(self.steamapps_dir, gcf)
            if not os.path.exists(gcf_path):
                return False
        return super(Tf2Installation, self).installed()


class IdlerTf2Installation(Tf2Installation):
    def __init__(self, steam_dir, username):
        super(Tf2Installation, self).__init__(steam_dir)
        self.username = username
        self.tf2_dir = os.path.join(self.steamapps_dir, username,
                                    'team fortress 2')


class LinkedSteamInstallation(SteamInstallation):
    STEAM_DIR_LINK_RULES = LinkRules(copy_dirs={'bin'},
                                     copy_files={'*.dll', '*.exe'})
    STEAMAPPS_DIR_LINK_RULES = LinkRules(symlinks={'*.gcf'})

    def link(self, other_installation, remove_existing=False,
             steam_dir_link_rules=STEAM_DIR_LINK_RULES,
             steamapps_dir_link_rules=STEAMAPPS_DIR_LINK_RULES):
        """Links this installation to `other_installation`.

        If `remove_existing` is True, the currently linked installation will
        be removed before linking.

        Raises ``LinkedInstallationError`` if there is a problem linking.
        """
        if self.installed() and not remove_existing:
            return

        if not other_installation.installed():
            error = 'Steam is not installed at {0}'.format(
                other_installation.steam_dir)
            raise LinkedInstallationError(error)

        try:
            self.unlink()

            self._link_dir(other_installation.steam_dir, self.steam_dir,
                           steam_dir_link_rules)

            self._link_dir(other_installation.steamapps_dir,
                           self.steamapps_dir,
                           steamapps_dir_link_rules)
        except LinkedInstallationError as e:
            error = 'Could not unlink existing installation.'
            raise LinkedInstallationError(error) from e
        except Exception as e:
            try:
                self.unlink()
            except:
                pass
            else:
                error = 'Could not link installation.'
                raise LinkedInstallationError(error) from e

    def unlink(self):
        """Unlinks this installation."""
        try:
            # order is important
            self._unlink_dir(self.steamapps_dir)
            self._unlink_dir(self.steam_dir)
        except Exception as e:
            error = 'Could not unlink installation.'
            raise LinkedInstallationError(error) from e

    def _link_dir(self, source_dir, dest_dir, rules):
        """Copy or symlink files and directories from source_dir to
        dest_dir according to link `rules`."""
        def fnmatch_any(name, patterns):
            """Returns True if `name` string matches any pattern string in the
            list of `patterns`."""
            return any(fnmatch.fnmatch(entry, pattern) for pattern in patterns)

        os.makedirs(dest_dir)

        for entry in os.listdir(source_dir):
            src = os.path.normpath(os.path.join(source_dir, entry))
            dest = os.path.join(dest_dir, entry)
            if fnmatch_any(entry, rules.symlinks):
                os.symlink(src, dest)
            elif fnmatch_any(entry, rules.copy_dirs):
                shutil.copytree(src, dest, symlinks=True)
            elif fnmatch_any(entry, rules.copy_files):
                shutil.copy2(src, dest)

    def _unlink_dir(self, linked_dir):
        """Remove files, directories, and symlinks from `linked_dir`."""
        if not os.path.exists(linked_dir):
            return
        for entry in os.listdir(linked_dir):
            entry_path = os.path.normpath(os.path.join(linked_dir, entry))
            if os.path.islink(entry_path) or os.path.isfile(entry_path):
                os.remove(entry_path)
            elif os.path.isdir(entry_path):
                shutil.rmtree(entry_path)
        os.rmdir(linked_dir)


class LinkedTf2Installation(LinkedSteamInstallation, Tf2Installation):
    pass
