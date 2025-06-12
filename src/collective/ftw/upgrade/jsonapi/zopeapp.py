from AccessControl import getSecurityManager
from collective.ftw.upgrade.jsonapi.base import APIView
from collective.ftw.upgrade.jsonapi.utils import action
from collective.ftw.upgrade.jsonapi.utils import jsonify


class ZopeAppAPI(APIView):

    @jsonify
    @action("GET")
    def list_plone_sites(self):
        """Returns a list of Plone sites."""
        return list(self._get_plone_sites())

    @jsonify
    @action("GET")
    def current_user(self):
        """Return the current user when authenticated properly.
        This can be used for testing authentication.
        """
        return getSecurityManager().getUser().getId()

    @property
    def sites(self):
        """Return all Plone sites in the Zope app."""
        try:
            from plone.distribution.api.site import get_sites
        except ImportError:
            get_sites = None

        if get_sites:
            return get_sites(self.context)

        # Fallback for Plone installations that do not have plone.distribution
        return self.context.restrictedTraverse("plone-overview").sites()

    def _get_plone_sites(self):
        for site in self.sites:
            yield {
                "id": site.getId(),
                "path": "/".join(site.getPhysicalPath()),
                "title": site.Title(),
            }
