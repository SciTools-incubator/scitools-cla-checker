import json
import os
from pprint import pprint
import sys

import requests
from tornado import gen
import tornado.httpclient
from tornado.ioloop import IOLoop

from . import update_pr


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Print/check the contributors list')
    parser.add_argument('check', default=None, nargs='?',
                        help='If defined, check that the given name is in the contributors list')
    args = parser.parse_args()
    update_pr.configure_default_client()
    signatures = IOLoop.current().run_sync(update_pr.get_contributors)
    if args.check is None:
        print('\n'.join(signatures))
    else:
        if args.check not in signatures:
            print('{} is not in the list of contributors ({})'.format(args.check, ', '.join(signatures)))
            sys.exit(1)
        else:
            print('{} is in the list of contributors'.format(args.check))
            sys.exit(0)


if __name__ == '__main__':
    main()
