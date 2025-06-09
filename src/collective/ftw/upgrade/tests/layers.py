from plone.app.testing import PLONE_FIXTURE
from plone.testing import Layer
from plone.testing import zca
from zope.configuration import xmlconfig


class ComponentRegistryIsolationLayer(Layer):
    defaultBases = (PLONE_FIXTURE, )

    def setUp(self):
        self['load_zcml_string'] = self.load_zcml_string

    def testSetUp(self):
        self['configurationContext'] = zca.stackConfigurationContext(
            self.get('configurationContext'),
            name='collective.ftw.upgrade.component_registry_isolation')
        zca.pushGlobalRegistry()

    def testTearDown(self):
        del self['configurationContext']
        zca.popGlobalRegistry()

    def load_zcml_string(self, *zcml_lines):
        zcml = '\n'.join(zcml_lines)
        xmlconfig.string(zcml, context=self['configurationContext'])

    def load_zcml_file(self, filename, module):
        xmlconfig.file(filename, module,
                       context=self['configurationContext'])


COMPONENT_REGISTRY_ISOLATION = ComponentRegistryIsolationLayer()
