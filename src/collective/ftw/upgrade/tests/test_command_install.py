from collective.ftw.upgrade import UpgradeStep
from collective.ftw.upgrade.command import jsonapi
from collective.ftw.upgrade.indexing import HAS_INDEXING
from collective.ftw.upgrade.tests.base import CommandAndInstanceTestCase
from collective.ftw.upgrade.tests.helpers import no_logging_threads
from collective.ftw.upgrade.tests.helpers import truncate_memory_and_duration
from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create
from persistent.list import PersistentList
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from unittest import skipIf

import os
import sys
import transaction


class TestInstallCommand(CommandAndInstanceTestCase):

    maxDiff = None

    def setUp(self):
        super().setUp()
        self.write_zconf_with_test_instance()

    def test_help(self):
        self.upgrade_script("install --help")

    def test_install_proposed_upgrades(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step")
                .to(datetime(2011, 1, 1))
                .named("The upgrade")
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            self.clear_recorded_upgrades("the.package:default")

            self.assertFalse(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            exitcode, output = self.upgrade_script("install -s plone --proposed")
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            self.assertIn("Result: SUCCESS", output)

    def test_skip_deferrable_upgrades_if_specified(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 1, 1)).as_deferrable()
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            self.clear_recorded_upgrades("the.package:default")

            self.assertFalse(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            exitcode, output = self.upgrade_script(
                "install -s plone --proposed --skip-deferrable"
            )
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertFalse(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            self.assertIn("Result: SUCCESS", output)

    def test_install_deferrable_upgrades_by_default(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 1, 1)).as_deferrable()
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            self.clear_recorded_upgrades("the.package:default")

            self.assertFalse(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            exitcode, output = self.upgrade_script("install -s plone --proposed")
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            self.assertIn("Result: SUCCESS", output)

    def test_install_failure_raises_exitcode(self):
        def failing_upgrade(setup_context):
            raise KeyError("foo")

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1", to="2")
                .calling(failing_upgrade)
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            with no_logging_threads():
                exitcode, output = self.upgrade_script(
                    "install -s plone --proposed", assert_exitcode=False
                )
            self.assertEqual(3, exitcode)
            self.assertIn("Result: FAILURE", output)

    def test_umlauts_can_be_printed(self):
        """Regression:
        https://github.com/4teamwork/ftw.upgrade/issues/141

        When the terminal's encoding is ascii (LC_ALL=C), printing unicode
        strings will result in an encoding error.
        """

        def upgrade(setup_context):
            import logging

            logging.getLogger("The Upgrade").error("Uml\xc3\xa4ut.")

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step").upgrading("1", to="2").calling(upgrade)
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")

            # The zc.buildout.testing's system implementation does encoding
            # the command result with the default encoding.
            # Since we need to log umlauts in order to proof that it works
            # we need to make the system implementation support utf-8 characters.
            # It's the easiest way to just temporarily change the system encoding.
            system_encoding = sys.getdefaultencoding()
            changed_defaultencoding = False
            try:
                exitcode, output = self.upgrade_script("install -s plone --proposed")
            finally:
                if changed_defaultencoding:
                    sys.setdefaultencoding(system_encoding)

            self.assertEqual(0, exitcode, output)

    def test_install_list_of_upgrades(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step")
                .to(datetime(2011, 1, 1))
                .named("The upgrade")
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            self.clear_recorded_upgrades("the.package:default")

            self.assertFalse(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            exitcode, output = self.upgrade_script(
                "install -s plone --upgrades 20110101000000@the.package:default"
            )
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            self.assertIn("Result: SUCCESS", output)

    def test_install_proposed_upgrades_of_profile(self):
        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(Builder("ftw upgrade step").to(datetime(2011, 1, 1)))
            .with_upgrade(Builder("ftw upgrade step").to(datetime(2011, 2, 2)))
        )

        with self.package_created():
            self.install_profile("the.package:default", version="20110101000000")
            self.clear_recorded_upgrades("the.package:default")
            self.record_installed_upgrades("the.package:default", "20110101000000")

            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            self.assertFalse(
                self.is_installed("the.package:default", datetime(2011, 2, 2))
            )
            exitcode, output = self.upgrade_script(
                "install -s plone --proposed the.package:default"
            )
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 1, 1))
            )
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 2, 2))
            )
            self.assertIn("Result: SUCCESS", output)

    @skipIf(not HAS_INDEXING, "Tests must only run when indexing is available")
    def test_install_proposed_upgrades_of_profile_with_intermediate_commit(self):
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
                .to(
                    datetime(
                        2011,
                        11,
                        11,
                    )
                )
                .calling(TriggerReindex)
            )
            .with_upgrade(Builder("ftw upgrade step").to(datetime(2012, 12, 12)))
        )

        self.setup_logging()
        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.clear_recorded_upgrades("the.package:default")
            exitcode, output = self.upgrade_script(
                "install -s plone --proposed the.package:default "
                "--intermediate-commit"
            )
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 11, 11))
            )
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2012, 12, 12))
            )

            self.assertEqual(
                [
                    "collective.ftw.upgrade: ______________________________________________________________________",
                    "collective.ftw.upgrade: UPGRADE STEP the.package:default: TriggerReindex",
                    "collective.ftw.upgrade: Ran upgrade step TriggerReindex for profile the.package:default",
                    "collective.ftw.upgrade: 1 of 2 (50%): Processing indexing queue",
                    "collective.ftw.upgrade: Transaction has been committed.",
                    "collective.ftw.upgrade: Upgrade step duration: XXX",
                    "collective.ftw.upgrade: Current memory usage in MB (RSS): XXX",
                    "collective.ftw.upgrade: ______________________________________________________________________",
                    "collective.ftw.upgrade: UPGRADE STEP the.package:default: Upgrade.",
                    "collective.ftw.upgrade: Ran upgrade step Upgrade. for profile the.package:default",
                    "collective.ftw.upgrade: Transaction has been committed.",
                    "collective.ftw.upgrade: Upgrade step duration: XXX",
                    "collective.ftw.upgrade: Current memory usage in MB (RSS): XXX",
                    "Result: SUCCESS",
                ],
                truncate_memory_and_duration(output.splitlines()),
            )

    def test_failing_install_proposed_upgrades_of_profile_with_intermediate_commit(
        self,
    ):
        class Upgrade(UpgradeStep):
            def __call__(self):
                raise Exception("failing upgrade")

        self.package.with_profile(
            Builder("genericsetup profile")
            .with_upgrade(Builder("ftw upgrade step").to(datetime(2011, 11, 11)))
            .with_upgrade(
                Builder("ftw upgrade step").to(datetime(2012, 12, 12)).calling(Upgrade)
            )
        )

        self.setup_logging()
        with self.package_created():
            self.install_profile("the.package:default", version="1000")
            self.clear_recorded_upgrades("the.package:default")
            exitcode, output = self.upgrade_script(
                "install -s plone --proposed the.package:default "
                "--intermediate-commit",
                assert_exitcode=False,
            )
            self.assertEqual(3, exitcode)
            transaction.begin()  # sync transaction
            self.assertTrue(
                self.is_installed("the.package:default", datetime(2011, 11, 11))
            )
            self.assertFalse(
                self.is_installed("the.package:default", datetime(2012, 12, 12))
            )

            self.assertEqual(
                [
                    "collective.ftw.upgrade: ______________________________________________________________________",
                    "collective.ftw.upgrade: UPGRADE STEP the.package:default: Upgrade.",
                    "collective.ftw.upgrade: Ran upgrade step Upgrade. for profile the.package:default",
                    "collective.ftw.upgrade: Transaction has been committed.",
                    "collective.ftw.upgrade: Upgrade step duration: XXX",
                    "collective.ftw.upgrade: Current memory usage in MB (RSS): XXX",
                    "collective.ftw.upgrade: ______________________________________________________________________",
                    "collective.ftw.upgrade: UPGRADE STEP the.package:default: Upgrade",
                    "collective.ftw.upgrade: FAILED",
                ],
                truncate_memory_and_duration(output.splitlines()[:9]),
            )
            self.assertEqual(["Result: FAILURE"], output.splitlines()[-1:])

    def test_install_proposed_upgrades_of_profile_fails_for_invalid_profiles(self):
        exitcode, output = self.upgrade_script(
            "install -s plone --proposed the.inexisting.package:default",
            assert_exitcode=False,
        )
        self.assertEqual(1, exitcode)
        self.assertIn("ERROR:", output)

    def test_virtual_host_monster_is_configured_by_environment_variable(self):
        os.environ["UPGRADE_PUBLIC_URL"] = "https://foo.bar.com/baz"
        self.layer["portal"].upgrade_info = PersistentList()

        setRoles(self.layer["portal"], TEST_USER_ID, ["Manager"])
        create(Builder("folder").titled("The Folder"))

        def upgrade_step(setup_context):
            portal = setup_context.portal_url.getPortalObject()
            folder = portal.get("the-folder")
            portal.upgrade_info.append(folder.absolute_url())

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1", to="2")
                .calling(upgrade_step)
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            exitcode, output = self.upgrade_script("install -s plone --proposed")
            self.assertEqual(0, exitcode)
            transaction.begin()  # sync transaction
            self.assertEqual(
                ["https://foo.bar.com/baz/the-folder"],
                self.layer["portal"].upgrade_info,
            )

    def test_install_profiles(self):
        self.package.with_profile(Builder("genericsetup profile"))

        self.setup_logging()
        with self.package_created():
            exitcode, output = self.upgrade_script(
                "install -s plone --profiles the.package:default"
            )
            self.assertEqual(
                [
                    "collective.ftw.upgrade: Installing profile the.package:default.",
                    "collective.ftw.upgrade: Done installing profile the.package:default.",
                    "Result: SUCCESS",
                ],
                output.splitlines(),
            )

    def test_install_profiles_skipped_when_already_installed(self):
        self.setup_logging()
        self.purge_log()
        exitcode, output = self.upgrade_script(
            "install -s plone --profiles collective.ftw.upgrade:default"
        )
        self.assertEqual(
            [
                "collective.ftw.upgrade: Ignoring already installed profile"
                " collective.ftw.upgrade:default.",
                "Result: SUCCESS",
            ],
            output.splitlines(),
        )

    def test_force_install_already_installed_profiles(self):
        self.setup_logging()
        self.purge_log()
        exitcode, output = self.upgrade_script(
            "install -s plone --force --profiles collective.ftw.upgrade:default"
        )
        self.assertEqual(
            [
                "collective.ftw.upgrade: Installing profile collective.ftw.upgrade:default.",
                "collective.ftw.upgrade: Done installing profile collective.ftw.upgrade:default.",
                "Result: SUCCESS",
            ],
            output.splitlines(),
        )

    def test_intermediate_commit_not_supported_with_install_profiles(self):
        self.package.with_profile(Builder("genericsetup profile"))

        self.setup_logging()
        with self.package_created():
            exitcode, output = self.upgrade_script(
                "install -s plone --profiles the.package:default "
                "--intermediate-commit",
                assert_exitcode=False,
            )
            self.assertEqual(3, exitcode)
            self.assertEqual(
                ["ERROR: --intermediate-commit is not implemented for --profiles."],
                output.splitlines(),
            )

    def test_force_option_is_meant_to_be_combined_with_profiles(self):
        exitcode, output = self.upgrade_script(
            "install -s plone --force --upgrades 20110101000000@the.package:default",
            assert_exitcode=False,
        )
        self.assertEqual(3, exitcode)
        self.assertEqual(
            ["ERROR: --force can only be used with --profiles."], output.splitlines()
        )

    def test_instance_argument(self):
        jsonapi.TIMEOUT = 5
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 1, 1))
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="20110101000000")

        exitcode, output = self.upgrade_script(
            "install -s plone --proposed --instance=instance1", assert_exitcode=False
        )

        self.assertEqual(1, exitcode)
        self.assertEqual("ERROR: No running Plone instance detected.\n", output)

        exitcode, output = self.upgrade_script(
            "install -s plone --proposed --instance=instance"
        )
        self.assertEqual("Result: SUCCESS\n", output)
