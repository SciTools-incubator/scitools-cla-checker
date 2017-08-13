import hashlib
import hmac
import logging
import os

import tornado.escape
import tornado.httpserver
import tornado.gen
import tornado.ioloop
import tornado.log
import tornado.web

from . import update_pr


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_status(404)
        self.write_error(404)


class WebhookHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        hmac_digest = headers.get('X-Hub-Signature', None)
        webhook_secret = os.environ['WEBHOOK_SECRET'].encode()
        # Compute the payload's hmac digest.
        expected_hmac = hmac.new(
                webhook_secret, self.request.body, hashlib.sha1).hexdigest()
        expected_digest = 'sha1={}'.format(expected_hmac.hexdigest())

        if hmac_digest != expected_digest:
            logging.warning('HMAC FAIL: expected: {}; got: {};'
                            ''.format(expected_digest, hmac_digest))
            self.set_status(403)

        if event == 'ping':
            self.write('pong')
        elif event == 'pull_request':
            body = tornado.escape.json_decode(self.request.body)

            repo_name = body['repository']['name']
            owner = body['repository']['owner']['login']
            pr_id = int(body['pull_request']['number'])
            is_open = body['pull_request']['state'] == 'open'

            # Do some sanity chceking
            if is_open and owner.lower() in ['scitools', 'scitools-incubator']:
                yield update_pr.check_pr('{}/{}'.format(owner, repo_name),
                                         pr_id)
        else:
            self.write('Unhandled event "{}".'.format(event))
            self.set_status(404)


def main():
    tornado.log.enable_pretty_logging()
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
