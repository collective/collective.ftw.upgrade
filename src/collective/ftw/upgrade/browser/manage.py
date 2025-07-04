from AccessControl.SecurityInfo import ClassSecurityInformation
from collective.ftw.upgrade.exceptions import CyclicDependencies
from collective.ftw.upgrade.interfaces import IExecutioner
from collective.ftw.upgrade.interfaces import IUpgradeInformationGatherer
from collective.ftw.upgrade.utils import format_duration
from collective.ftw.upgrade.utils import get_portal_migration
from Products.CMFCore.utils import getToolByName
from zope.component import getAdapter
from zope.publisher.browser import BrowserView

import logging
import time
import traceback


LOG = logging.getLogger("collective.ftw.upgrade")


class ResponseLogger:

    security = ClassSecurityInformation()

    def __init__(self, response, annotate_result=False):
        self.response = response
        self.handler = None
        self.formatter = None
        self.annotate_result = annotate_result

    def __enter__(self):
        self.handler = logging.StreamHandler(self)
        self.formatter = logging.root.handlers[-1].formatter
        self.handler.setFormatter(self.formatter)
        logging.root.addHandler(self.handler)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            LOG.error("FAILED")
            traceback.print_exception(exc_type, exc_value, tb, None, self)
            if self.annotate_result:
                self.write("Result: FAILURE\n")

        elif self.annotate_result:
            self.write("Result: SUCCESS\n")

        logging.root.removeHandler(self.handler)

        # Plone testing does not collect data written to the response stream
        # but only data set directly as body.
        # Since we want to test the response body, we need to re-set the
        # stream data as body for testing..
        if self.response.__class__.__name__ == "TestResponse":
            self.response.setBody(self.response.stdout.getvalue())

    security.declarePrivate("write")

    def write(self, line):
        if isinstance(line, str):
            line = line.encode("utf8")

        line = line.replace(b"<", b"&lt;").replace(b">", b"&gt;")

        self.response.write(line)
        self.response.flush()

    security.declarePrivate("writelines")

    def writelines(self, lines):
        for line in lines:
            self.write(line)


class ManageUpgrades(BrowserView):

    security = ClassSecurityInformation()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cyclic_dependencies = False

    def __call__(self):
        if self.request.get("submitted", False):
            assert (
                not self.plone_needs_upgrading()
            ), "Plone is outdated. Upgrading add-ons is disabled."

            self.install()
        return super().__call__(self)

    security.declarePrivate("install")

    def install(self):
        """Installs the selected upgrades."""
        start = time.time()

        gstool = getToolByName(self.context, "portal_setup")
        executioner = getAdapter(gstool, IExecutioner)
        data = self._get_upgrades_to_install()
        executioner.install(data)

        logging.getLogger("collective.ftw.upgrade").info("FINISHED")

        logging.getLogger("collective.ftw.upgrade").info(
            "Duration for all selected upgrade steps: %s"
            % (format_duration(time.time() - start))
        )

    security.declarePrivate("get_data")

    def get_data(self):
        gstool = getToolByName(self.context, "portal_setup")
        gatherer = getAdapter(gstool, IUpgradeInformationGatherer)
        try:
            return gatherer.get_profiles()
        except CyclicDependencies as exc:
            self.cyclic_dependencies = exc.cyclic_dependencies
            return []

    security.declarePrivate("plone_needs_upgrading")

    def plone_needs_upgrading(self):
        portal_migration = get_portal_migration(self.context)
        return portal_migration.needUpgrading()

    security.declarePrivate("_get_upgrades_to_install")

    def _get_upgrades_to_install(self):
        """Returns a dict where the key is a profileid and the value
        is a list of upgrade ids.
        """

        data = {}
        for item in self.request.get("upgrade", []):
            item = dict(item)
            profileid = item["profileid"]
            del item["profileid"]

            if item:
                data[profileid] = item.keys()

        upgrades = []

        for profile in self.get_data():
            if profile.get("id") not in data:
                continue

            profile_data = data[profile.get("id")]
            if not profile.get("upgrades", []):
                continue

            profile_upgrades = []
            upgrades.append((profile.get("id"), profile_upgrades))

            for upgrade in profile.get("upgrades", []):
                if upgrade.get("id") in profile_data:
                    profile_upgrades.append(upgrade.get("id"))

        return upgrades


class ManageUpgradesPlain(ManageUpgrades):

    def __getitem__(self, key):
        return self.index.macros[key]

    def __call__(self):
        self.request.response.setHeader("X-Theme-Disabled", "true")
        return super().__call__()
