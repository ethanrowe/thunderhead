
import httplib
from urlparse import urlparse
from . import exceptions

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
        klass = httplib.HTTPSConnection if request.scheme == 'https' else httplib.HTTPConnection
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
            body = body.toprettyxml()
            mergedHeaders['Content-Type'] = 'application/xml'
        return self.connection.request(method, self.pathPrefix + url, body, mergedHeaders)
        
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
        klass = httplib.HTTPConnection if request.scheme == 'http' else httplib.HTTPSConnection
        args = [request.hostname]
        if request.port: args.append(request.port)
        return klass(*args)

