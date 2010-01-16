
import sys, os, time, pickle
import os.path
from unittest import *
import BaseHTTPServer

sys.path = [
    os.path.abspath(
        os.path.join( os.path.dirname(__file__), '..', 'lib')
        ) ] + sys.path


#class StubServer(threading.Thread):
class StubServer(object):
    class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
        def generalHandler(self, type):
            self.server.testStub.sendRequestData(self)
            return self.server.handlers.has_key(type) and self.server.handlers[type](self)

        def do_GET(self):
            return self.generalHandler('get')

        def do_POST(self):
            return self.generalHandler('post')

        def do_PUT(self):
            return self.generalHandler('put')

        def do_DELETE(self):
            return self.generalHandler('delete')

    def __init__(self, handlers):
        self.server = BaseHTTPServer.HTTPServer(('127.0.0.1', 0), StubServer.Handler)
        self.server.handlers = handlers or {}
        self.server.testStub = self
        self.port = self.server.server_port
        #threading.Thread.__init__(self)

    def sendRequestData(self, request):
        info = {
            'method': request.command,
            'path': request.path,
            'headers': dict([(k, request.headers.getheader(k)) for k in request.headers.keys()]),
            'body': '' }
        length = request.headers.getheader('content-length')
        if length and int(length): info['body'] = request.rfile.read(int(length))
        pickle.Pickler(self.pipeOut).dump(info)
        self.pipeOut.flush()

    def getRequestData(self):
        time.sleep(0.1)
        return pickle.Unpickler(self.pipeIn).load()

    def start(self):
        pipein, pipeout = os.pipe()
        self.pipeIn = os.fdopen(pipein, 'r')
        self.pipeOut = os.fdopen(pipeout, 'w')
        self.pid = os.fork()
        if self.pid == 0:
            self.pipeIn.close()
            self.run()
            os._exit(0)
        self.pipeOut.close()
        time.sleep(0.1)
        return self.pid

    def run(self):
        self.server.handle_request()

    @classmethod
    def test(self, handlers):
        instance = self(handlers)
        instance.start()
        return instance

    def finish(self, timeout=5):
        os.waitpid(self.pid, os.WNOHANG)
        # join once extra in case of blocking IO
        # self.join(timeout)

class Authenticator(StubServer):
    authToken = 'StandardAuthenticatorToken'
    def makeURL(self, path):
        return 'http://localhost:' + str(self.server.server_port) + path

    @classmethod
    def test(self):
        instance = self({'get': lambda (handler): handler.server.testStub.do_GET(handler) })
        instance.start()
        return instance

    def do_GET(self, handler):
        handler.send_response(204)
        handler.send_header('X-Auth-Token', self.authToken)
        handler.send_header('X-Server-Management-URL', self.makeURL('/server'))
        handler.send_header('X-Storage-URL', self.makeURL('/storage'))
        handler.send_header('X-CDN-Management-URL', self.makeURL('/cdn'))
        handler.end_headers()
