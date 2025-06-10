class CyclicDependencies(Exception):
    """Cyclic dependencies detected.
    """

    def __init__(self, dependencies, cyclic_dependencies=()):
        super().__init__(
            'Cyclic dependencies detected.')
        self.dependencies = dependencies
        self.cyclic_dependencies = cyclic_dependencies


class UpgradeNotFound(Exception):
    """An upgrade could not be found.
    """

    def __init__(self, api_id):
        self.api_id = api_id
        super().__init__(
            f'The upgrade "{api_id}" could not be found.')


class UpgradeStepDefinitionError(Exception):
    """An upgrade step definition is wrong.
    """


class UpgradeStepConfigurationError(Exception):
    """The upgrade steps directory configuration is wrong.
    """


class NoAssociatedProfileError(ValueError):
    """The upgrade step has no associated profile.
    """

    def __init__(self):
        super().__init__(
            self, NoAssociatedProfileError.__doc__.strip())
