from __future__ import absolute_import, division, print_function

import os
import sys
import argparse
from functools import partial

from jsshd.sshd import Service
from jsshd.config import Config
from jsshd import logger

def load_config():
    class DictAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            d = getattr(namespace, self.dest)
            if d is None:
                d = {}
                setattr(namespace, self.dest, d)
            k, v = values.split('=')
            d[k] = eval(v)


    def _parse_command(cmd, args): return (cmd, args)

    # main parser
    parser = argparse.ArgumentParser(prog='jsshd', description="A ssh service for jumpserver")
    sparser = parser.add_subparsers()

    # config
    config = sparser.add_parser('config', help='Check and export default config')
    config.set_defaults(func=partial(_parse_command, 'config'))
    config.add_argument('-p', '--print', action='store_true', default=False, help='Print default config')
    config.add_argument('-o', '--output', type=str, help='Output default config file to specific path')
    config.add_argument('-s', '--set', type=str, action=DictAction, default={}, help='Set specific key in config')

    # start
    start = sparser.add_parser('start', help='Start jssh')
    start.set_defaults(func=partial(_parse_command, 'start'))
    start.add_argument('-c', '--config', type=str, default=None, help='Config module path')
    start.add_argument('-s', '--set', type=str, action=DictAction, default={}, help='Set specific key in config')

    args = parser.parse_args()
    if getattr(args, 'func', None) is None:
        parser.print_help()
        sys.exit(0)

    return args.func(args)


def cmd_config(args):
    pass


def cmd_start(args):
    # load config
    config = Config(args.config, args.set)

    # init logger
    logger.initialize(config.LOG_FILE_PATH)

    # run service
    service = Service(config)
    service()


def main():
    cmd, args = load_config()

    if cmd == 'config':
        cmd_config(args)

    elif cmd == 'start':
        cmd_start(args)

    else:
        raise Exception('Invalid command {0}'.format(cmd))


if __name__ == '__main__':
    main()