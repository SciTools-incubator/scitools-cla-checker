import json
import os

from tornado import gen
import tornado.escape
import tornado.httpclient
from tornado.ioloop import IOLoop


TOKEN = os.environ['TOKEN']


# Without setting the user agent, github 403s us :(
user_agent = 'scitools-cla-checker'


LABEL_TEXT = 'Blocked: CLA needed'


@gen.coroutine
def get_pr_sha(repo, number):
    """Given a PR, get the SHA of the HEAD of the PR's branch"""
    http_client = tornado.httpclient.AsyncHTTPClient()
    headers = {'Authorization': 'token {}'.format(TOKEN),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/{}/pulls/{}'.format(repo, number)
    response = yield http_client.fetch(URL, method='GET',
                                       user_agent=user_agent,
                                       headers=headers)
    content = json.loads(response.body.decode())
    return content['head']['sha']


@gen.coroutine
def update_pr_no_cla(repo, number, logins_without_cla=None):
    """
    Update the given PR to show that a CLA does not exist for the given logins

    This involves:
      * Adding a label of "Blocked: CLA needed" (even if it doesn't yet exist)
      * Adding a GitHub status showing that the check was a failure, and why

    """
    http_client = tornado.httpclient.AsyncHTTPClient()

    # Get the SHA of the PR's HEAD, this is where we attach the status.
    sha = yield get_pr_sha(repo, number)

    headers = {'Authorization': 'token {}'.format(TOKEN),
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
                                       user_agent=user_agent,
                                       method='POST',
                                       headers=headers)
    content = json.loads(response.body.decode())

    headers = {'Authorization': 'token {}'.format(TOKEN),
               'Accept': 'application/vnd.github.v3+json'}
    URL = ('https://api.github.com/repos/{}/issues/{}/labels'
           ''.format(repo, number))
    content = [LABEL_TEXT]
    yield http_client.fetch(
            URL, body=json.dumps(content).encode(), method='POST',
            user_agent=user_agent, headers=headers)


@gen.coroutine
def update_pr_cla_exists(repo, number):
    """
    Update the given PR to show that a CLA exists

    This involves:
      * Removing a label of "Blocked: CLA needed" (if it exists)
      * Adding a GitHub status showing that the check was a success

    """
    http_client = tornado.httpclient.AsyncHTTPClient()

    headers = {'Authorization': 'token {}'.format(TOKEN),
               'Accept': 'application/vnd.github.v3+json'}
    escaped_label_name = tornado.escape.url_escape(LABEL_TEXT, plus=False)
    URL = ('https://api.github.com/repos/{}/issues/{}/labels/{}'
           ''.format(repo, number, escaped_label_name))
    try:
        yield http_client.fetch(URL, method='DELETE',
                                user_agent=user_agent, headers=headers)
    except tornado.httpclient.HTTPError:
        # We couldn't delete the label, as it doesn't exist.
        # That's fine though.
        pass

    # Get the SHA of the PR's HEAD, this is where we attach the status.
    sha = yield get_pr_sha(repo, number)

    headers = {'Authorization': 'token {}'.format(TOKEN),
               'Accept': 'application/vnd.github.v3+json'}
    URL = 'https://api.github.com/repos/{}/statuses/{}'.format(repo, sha)
    content = {
      "state": "success",
      "description": "SciTools CLA exists",
      "context": "SciTools-CLA-checker"
    }

    yield http_client.fetch(
            URL, body=json.dumps(content).encode(),
            method='POST', user_agent=user_agent, headers=headers)


@gen.coroutine
def check_pr(repo, number):
    """
    Check that the given PR has a CLA signatory for each commit.

    If it does, ``update_pr_cla_exists`` is called, otherwise
    ``update_pr_no_cla`` is called.

    """
    http_client = tornado.httpclient.AsyncHTTPClient()

    headers = {'Authorization': 'token {}'.format(TOKEN),
               'Accept': 'application/vnd.github.v3+json'}
    URL = ('https://api.github.com/repos/{}/pulls/{}/commits'
           ''.format(repo, number))
    response = yield http_client.fetch(URL, method='GET',
                                       user_agent=user_agent,
                                       headers=headers)
    content = json.loads(response.body.decode())
    authors = {commit['author']['login'] for commit in content}

    cla_signatories = yield get_contributors()

    missing_cla = authors - set(cla_signatories)
    if missing_cla:
        yield update_pr_no_cla(repo, number, missing_cla)
    else:
        yield update_pr_cla_exists(repo, number)


@gen.coroutine
def get_contributors():
    """
    Return a list of GitHub logins for those that are on the contributors.json
    document.

    """
    contrib_json = ('https://raw.githubusercontent.com/SciTools/'
                    'scitools.org.uk/gh-pages/contributors.json')
    http_client = tornado.httpclient.AsyncHTTPClient()
    response = yield http_client.fetch(contrib_json)
    content = json.loads(response.body.decode())
    signatures = sorted([person['profile_name']
                         for person in content['contributors']])
    return signatures


def configure_default_client():
    """
    Configure the default AsyncHTTPClient to use pycurl, and to handle the
    http_proxy environment variable, which is useful for CLI users behind a
    coorporate proxy.

    """
    defaults = {}
    http_proxy = os.environ.get('http_proxy')
    if http_proxy:
        if http_proxy[:7] == "http://":
            http_proxy = http_proxy[7:]
        defaults['proxy_host'], defaults['proxy_port'] = http_proxy.split(":")
        defaults['proxy_port'] = int(defaults['proxy_port'])

    # Note: I had issues akin to
    # https://stackoverflow.com/questions/21096436/ssl-backend-error-when-using-openssl
    tornado.httpclient.AsyncHTTPClient.configure(
            "tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=defaults)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Update the given PR with its CLA status')
    parser.add_argument('repo',
                        help='The name of the repo (e.g. SciTools/iris)')
    parser.add_argument('pr_number',
                        help='The PR number to check')
    args = parser.parse_args()
    configure_default_client()
    IOLoop.current().run_sync(lambda: check_pr(args.repo, int(args.pr_number)))


if __name__ == '__main__':
    main()
