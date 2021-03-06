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
import thunderhead.rackspace.api
import base64, datetime
import xml.dom.minidom as minidom

class TestRackspaceAPICachedResources(test_helper.TestCase):
    def setUp(self):
        self.calls = {}
        def baseFunction(*args, **kwargs):
            calls = {}
            key = len(self.calls.keys()) + 1
            calls[key] = (args, kwargs)
            self.calls[key] = calls[key]
            return calls
        self.resource = thunderhead.rackspace.api.CachedResource(baseFunction)

    def testDefaults(self):
        self.assertEqual(self.resource.interval, 60, 'cache interval defaults to 60 seconds')
        self.assertEqual(self.resource.timestamp, None, 'timestamp defaults to none')

    def testNeedsUpdate(self):
        self.resource.timestamp = thunderhead.rackspace.api.unixNow()
        self.resource.interval = 60
        self.assertFalse(self.resource.needsUpdate(), 'needsUpdate false if time within interval')
        self.resource.interval = 0
        self.assertTrue(self.resource.needsUpdate(), 'needsUpdate true if time outside interval')

    def testMergeFunction(self):
        self.resource.asset = {'a': 1, 'b': 2}
        self.assertEqual(
            self.resource.merge({'c': 3}),
            {'a':1, 'b':2, 'c':3},
            'merge adds new entry into asset',
        )
        class Entity(object):
            status = 'DELETED'
        entity = Entity()
        self.assertEqual(
            self.resource.merge({'a': entity}),
            {'b': 2},
            'merge removes entity if it has a "status" attribute with "DELETED" value',
        )
        self.assertEqual(
            self.resource.merge({'b': {'status': 'DELETED'}}),
            {'a': 1},
            'merge removes hash entity if it has a "status" key with value "DELETED"',
        )
        self.assertEqual(
            self.resource.merge({'a': 1.1}),
            {'a': 1.1, 'b': 2},
            'merge replaces old value with new value for a given key',
        )
        self.assertEqual(
            self.resource.merge({'a': 5, 'c': 'C', 'b': {'status': 'DELETED'}}),
            {'a': 5, 'c': 'C'},
            'merge handles combination of new, edited, and deleted items',
        )

    def testBaseFunctionUsage(self):
        self.assertEqual(
            self.resource('some', 'arguments', other='argument'),
            {1: (('some','arguments'), {'other':'argument'})},
            'initialization calls base function appropriately',
        )
        self.assertTrue(self.resource.timestamp, 'timestamp set after initial invocation')
        self.assertEqual(
            self.resource('z', 'y', 'x', foof='flaf'),
            {1: (('some', 'arguments'), {'other':'argument'})},
            'update leaves base function uncalled when update is not necessary',
        )
        self.resource.interval = 0
        ts = self.resource.timestamp
        test_helper.time.sleep(1)
        self.assertEqual(
            self.resource('a', 'b', 'c', z='Z', y='Y'),
            {
                1: (('some', 'arguments'), {'other':'argument'}),
                2: (('a','b','c'), {'z':'Z', 'y':'Y', 'since': ts}),
            },
            #'update calls base function with args and timestamp when interval elapsed'
        )
        self.assertTrue(
            self.resource.timestamp > ts,
            'update adjusts the timestamp appropriately',
        )
        

class TestRackspaceAPIObjects(test_helper.TestCase):
    def testAPIServerManagementInterface(self):
        self.assertTrue(hasattr(thunderhead.rackspace.api, 'serverManagementInterface'))
        api = thunderhead.rackspace.api.serverManagementInterface[::]
        api.sort(cmp=(lambda x, y: cmp((hasattr(x, 'keys') and x['name'].lower()) or x.lower(), (hasattr(y, 'keys') and y['name'].lower()) or y.lower()) ))
        self.assertEqual(
            api,
            [
                'createServer',
                'createSharedIPGroup',
                'deleteServer',
                'deleteSharedIPGroup',
                {'name':'getFlavors', 'wrapper': thunderhead.rackspace.api.CachedResource},
                {'name':'getImages', 'wrapper': thunderhead.rackspace.api.CachedResource},
                'getPublicIPs',
                {'name':'getServers', 'wrapper': thunderhead.rackspace.api.CachedResource},
                {'name':'getSharedIPGroups', 'wrapper': thunderhead.rackspace.api.CachedResource},
                {'name':'Server', 'wrapper': None},
                'shareIP',
            ],
            'serverManagementInterface provides appropriate functions and wrappers',
        )

    def testServerClassToXML(self):
        props = {
            'name': 'Test-Server-Foo',
            'id': 13579,
            'adminPass': 'foofoofoo',
            'hostId': 'ae81' * 8,
            'flavorId': 3,
            'imageId': 7,
            'status': 'BUILD',
            'progress': 75,
            'publicIPs': ['10.10.1.1', '10.11.1.1'],
            'privateIPs': ['192.168.1.1', '192.168.70.1'],
            'metadata': {'aard': 'vark', 'platy': 'pus'},
            'files': {'/path/a': 'Path A file content', '/path/b': 'Path B file content'},
            'sharedIpGroupId': 2500,
        }
        server = thunderhead.rackspace.api.Server(**props).toXML()
        self.assertEqual(server.getAttribute('xmlns'), 'http://docs.rackspacecloud.com/servers/api/v1.0')
        for attr in ['name', 'id', 'hostId', 'flavorId', 'imageId', 'status', 'progress', 'sharedIpGroupId', 'adminPass']:
            self.assertEqual(server.getAttribute(attr), str(props[attr]))

        addr, = server.getElementsByTagName('addresses')
        priv, = addr.getElementsByTagName('private')
        pub, = addr.getElementsByTagName('public')
        privAddr = [ip.getAttribute('addr') for ip in priv.getElementsByTagName('ip')]
        pubAddr = [ip.getAttribute('addr') for ip in pub.getElementsByTagName('ip')]
        privAddr.sort()
        pubAddr.sort()
        self.assertEqual(pubAddr, props['publicIPs'])
        self.assertEqual(privAddr, props['privateIPs'])
        
        meta, = server.getElementsByTagName('metadata')
        meta = dict([(m.getAttribute('key'), m.firstChild.data) for m in meta.getElementsByTagName('meta')])
        self.assertEqual(meta, props['metadata'])

        files = server.getElementsByTagName('personality')
        self.assertTrue(files and len(files) == 1, 'one personality segment found')
        files = files[0].getElementsByTagName('file')
        self.assertTrue(files and len(files) == 2, 'two files in personality segment')
        self.assertEqual(
            dict([(str(f.getAttribute('path')), base64.decodestring(f.firstChild.data)) for f in files]),
            props['files'],
            'file contents have proper path attribute and base64-encoded contents',
        )

    def testSharedIPGroupClassToXML(self):
        props = {
            'id': 123,
            'server_id': 99,
            'name': 'Foo foo the snoo',
        }
        group = thunderhead.rackspace.api.SharedIPGroup(**props).toXML()
        self.assertEqual(group.getAttribute('xmlns'), 'http://docs.rackspacecloud.com/servers/api/v1.0')
        for attr in ['id', 'name']:
            self.assertEqual(group.getAttribute(attr), str(props[attr]))
        server, = group.getElementsByTagName('server')
        self.assertEqual(server.getAttribute('id'), str(props['server_id']), 'SharedIPGroup XML uses single server node if only one server')
        props['servers'] = [77, 88]
        group = thunderhead.rackspace.api.SharedIPGroup(**props).toXML()
        servers, = group.getElementsByTagName('servers')
        servers = [int(server.getAttribute('id')) for server in servers.getElementsByTagName('server')]
        servers.sort()
        self.assertEqual(
            servers,
            [77, 88, 99],
            'SharedIPGroup XML uses servers node if multiple servers present',
        )


class TestRackspaceAPIInteractions(test_helper.TestCase):
    def setUp(self):
        self.server = test_helper.APIServer.test()
        self.connection = thunderhead.rackspace.BoundConnection(
            'http://localhost:' + str(self.server.port),
            {'X-Auth-Token': 'SOME-AUTH-TOKEN'},
        )

    def tearDown(self):
        self.server.finish()
        self.server = None
        self.connection = None

    def testServersDetail(self):
        hash = thunderhead.rackspace.api.getServers(self.connection)
        self.assertTrue(
            hasattr(hash, 'has_key') and hasattr(hash, 'iteritems'),
            'getServers result looks like a dictionary'
        )
        one = hash[1234]
        two = hash[5678]
        self.assertTrue(one and two, 'getServers result keyed by server id')
        self.assertEqual(one.id, 1234)
        self.assertEqual(one.name, 'sample-server')
        self.assertEqual(one.imageId, 2)
        self.assertEqual(one.flavorId, 1)
        self.assertEqual(one.status, 'BUILD')
        self.assertEqual(one.progress, 60)
        self.assertEqual(one.hostId, 'e4d909c290d0fb1ca068ffaddf22cbd0')
        self.assertEqual(one.metadata, {'Server Label': 'Web Head 1', 'Image Version': '2.1'})
        self.assertEqual(one.publicIPs, ['67.23.10.132', '67.23.10.131'])
        self.assertEqual(one.privateIPs, ['10.176.42.16'])
        self.assertEqual(two.id, 5678)
        self.assertEqual(two.name, 'sample-server2')
        self.assertEqual(two.imageId, 2)
        self.assertEqual(two.flavorId, 1)
        self.assertEqual(two.status, 'ACTIVE')
        self.assertEqual(two.hostId, '9e107d9d372bb6826bd81d3542a419d6')
        self.assertEqual(two.metadata, {'Server Label': 'DB 1'})
        self.assertEqual(two.publicIPs, ['67.23.10.133'])
        self.assertEqual(two.privateIPs, ['10.176.42.17'])

    def testServersDetailSince(self):
        result = thunderhead.rackspace.api.getServers(self.connection, since='foo')
        request = self.server.getRequestData()
        self.assertEqual(request['path'], '/servers/detail?changes-since=foo')

    def testFlavorsSince(self):
        result = thunderhead.rackspace.api.getFlavors(self.connection, since='foo')
        request = self.server.getRequestData()
        self.assertEqual(request['path'], '/flavors/detail?changes-since=foo')

    def testImagesSince(self):
        result = thunderhead.rackspace.api.getImages(self.connection, since='foo')
        request = self.server.getRequestData()
        self.assertEqual(request['path'], '/images/detail?changes-since=foo')
        
    def testSharedIPGroupsSince(self):
        result = thunderhead.rackspace.api.getSharedIPGroups(self.connection, since='foo')
        request = self.server.getRequestData()
        self.assertEqual(request['path'], '/shared_ip_groups?changes-since=foo')

    def testServerDeleteById(self):
        result = thunderhead.rackspace.api.deleteServer(self.connection, 1234)
        request = self.server.getRequestData()
        self.assertTrue(result, 'deleteServer() with raw ID returns true')
        self.assertEqual(
            request['path'],
            '/servers/1234',
            'deleteServer() with raw ID requests /servers/<id>'
        )
        self.assertEqual(
            request['method'],
            'DELETE',
            'deleteServer() with raw ID uses a DELETE request',
        )

    def testServerDeleteByObject(self):
        server = thunderhead.rackspace.api.Server(id=4567)
        result = thunderhead.rackspace.api.deleteServer(self.connection, server)
        request = self.server.getRequestData()
        self.assertTrue(result, 'deleteServer() with object returns true')
        self.assertEqual(
            request['path'],
            '/servers/4567',
            'deleteServer() with object requests /servers/<object.id>',
        )
        self.assertEqual(
            request['method'],
            'DELETE',
            'deleteServer() with object uses a DELETE request',
        )

    def testFlavorsDetail(self):
        flavors = thunderhead.rackspace.api.getFlavors(self.connection)
        self.assertEqual(
            self.server.getRequestData()['path'],
            '/flavors/detail',
            'getFlavors requests the flavors detailed listing',
        )
        self.assertEqual(
            flavors,
            {
                1: {'id': 1, 'name': '256 MB Server', 'ram': 256, 'disk': 10},
                2: {'id': 2, 'name': '512 MB Server', 'ram': 512, 'disk': 20},
            },
            'Flavors dictionary properly derived from XML',
        )

    def testImagesDetail(self):
        images = thunderhead.rackspace.api.getImages(self.connection)
        self.assertEqual(
            self.server.getRequestData()['path'],
            '/images/detail',
            'getImages request the images detailed listing',
        )
        self.assertEqual(
            images,
            {
                2: {
                    'id': 2,
                    'name': 'CentOS 5.2',
                    'status': 'ACTIVE',
                    'updated': '2010-10-10T12:00:00Z',
                    'created': '2010-08-10T12:00:00Z',
                },
                743: {
                    'id': 743,
                    'name': 'My Server Backup',
                    'serverId': 12,
                    'updated': '2010-10-10T12:00:00Z',
                    'created': '2010-08-10T12:00:00Z',
                    'status': 'SAVING',
                    'progress': 80,
                },
            },
            'images detail XML properly maps to dictionary',
        )

    def testServerCreation(self):
        properties = {
            'name': 'Thunderhead Blunderfred Testing Server',
            'imageId': 5,
            'flavorId': 6,
            'metadata': {
                'role': 'Some testing role',
                'froggies': 'No froggies.',
            },
            'files': {
                '/file/one': 'This is the content of my first faux-file.  Love it!',
                '/file/two': 'And once more, with feeling!',
            },
        }
        server = thunderhead.rackspace.api.Server(**properties)
        created = thunderhead.rackspace.api.createServer(self.connection, server)
        request = self.server.getRequestData()
        self.assertEqual(request['method'], 'POST', 'createServer issues a POST')
        self.assertEqual(request['path'], '/servers', 'createServer path is /servers')
        # The APIServer strips out any personality block (i.e. files), so verify
        # their presence in the request info
        xml = minidom.parseString(request['body'])
        personality, = xml.documentElement.getElementsByTagName('personality')
        self.assertEqual(
            dict([
                (f.getAttribute('path'), base64.decodestring(f.firstChild.data)) for f in personality.getElementsByTagName('file')
            ]),
            properties['files'],
            'POST XML includes file data as intended',
        )
        # The APIServer amends the XML structure it receives, so it suffices to inspect
        # the resulting structure and not fret about the rest of the request received.
        self.assertEqual(created.name, properties['name'])
        self.assertEqual(created.imageId, properties['imageId'])
        self.assertEqual(created.flavorId, properties['flavorId'])
        self.assertEqual(created.metadata, properties['metadata'])
        self.assertFalse(hasattr(created, 'files'), 'files do not propagate from service')
        # these are hard-coded in APIServer
        self.assertEqual(created.id, test_helper.APIServer.createId)
        self.assertEqual(created.status, test_helper.APIServer.createStatus)
        self.assertEqual(created.progress, test_helper.APIServer.createProgress)
        self.assertEqual(created.hostId, test_helper.APIServer.createHostId)
        self.assertEqual(created.adminPass, test_helper.APIServer.createAdminPass)
        self.assertEqual(created.privateIPs, ['192.168.1.1'])
        self.assertEqual(created.publicIPs, ['10.10.1.1'])

    def testServerPublicIPs(self):
        testIPs = thunderhead.rackspace.api.getPublicIPs(self.connection, '1')
        self.assertEqual(testIPs, { 1: { 'addr': '67.23.10.132' }, 2: { 'addr': '67.23.10.131' }, } )

# Plan: store requested shared IPs, look to see if there is one for that server
# if so: return it
# if not - report that none were found
    def testShareIP(self):
        properties = {
            'sharedIpGroupId': 1234,
            'configureServer': 'true',
        }
        mySharedIP = thunderhead.rackspace.api.SharedIP(**properties)
        # Result should be 202
        returnCode = thunderhead.rackspace.api.shareIP(self.connection, mySharedIP, '1', '67.23.10.132')
        self.assertEqual(returnCode, 202)

    def testCreateSharedIPGroup(self):
        properties = {
                'name': 'Shared IP Group 1',
                'server_id': 422,
        }
        # Create shared IP group object that emits XML for the server
        sharedIPGroup = thunderhead.rackspace.api.SharedIPGroup(**properties)
        created = thunderhead.rackspace.api.createSharedIPGroup(self.connection, sharedIPGroup)
        request = self.server.getRequestData()
        self.assertEqual(request['method'], 'POST', 'createSharedIPGroup  issues a POST')
        self.assertEqual(request['path'], '/shared_ip_groups', 'createSharedIPGroup  path is /shared_ip_groups')
        xml = minidom.parseString(request['body'])
        ## XXX: Need to add some real tests here
        #self.assertTrue(hasattr(created, 'name'), 'Has attribute name')

    def testListSharedIPGroup(self):
        ipList = thunderhead.rackspace.api.getSharedIPGroups(self.connection)
        self.assertTrue(
            hasattr(ipList, 'has_key'),
            'getSharedIPGroups result set looks like a dictionary'
        )
        request = self.server.getRequestData()
        self.assertEqual(request['method'], 'GET', 'createSharedIPGroup  issues a GET')
        self.assertEqual(request['path'], '/shared_ip_groups', 'createSharedIPGroup  path is /shared_ip_groups')
        self.assertEqual(
            len(ipList.keys()),
            2,
            #'getSharedIPGroups returns entries for two expected groups',
        )
        ids = ipList.keys()
        ids.sort()
        self.assertEqual(
            ids,
            [1234, 5678],
            'getSharedIPGroups keys result set by shared IP group ID',
        )
        group1 = ipList[1234]
        group2 = ipList[5678]
        self.assertEqual(group1.id, 1234)
        servers = group1.servers[::]
        servers.sort()
        self.assertEqual(servers, [422, 3445])
        
        self.assertEqual(group2.id, 5678)
        servers = group2.servers[::]
        servers.sort()
        self.assertEqual(servers, [2456, 9891, 23203])

    def testDeleteSharedIPGroup(self):
        code = thunderhead.rackspace.api.deleteSharedIPGroup(self.connection, '1234')
        # code should be 204 if success
        self.assertEqual(code, 204)

class TestEmptyResources(test_helper.TestCase):
    def setUp(self):
        self.server = test_helper.APIServerEmpty.test()
        self.connection = thunderhead.rackspace.BoundConnection(
            'http://localhost:' + str(self.server.port),
            {'X-Auth-Token': 'SOME-AUTH-TOKEN'},
        )

    def tearDown(self):
        self.server.finish()
        self.server = None
        self.connection = None

    def testEmptyServers(self):
        hash = thunderhead.rackspace.api.getServers(self.connection)
        self.assertEqual(hash, {}, 'Empty server result yields empty hash')

    def testEmptyFlavors(self):
        hash = thunderhead.rackspace.api.getFlavors(self.connection)
        self.assertEqual(hash, {}, 'Empty flavors result yields empty hash')

    def testEmptyImages(self):
        hash = thunderhead.rackspace.api.getImages(self.connection)
        self.assertEqual(hash, {}, 'Empty images result yields empty hash')

    def testEmptySharedIPGroups(self):
        hash = thunderhead.rackspace.api.getSharedIPGroups(self.connection)
        self.assertEqual(hash, {}, 'Empty shared IP groups result yields empty hash')

if __name__ == '__main__':
    test_helper.main()
