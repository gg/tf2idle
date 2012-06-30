# coding: utf-8
from __future__ import unicode_literals

import contextlib
import os
import tempfile
import unittest

from tf2idle.steam import (SteamInstallation, LinkedSteamInstallation,
                           LinkedInstallationError)


@contextlib.contextmanager
def build_installation(installation_type, installed=True):
    def create_dirtree(dirpath, subdirs, filenames):
        os.makedirs(dirpath)
        for subdir in subdirs:
            os.makedirs(os.path.join(dirpath, subdir))

        for f in filenames:
            filepath = os.path.join(dirpath, f)
            with open(filepath, 'wb'):
                pass

    with tempfile.TemporaryDirectory() as d:
        steam_dir = os.path.join(d, 'FakeSteamInstallation')
        installation = installation_type(steam_dir)

        if installed:
            steam_subdirs = ('appcache', 'bin', 'config', 'friends',
                             'Graphics', 'old', 'Public', 'resource',
                             'servers', 'skins', 'steamapps', 'userdata')
            steam_files = ('ClientRegistry.blob', 'AppUpdateStats.blob',
                           'GameOverlayUI.exe', 'Steam.dll', 'steam.exe',
                           'SteamUI_1771.mst')
            create_dirtree(steam_dir, steam_subdirs, steam_files)

        yield installation


def create_steam_installation(installed=True):
    return build_installation(SteamInstallation, installed)


def create_linked_steam_installation(already_linked=False):
    return build_installation(LinkedSteamInstallation, already_linked)


class SteamInstallationTests(unittest.TestCase):
    def test_installation_installed(self):
        with create_steam_installation(installed=True) as ins:
            self.assertTrue(ins.installed())
        with create_steam_installation(installed=False) as ins:
            self.assertFalse(ins.installed())


class LinkedSteamInstallationTests(unittest.TestCase):
    def test_link_to_not_installed_installation_when_already_linked(self):
        with create_linked_steam_installation(already_linked=False) as l:
            with create_steam_installation(installed=False) as other:
                with self.assertRaises(LinkedInstallationError):
                    l.link(other)

    def test_link_to_not_installed_installation_when_not_already_linked(self):
        with create_linked_steam_installation(already_linked=True) as l:
            with create_steam_installation(installed=False) as other:
                l.link(other)

    def test_link_when_not_already_linked(self):
        with create_steam_installation(installed=True) as other:
            with create_linked_steam_installation(already_linked=False) as l:
                l.link(other)
                self.assertTrue(l.installed())

    def test_link_when_already_linked_with_remove_existing(self):
        with create_steam_installation(installed=True) as other:
            with create_linked_steam_installation(already_linked=True) as l:
                l.link(other)
                self.assertTrue(l.installed())

        with create_steam_installation(installed=True) as other:
            with create_linked_steam_installation(already_linked=True) as l:
                l.link(other, remove_existing=True)
                self.assertTrue(l.installed())

    def test_link_when_already_linked_without_remove_existing(self):
        with create_steam_installation(installed=True) as other:
            with create_linked_steam_installation(already_linked=True) as l:
                l.link(other, remove_existing=False)

    def test_unlink_when_not_already_linked(self):
        with create_linked_steam_installation(already_linked=False) as l:
            l.unlink()
            self.assertFalse(l.installed())

    def test_unlink_when_already_linked(self):
        with create_linked_steam_installation(already_linked=True) as l:
            l.unlink()
            self.assertFalse(l.installed())


if __name__ == '__main__':
    unittest.main()
