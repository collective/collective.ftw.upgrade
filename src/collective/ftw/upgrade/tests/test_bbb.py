from collective.ftw.upgrade.bbb.interfaces import IUpgradeLayer
from unittest import TestCase

import importlib


class TestBbbAlias(TestCase):

    def test_legacy_interfaces_import_is_aliased(self):
        module = importlib.import_module("ftw.upgrade.interfaces")

        self.assertTrue(hasattr(module, "IUpgradeLayer"))
        self.assertIs(IUpgradeLayer, module.IUpgradeLayer)
