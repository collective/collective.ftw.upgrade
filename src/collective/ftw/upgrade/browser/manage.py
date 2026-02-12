from AccessControl.SecurityInfo import ClassSecurityInformation
from collective.ftw.upgrade.exceptions import CyclicDependencies
from collective.ftw.upgrade.interfaces import IExecutioner
from collective.ftw.upgrade.interfaces import IUpgradeInformationGatherer
from collective.ftw.upgrade.utils import format_duration
from collective.ftw.upgrade.utils import get_portal_migration
from io import StringIO
from Products.CMFCore.utils import getToolByName
from zope.component import getAdapter
from zope.publisher.browser import BrowserView

import logging
import time
import traceback


LOG = logging.getLogger("collective.ftw.upgrade")


class ResponseLogger:

    security = ClassSecurityInformation()

    def __init__(self, annotate_result=False):
        self.buffer = StringIO()
        self.handler = None
        self.formatter = None
        self.annotate_result = annotate_result

    def __enter__(self):
        self.handler = logging.StreamHandler(self.buffer)
        self.formatter = logging.root.handlers[-1].formatter
        self.handler.setFormatter(self.formatter)
        logging.root.addHandler(self.handler)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            LOG.error("FAILED")
            traceback.print_exception(exc_type, exc_value, tb, None, self.buffer)
            if self.annotate_result:
                self.buffer.write("Result: FAILURE\n")

        elif self.annotate_result:
            self.buffer.write("Result: SUCCESS\n")

        logging.root.removeHandler(self.handler)

    def get_output(self):
        return self.buffer.getvalue()


class ManageUpgrades(BrowserView):

    security = ClassSecurityInformation()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cyclic_dependencies = False

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


class ManageUpgradesPlain(ManageUpgrades):

    def __getitem__(self, key):
        return self.index.macros[key]

    def __call__(self):
        self.request.response.setHeader("X-Theme-Disabled", "true")
        return super().__call__()


class ExecuteUpgradesView(ManageUpgrades):

    security = ClassSecurityInformation()

    def __call__(self):
        self.request.response.setHeader("Content-Type", "text/plain; charset=utf-8")
        self.request.response.setHeader("X-Theme-Disabled", "true")

        assert (
            not self.plone_needs_upgrading()
        ), "Plone is outdated. Upgrading add-ons is disabled."

        return self._execute_upgrades()

    security.declarePrivate("_execute_upgrades")

    def _execute_upgrades(self):
        start = time.time()

        with ResponseLogger(annotate_result=True) as logger:
            gstool = getToolByName(self.context, "portal_setup")
            executioner = getAdapter(gstool, IExecutioner)
            data = self._get_upgrades_to_install()
            executioner.install(data)

            LOG.info("FINISHED")
            LOG.info(
                "Duration for all selected upgrade steps: %s"
                % (format_duration(time.time() - start))
            )

        return logger.get_output()

    security.declarePrivate("_get_upgrades_to_install")

    def _get_upgrades_to_install(self):
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
