#!/usr/bin/env python

##  Copyright (c) 2009-2010 Ethan Rowe (ethan@endpoint.com)
##  For more information, see http://github.com/ethanrowe/thunderhead
##
##  This file is part of Thunderhead.
##
##  Thunderhead is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  Thunderhead is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with Thunderhead.  If not, see <http://www.gnu.org/licenses/>.

import test_helper
import thunderhead

class ProviderStub(object):
    class api(object):
        class FuncCWrapper(object):
            def __init__(self, func):
                self.func = func

            def __call__(object, *args, **kwargs):
                return object.func(*(args + ('wrapper',)), **kwargs)

        serverManagementInterface = [
            'funcA',
            'funcB',
            {'name': 'funcC', 'wrapper': FuncCWrapper},
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
        for item in ProviderStub.api.serverManagementInterface:
            if hasattr(item, 'has_key'):
                func = item['name']
                wrappedArg = ('wrapper',)
            else:
                func = item
                wrappedArg = ()
            self.assertTrue(hasattr(self.account, func), 'Account gets method ' + func)
            self.assertEqual(
                getattr(self.account, func)(),
                (func, (self.account.session.serverManager,) + wrappedArg, {}),
                func + ' empty invocation passes through account session attr only',
            )
            self.assertEqual(
                getattr(self.account, func)('aard', 'vark', 'spamminator'),
                (func, (self.account.session.serverManager, 'aard', 'vark', 'spamminator') + wrappedArg, {}),
                func + ' invocation with positional params only'
            )
            self.assertEqual(
                getattr(self.account, func)(aard='vark', spam='minator'),
                (func, (self.account.session.serverManager,) + wrappedArg, {'aard': 'vark', 'spam': 'minator'}),
                func + ' invocation with named params only',
            )
            self.assertEqual(
                getattr(self.account, func)('aard', 'vark', aard='vark'),
                (func, (self.account.session.serverManager, 'aard', 'vark') + wrappedArg, {'aard': 'vark'}),
                func + ' invocation with both param types',
            )


if __name__ == '__main__':
    test_helper.main()

