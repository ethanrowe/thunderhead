#!/usr/bin/env python

import test_helper
import thunderhead.rackspace.exceptions as exceptions

class StubException(Exception):
    pass
    
class TestResponseExceptions(test_helper.TestCase):
    def testExceptionRegistryOps(self):
        err = None
        exceptionType = 'fuError'
        self.assertFalse(exceptions.handlerFor(exceptionType))
        try:
            exceptions.throw(exceptionType)
        except exceptions.UnknownExceptionType:
            err = True
        self.assertTrue(err)
        # Now register the handler and we should be able to throw it
        exceptions.registerHandler('fuError', StubException)
        self.assertEqual(exceptions.handlerFor(exceptionType), StubException)
        err = None
        try:
            exceptions.throw(exceptionType)
        except StubException:
            err = True
        self.assertTrue(err)
        
    def testExceptionMap(self):
        faultList = [
            'cloudServersFault',
            'serviceUnavailable',
            'unauthorized',
            'badRequest',
            'overLimit',
            'badMediaType',
            'badMethod',
            'itemNotFound',
            'buildInProgress',
            'serverCapacityUnavailable',
            'backupOrResizeInProgress',
            'resizeNotAllowed',
            'notImplemented',
        ]
        for fault in faultList:
            klass = getattr(exceptions, fault[0].upper() + fault[1::] + 'Exception')
            self.assertEqual(exceptions.handlerFor(fault), klass)
            self.assertEqual(klass.fault, fault)
        
        
if __name__ == '__main__':
    test_helper.main()

