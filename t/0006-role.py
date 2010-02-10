#!/bin/env python

import test_helper
import thunderhead

class StubAccount(object):
    def __init__(self, *args, **kwargs):
        self.calls = []

    def handler(self, func, args, kwargs):
        tup = ((func,) + args, kwargs)
        self.calls.append(tup)
        return tup

    def Server(self, *args, **kwargs):
        return self.handler('Server', args, kwargs)

    def getServers(self, *args, **kwargs):
        self.handler('getServers', args, kwargs)
        return {1: {'role': 'foo', 'id': 1}, 2: {'role': 'blah', 'id': 2}, 3: {'role': 'foo', 'id': 3}}

    def createServer(self, *args, **kwargs):
        return self.handler('createServer', args, kwargs)

class StubRole(thunderhead.Role):
    serverDefaults = {'x': 'X', 'y': 'Y'}

    @classmethod
    def serverInit(self, server):
        return {'init': server}

    @classmethod
    def isMember(self, server):
        return server['role'] == 'foo'

class TestRoleBaseClass(test_helper.TestCase):
    def setUp(self):
        self.account = StubAccount()
        self.role = type('testRole', (StubRole,), {'account': self.account})

    def testServer(self):
        result = self.role.Server('pos1', 'pos2', arg='Arg')
        last = self.account.calls.pop()
        self.assertEqual(
            last,
            (('Server', 'pos1', 'pos2'), {'x':'X', 'y':'Y', 'arg': 'Arg'}),
            'Server() passes through to account.Server() with arguments merged'
        )
        self.assertEqual(
            result,
            {'init': last},
            'Server() passes structure to serverInit and returns the result'
        )

    def testGetServers(self):
        self.assertEqual(
            self.role.getServers('a', 'b', c='C', d='D'),
            {1: {'role': 'foo', 'id': 1}, 3: {'role': 'foo', 'id': 3}},
            'getServers returns subset for which isMember is true',
        )
        self.assertEqual(
            self.account.calls.pop(),
            (('getServers', 'a', 'b'), {'c':'C', 'd':'D'}),
            'getServers passes arguments through to account.getServers',
        )

    def testCreateServer(self):
        result = self.role.createServer('a', 'b', c='C', d='D')
        last = self.account.calls.pop()
        self.assertEqual(
            last,
            (('createServer', 'a', 'b'), {'c':'C', 'd':'D'}),
            'createServer passes args through to account.createServer()',
        )
        self.assertEqual(
            result,
            last,
            'createServer returns the result of account.createServer()',
        )

if __name__ == '__main__':
    test_helper.main()

