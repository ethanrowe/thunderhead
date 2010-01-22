#!/usr/bin/env python

import test_helper
import thunderhead.rackspace.api
import base64, datetime
import xml.dom.minidom as minidom

class TestRackspaceAPIObjects(test_helper.TestCase):
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
        one, two = thunderhead.rackspace.api.getServers(self.connection)
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

if __name__ == '__main__':
    test_helper.main()
