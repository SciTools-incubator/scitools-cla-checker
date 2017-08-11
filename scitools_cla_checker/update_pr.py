import json
import os
from pprint import pprint
from pathlib import Path
import sys

import requests
from tornado import gen
import tornado.httpclient
from tornado.ioloop import IOLoop


def api_token():
    token_file = Path('token.txt')
    if not token_file.exists():
        raise IOError('Please create a token at github.com, and save it in {}'.format(token_file))

    token = token_file.read_text().strip()
    return token


CONTRIBUTORS_DOC = 'https://raw.githubusercontent.com/SciTools/scitools.org.uk/gh-pages/contributors.json'


token = api_token()


@gen.coroutine
def update_pr_no_cla():
    http_client = tornado.httpclient.AsyncHTTPClient()
    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/pelson/scitools-cla-checker/issues/1/labels'
    content = ['testing']
    response = yield http_client.fetch(URL, body=json.dumps(content).encode(), method='POST',
                                       headers=headers)
    if response.error:
        raise RuntimeError(response.body)
    content = json.loads(response.body.decode())
    print(content)
    return content


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
    parser = argparse.ArgumentParser(description='Print/check the contributors list')
    parser.add_argument('check', default=None, nargs='?',
                        help='If defined, check that the given name is in the contributors list')
    args = parser.parse_args()
    configure_default_client()
    contributors = IOLoop.current().run_sync(update_pr_no_cla)



if __name__ == '__main__':
    main()
