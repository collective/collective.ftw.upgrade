from collective.ftw.upgrade import UpgradeStep
from Products.CMFPlone.interfaces import IMigratingPloneSiteRoot
from Products.GenericSetup.interfaces import EXTENSION
from Products.GenericSetup.zcml import registerProfile
from Products.GenericSetup.zcml import upgradeStep
from zope.configuration.fields import GlobalObject
from zope.configuration.fields import Path
from zope.interface import Interface

import zope.schema


class IImportProfileUpgradeStep(Interface):
    """Register an upgrade step which imports a generic setup profile
    specific to this upgrade step.
    """

    title = zope.schema.TextLine(
        title="Title",
        required=True)

    description = zope.schema.TextLine(
        title="Upgrade step description",
        required=False)

    profile = zope.schema.TextLine(
        title="GenericSetup profile id",
        required=True)

    source = zope.schema.ASCII(
        title="Source version",
        required=True)

    destination = zope.schema.ASCII(
        title="Destination version",
        required=True)

    directory = Path(
        title='Path',
        required=True)

    handler = GlobalObject(
        title='Handler',
        required=False)


class DefaultUpgradeStep(UpgradeStep):
    def __call__(self):
        self.install_upgrade_profile()


def importProfileUpgradeStep(_context, title, profile, source, destination,
                             directory, description=None, handler=None):
    profile_id = "upgrade_to_%s" % destination
    registerProfile(_context, name=profile_id, title=title,
                    description=description, directory=directory,
                    provides=EXTENSION, for_=IMigratingPloneSiteRoot)

    if handler is None:
        handler = DefaultUpgradeStep

    profileid = f'profile-{_context.package.__name__}:{profile_id}'
    def handler_wrapper(portal_setup):
        return handler(portal_setup, profileid)

    upgradeStep(_context, title=title, profile=profile,
                handler=handler_wrapper, description=description,
                source=source, destination=destination)
