
import httplib
from urlparse import urlparse
# Change to relative import syntax when we can safely deprecate Python 2.4 support
import thunderhead.rackspace.exceptions
import thunderhead.rackspace.api
import xml.dom.minidom as minidom

class BoundConnection(object):

    def __init__(self, url, headers):
        request = urlparse(url)
        self.scheme = request.scheme
        self.host = request.hostname
        self.port = request.port
        self.pathPrefix = request.path
        self.headers = headers
        self.connection = self.getConnection(request)

    @classmethod
    def getConnection(self, request):
        klass = ((request.scheme == 'https' and httplib.HTTPSConnection) or httplib.HTTPConnection)
        args = [request.hostname]
        if request.port: args.append(request.port)
        return klass(*args)

    def mergeHeaders(self, headers={}):
        return dict(dict(self.standardHeaders, **self.headers), **headers)

    standardHeaders = {
        'Accept': 'application/xml',
        }

    def request(self, method, url, body=None, headers={}):
        mergedHeaders = self.mergeHeaders(headers)
        if body:
            body = body.toxml()
            mergedHeaders['Content-Type'] = 'application/xml'
        # stateful connections are tricky to manage, so for the time being,
        # do the rather blunt close/reopen strategy here; improve later.
        self.connection.close()
        self.connection.connect()
        self.connection.request(method, self.pathPrefix + url, body, mergedHeaders)
        return self.handleResponse()

    def handleResponse(self):
        resp = self.connection.getresponse()
        code = resp.status
        length = int(resp.getheader('content-length', 0))
        body = None
        if length and resp.getheader('content-type', '') == 'application/xml':
            body = minidom.parseString(resp.read(length)).documentElement
        if code >= 400: self.handleFault(code, body)
        return (body, code)

    def handleFault(self, code, xml):
        type = ((xml and xml.nodeName) or '')
        args = []
        if type:
            notes = dict([
                (n.nodeName, n.firstChild.data) for n in xml.childNodes if n.nodeName in ('message', 'details')
            ])
            args.append( (notes.has_key('message') and notes['message']) or None )
            args.append(code)
            if notes.has_key('details'): args.append(notes['details'])
        else:
            args.extend([None, code])
        exceptions.throw(type, *args)


        
        
class Authorization(object):
    baseURL = 'https://auth.api.rackspacecloud.com/v1.0'

    def __init__(self, name, key):
        response = self.getAuthorization(name, key)
        self.manageServerURL = response.getheader('X-Server-Management-URL')
        self.storageURL = response.getheader('X-Storage-URL')
        self.cdnURL = response.getheader('X-CDN-Management-URL')
        self.authToken = response.getheader('X-Auth-Token')
        self.serverManager = self.getBoundConnection(self.manageServerURL)

    def getBoundConnection(self, url):
        return BoundConnection(url, {'X-Auth-Token': self.authToken})

    @classmethod
    def getAuthorization(self, name, key):
        response = self.performAuthRequest(name, key)
        if response.status == 401: raise exceptions.BadCredentialsException()
        return response

    @classmethod
    def performAuthRequest(self, name, key):
        request = urlparse(self.baseURL)
        connection = self.getConnection(request)
        connection.request('GET', request.path, None, {'X-Auth-User': name, 'X-Auth-Key': key})
        return connection.getresponse()

    @classmethod
    def getConnection(self, request):
        klass = ((request.scheme == 'http' and httplib.HTTPConnection) or httplib.HTTPSConnection)
        args = [request.hostname]
        if request.port: args.append(request.port)
        return klass(*args)

