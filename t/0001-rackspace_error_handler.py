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

