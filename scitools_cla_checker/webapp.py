import datetime
import os

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.web


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_status(404)
        self.write_error(404)
        return
        self.write("Hello damp world ({})".format(datetime.datetime.now().isoformat()))


class LintingHookHandler(tornado.web.RequestHandler):
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        if event == 'ping':
            self.write('pong')
        elif event == 'pull_request':
            body = tornado.escape.json_decode(self.request.body)
            repo_name = body['repository']['name']
            repo_url = body['repository']['clone_url']
            owner = body['repository']['owner']['login']
            pr_id = int(body['pull_request']['number'])
            is_open = body['pull_request']['state'] == 'open'

            # Only do anything if we are working with conda-forge, and an open PR.
            if is_open and owner == 'conda-forge':
                lint_info = linting.compute_lint_message(owner, repo_name, pr_id,
                                                         repo_name == 'staged-recipes')
                if lint_info:
                    msg = linting.comment_on_pr(owner, repo_name, pr_id, lint_info['message'])
                    linting.set_pr_status(owner, repo_name, lint_info, target_url=msg.html_url)
        else:
            self.write('Unhandled event "{}".'.format(event))
            self.set_status(404)


def main():
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    PORT = os.environ.get('PORT', 8080)
    http_server.listen(PORT)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
