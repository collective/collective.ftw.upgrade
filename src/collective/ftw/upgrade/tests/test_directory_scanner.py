from collective.ftw.upgrade.directory.scanner import Scanner
from collective.ftw.upgrade.exceptions import UpgradeStepDefinitionError
from collective.ftw.upgrade.tests.base import UpgradeTestCase
from contextlib import contextmanager
from datetime import datetime
from ftw.builder import Builder
from ftw.builder import create


class TestDirectoryScanner(UpgradeTestCase):

    def setUp(self):
        super().setUp()
        self.profile = Builder("genericsetup profile")
        self.package.with_profile(self.profile)

    def test_returns_chained_upgrade_infos(self):
        self.profile.with_upgrade(
            Builder("ftw upgrade step")
            .to(datetime(2011, 1, 1, 8))
            .named("add an action")
        )
        self.profile.with_upgrade(
            Builder("ftw upgrade step")
            .to(datetime(2011, 2, 2, 8))
            .named("update the action")
        )
        self.profile.with_upgrade(
            Builder("ftw upgrade step")
            .to(datetime(2011, 3, 3, 8))
            .named("remove the action")
        )

        with self.scanned() as upgrade_infos:
            list(
                map(
                    lambda info: (
                        info.__delitem__("path"),
                        info.__delitem__("callable"),
                    ),
                    upgrade_infos,
                )
            )

            self.maxDiff = None
            self.assertEqual(
                [
                    {
                        "source-version": None,
                        "target-version": "20110101080000",
                        "title": "Add an action.",
                    },
                    {
                        "source-version": "20110101080000",
                        "target-version": "20110202080000",
                        "title": "Update the action.",
                    },
                    {
                        "source-version": "20110202080000",
                        "target-version": "20110303080000",
                        "title": "Remove the action.",
                    },
                ],
                upgrade_infos,
            )

    def test_exception_raised_when_upgrade_has_no_code(self):
        self.profile.with_upgrade(
            Builder("ftw upgrade step")
            .to(datetime(2011, 1, 1, 8))
            .named("add action")
            .with_code("")
        )

        with create(self.package) as package:
            with self.assertRaises(UpgradeStepDefinitionError) as cm:
                self.scan(package)
        self.assertRegex(
            str(cm.exception),
            "The upgrade step file (.*)upgrade.py has no upgrade class.",  # noqa: E501
        )

    def test_exception_raised_when_multiple_upgrade_steps_detected(self):
        code = "\n".join(
            (
                "from collective.ftw.upgrade import UpgradeStep",
                "class Foo(UpgradeStep): pass",
                "class Bar(UpgradeStep): pass",
            )
        )

        self.profile.with_upgrade(
            Builder("ftw upgrade step")
            .to(datetime(2011, 1, 1, 8))
            .named("add action")
            .with_code(code)
        )

        with create(self.package) as package:
            with self.assertRaises(UpgradeStepDefinitionError) as cm:
                self.scan(package)
        self.assertRegex(
            str(cm.exception),
            "The upgrade step file (.*)upgrade.py has more than one upgrade class.",  # noqa: E501
        )

    def test_does_not_fail_when_no_upgrades_present(self):
        self.package.with_zcml_include("collective.ftw.upgrade", file="meta.zcml")
        self.package.with_zcml_node(
            "upgrade-step:directory", profile="the.package:default", directory="."
        )

        with self.scanned() as upgrade_infos:
            self.assertEqual([], upgrade_infos)

    @contextmanager
    def scanned(self):
        with create(self.package) as package:
            yield self.scan(package)

    def scan(self, package):
        upgrades = package.package_path.joinpath("upgrades")
        return Scanner("the.package.upgrades", upgrades).scan()
