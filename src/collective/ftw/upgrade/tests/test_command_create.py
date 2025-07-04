from collective.ftw.upgrade.tests.base import CommandTestCase
from ftw.builder import Builder
from ftw.builder import create


class TestCreateCommand(CommandTestCase):

    def test_creating_an_upgrade_step(self):
        package = create(
            Builder("python package")
            .named("the.package")
            .at_path(self.layer.sample_buildout)
            .with_directory("upgrades")
        )

        self.upgrade_script("create AddControlpanelAction")

        upgrades_dir = package.package_path.joinpath("upgrades")
        self.assertEqual(
            1,
            len(upgrades_dir.dirs()),
            "Expected exactly one directory to be generated, got {}".format(
                upgrades_dir.dirs()
            ),
        )

        (step_path,) = upgrades_dir.dirs()
        self.assertRegex(step_path.name, r"^\d{14}_add_controlpanel_action$")

        code_path = step_path.joinpath("upgrade.py")
        self.assertTrue(code_path.exists(), "upgrade.py is missing")
        self.assertTrue(
            step_path.joinpath("__init__.py").exists(),
            "There is no __init__.py in the upgrade directory."
            " It is important so that plone.reload works.",
        )
        self.maxDiff = True
        self.assertIn(
            "class AddControlpanelAction(UpgradeStep):", code_path.read_text()
        )

    def test_creating_an_upgrade_step_with_specifying_upgrades_directory(self):
        package = create(
            Builder("python package")
            .named("the.package")
            .at_path(self.layer.sample_buildout)
            .with_directory("upgrades")
            .with_directory("subpackage/upgrades")
        )

        upgrades_dir = package.package_path.joinpath("upgrades")
        subpackage_upgrades_dir = package.package_path.joinpath(
            "subpackage", "upgrades"
        )
        self.upgrade_script(
            f"create AddControlpanelAction --path {subpackage_upgrades_dir}"
        )

        self.assertEqual(
            0,
            len(upgrades_dir.dirs()),
            "Expected default upgrades directory to be empty; {}".format(
                upgrades_dir.dirs()
            ),
        )

        self.assertEqual(
            1,
            len(subpackage_upgrades_dir.dirs()),
            "Expected subpackage upgrades directory to have one upgrade; {}".format(
                subpackage_upgrades_dir.dirs()
            ),
        )

    def test_creating_an_upgrade_step_with_text_containing_dots(self):
        package = create(
            Builder("python package")
            .named("the.package")
            .at_path(self.layer.sample_buildout)
            .with_directory("upgrades")
        )

        self.upgrade_script('create "Update ftw.upgrade to version 3."')

        upgrades_dir = package.package_path.joinpath("upgrades")
        (step_path,) = upgrades_dir.dirs()
        self.assertRegex(step_path.name, r"^\d{14}_update_ftw_upgrade_to_version_3$")

        code_path = step_path.joinpath("upgrade.py")
        self.assertTrue(code_path.exists(), "upgrade.py is missing")
        self.maxDiff = True
        self.assertIn(
            "class UpdateFtwUpgradeToVersion3(UpgradeStep):", code_path.read_text()
        )
        self.assertIn(
            """Update ftw.upgrade to version 3.\n    """, code_path.read_text()
        )

    def test_fails_when_no_egginfo_found(self):
        exitcode, output = self.upgrade_script("create Title", assert_exitcode=False)
        self.assertEqual(
            1, exitcode, "command should fail because there is no egg-info"
        )
        self.assertIn("WARNING: no *.egg-info directory could be found.", output)
        self.assertIn(
            "ERROR: Please provide the path to the upgrades directory with --path.",
            output,
        )

    def test_fails_when_no_upgrades_directory_found(self):
        create(
            Builder("python package")
            .named("the.package")
            .at_path(self.layer.sample_buildout)
        )

        exitcode, output = self.upgrade_script("create Title", assert_exitcode=False)
        self.assertEqual(
            1, exitcode, "command should fail because there is no upgrades directory"
        )
        self.assertIn('WARNING: no "upgrades" directory could be found.', output)
        self.assertIn(
            "ERROR: Please provide the path to the upgrades directory with --path.",
            output,
        )
