#!/usr/bin/env python

import test_helper
import thunderhead.rackspace
import xml.dom.minidom as minidom

def handleResponse(server):
    server.send_response(204)

def handleXMLResponse(server, xml, code=200):
    server.send_response(code)
    server.send_header('content-type', 'application/xml')
    server.send_header('content-length', str(len(xml)))
    server.end_headers()
    server.wfile.write(xml)

class TestRackspaceBoundConnection(test_helper.TestCase):
    def simpleServer(self):
        self.server = test_helper.StubServer.test({'get': handleResponse, 'post': handleResponse})
        self.commonConfig()

    def commonConfig(self):
        self.pathPrefix = '/test-prefix'
        self.url = 'http://localhost:' + str(self.server.port) + self.pathPrefix

    def testEmptyRequest(self):
        self.simpleServer()
        authHeader = 'SOME-AUTHORIZATION-TOKEN'
        specificPath = '/some-path/for-this'
        connection = thunderhead.rackspace.BoundConnection(
            self.url,
            {'X-Auth-Token': authHeader, 'X-Merge-Header': 'bad'} )
        connection.request('GET', specificPath, None, {'X-Merge-Header': 'good'})
        requestReceived = self.server.getRequestData()
        self.server.finish(1)
        # verify path includes prefix and specific
        self.assertEqual(requestReceived['path'], self.pathPrefix + specificPath)
        # verify the request method is consistent with what we issued
        self.assertEqual(requestReceived['method'], 'GET')
        headers = requestReceived['headers']
        # Accept header should always be present
        self.assertEqual(headers['accept'], 'application/xml')
        # X-Auth-Token provided in constructor should be present
        self.assertEqual(headers['x-auth-token'], authHeader)
        # X-Merge-Header should have value from request rather than constructor
        self.assertEqual(headers['x-merge-header'], 'good')
        # in the simple case, the body should be empty
        self.assertEqual(requestReceived['body'], '')
        # and no Content-Type header is present
        self.assertFalse(headers.has_key('content-type'))

    def testPopulatedRequest(self):
        self.simpleServer()
        node = minidom.parseString('<someNode>Some data</someNode>').documentElement
        connection = thunderhead.rackspace.BoundConnection(self.url, {})
        connection.request('POST', '/somenode/submission', node)
        requestReceived = self.server.getRequestData()
        self.server.finish(1)
        # verify that XML submitted upstream results in a Content-Type header and
        # that the XML is intact server-side
        self.assertEqual(requestReceived['headers']['content-type'], 'application/xml')
        self.assertEqual(requestReceived['body'], node.toxml())

    def testPopulatedXMLResult(self):
        xml = '<someNode>some content</someNode>'
        self.server = test_helper.StubServer.test({
            'get': lambda (server): handleXMLResponse(server, xml)
        })
        self.commonConfig()
        connection = thunderhead.rackspace.BoundConnection(self.url, {})
        (response, code) = connection.request('GET', '/any-path-will-do')
        requestReceived = self.server.getRequestData()
        self.server.finish(1)
        # verify that the xml in the response is automatically converted to a DOM doc element
        # (or something like it)
        self.assertEqual(code, 200)
        self.assertEqual(response.nodeName, 'someNode')

    def testPopulatedXMLResultFault(self):
        xml = '<cloudServersFault><message>Everything is awful</message><details>We all perish</details></cloudServersFault>'
        self.server = test_helper.StubServer.test({
                'get': lambda (server): handleXMLResponse(server, xml, 400)
        })
        self.commonConfig()
        connection = thunderhead.rackspace.BoundConnection(self.url, {})
        message, code, details = (None, None, None)
        try:
            (foo, bar) = connection.request('GET', '/any-path-will-do')
        except thunderhead.rackspace.exceptions.CloudServersFaultException as expected:
            message, code, details = expected.args
        self.assertEqual((message, code, details), ('Everything is awful', 400, 'We all perish'))
            

if __name__ == '__main__':
    test_helper.main()

