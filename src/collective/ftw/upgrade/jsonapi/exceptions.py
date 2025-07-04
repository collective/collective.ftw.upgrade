class APIError(Exception):
    def __init__(self, message, details="", response_code=400):
        super().__init__(message)
        self.message = message
        self.details = details
        self.response_code = response_code

    def process_error(self, response):
        return


class WrongAPIVersion(APIError):
    def __init__(self, requested_version):
        super().__init__(
            "Wrong API version",
            f'The API version "{requested_version}" is not available.',
            response_code=404,
        )


class UnknownAPIAction(APIError):
    def __init__(self, action_name):
        super().__init__(
            "Unknown API action",
            f'There is no API action "{action_name}".',
            response_code=404,
        )


class UnauthorizedWrapper(APIError):
    def __init__(self, original_exception):
        super().__init__(
            "Unauthorized", "Admin authorization required.", response_code=401
        )


class MethodNotAllowed(APIError):
    def __init__(self, required_method):
        self.required_method = required_method.upper()
        super().__init__(
            "Method Not Allowed",
            f"Action requires {self.required_method}",
            response_code=405,
        )

    def process_error(self, response):
        response.setHeader("Allow", self.required_method)


class MissingParam(APIError):
    def __init__(self, param_name):
        super().__init__(
            "Param missing",
            f'The param "{param_name}" is required for this API action.',
        )


class PloneSiteOutdated(APIError):
    def __init__(self):
        super().__init__(
            "Plone site outdated",
            "The Plone site is outdated and needs to be upgraded"
            " first using the regular Plone upgrading tools.",
        )


class CyclicDependenciesWrapper(APIError):
    def __init__(self, original_exception):
        super().__init__(
            "Cyclic dependencies",
            "There are cyclic Generic Setup profile dependencies.",
            response_code=500,
        )


class ProfileNotAvailable(APIError):
    def __init__(self, profileid):
        super().__init__(
            "Profile not available",
            'The profile "{}" is wrong or not installed'
            " on this Plone site.".format(profileid),
        )


class ProfileNotFound(APIError):
    def __init__(self, profileid):
        super().__init__("Profile not found", f'The profile "{profileid}" is unknown.')


class UpgradeNotFoundWrapper(APIError):
    def __init__(self, original_exception):
        api_upgrade_id = original_exception.api_id
        super().__init__(
            "Upgrade not found", f'The upgrade "{api_upgrade_id}" is unknown.'
        )


class AbortTransactionWithStreamedResponse(Exception):
    """This exception wraps another exception and is used to indicate that
    the original exception should cause the transaction to be aborted but
    not cause 500 since we are streaming a response.
    It is expected that the exception information (e.g. the traceback) is
    already written to the response and streamed to the browser.
    """

    def __init__(self, original_exception):
        self.original_exception = original_exception
