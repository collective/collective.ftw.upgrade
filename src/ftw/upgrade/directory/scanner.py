from ftw.upgrade import UpgradeStep
from ftw.upgrade.exceptions import UpgradeStepDefinitionError
from ftw.upgrade.utils import subject_from_docstring
from functools import reduce
from glob import glob
from plone.base.utils import safe_text
from Products.GenericSetup.upgrade import normalize_version

import importlib
import inspect
import os.path
import re


UPGRADESTEP_DATETIME_REGEX = re.compile(r"^.*/?(\d{14})[^/]*/upgrade.py$")


class Scanner:

    def __init__(self, dottedname, directory):
        self.dottedname = dottedname
        self.directory = directory

    def scan(self):
        infos = list(
            map(self._build_upgrade_step_info, self._find_upgrade_directories())
        )
        infos.sort(key=lambda info: normalize_version(info["target-version"]))
        if len(infos) > 0:
            reduce(self._chain_upgrade_steps, infos)
        return infos

    def _find_upgrade_directories(self):
        return list(
            filter(
                UPGRADESTEP_DATETIME_REGEX.match, glob(f"{self.directory}/*/upgrade.py")
            )
        )

    def _build_upgrade_step_info(self, path):
        title, callable = self._load_upgrade_step_code(path)
        return {
            "source-version": None,
            "target-version": UPGRADESTEP_DATETIME_REGEX.match(path).group(1),
            "path": os.path.dirname(path),
            "title": title,
            "callable": callable,
        }

    def _chain_upgrade_steps(self, first, second):
        second["source-version"] = first["target-version"]
        return second

    def _load_upgrade_step_code(self, upgrade_path):
        spec = importlib.util.spec_from_file_location(".", upgrade_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        upgrade_steps = tuple(self._find_upgrade_step_classes_in_module(module))

        if len(upgrade_steps) == 0:
            raise UpgradeStepDefinitionError(
                f"The upgrade step file {upgrade_path} has no upgrade class."
            )

        if len(upgrade_steps) > 1:
            raise UpgradeStepDefinitionError(
                "The upgrade step file {} has more than one upgrade class.".format(  # noqa: E501
                    upgrade_path
                )
            )

        return upgrade_steps[0]

    def _find_upgrade_step_classes_in_module(self, module):
        for name, value in inspect.getmembers(module, inspect.isclass):
            if value == UpgradeStep or not issubclass(value, UpgradeStep):
                continue
            title = subject_from_docstring(inspect.getdoc(value) or name)
            title = safe_text(title)
            yield (title, value)
