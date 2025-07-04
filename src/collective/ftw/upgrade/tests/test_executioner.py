from collective.ftw.upgrade import UpgradeStep
from collective.ftw.upgrade.executioner import Executioner
from collective.ftw.upgrade.indexing import HAS_INDEXING
from collective.ftw.upgrade.interfaces import IExecutioner
from collective.ftw.upgrade.tests.base import UpgradeTestCase
from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from Products.CMFCore.utils import getToolByName
from unittest import skipIf
from zope.component import queryAdapter
from zope.interface.verify import verifyClass

import transaction


class TestExecutioner(UpgradeTestCase):

    maxDiff = None

    def test_component_is_registered(self):
        setup_tool = getToolByName(self.layer["portal"], "portal_setup")
        executioner = queryAdapter(setup_tool, IExecutioner)
        self.assertNotEqual(None, executioner)

    def test_implements_interface(self):
        verifyClass(IExecutioner, Executioner)

    def test_installs_upgrades(self):
        def upgrade(setup_context):
            portal = setup_context.portal_url.getPortalObject()
            portal.upgrade_step_executed = True

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1000", to="1002")
                .calling(upgrade)
            )
        )

        self.portal.upgrade_step_executed = False
        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.assertFalse(self.portal.upgrade_step_executed)
            self.install_profile_upgrades("the.package:default")
            self.assertTrue(self.portal.upgrade_step_executed)

    def test_install_upgrades_by_api_ids(self):
        def upgrade(setup_context):
            portal = setup_context.portal_url.getPortalObject()
            portal.upgrade_step_executed = True

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1000", to="1002")
                .calling(upgrade)
            )
        )

        self.portal.upgrade_step_executed = False
        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.assertFalse(self.portal.upgrade_step_executed)
            executioner = queryAdapter(self.portal_setup, IExecutioner)
            executioner.install_upgrades_by_api_ids("1002@the.package:default")
            self.assertTrue(self.portal.upgrade_step_executed)

    def test_transaction_note(self):
        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1000", to="1001")
                .titled('Register "foo" utility')
            )
            .with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1001", to="1002")
                .titled("Update email address")
            )
            .with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1002", to="1003")
                .titled("Update email from name")
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.install_profile_upgrades("the.package:default")
            self.assertMultiLineEqual(
                'the.package:default -> 1001 (Register "foo" utility)\n'
                "the.package:default -> 1002 (Update email address)\n"
                "the.package:default -> 1003 (Update email from name)",
                transaction.get().description,
            )

    def test_after_commit_hook(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1000", to="1001")
                .titled('Register "foo" utility')
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.install_profile_upgrades("the.package:default")

            hooks = list(transaction.get().getAfterCommitHooks())
            hook_funcs = [h[0] for h in hooks]

            self.assertIn(
                "notification_hook",
                [f.__name__ for f in hook_funcs],
                "Our notification_hook should be registered",
            )

            transaction.commit()
            self.assertEqual(
                [],
                list(transaction.get().getAfterCommitHooks()),
                "Hook registrations should not persist across transactions",
            )

    def test_install_profiles_by_profile_ids(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step").upgrading("1000", to="1001")
            )
        )

        self.setup_logging()
        profile_id = "the.package:default"
        with self.package_created():
            executioner = queryAdapter(self.portal_setup, IExecutioner)
            executioner.install_profiles_by_profile_ids(profile_id)
            self.assertEqual(
                [
                    "Installing profile the.package:default.",
                    "Done installing profile the.package:default.",
                ],
                self.get_log(),
            )

            self.purge_log()
            executioner.install_profiles_by_profile_ids(profile_id)
            self.assertEqual(
                ["Ignoring already installed profile the.package:default."],
                self.get_log(),
            )

            self.purge_log()
            executioner.install_profiles_by_profile_ids(
                profile_id, force_reinstall=True
            )
            self.assertEqual(
                [
                    "Installing profile the.package:default.",
                    "Done installing profile the.package:default.",
                ],
                self.get_log(),
            )

    def test_do_not_decrease_version_when_only_installing_orphan_steps(self):
        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 11, 11, 11, 11))
            )
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2012, 12, 12, 12, 12))
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", "20121212121200")
            self.clear_recorded_upgrades("the.package:default")
            self.record_installed_upgrades("the.package:default", "20121212121200")
            self.assert_gathered_upgrades(
                {
                    "the.package:default": {
                        "done": ["20121212121200"],
                        "proposed": ["20111111111100"],
                        "orphan": ["20111111111100"],
                    }
                }
            )
            self.assertEqual(
                ("20121212121200",),
                self.portal_setup.getLastVersionForProfile("the.package:default"),
            )

            executioner = queryAdapter(self.portal_setup, IExecutioner)
            executioner.install_upgrades_by_api_ids(
                "20111111111100@the.package:default"
            )
            self.assertEqual(
                ("20121212121200",),
                self.portal_setup.getLastVersionForProfile("the.package:default"),
            )
            self.assert_gathered_upgrades(
                {
                    "the.package:default": {
                        "done": ["20111111111100", "20121212121200"],
                        "proposed": [],
                        "orphan": [],
                    }
                }
            )

    @skipIf(not HAS_INDEXING, "Tests must only run when indexing is available")
    def test_logs_indexing_progress_of_final_reindex(self):
        self.grant("Manager")
        create(Builder("folder"))
        create(Builder("folder"))

        class TriggerReindex(UpgradeStep):
            def __call__(self):
                catalog = self.getToolByName("portal_catalog")
                for brain in catalog(portal_type="Folder"):
                    brain.getObject().reindexObject()

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step")
                .to(datetime(2013, 1, 1))
                .calling(TriggerReindex)
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.setup_logging()

            self.install_profile_upgrades("the.package:default")
            self.assertEqual(
                "1 of 2 (50%): Processing indexing queue", self.get_log()[-1]
            )

    def test_regression_switching_versioning_system(self):
        # test_do_not_decrease_version_when_only_installing_orphan_steps
        # caused an issue when switching to upgrade step directories,
        # since the versioning system changed and '4' > '2016' but 4 < 2016.

        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(Builder("plone upgrade step").upgrading("4000", to="4002"))
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 11, 11, 11, 11))
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", "4002")
            self.clear_recorded_upgrades("the.package:default")
            self.assert_gathered_upgrades(
                {
                    "the.package:default": {
                        "done": ["4002"],
                        "proposed": ["20111111111100"],
                        "orphan": [],
                    }
                }
            )
            self.assertEqual(
                ("4002",),
                self.portal_setup.getLastVersionForProfile("the.package:default"),
            )

            executioner = queryAdapter(self.portal_setup, IExecutioner)
            executioner.install_upgrades_by_api_ids(
                "20111111111100@the.package:default"
            )
            self.assertEqual(
                ("20111111111100",),
                self.portal_setup.getLastVersionForProfile("the.package:default"),
            )
            self.assert_gathered_upgrades(
                {
                    "the.package:default": {
                        "done": ["4002", "20111111111100"],
                        "proposed": [],
                        "orphan": [],
                    }
                }
            )

    def test_installs_upgrades_with_intermediate_commit(self):
        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 11, 11, 11, 11))
            )
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2012, 12, 12, 12, 12))
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.install_profile_upgrades(
                "the.package:default", intermediate_commit=True
            )

        self.assertEqual(
            ("20121212121200",),
            self.portal_setup.getLastVersionForProfile("the.package:default"),
        )

    @skipIf(not HAS_INDEXING, "Tests must only run when indexing is available")
    def test_logs_indexing_progress_of_intermediate_reindex(self):
        self.grant("Manager")
        create(Builder("folder"))
        create(Builder("folder"))

        class TriggerReindex(UpgradeStep):
            def __call__(self):
                catalog = self.getToolByName("portal_catalog")
                for brain in catalog(portal_type="Folder"):
                    brain.getObject().reindexObject()

        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(
                Builder("ftw upgrade step")
                .to(datetime(2011, 11, 11, 11, 11))
                .calling(TriggerReindex)
            )
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2012, 12, 12, 12, 12))
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.setup_logging()

            self.install_profile_upgrades(
                "the.package:default", intermediate_commit=True
            )
            self.assertEqual(
                [
                    "______________________________________________________________________",
                    "UPGRADE STEP the.package:default: TriggerReindex",
                    "Ran upgrade step TriggerReindex for profile the.package:default",
                    "1 of 2 (50%): Processing indexing queue",
                    "Transaction has been committed.",
                    "Upgrade step duration: XXX",
                    "Current memory usage in MB (RSS): XXX",
                    "______________________________________________________________________",
                    "UPGRADE STEP the.package:default: Upgrade.",
                    "Ran upgrade step Upgrade. for profile the.package:default",
                    "Transaction has been committed.",
                    "Upgrade step duration: XXX",
                    "Current memory usage in MB (RSS): XXX",
                ],
                self.get_log(),
            )

    def test_installed_version_if_upgrade_fails_with_intermediate_commit(self):
        class Upgrade(UpgradeStep):
            def __call__(self):
                raise Exception("failing upgrade")

        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 11, 11, 11, 11))
            )
            .with_upgrade(
                Builder("ftw upgrade step")
                .to(datetime(2012, 12, 12, 12, 12))
                .calling(Upgrade)
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            with self.assertRaises(Exception):
                self.install_profile_upgrades(
                    "the.package:default", intermediate_commit=True
                )

        self.assertEqual(
            ("20111111111100",),
            self.portal_setup.getLastVersionForProfile("the.package:default"),
        )
