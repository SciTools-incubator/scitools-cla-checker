import datetime
import logging
import os

import tornado.escape
import tornado.httpserver
import tornado.gen
import tornado.ioloop
import tornado.web

from . import update_pr
from __main__ import get_contributors


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_status(404)
        self.write_error(404)


class WebhookHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        if event == 'ping':
            self.write('pong')
        elif event == 'pull_request':
            body = tornado.escape.json_decode(self.request.body)
            logging.info(body)
            return

            repo_name = body['repository']['name']
            repo_url = body['repository']['clone_url']
            owner = body['repository']['owner']['login']
            pr_id = int(body['pull_request']['number'])
            is_open = body['pull_request']['state'] == 'open'

            if is_open and 'checker' in repo_name:
                contribs = get_contributors()

        else:
            self.write('Unhandled event "{}".'.format(event))
            self.set_status(404)


def main():
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/webhook", WebhookHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    PORT = os.environ.get('PORT', 8080)
    http_server.listen(PORT)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
