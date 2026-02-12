from collective.ftw.upgrade.browser.manage import ResponseLogger
from collective.ftw.upgrade.tests.base import JsonApiTestCase
from datetime import datetime
from ftw.builder import Builder
from Products.CMFCore.utils import getToolByName
from unittest import TestCase

import logging
import re
import transaction


class TestResponseLogger(TestCase):

    def test_logging(self):
        with ResponseLogger() as logger:
            logging.error("foo")
            logging.error("bar")

        output = logger.get_output().strip()
        self.assertEqual(["foo", "bar"], output.split("\n"))

    def test_logging_exceptions(self):
        with self.assertRaises(KeyError):
            with ResponseLogger() as logger:
                raise KeyError("foo")

        output = logger.get_output().strip()
        output = re.sub(r'(File ").*(ftw/upgrade/.*")', r"\1/.../\2", output)
        output = re.sub(r"(line )\d*", r"line XX", output)

        self.assertEqual(
            [
                "FAILED",
                "Traceback (most recent call last):",
                '  File "/.../ftw/upgrade/tests/'
                'test_manage_view.py", line XX, in test_logging_exceptions',
                '    raise KeyError("foo")',
                "KeyError: 'foo'",
            ],
            output.split("\n"),
        )

    def test_annotate_result_on_success(self):
        with ResponseLogger(annotate_result=True) as logger:
            logging.error("foo")
            logging.error("bar")

        output = logger.get_output().strip()
        self.assertEqual(["foo", "bar", "Result: SUCCESS"], output.split("\n"))

    def test_annotate_result_on_error(self):
        with self.assertRaises(KeyError):
            with ResponseLogger(annotate_result=True) as logger:
                raise KeyError("foo")

        output = logger.get_output().strip()
        output = re.sub(r'(File ").*(ftw/upgrade/.*")', r"\1/.../\2", output)
        output = re.sub(r"(line )\d*", r"line XX", output)
        self.assertEqual(
            [
                "FAILED",
                "Traceback (most recent call last):",
                '  File "/.../ftw/upgrade/tests/'
                'test_manage_view.py", line XX, in test_annotate_result_on_error',
                '    raise KeyError("foo")',
                "KeyError: 'foo'",
                "Result: FAILURE",
            ],
            output.split("\n"),
        )

    def test_get_output_returns_string(self):
        with ResponseLogger() as logger:
            logging.error("test message")

        output = logger.get_output()
        self.assertIsInstance(output, str)
        self.assertIn("test message", output)


class TestManageUpgrades(JsonApiTestCase):

    def setUp(self):
        super().setUp()
        self.portal_url = self.layer["portal"].portal_url()
        self.portal = self.layer["portal"]

    def assertEqualURL(self, first, second, msg=None):
        # WebOb generates requests that always contain the port even for the
        # default port 80.
        return self.assertEqual(
            first.replace(":80", ""), second.replace(":80", ""), msg
        )

    def test_registered_in_controlpanel(self):
        response = self.html_request("GET", "overview-controlpanel")
        link = self.find_content(response.content, '[href$="@@manage-upgrades"]')
        self.assertEqualURL(self.portal_url + "/@@manage-upgrades", link.attrs["href"])

    def test_manage_view_renders(self):
        response = self.html_request("GET", "manage-upgrades")
        up_link = self.find_content(response.content, ".link-parent")
        self.assertEqualURL(
            self.portal_url + "/@@overview-controlpanel", up_link.attrs["href"]
        )

        self.assertTrue(
            self.find_content(
                response.content, 'input[value="plone.app.event:default"]'
            )
        )

    def test_manage_view_has_spinner_container(self):
        response = self.html_request("GET", "manage-upgrades")
        self.assertIsNotNone(self.find_content(response.content, "#upgrade-progress"))

    def test_manage_view_has_log_output_container(self):
        response = self.html_request("GET", "manage-upgrades")
        self.assertIsNotNone(self.find_content(response.content, "#upgrade-log"))

    def test_manage_view_form_targets_execute_endpoint(self):
        response = self.html_request("GET", "manage-upgrades")
        form = self.find_content(response.content, "#upgrade-form")
        self.assertIn("@@upgrade-execute", form.attrs["action"])
        self.assertNotIn("target", form.attrs)

    def test_manage_plain_view_renders(self):
        response = self.html_request("GET", "manage-upgrades-plain")
        self.assertTrue(
            self.find_content(
                response.content, 'input[value="plone.app.event:default"]'
            )
        )

    def test_manage_view_pre_selects_deferrable_upgrades(self):
        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("ftw upgrade step").to(datetime(2011, 1, 1)).as_deferrable()
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", version="1")
            self.clear_recorded_upgrades("the.package:default")
            transaction.commit()

            transaction.begin()  # sync transaction
            response = self.html_request("GET", "manage-upgrades")
            deferrable_upgrade_checkbox = self.find_content(
                response.content, 'input[id|="the.package:default"]'
            )
            self.assertEqual("checked", deferrable_upgrade_checkbox.attrs["checked"])

    def test_install(self):
        def upgrade_step(setup_context):
            portal = getToolByName(setup_context, "portal_url").getPortalObject()
            portal.upgrade_installed = True

        self.package.with_profile(
            Builder("genericsetup profile").with_upgrade(
                Builder("plone upgrade step")
                .upgrading("1111", "2222")
                .calling(upgrade_step, getToolByName)
            )
        )

        with self.package_created():
            self.install_profile("the.package:default", "1111")
            self.portal.upgrade_installed = False
            transaction.commit()

            transaction.begin()  # sync transaction
            self.assertFalse(self.portal.upgrade_installed)

            response = self.html_request("GET", "manage-upgrades")
            action = self.find_content(response.content, "#upgrade-form").attrs[
                "action"
            ]
            input_elements = self.find_content(
                response.content, "input:checked", "select"
            )
            data = {element.attrs["name"]: "on" for element in input_elements}
            data["submitted"] = "Install"
            data["upgrade.profileid:records"] = "the.package:default"
            data["_authenticator"] = self.find_content(
                response.content, '[name="_authenticator"]'
            ).attrs["value"]
            response = self.html_request("POST", action, data=data)

            self.assertIn("Result: SUCCESS", response.text)
            self.assertIn("FINISHED", response.text)

            transaction.begin()  # sync transaction
            self.assertTrue(self.portal.upgrade_installed)

    def test_upgrades_view_shows_cyclic_dependencies_error(self):
        self.package.with_profile(
            Builder("genericsetup profile")
            .named("foo")
            .with_dependencies("the.package:bar")
        )
        self.package.with_profile(
            Builder("genericsetup profile")
            .named("bar")
            .with_dependencies("the.package:foo")
        )

        with self.package_created():
            self.install_profile("the.package:foo")
            self.install_profile("the.package:bar")
            transaction.commit()

            response = self.html_request("GET", "manage-upgrades")
            self.assertEqual(
                "Cyclic dependencies\nThere are cyclic dependencies. The profiles could not be sorted by dependencies!",
                self.find_content(response.content, ".portalMessage").text.strip(),
            )

            possibilities = (
                ["the.package:foo", "the.package:bar"],
                ["the.package:bar", "the.package:foo"],
            )

            dep = self.find_content(response.content, ".cyclic-dependencies li").text
            self.assertIn(re.findall(r"the\.package:\w+", dep), possibilities)
