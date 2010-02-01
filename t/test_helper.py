
import sys, os.path, time, pickle, BaseHTTPServer
import xml.dom.minidom as minidom
from unittest import *

sys.path = [
    os.path.abspath(
        os.path.join( os.path.dirname(__file__), '..', 'lib')
        ) ] + sys.path


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

    def sendRequestData(self, request):
        info = {
            'method': request.command,
            'path': request.path,
            'headers': dict([(k, request.headers.getheader(k)) for k in request.headers.keys()]),
            'body': '' }
        length = request.headers.getheader('content-length')
        if length and int(length): info['body'] = request.rfile.read(int(length))
        request.info = info
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


import re
def transformHandler(list):
    return [(re.compile('/' + segment + '\Z'), method) for (segment, method) in list]

class APIServer(StubServer):
    @classmethod
    def test(self):
        instance = self({
            'get': (lambda (handler): handler.server.testStub.dispatch('get', handler)),
            'post': (lambda (handler): handler.server.testStub.dispatch('post', handler)),
            'put': (lambda (handler): handler.server.testStub.dispatch('put', handler)),
            'delete': (lambda (handler): handler.server.testStub.dispatch('delete', handler)),
        })
        instance.start()
        return instance

    map = {
        'get': transformHandler([
            ('servers/detail', 'serversDetail'),
            ('servers/(\d+)', 'serverDetail'),
            ('flavors/detail', 'flavorsDetail'),
            ('images/detail', 'imagesDetail'),
        ]),
        'post': transformHandler([
            ('servers', 'serverCreate'),
        ]),
        'put': {
        },
        'delete': transformHandler([
            ('servers/(\d+)', 'serverDelete'),
        ]),
    }

    def dispatch(self, httpMethod, handler):
        if self.map.has_key(httpMethod):
            for (exp, action) in self.map[httpMethod]:
                result = exp.match(handler.path)
                if result:
                    func = getattr(self, action)
                    arg = result.groups()
                    return self.xmlWrapper(handler, *func(*arg, **{'request': handler}))
        return self.notFound(handler)

    def xmlWrapper(self, handler, content, *extra):
        handler.send_response((extra and extra[0]) or 200)
        if content:
            handler.send_header('content-type', 'application/xml')
            handler.send_header('content-length', len(content))
            handler.end_headers()
            handler.wfile.write(content)
        else:
            handler.end_headers()
        return handler

    def notFound(self, handler):
        handler.send_response(404)
        handler.end_headers()

    # XML samples taken from Rackspace Cloud API documentation
    def serversDetail(self, request=None):
        return ("""<servers xmlns="http://docs.rackspacecloud.com/servers/api/v1.0">
  <server id="1234" name="sample-server"
        imageId="2" flavorId="1"
        status="BUILD" progress="60"
        hostId="e4d909c290d0fb1ca068ffaddf22cbd0"
        >
    <metadata>
      <meta key="Server Label">Web Head 1</meta>
      <meta key="Image Version">2.1</meta>
    </metadata>
    <addresses>
      <public>
        <ip addr="67.23.10.132"/>
        <ip addr="67.23.10.131"/>
      </public>
      <private>
        <ip addr="10.176.42.16"/>
      </private>
    </addresses>
  </server>
  <server id="5678" name="sample-server2"
        imageId="2" flavorId="1"
        status="ACTIVE"
        hostId="9e107d9d372bb6826bd81d3542a419d6">
    <metadata>
      <meta key="Server Label">DB 1</meta>
    </metadata>
    <addresses>
      <public>
        <ip addr="67.23.10.133"/>
      </public>
      <private>
        <ip addr="10.176.42.17"/>
      </private>
    </addresses>
  </server>
</servers>""",)

    def serverCreate(self, request=None):
        assert request.info['headers']['content-type'] == 'application/xml'
        assert request.info['body']
        node = minidom.parseString(request.info['body'])
        for files in node.documentElement.getElementsByTagName('personality'):
            node.documentElement.removeChild(files)
        addrs = node.createElement('addresses')
        priv = node.createElement('private')
        pub = node.createElement('public')
        priv.appendChild(node.createElement('ip'))
        pub.appendChild(node.createElement('ip'))
        priv.firstChild.setAttribute('addr', '192.168.1.1')
        pub.firstChild.setAttribute('addr', '10.10.1.1')
        addrs.appendChild(priv)
        addrs.appendChild(pub)
        node.documentElement.appendChild(addrs)
        node.documentElement.setAttribute('id', str(self.createId))
        node.documentElement.setAttribute('status', str(self.createStatus))
        node.documentElement.setAttribute('progress', str(self.createProgress))
        node.documentElement.setAttribute('hostId', str(self.createHostId))
        node.documentElement.setAttribute('adminPass', str(self.createAdminPass))
        return (node.documentElement.toxml(), 202)

    def serverDelete(self, id, request=None):
        assert(id)
        return (None, 202)

    createId = 2000
    createStatus = 'BUILD'
    createProgress = 0
    createHostId = 'f091' * 8
    createAdminPass = 'aardvarks freak me out the door'

    def serverDetail(self, handler, id, request=None):
        handler.send_response(200)
        msg = 'Got id: ' + id
        handler.send_header('content-length', len(msg))
        handler.end_headers()
        handler.wfile.write(msg)

    def flavorsDetail(self, request=None):
        return ("""
<flavors xmlns="http://docs.rackspacecloud.com/servers/api/v1.0">
  <flavor id="1" name="256 MB Server" ram="256" disk="10" />
  <flavor id="2" name="512 MB Server" ram="512" disk="20" />
</flavors>""",)

    def imagesDetail(self, request=None):
        return ("""
<images xmlns="http://docs.rackspacecloud.com/servers/api/v1.0">
   <image id="2"   name="CentOS 5.2"
          updated="2010-10-10T12:00:00Z"
          created="2010-08-10T12:00:00Z"
          status="ACTIVE"
   />
   <image id="743" name="My Server Backup"
          serverId="12"
          updated="2010-10-10T12:00:00Z"
          created="2010-08-10T12:00:00Z"
          status="SAVING" progress="80"
   />
</images>""",)

