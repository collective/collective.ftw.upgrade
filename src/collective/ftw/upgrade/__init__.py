# pylint: disable=W0104
# W0104: Statement seems to have no effect

__version__ = "4.0.0a7.dev0"


from collective.ftw.upgrade.progresslogger import ProgressLogger
from collective.ftw.upgrade.step import UpgradeStep


try:
    import ftw.upgrade.interfaces

    del ftw.upgrade.interfaces
except ImportError:
    from .bbb import interfaces
    from plone.app.upgrade.utils import alias_module

    alias_module("ftw.upgrade.interfaces", interfaces)
    del interfaces
    del alias_module


UpgradeStep

ProgressLogger
