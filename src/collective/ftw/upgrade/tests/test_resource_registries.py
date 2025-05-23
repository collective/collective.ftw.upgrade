from collective.ftw.upgrade.resource_registries import recook_resources
from collective.ftw.upgrade.tests.base import UpgradeTestCase


class TestResourceRegistries(UpgradeTestCase):

    def test_recooking_resources(self):
        with self.assert_resources_recooked():
            recook_resources()
