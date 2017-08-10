import json
import os
from pprint import pprint
import sys

import requests
from tornado import gen
import tornado.httpclient
from tornado.ioloop import IOLoop


CONTRIBUTORS_DOC = 'https://raw.githubusercontent.com/SciTools/scitools.org.uk/gh-pages/contributors.json'


@gen.coroutine
def get_contributors():
    http_client = tornado.httpclient.AsyncHTTPClient()
    response = yield http_client.fetch(CONTRIBUTORS_DOC)
    if response.error:                                                   
        raise ValueError('Unable to fetch contributors.json')
    content = json.loads(response.body)
    return content


#def get_contributors_doc():
#    resp = requests.get('https://raw.githubusercontent.com/SciTools/scitools.org.uk/gh-pages/contributors.json')
#    content = resp.json()
#    print(content)


def configure_default_client():
    defaults = {}
    http_proxy = os.environ.get('http_proxy')
    if http_proxy:
        if http_proxy[:7] == "http://":
            http_proxy = http_proxy[7:]
        defaults['proxy_host'], defaults['proxy_port'] = http_proxy.split(":")
        defaults['proxy_port'] = int(defaults['proxy_port'])

    # Note: I had issues akin to https://stackoverflow.com/questions/21096436/ssl-backend-error-when-using-openssl
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=defaults)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Print the contributors list')
    parser.add_argument('check', default=None, nargs='?',
                        help='If defined, check that the given name is in the contributors list')
    args = parser.parse_args()
    configure_default_client()
    contributors = IOLoop.current().run_sync(get_contributors)
    signatures = sorted([person['profile_name'] for person in contributors['contributors']])
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
