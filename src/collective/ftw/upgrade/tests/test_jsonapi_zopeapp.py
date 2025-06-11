from collective.ftw.upgrade.tests.base import JsonApiTestCase


class TestZopeAppJsonApi(JsonApiTestCase):

    def setUp(self):
        super().setUp()
        self.app = self.layer["app"]

    def test_api_discovery(self):
        response = self.api_request("GET", "", context=self.app)

        self.assert_json_equal(
            {
                "api_version": "v1",
                "actions": [
                    {
                        "name": "current_user",
                        "required_params": [],
                        "description": "Return the current user when authenticated properly."
                        " This can be used for testing authentication.",
                        "request_method": "GET",
                    },
                    {
                        "name": "list_plone_sites",
                        "required_params": [],
                        "description": "Returns a list of Plone sites.",
                        "request_method": "GET",
                    },
                ],
            },
            response.json(),
        )

        self.assertTrue(
            response.content.endswith(b"\n"),
            "There should always be a trailing newline.",
        )

    def test_list_plone_sites(self):
        response = self.api_request("GET", "list_plone_sites", context=self.app)

        self.assert_json_equal(
            [{"id": "plone", "path": "/plone", "title": "Plone site"}], response.json()
        )

    def test_current_user(self):
        response = self.api_request("GET", "current_user", context=self.app)
        self.assertEqual("admin", response.json())

    def test_requiring_available_api_version_by_url(self):
        response = self.api_request("GET", "v1/list_plone_sites", context=self.app)
        self.assert_json_equal(
            [{"id": "plone", "path": "/plone", "title": "Plone site"}], response.json()
        )

    def test_requiring_wrong_api_version_by_url(self):
        with self.expect_api_error(
            status=404,
            message="Wrong API version",
            details='The API version "v100" is not available.',
        ) as result:
            result["response"] = self.api_request(
                "GET", "v100/list_plone_sites", context=self.app
            )

        self.assertTrue(
            result["response"].content.endswith(b"\n"),
            "There should always be a trailing newline.",
        )

    def test_requesting_unknown_action(self):
        with self.expect_api_error(
            status=404,
            message="Unknown API action",
            details='There is no API action "something".',
        ) as result:
            result["response"] = self.api_request("GET", "something", context=self.app)
