import tarfile
import unittest
import json
import pathlib
import urllib3
import random
import requests
import soarsdk
from soarsdk.client import PhantomClient
from soarsdk.objects import Artifact, Container, Indicator, Playbook, Action, Pin, Asset, App
from soarsdk.exceptions import *
from soarsdk.objects import PhantomObject
from unittest.mock import Mock
from unittest.mock import MagicMock
from unittest.mock import patch


class PhantomClientTests(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        self.container = Container(
            name="soarsdk Test Container",
            label="workbench",
            artifacts=[Artifact(name="dummy", label="dummy")],
        )
        with patch("soarsdk.client.PhantomClient.test_authorization") as patched_auth:
            self.phantom = PhantomClient(
                url='https://example.test/', 
                session=requests.session()
            )
            
        self.mock_container = Container(name="test", label="foobar")
        
        with open('tests/sample_objects.json') as f:
            test_data = json.load(f)
        
        self.test_data = test_data
        self.test_artifacts = self.test_data["artifacts"]
        self.test_containers = self.test_data["containers"]
        self.test_indicator = self.test_data["indicator"]
        
    @patch("requests.Session.post")
    def test_create_container_throws_invalid_exception(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "Mocked HTTPError"
        )
        mock_post.return_value = mock_response

        misconfigured_container: Container = Container(
            name="bad container that should fail", label="NON_EXISTENT_LABEL"
        )
        with self.assertRaises(ServerException):
            self.phantom.create_container(container=misconfigured_container)

    @patch("requests.Session.post")
    @patch("requests.Session.get")
    def test_create_artifact(self, mock_post, mock_get):
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"id": 1, "success": True}
        mock_post.data = mock_post_response

        mock_get_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = self.test_artifacts
        mock_get.data = mock_get_response
        test_artifact = Artifact(name="Test Artifact", label="Test Artifact")
        mocked_container = Container(**self.test_containers[0])
        self.phantom.create_artifacts(mocked_container, test_artifact)
        self.assertEqual(test_artifact.container_id, mocked_container.id)

    def test_update_object(self):
        object1: Artifact = Artifact(name="test", label="test", cef={})
        object2: Artifact = Artifact(name="test", label="test", cef={"updated": True})
        object1.update(object2)
        assert object1.cef["updated"] == True

    def test_run_playbooks_without_id(self):
        uninitialized_container: Container = Container(name="test_container")
        self.assertRaises(
            soarsdk.exceptions.ContainerNotInitialized,
            self.phantom.run_playbooks,
            uninitialized_container,
        )

    def test_run_playbooks_no_args(self):
        uninitialized_container: Container = Container(name="test_container", id=1)
        self.assertRaises(
            AttributeError,
            self.phantom.run_playbooks,
            uninitialized_container,
        )

    def test_playbook_exception_bool_property(self):
        mocked_playbook: Playbook = Playbook(
            name="playbook_exception_thrower",
            logs=[
                {
                    "message": 'Unable to call the on_finish function for playbook \'test_throw_exception\'. Python Error: Traceback (most recent call last):\n  File "lib3/phantom/api/data_management/api_io_data.py/api_io_data.py", line 39, in save_playbook_output_data\n  File "/opt/phantom/usr/python39/lib/python3.9/site-packages/simplejson/__init__.py", line 395, in dumps\n    return _default_encoder.encode(obj)\n  File "/opt/phantom/usr/python39/lib/python3.9/site-packages/simplejson/encoder.py", line 296, in encode\n    chunks = self.iterencode(o, _one_shot=True)\n  File "/opt/phantom/usr/python39/lib/python3.9/site-packages/simplejson/encoder.py", line 378, in iterencode\n    return _iterencode(o, 0)\n  File "/opt/phantom/usr/python39/lib/python3.9/site-packages/simplejson/encoder.py", line 272, in default\n    raise TypeError(\'Object of type %s is not JSON serializable\' %\nTypeError: Object of type Test is not JSON serializable\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "lib3/phantom/decided/playbook_resource_score.py/playbook_resource_score.py", line 126, in _wrapper\n  File "lib3/phantom/decided/playbook_resource_score.py/playbook_resource_score.py", line 123, in _wrapper\n  File "<test_throw_exception>", line 64, in on_finish\n  File "lib3/phantom/utils.py/utils.py", line 1152, in inner\n  File "lib3/phantom/api/data_management/api_io_data.py/api_io_data.py", line 41, in save_playbook_output_data\nTypeError: Error in save_playbook_output_data(): "output" must be a JSON-serializable object.\n',
                    "time": "2023-05-20T01:08:40.681366Z",
                    "message_type": 0,
                },
                {
                    "message": "on_finish() called",
                    "time": "2023-05-20T01:08:40.669705Z",
                    "message_type": 1,
                },
            ],
        )
        self.assertTrue(mocked_playbook.exception_occurred)

    def get_sample_artifact(self) -> Artifact:
        """Grabs an artifact from the API to test methods"""
        return self.test_artifacts[0]

    def get_sample_container_with_playbook_run(self) -> Container:
        sample_container_id: int = self.phantom.get_playbook_runs()[0].container
        return Container(id=sample_container_id)

    @patch("requests.Session.post")
    def test_server_exception(self, mock_post):
        """Tests that the ServerException is called when errors occur from the PhantomSide"""
        mock_post_response = Mock()
        mock_post_response.status_code = 400
        mock_post_response.raise_for_status.side_effect = requests.HTTPError(
            'Label "foobar" is not a known label.'
        )
        mock_post_response.json.return_value: dict = {
            "failed": True,
            "message": 'Label "foobar" is not a known label.',
        }

        mock_post.return_value = mock_post_response

        bad_container = Container(name="bad container that should fail", label="foobar")
        self.assertRaises(ServerException, self.phantom.create_container, bad_container)

    def test_bad_handle_request_method(self):
        self.assertRaises(
            AttributeError,
            self.phantom._handle_request,
            method="DESTROY",
            url="container?",
        )

    def get_mock_artifacts_response(self) -> Mock:
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value: dict = self.test_artifacts
        return mock_get_response
    
    def get_mock_indicator_response(self) -> Mock:
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value: dict = self.test_indicator
        return mock_get_response

    def get_mock_containers_response(self) -> Mock:
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value: dict = {
            "count": 1,
            "num_pages": 1,
            "data": [
                {
                    "tags": [],
                    "id": 1,
                    "artifact_count": 0,
                    "artifact_update_time": "2023-01-02T01:11:07.408873Z",
                    "asset": None,
                    "close_time": None,
                    "closing_owner": None,
                    "closing_rule_run": None,
                    "container_update_time": None,
                    "create_time": "2023-01-02T01:11:04.811853Z",
                    "description": "",
                    "due_time": "2023-01-03T01:11:04.821564Z",
                    "end_time": None,
                    "hash": "3c07c2f2346d6b0a24e2223e76728529",
                    "external_id": None,
                    "ingest_app": None,
                    "kill_chain": None,
                    "label": "mock_label",
                    "name": "Mock Container #1",
                    "open_time": None,
                    "owner": None,
                    "role": None,
                    "owner_name": None,
                    "sensitivity": "green",
                    "severity": "low",
                    "source_data_identifier": "122ece04-e287-4f53-9bb2-4cca12db12d3",
                    "start_time": "2023-01-02T01:11:04.821554Z",
                    "status": "new",
                    "version": 1,
                    "workflow_name": "",
                    "custom_fields": {},
                    "container_type": "default",
                    "in_case": False,
                    "current_phase": None,
                    "tenant": 0,
                    "parent_container": None,
                    "node_guid": None,
                },
                {
                    "tags": ["example_tag"],
                    "id": 2,
                    "artifact_count": 1,
                    "artifact_update_time": "2023-03-04T00:19:04.384170Z",
                    "asset": None,
                    "close_time": None,
                    "closing_owner": None,
                    "closing_rule_run": None,
                    "container_update_time": None,
                    "create_time": "2023-03-04T00:19:04.384197Z",
                    "description": "",
                    "due_time": "2023-03-05T00:19:04.394528Z",
                    "end_time": None,
                    "hash": "e1fe6dc0abe1d253cc3e87823b7f71f3",
                    "external_id": None,
                    "ingest_app": None,
                    "kill_chain": None,
                    "label": "intel_ioc",
                    "name": "Mock Container #2",
                    "open_time": None,
                    "owner": None,
                    "role": None,
                    "owner_name": None,
                    "sensitivity": "green",
                    "severity": "low",
                    "source_data_identifier": "0aeb64d8-c11b-4319-bc16-0ddc475653a8",
                    "start_time": "2023-03-04T00:19:04.394520Z",
                    "status": "new",
                    "version": 1,
                    "workflow_name": "",
                    "custom_fields": {},
                    "container_type": "default",
                    "in_case": False,
                    "current_phase": None,
                    "tenant": 0,
                    "parent_container": None,
                    "node_guid": None,
                },
            ],
        }
        return mock_get_response

    @patch("soarsdk.client.PhantomClient.get_artifacts")
    @patch("requests.Session.post")
    @patch("requests.Session.get")
    def test_create_artifact(self, mock_artifacts, mock_post, mock_get):
        mock_response_post = Mock()
        mock_response_post.status_code = 200
        mock_response_post.json.return_value: dict = {"id": 1, "success": True}
        mock_post.return_value = mock_response_post

        # First Artifact intentionally has container field set to null
        mocked_artifacts: list[dict] = [self.test_artifacts[0]]
        mock_artifacts.return_value = mocked_artifacts
        mock_get.return_value = self.get_mock_containers_response()

        test_container: Container = Container(
            name="mock_container", label="mock_label", id=1
        )
        test_artifact: Artifact = Artifact(name="Test Artifact", label="Test Artifact")
        self.phantom.create_artifacts(test_container, test_artifact)
        self.assertEqual(test_artifact.container_id, test_container.id)

    @patch("requests.Session.delete")
    def test_delete_artifact(self, mock_delete):
        mock_delete_response = Mock()
        mock_delete_response.status_code == 200
        mock_delete.return_value = mock_delete_response

        deletion_artifact: Artifact = Artifact(
            name="test-delete", label="test-delete", id=1337
        )
        self.assertIsNotNone(deletion_artifact.id)
        self.phantom.delete_artifact(deletion_artifact)
        self.assertIsNone(deletion_artifact.id)

    @patch("requests.Session.delete")
    def test_delete_artifact_by_int(self, mock_delete):
        mock_delete_response = Mock()
        mock_delete_response.status_code == 200
        mock_delete.return_value = mock_delete_response
        self.phantom.delete_artifact(1)

    def test_delete_artifact_no_id(self):
        deletion_artifact: Artifact = Artifact(
            name="Nonexistent artifact", label="None"
        )
        self.assertRaises(
            ArtifactNotInitialized, self.phantom.delete_artifact, deletion_artifact
        )

    def test_upload_file_to_container_wrong_file(self):
        test_upload_file: pathlib.Path = pathlib.Path("./tests/ImaginaryFile.json")
        self.assertRaises(
            FileNotFoundError,
            self.phantom.upload_file,
            container=self.container,
            file_path=test_upload_file,
        )

    @patch("requests.Session.get")
    def test_get_container_attachment_ids_no_files(self, mock_get):
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"count": 0, "num_pages": 0, "data": []}
        mock_get.return_value = mock_get_response

        attachment_ids: list[int] = self.phantom.get_container_attachments_ids(
            self.mock_container
        )
        self.assertEqual(attachment_ids, [])

    def test_export_container_as_tar(self):
        ...

    def test_export_container_as_tar_bad_params(self):
        self.assertRaises(
            ContainerNotInitialized,
            self.phantom.export_container_as_tar,
            self.mock_container,
        )

    @patch("requests.Session.get")
    def test_get_containers(self, mock_get):
        params: dict = {"page_size": 1}
        mock_get.return_value = self.get_mock_containers_response()
        containers: list[Container] = self.phantom.get_containers(params)
        for container in containers:
            self.assertIsInstance(container, Container)

    @patch("requests.Session.get")
    def test_get_artifacts(self, mock_get):
        params: dict = {}
        artifacts: list[Artifact] = self.phantom.get_artifacts(params)
        mock_get.return_value = self.get_mock_artifacts_response()
        for artifact in artifacts:
            self.assertIsInstance(artifact, Artifact)
            
    @patch("requests.Session.get")
    def test_get_indicator_by_value(self, mock_get):
        mock_get.return_value = self.get_mock_indicator_response()
        indicator: Indicator = self.phantom.get_indicator_by_value("anything")
        self.assertIsInstance(indicator, Indicator)

    def test_update_container_values_none_id(self):
        bad_container: Container = Container(name="test", label="foobar")
        self.assertRaises(
            ContainerNotInitialized, self.phantom.update_container_values, bad_container
        )

    def test_update_Container_values_bad_param(self):
        self.assertRaises(
            ContainerNotInitialized,
            self.phantom.modify_container_values,
            Container(name="test", label="foobar"),
        )

    def test_update_object(self):
        object1: Artifact = Artifact(name="test", label="test", cef={})
        object2: Artifact = Artifact(name="test", label="test", cef={"updated": True})
        object1.update(object2)
        assert object1.cef.get("updated")


class PhantomClientAuthenticationTest(unittest.TestCase):
    @classmethod
    def setUp(self) -> None:
        pass

    def test_invalid_kwargs_raises_exception(self):
        self.assertRaises(ConnectionError, PhantomClient, "www.example.com")

    def test_username_password_missing_exception(self):
        self.assertRaises(
            AuthenticationError,
            PhantomClient,
            "www.example.com",
            username="test_username",
        )
        self.assertRaises(
            AuthenticationError,
            PhantomClient,
            "www.example.com",
            password="test_password",
        )


if __name__ == "__main__":
    unittest.main(warnings="ignore", failfast=True)
    urllib3.disable_warnings()
    unittest.main()
