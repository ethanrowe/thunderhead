#!/usr/bin/env python

import test_helper
import os
import re

test_path = os.path.dirname(__file__)

for root, dirs, files in os.walk(test_path):
    modules = [file[:-3] for file in sorted(files) if file[-3:] == '.py' and re.match('\d{3,}', file)]

suite = test_helper.TestSuite()
for module_name in modules:
    module = __import__(module_name)
    suite.addTest( test_helper.defaultTestLoader.loadTestsFromModule(module) )

test_helper.TextTestRunner(verbosity=2).run(suite)

