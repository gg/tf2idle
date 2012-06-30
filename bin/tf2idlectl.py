# coding: utf-8

import argparse
import configparser
import getpass
import os

import tf2idle.app
from tf2idle.steam import SteamAccount


def get_accounts(usernames, password_required=False):
    accounts = []
    for username in usernames:
        password = None
        if password_required:
            password = getpass.getpass(
                prompt='Enter password for {}: '.format(username))
        accounts.append(SteamAccount(username, password))

    return accounts


def login(app, args):
    accounts = get_accounts(args.usernames, password_required=True)
    app.login(accounts)


def logout(app, args):
    accounts = get_accounts(args.usernames)
    app.logout(accounts)


def launch_tf2(app, args):
    accounts = get_accounts(args.usernames)
    app.launch_tf2(accounts, launch_options=args.launch_options,
                   autoexec_cfg=args.autoexec)


def close_tf2(app, args):
    accounts = get_accounts(args.usernames)
    app.close_tf2(accounts)


def build_arg_parser():
    parser = argparse.ArgumentParser(description='tf2idle')
    parser.add_argument('--working-dir', dest='working_dir',
                        help=('Directory in which idler Steam installations '
                              'are contained.'))
    parser.add_argument('--steam-base-dir', dest='steam_base_dir',
                        help=('Path to the base Steam installation. '
                              'To save disk space, each idler Steam '
                              'installation symlinks to one set of .gcf '
                              'files.'))
    parser.add_argument('--sandboxie-install-dir',
                        dest='sandboxie_install_dir',
                        help='Path to Sandboxie installation.')

    subparsers = parser.add_subparsers(title='commands')

    accounts = argparse.ArgumentParser('Steam Account', add_help=False)
    accounts_group = accounts.add_mutually_exclusive_group(required=True)
    accounts_group.add_argument('--usernames', metavar='USERNAME', nargs='+',
                                help='Steam account usernames')

    login_parser = subparsers.add_parser('login', parents=[accounts],
                                         help='Login to Steam')
    login_parser.set_defaults(func=login)

    logout_parser = subparsers.add_parser('logout', parents=[accounts],
                                          help='Logout of Steam')
    logout_parser.set_defaults(func=logout)

    launchtf2_parser = subparsers.add_parser('launchtf2', help='Launch TF2',
                                             parents=[accounts])
    launchtf2_parser.add_argument('--launch-options', dest='launch_options',
                                  default=None,
                                  help=('TF2 launch options.'))
    launchtf2_parser.add_argument('--autoexec',
                                  type=argparse.FileType('r'),
                                  help=('Path to the .cfg file that will be '
                                        'executed upon launching TF2.'))
    launchtf2_parser.set_defaults(func=launch_tf2)

    closetf2_parser = subparsers.add_parser('closetf2', help='Close TF2',
                                            parents=[accounts])
    closetf2_parser.set_defaults(func=close_tf2)

    return parser



def main(args):
    app = tf2idle.app.Tf2IdleApp(steam_base_dir=args.steam_base_dir,
                                 working_dir=args.working_dir,
                                 sandboxie_install_dir=args.sandboxie_install_dir)
    args.func(app, args)


if __name__ == '__main__':
    main(build_arg_parser().parse_args())
