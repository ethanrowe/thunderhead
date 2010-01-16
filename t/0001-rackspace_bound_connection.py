#!/usr/bin/env python

import test_helper
import thunderhead.rackspace
import xml.dom.minidom as minidom

class TestRackspaceBoundConnection(test_helper.TestCase):
    def setUp(self):
        self.server = test_helper.StubServer.test({'get': lambda (server): server.send_response(201)})
        self.pathPrefix = '/test-prefix'
        self.url = 'http://localhost:' + str(self.server.port) + self.pathPrefix

    def testEmptyRequest(self):
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
        node = minidom.parseString('<someNode>Some data</someNode>').documentElement
        connection = thunderhead.rackspace.BoundConnection(self.url, {})
        connection.request('POST', '/somenode/submission', node)
        requestReceived = self.server.getRequestData()
        self.server.finish(1)
        # verify that XML submitted upstream results in a Content-Type header and
        # that the XML is intact server-side
        self.assertEqual(requestReceived['headers']['content-type'], 'application/xml')
        self.assertEqual(requestReceived['body'], node.toprettyxml())

if __name__ == '__main__':
    test_helper.main()

