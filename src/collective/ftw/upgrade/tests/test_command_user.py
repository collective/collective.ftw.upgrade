from collective.ftw.upgrade.tests.base import CommandAndInstanceTestCase
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

import os


class TestUserCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super().setUp()
        self.write_zconf_with_test_instance()

    def test_sites_help(self):
        self.upgrade_script("user --help")

    def test_prints_authenticated_user(self):
        exitcode, output = self.upgrade_script("user")
        self.assertEqual(0, exitcode)
        self.assertEqual('Authenticated as "admin".\n', output)

    def test_authentication_by_param(self):
        del os.environ["UPGRADE_AUTHENTICATION"]
        exitcode, output = self.upgrade_script(
            f"user --auth {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
        )
        self.assertEqual(0, exitcode)
        self.assertEqual('Authenticated as "admin".\n', output)

    def test_tempfile_authentication_fallback(self):
        del os.environ["UPGRADE_AUTHENTICATION"]
        exitcode, output = self.upgrade_script("user")
        self.assertEqual(0, exitcode)
        self.assertEqual('Authenticated as "system-upgrade".\n', output)

    def test_valid_authentication_format_is_required(self):
        exitcode, output = self.upgrade_script(
            "user --auth=john", assert_exitcode=False
        )
        self.assertEqual(1, exitcode)
        self.assertEqual(
            'ERROR: Invalid authentication information "john".', output.splitlines()[0]
        )
