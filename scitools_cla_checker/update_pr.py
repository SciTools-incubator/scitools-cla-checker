import json
import os
from pprint import pprint
from pathlib import Path
import sys

import requests
from tornado import gen
import tornado.escape
import tornado.httpclient
from tornado.ioloop import IOLoop




def api_token():
    token_file = Path(__file__).parent / 'token.txt'
    if not token_file.exists():
        raise IOError('Please create a token at github.com, and save it in {}'.format(token_file))

    token = token_file.read_text().strip()
    return token


CONTRIBUTORS_DOC = 'https://raw.githubusercontent.com/SciTools/scitools.org.uk/gh-pages/contributors.json'


token = api_token()


@gen.coroutine
def get_pr_sha(repo, number):
    http_client = tornado.httpclient.AsyncHTTPClient()
    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/{}/pulls/{}'.format(repo, number)
    response = yield http_client.fetch(URL, method='GET',
                                       headers=headers)
    if response.error:
        raise RuntimeError(response.body)
    content = json.loads(response.body.decode())
    return content['head']['sha']


@gen.coroutine
def update_pr_no_cla(repo, number, logins_without_cla=None):
    http_client = tornado.httpclient.AsyncHTTPClient()

    sha = yield get_pr_sha(repo, number)

    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/{}/statuses/{}'.format(repo, sha)

    if logins_without_cla:
        context = ' (authors: {})'.format(', '.join(logins_without_cla))
    else:
        context = ''
    content = {
      "state": "failure",
      "target_url": "http://scitools.org.uk/governance.html#contributors",
      "description": "CLA doesn't exist for all commits{}".format(context),
      "context": "SciTools-CLA-checker"
    }

    response = yield http_client.fetch(URL, body=json.dumps(content).encode(),
                                       method='POST',
                                       headers=headers)
    if response.error:
        raise RuntimeError(response.body)
    content = json.loads(response.body.decode())

    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/{}/issues/{}/labels'.format(repo, number)
    content = ['Blocked: CLA needed']
    response = yield http_client.fetch(URL, body=json.dumps(content).encode(), method='POST',
                                       headers=headers)
    if response.error:
        raise RuntimeError(response.body)
    content = json.loads(response.body.decode())


@gen.coroutine
def update_pr_cla_exists(repo, number):
    http_client = tornado.httpclient.AsyncHTTPClient()

    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = ('https://api.github.com/repos/{}/issues/{}/labels/{}'
           ''.format(repo, number, tornado.escape.url_escape('Blocked: CLA needed', plus=False)))
    try:
        response = yield http_client.fetch(URL, method='DELETE',
                                           headers=headers)
    except tornado.httpclient.HTTPError:
        pass

    sha = yield get_pr_sha(repo, number)

    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/{}/statuses/{}'.format(repo, sha)
    content = {
      "state": "success",
      "description": "SciTools CLA exists",
      "context": "SciTools-CLA-checker"
    }

    response = yield http_client.fetch(URL, body=json.dumps(content).encode(), method='POST',
                                       headers=headers)
    if response.error:
        raise RuntimeError(response.body)


@gen.coroutine
def check_pr(repo, number):
    http_client = tornado.httpclient.AsyncHTTPClient()

    headers = {'Authorization': 'token {}'.format(token),
               'Accept': 'application/vnd.github.v3+json'}
    URL = ('https://api.github.com/repos/{}/pulls/{}/commits'
           ''.format(repo, number))
    response = yield http_client.fetch(URL, method='GET',
                                       headers=headers)
    content = json.loads(response.body.decode())
    authors = {commit['author']['login'] for commit in content}

    cla_signatories = yield get_contributors()

    missing_cla = authors - set(cla_signatories)
    if missing_cla:
        yield update_pr_no_cla(repo, number, missing_cla)
    else:
        yield update_pr_cla_exists(repo, number)

    return


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


CONTRIBUTORS_DOC = 'https://raw.githubusercontent.com/SciTools/scitools.org.uk/gh-pages/contributors.json'


@gen.coroutine
def get_contributors():
    http_client = tornado.httpclient.AsyncHTTPClient()
    response = yield http_client.fetch(CONTRIBUTORS_DOC)
    if response.error:
        raise ValueError('Unable to fetch contributors.json')
    content = json.loads(response.body.decode())
    signatures = sorted([person['profile_name']
                         for person in content['contributors']])
    return signatures


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Print/check the contributors list')
    parser.add_argument('repo',
                        help='The name of the repo (e.g. SciTools/iris)')
    parser.add_argument('pr_number',
                        help='The PR number to check')
    args = parser.parse_args()
    configure_default_client()
    # IOLoop.current().run_sync(lambda: update_pr_no_cla('pelson/scitools-cla-checker', 2))
    # IOLoop.current().run_sync(lambda: update_pr_cla_exists('pelson/scitools-cla-checker', 2))
    IOLoop.current().run_sync(lambda: check_pr(args.repo, int(args.pr_number)))


if __name__ == '__main__':
    main()
