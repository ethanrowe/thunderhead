#!/usr/bin/env python

import test_helper
import thunderhead.rackspace

class AuthorizationOverride(thunderhead.rackspace.Authorization):
    def __init__(self, user, pw):
        thunderhead.rackspace.Authorization.__init__(self, user, pw)

    @classmethod
    def bindToTestServer(self, server):
        self.baseURL = 'http://localhost:' + str(server.port)
        return self.baseURL

class TestRackspaceAuthorization(test_helper.TestCase):
    def setUp(self):
        pass

    def testAuthorizationBaseURL(self):
        self.assertEqual(
            thunderhead.rackspace.Authorization.baseURL,
            'https://auth.api.rackspacecloud.com/v1.0' )

    def testAuthorization(self):
        server = test_helper.Authenticator.test()
        user, pw = 'foofoo', 'abcdefghijklmnop0987654321'
        AuthorizationOverride.bindToTestServer(server)
        session = AuthorizationOverride(user, pw)
        requestReceived = server.getRequestData()
        server.finish(1)
        # verify presence of appropriate headers
        self.assertEqual(requestReceived['headers']['x-auth-user'], user)
        self.assertEqual(requestReceived['headers']['x-auth-key'], pw)
        # verify that session has what we expect
        self.assertEqual(session.manageServerURL, server.makeURL('/server'))
        self.assertEqual(session.storageURL, server.makeURL('/storage'))
        self.assertEqual(session.cdnURL, server.makeURL('/cdn'))
        self.assertEqual(session.authToken, server.authToken)
        # verify that the session connects to the manageServerURL for server operations
        conn = session.serverManager
        self.assertEqual(conn.scheme, 'http')
        self.assertEqual(conn.host, 'localhost')
        self.assertEqual(conn.port, server.port)
        self.assertEqual(conn.pathPrefix, '/server')
         
    def testAuthorizationFailure(self):
        get = lambda (request): request.send_response(401)
        server = test_helper.StubServer.test({'get': get})
        AuthorizationOverride.bindToTestServer(server)
        test = lambda: AuthorizationOverride('bah', 'blah')
        self.assertRaises(thunderhead.rackspace.BadCredentialsException, test)
        server.finish(1)

if __name__ == '__main__':
    test_helper.main()

