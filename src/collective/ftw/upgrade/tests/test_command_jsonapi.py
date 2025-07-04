from collective.ftw.upgrade.command import jsonapi
from collective.ftw.upgrade.command.jsonapi import APIRequestor
from collective.ftw.upgrade.command.jsonapi import get_api_url
from collective.ftw.upgrade.command.jsonapi import get_instance_port
from collective.ftw.upgrade.command.jsonapi import get_running_instance
from collective.ftw.upgrade.command.jsonapi import get_zope_url
from collective.ftw.upgrade.command.jsonapi import NoRunningInstanceFound
from collective.ftw.upgrade.command.jsonapi import TempfileAuth
from collective.ftw.upgrade.tests.base import CommandAndInstanceTestCase
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from Products.CMFPlone.utils import safe_unicode
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

import os
import time


class ZopeConfPathStub:
    """Stubs a path.py Path object for a zope.conf file."""

    def __init__(self, *lines):
        self._text = "\n".join(map(safe_unicode, lines))

    def read_text(self):
        return self._text


class TestAPIRequestor(CommandAndInstanceTestCase):

    def setUp(self):
        super().setUp()
        self.write_zconf_with_test_instance()

    def test_GET(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        jsondata = requestor.GET("list_plone_sites").json()
        self.assertEqual(
            [{"id": "plone", "path": "/plone", "title": "Plone site"}], jsondata
        )

    def test_GET_raises_error(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        with self.assertRaises(HTTPError) as cm:
            requestor.GET("wrong_action")

        self.assertEqual(
            ["ERROR", "Unknown API action", 'There is no API action "wrong_action".'],
            cm.exception.response.json(),
        )

    def test_GET_with_params(self):
        requestor = APIRequestor(
            HTTPBasicAuth(SITE_OWNER_NAME, SITE_OWNER_PASSWORD), site="plone"
        )

        requestor.GET(
            "get_profile", site="plone", params={"profileid": "plone.app.event:default"}
        )

    def test_GET_with_specific_instance(self):
        jsonapi.TIMEOUT = 5
        requestor = APIRequestor(
            HTTPBasicAuth(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            instance_name="instance",
        )

        self.assertEqual(200, requestor.GET("list_plone_sites").status_code)

        with self.assertRaises(NoRunningInstanceFound):
            requestor.GET("list_plone_sites", instance_name="instance2")

    def test_error_when_no_running_instance_found(self):
        jsonapi.TIMEOUT = 5
        self.layer["root_path"].joinpath("parts/instance").rmtree()
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        with self.assertRaises(NoRunningInstanceFound):
            requestor.GET("list_plone_sites")

    def test_basic_authentication(self):
        requestor = APIRequestor(HTTPBasicAuth(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        jsondata = requestor.GET("current_user").json()
        self.assertEqual("admin", jsondata)

    def test_tempfile_authentication(self):
        requestor = APIRequestor(TempfileAuth(relative_to=os.getcwd()))
        jsondata = requestor.GET("current_user").json()
        self.assertEqual("system-upgrade", jsondata)


class TestJsonAPIUtils(CommandAndInstanceTestCase):

    def test_get_api_url(self):
        self.write_zconf_with_test_instance()
        test_instance_port = self.layer["port"]

        self.assertEqual(
            f"http://localhost:{test_instance_port}/upgrades-api/foo",
            get_api_url("foo"),
        )

        self.assertEqual(
            f"http://localhost:{test_instance_port}/Plone/upgrades-api/bar",
            get_api_url("bar", site="Plone"),
        )

        self.assertEqual(
            f"http://localhost:{test_instance_port}/Plone/upgrades-api/baz",
            get_api_url("baz", site="/Plone/"),
        )

    def test_get_api_url_with_public_url(self):
        self.write_zconf_with_test_instance()
        test_instance_port = self.layer["port"]

        os.environ["UPGRADE_PUBLIC_URL"] = "http://domain.com"
        self.assertEqual(
            "http://localhost:{}/"
            "VirtualHostBase/http/domain.com:80/mount-point/platform/"
            "VirtualHostRoot/upgrades-api/action".format(test_instance_port),
            get_api_url("action", site="mount-point/platform"),
        )

        os.environ["UPGRADE_PUBLIC_URL"] = "https://domain.com"
        self.assertEqual(
            "http://localhost:{}/"
            "VirtualHostBase/https/domain.com:443/mount-point/platform/"
            "VirtualHostRoot/upgrades-api/action".format(test_instance_port),
            get_api_url("action", site="mount-point/platform"),
        )

        os.environ["UPGRADE_PUBLIC_URL"] = "https://domain.com/"
        self.assertEqual(
            "http://localhost:{}/"
            "VirtualHostBase/https/domain.com:443/mount-point/platform/"
            "VirtualHostRoot/upgrades-api/action".format(test_instance_port),
            get_api_url("action", site="mount-point/platform"),
        )

        os.environ["UPGRADE_PUBLIC_URL"] = "https://domain.com/foo"
        self.assertEqual(
            "http://localhost:{}/"
            "VirtualHostBase/https/domain.com:443/mount-point/platform/"
            "VirtualHostRoot/_vh_foo/upgrades-api/action".format(test_instance_port),
            get_api_url("action", site="mount-point/platform"),
        )

    def test_get_api_url_for_specific_instance(self):
        jsonapi.TIMEOUT = 5
        test_instance_port = self.layer["port"]
        self.write_zconf("instance1", "1000")
        self.write_zconf("instance2", test_instance_port)

        with self.assertRaises(NoRunningInstanceFound):
            get_api_url("foo", instance_name="instance1")
        self.assertEqual(
            f"http://localhost:{test_instance_port}/upgrades-api/foo",
            get_api_url("foo", instance_name="instance2"),
        )

    def test_get_zope_url_without_zconf(self):
        jsonapi.TIMEOUT = 5
        with self.assertRaises(NoRunningInstanceFound):
            get_zope_url()

    def test_find_running_instance_retries_until_timeout(self):
        jsonapi.TIMEOUT = 5
        self.write_zconf("instance1", "1000")

        t0 = time.time()
        info = get_running_instance(self.layer["root_path"])
        elapsed = time.time() - t0

        self.assertIsNone(info)
        self.assertTrue(elapsed >= jsonapi.TIMEOUT)

    def test_find_first_running_instance_info(self):
        test_instance_port = self.layer["port"]
        self.write_zconf("instance1", "1000")
        part2 = self.write_zconf("instance2", test_instance_port)
        self.assertEqual(
            {"port": test_instance_port, "path": str(part2)},
            get_running_instance(self.layer["root_path"]),
        )

    def test_find_specific_running_instance_info(self):
        test_instance_port = self.layer["port"]
        part1 = self.write_zconf("instance1", test_instance_port)
        part2 = self.write_zconf("instance2", test_instance_port)
        self.assertEqual(
            {"port": test_instance_port, "path": str(part1)},
            get_running_instance(self.layer["root_path"], "instance1"),
        )
        self.assertEqual(
            {"port": test_instance_port, "path": str(part2)},
            get_running_instance(self.layer["root_path"], "instance2"),
        )

    def test_find_first_running_instance_info_with_network_interface(self):
        test_instance_port = self.layer["port"]
        self.write_zconf("instance1", "1000")
        part2 = self.write_zconf("instance2", f"0.0.0.0:{test_instance_port}")
        self.assertEqual(
            {"port": test_instance_port, "path": str(part2)},
            get_running_instance(self.layer["root_path"]),
        )

    def test_find_first_running_instance_info_named_zeoclient(self):
        test_zeoclient_port = self.layer["port"]
        self.write_zconf("zeoclient1", "1000")
        part2 = self.write_zconf("zeoclient2", test_zeoclient_port)
        self.assertEqual(
            {"port": test_zeoclient_port, "path": str(part2)},
            get_running_instance(self.layer["root_path"]),
        )

    def test_get_instance_port_port_only(self):
        zconf = ZopeConfPathStub("<http-server>", "  address 8080", "</http-server>")
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_localhost_interface_prefix(self):
        zconf = ZopeConfPathStub(
            "<http-server>", "  address 127.0.0.1:8080", "</http-server>"
        )
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_public_interface_prefix(self):
        zconf = ZopeConfPathStub(
            "<http-server>", "  address 127.0.0.1:8080", "</http-server>"
        )
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_localhost_ip(self):
        zconf = ZopeConfPathStub(
            "ip-address 127.0.0.1",
            "<http-server>",
            "  address 127.0.0.1:8080",
            "</http-server>",
        )
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_public_ip(self):
        zconf = ZopeConfPathStub(
            "ip-address 0.0.0.0",
            "<http-server>",
            "  address 127.0.0.1:8080",
            "</http-server>",
        )
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_no_indent(self):
        zconf = ZopeConfPathStub("<http-server>", "address 8080", "</http-server>")
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_not_found(self):
        zconf = ZopeConfPathStub("<http-server>", "</http-server>")
        self.assertEqual(None, get_instance_port(zconf))

    def test_get_instance_port_wsgi_listen(self):
        zconf = ZopeConfPathStub("[server:main]\n" "listen = 127.0.0.1:8080")
        self.assertEqual(8080, get_instance_port(zconf))

    def test_get_instance_port_wsgi_fast_listen(self):
        zconf = ZopeConfPathStub("[server:main]\n" "fast-listen = 0.0.0.0:8080")
        self.assertEqual(8080, get_instance_port(zconf))
