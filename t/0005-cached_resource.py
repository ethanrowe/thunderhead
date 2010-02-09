#!/usr/bin/env python

import test_helper
import thunderhead

class Cache(thunderhead.CachedResource):
    def __init__(self):
        self.initializeCount = 0
        self.updateCount = 0

    def initialize(self, *args, **kwargs):
        return self.incrementer('initializeCount', *args, **kwargs)

    def update(self, *args, **kwargs):
        return self.incrementer('updateCount', *args, **kwargs)

    def incrementer(self, item, *args, **kwargs):
        if not getattr(self, 'asset', None): self.asset = []
        setattr(self, item, getattr(self, item, 0) + 1)
        self.asset.append((item, args, kwargs))
        return getattr(self, item)

    def representation(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self.asset

class TestCachedResource(test_helper.TestCase):
    def setUp(self):
        self.cache = Cache()

    def testCachedResource(self):
        self.assertFalse(self.cache.initialized, 'uninitialized by default')
        self.assertTrue(self.cache.asset == None, 'asset is None by default')
        self.assertEqual(
            self.cache(),
            [('initializeCount', (), {})],
            '__call__ returns initialize asset value'
        )
        self.assertTrue(self.cache.initialized, 'initialized after first call')
        self.assertEqual(
            self.cache(),
            [('initializeCount', (), {}), ('updateCount', (), {})],
            '__call__ returns updated asset value after initialization'
        )
        self.assertTrue(self.cache.initialized, 'still initialized after subsequent call')
        def foo (*args, **kwargs): return 'this result'
        self.cache.representation = foo
        self.assertEqual(
            self.cache(),
            'this result',
            '__call__ returns result of representation()',
        )

    def testCachedResourceOnePositionalArg(self):
        self.assertEqual(
            self.cache('a'),
            [('initializeCount', ('a',), {})],
            '__call__ and initialize pass through single positional argument',
        )
        self.assertEqual(
            self.cache.args,
            ('a',),
            '__call__ passes single positional argument to representation for init',
        )
        self.assertEqual(
            self.cache.kwargs,
            {},
            'no keyword arguments for representation on init',
        )
        self.assertEqual(
            self.cache('b')[1],
            ('updateCount', ('b',), {}),
            '__call__ and update pass through single positional argument',
        )
        self.assertEqual(
            self.cache.args,
            ('b',),
            '__call__ passes single positional argument to representation for update',
        )
        self.assertEqual(
            self.cache.kwargs,
            {},
            'no keyword arguments for representation on update',
        )

    def testCachedResourceKeywordOnly(self):
        self.assertEqual(
            self.cache(a='A', b='B'),
            [('initializeCount', (), {'a': 'A', 'b': 'B'})],
            '__call__ and initialize pass through keyword args',
        )
        self.assertEqual(
            self.cache.kwargs,
            {'a': 'A', 'b': 'B'},
            '__call__ passes keyword args through to representation on init',
        )
        self.assertEqual(
            self.cache.args,
            (),
            'no positional args for representation on init',
        )
        self.assertEqual(
            self.cache(c='C', d='D')[1],
            ('updateCount', (), {'c': 'C', 'd': 'D'}),
            '__call__ and update pass through keyword args',
        )
        self.assertEqual(
            self.cache.kwargs,
            {'c': 'C', 'd': 'D'},
            '__call__ passes keyword args through to representation on update',
        )

    def testCachedResourcePositionalAndKeyWord(self):
        self.assertEqual(
            self.cache('a', 'b', 'c', foo='bar', blee='blah'),
            [('initializeCount', ('a','b','c'), {'foo':'bar', 'blee':'blah'})],
            '__call__ and initialize pass through positional and keyword args',
        )
        self.assertEqual(
            self.cache.args,
            ('a','b','c'),
            '__call__ passes along positional args to representation on init',
        )
        self.assertEqual(
            self.cache.kwargs,
            {'foo':'bar', 'blee':'blah'},
            '__call__ passes along keyword args to representation on init',
        )
        self.assertEqual(
            self.cache('d', 'e', 'f', wonk='womp', ponk='pomk')[1],
            ('updateCount', ('d','e','f'), {'wonk':'womp', 'ponk':'pomk'}),
            '__call__ and update pass through positional and keyword args',
        )
        self.assertEqual(
            self.cache.args,
            ('d', 'e', 'f'),
            '__call__ passes along positional args to representation on init',
        )
        self.assertEqual(
            self.cache.kwargs,
            {'wonk':'womp', 'ponk':'pomk'},
            '__call__ passes along keyword args to representation on update',
        )

if __name__ == '__main__':
    test_helper.main()

