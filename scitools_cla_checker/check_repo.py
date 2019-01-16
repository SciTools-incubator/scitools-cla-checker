import json
import os

from tornado import gen
import tornado.escape
import tornado.httpclient
from tornado.ioloop import IOLoop

from .update_pr import (
        user_agent, TOKEN, get_contributors, configure_default_client)


@gen.coroutine
def check_repo(repo):
    """
    Check that all contributors on a repositroy have a valid CLA signed.

    """
    http_client = tornado.httpclient.AsyncHTTPClient()

    headers = {'Authorization': 'token {}'.format(TOKEN),
               'Accept': 'application/vnd.github.v3+json'}
    URL = ('https://api.github.com/repos/{}/contributors'
           ''.format(repo))
    response = yield http_client.fetch(URL, method='GET',
                                       user_agent=user_agent,
                                       headers=headers)
    contributors = json.loads(response.body.decode())

    authors = set()
    for author in contributors:
        authors.add(author['login'])

    # Now get the list of those that have signed the CLA.
    cla_signatories = yield get_contributors()

    missing_cla = sorted(authors - set(cla_signatories), key=str.lower)
    if missing_cla:
        print('Missing signatories:\n  ', end="")
        print('\n  '.join(missing_cla))


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description=(
            'Check that the given repo has an appropriate CLA signed '
            'for each contributor.'))
    parser.add_argument('repo',
                        help='The name of the repo (e.g. SciTools/iris)')
    args = parser.parse_args()
    configure_default_client()
    IOLoop.current().run_sync(lambda: check_repo(args.repo))


if __name__ == '__main__':
    main()
