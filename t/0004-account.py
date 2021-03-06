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
                return object.func(*(('wrapper',) + args), **kwargs)

        serverManagementInterface = [
            'funcA',
            {'name': 'funcB', 'wrapper': None},
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

    def checkBasicInterface(self, func, *prefixed):
        function = getattr(self.account, func, None)
        self.assertTrue(function, 'Account gets method ' + func)
        self.assertEqual(
            function(),
            (func, prefixed, {}),
            #'Invocation of ' + func + ' with no args gives expected positional set',
        )
        posArgs = ('aard', 'vark', 'spamminator')
        kwArgs = {'aard': 'Vark', 'vark': 'VARK!'}
        self.assertEqual(
            function(*posArgs),
            (func, prefixed + posArgs, {}),
            'Invocation of ' + func + ' with positional args includes expected set',
        )
        self.assertEqual(
            function(**kwArgs),
            (func, prefixed, kwArgs),
            'Invocation of ' + func + ' with keywords only includes expected positional set and keywords',
        )
        self.assertEqual(
            function(*posArgs, **kwArgs),
            (func, prefixed + posArgs, kwArgs),
            'Invocation of ' + func + ' with both pos and keyword args yields full expected set',
        )

    def testSimpleWrappedFunction(self):
        self.checkBasicInterface('funcA', self.account.session.serverManager)

    def testUnwrappedFunction(self):
        self.checkBasicInterface('funcB')

    def testWrappedFunction(self):
        self.checkBasicInterface('funcC', 'wrapper', self.account.session.serverManager)

if __name__ == '__main__':
    test_helper.main()

