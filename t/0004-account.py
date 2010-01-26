#!/usr/bin/env python

import test_helper
import thunderhead

class ProviderStub(object):
    class api(object):
        serverManagementInterface = [
            'funcA',
            'funcB',
            'funcC',
        ]

        @classmethod
        def funcA(self, *args, **kwargs):
            return ('funcA', args, kwargs)

        @classmethod
        def funcB(self, *args, **kwargs):
            return ('funcB', args, kwargs)

        @classmethod
        def funcC(self, *args, **kwargs):
            return ('funcC', args, kwargs)

    class Authorization(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.serverManager = object()

class TestAccountComposition(test_helper.TestCase):
    def setUp(self):
        self.provider = ProviderStub()
        self.account = thunderhead.Account(self.provider)
        self.account.credentials = ('a', 'b', 'c')
        self.account.namedCredentials = {'a': 'A', 'b': 'B', 'c': 'C'}

    def testAuthorization(self):
        # the session attribute should have the authorization object
        # with the relevant credentials in place
        self.assertTrue(
            isinstance(self.account.session, ProviderStub.Authorization),
            'session instantiated from the provider.Authorization member class',
        )
        self.assertEqual(
            self.account.session.args,
            self.account.credentials,
            'credentials (positional) passed through to provider.Authorization constructor',
        )
        self.assertEqual(
            self.account.session.kwargs,
            self.account.namedCredentials,
            'credentials (named) passed through to provider.Authorization constructor',
        )

    def testConstructor(self):
        # basic constructur invocation: provider set from first arg
        self.assertEqual(self.account.provider, self.provider)
        # additional positional params treated as credentials attr
        account = thunderhead.Account(ProviderStub, 'one', 'two', 'three')
        self.assertEqual(account.provider, ProviderStub)
        self.assertEqual(account.credentials, ('one', 'two', 'three'))
        # named params treated as namedCredentials attr
        account = thunderhead.Account(ProviderStub, one=1, two=2, three=3)
        self.assertEqual(account.provider, ProviderStub)
        self.assertEqual(account.namedCredentials, {'one': 1, 'two': 2, 'three': 3})
        # mixed params handled appropriately
        account = thunderhead.Account(ProviderStub, 'one', 'two', foo='fu', bar='bargh')
        self.assertEqual(account.provider, ProviderStub)
        self.assertEqual(account.credentials, ('one', 'two'))
        self.assertEqual(account.namedCredentials, {'foo': 'fu', 'bar': 'bargh'})

    def testServerManagementInterface(self):
        # every method in provider's serverManagementInterface should be
        # wrapped on the account object, passing the account's session as the
        # first argument, and positional/named params passed along as well.
        for func in ProviderStub.api.serverManagementInterface:
            self.assertTrue(hasattr(self.account, func), 'Account gets method ' + func)
            self.assertEqual(
                getattr(self.account, func)(),
                (func, (self.account.session.serverManager,), {}),
                func + ' empty invocation passes through account session attr only',
            )
            self.assertEqual(
                getattr(self.account, func)('aard', 'vark', 'spamminator'),
                (func, (self.account.session.serverManager, 'aard', 'vark', 'spamminator'), {}),
                func + ' invocation with positional params only'
            )
            self.assertEqual(
                getattr(self.account, func)(aard='vark', spam='minator'),
                (func, (self.account.session.serverManager,), {'aard': 'vark', 'spam': 'minator'}),
                func + ' invocation with named params only',
            )
            self.assertEqual(
                getattr(self.account, func)('aard', 'vark', aard='vark'),
                (func, (self.account.session.serverManager, 'aard', 'vark'), {'aard': 'vark'}),
                func + ' invocation with both param types',
            )

if __name__ == '__main__':
    test_helper.main()
