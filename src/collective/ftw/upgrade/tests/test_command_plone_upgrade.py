from Acquisition import aq_chain
from collective.ftw.upgrade.tests.base import CommandAndInstanceTestCase
from collective.ftw.upgrade.utils import get_portal_migration
from ZPublisher.BaseRequest import RequestContainer
from ZPublisher.HTTPRequest import HTTPRequest

import transaction


class TestPloneUpgradeCommand(CommandAndInstanceTestCase):

    def setUp(self):
        super().setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script("plone_upgrade --help")

    def test_plone_upgrade_already_uptodate(self):
        exitcode, output = self.upgrade_script("plone_upgrade -s plone")
        self.assertEqual(0, exitcode)
        transaction.begin()  # sync transaction
        self.assertIn("Plone Site was already up to date.", output)

    def test_portal_migration_tool_is_wrapped_in_request_container(self):
        portal = self.layer["portal"]
        portal_migration = get_portal_migration(portal)

        self.assertIsInstance(portal_migration.REQUEST, HTTPRequest)
        self.assertIsInstance(aq_chain(portal_migration)[-1], RequestContainer)
