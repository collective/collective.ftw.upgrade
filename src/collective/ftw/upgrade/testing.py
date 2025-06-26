from collective.ftw.upgrade.tests.layers import COMPONENT_REGISTRY_ISOLATION
from collective.ftw.upgrade.tests.layers import ConsoleScriptLayer
from collective.ftw.upgrade.tests.layers import TEMP_DIRECTORY
from ftw.builder.testing import BUILDER_LAYER
from ftw.builder.testing import functional_session_factory
from ftw.builder.testing import set_builder_session_factory
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_ZSERVER
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from Products.SiteAccess.VirtualHostMonster import manage_addVirtualHostMonster
from zope.configuration import xmlconfig

import collective.ftw.upgrade.tests.builders


collective.ftw.upgrade.tests.builders  # pyflakes


COMMAND_LAYER = ConsoleScriptLayer(
    "collective.ftw.upgrade",
    extras=("test",),
    bases=(BUILDER_LAYER,),
    name="ftw.upgrade:command",
)


class UpgradeLayer(PloneSandboxLayer):
    defaultBases = (COMPONENT_REGISTRY_ISOLATION, BUILDER_LAYER, TEMP_DIRECTORY)

    def setUpZope(self, app, configurationContext):
        import Products.CMFPlacefulWorkflow

        xmlconfig.file(
            "configure.zcml", Products.CMFPlacefulWorkflow, context=configurationContext
        )

        import collective.ftw.upgrade

        xmlconfig.file(
            "configure.zcml", collective.ftw.upgrade, context=configurationContext
        )

        z2.installProduct(app, "Products.DateRecurringIndex")
        import plone.app.contenttypes

        xmlconfig.file(
            "configure.zcml", plone.app.contenttypes, context=configurationContext
        )

        z2.installProduct(app, "Products.CMFPlacefulWorkflow")

        manage_addVirtualHostMonster(app, "virtual_hosting")

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.app.contenttypes:default")
        applyProfile(portal, "Products.CMFPlacefulWorkflow:CMFPlacefulWorkflow")
        applyProfile(portal, "collective.ftw.upgrade:default")


UPGRADE_LAYER = UpgradeLayer()
UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(
        PLONE_ZSERVER,
        UPGRADE_LAYER,
        set_builder_session_factory(functional_session_factory),
    ),
    name="ftw.upgrade:functional",
)

COMMAND_AND_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(
        PLONE_ZSERVER,
        UPGRADE_LAYER,
        set_builder_session_factory(functional_session_factory),
        COMMAND_LAYER,
    ),
    name="ftw.upgrade:command_and_functional",
)


class IntIdUpgradeLayer(PloneSandboxLayer):

    defaultBases = (UPGRADE_LAYER,)

    def setUpZope(self, app, configurationContext):
        import plone.app.intid

        xmlconfig.file("configure.zcml", plone.app.intid, context=configurationContext)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.app.intid:default")


INTID_UPGRADE_LAYER = IntIdUpgradeLayer()
INTID_UPGRADE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(
        INTID_UPGRADE_LAYER,
        set_builder_session_factory(functional_session_factory),
    ),
    name="ftw.upgrade-intid:functional",
)
