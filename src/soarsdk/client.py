import glob
import json
import pathlib
import tarfile
import textwrap
from hashlib import sha256
from typing import Union
import colorama
import requests
from requests import Response
from requests.models import HTTPError
from requests.structures import CaseInsensitiveDict

from .exceptions import (
    ArtifactNotInitialized,
    ContainerNotInitialized,
    MissingApprovalResponse,
    ObjectMissingAttributes,
    PhantomObjectRequired,
    PlaybookException,
    ServerException,
    AuthenticationError,
)
from .objects import (
    Action,
    App,
    Artifact,
    Asset,
    Container,
    Note,
    Pin,
    PhantomObject,
    Playbook,
)


class PhantomClient:
    def __init__(self, url: str, **kwargs):
        """
        Class responsible for handling connections and requests to the Splunk SOAR instance.

        Attributes:
            base_url (str): Base domain address of the Splunk SOAR instance
            rest_url (str): REST endpoint of the Splunk SOAR instance inferred from base_url
            action_builder (list): Cache for available actions and app configurations
            request_log (list): Cache of requests between the Client and the SOAR server
            _TLS_VERIFY (bool): SSL Verification for requests. Defaults to False
            session (requests.Session): Session object used for the requests library


        Keyword Args:
            url (str): Target Server Hostname
            splunkToken (Optional[str]): Token for Authentication
            username (Optional[str]): Username for Authentication
            password (Optional[str]): Password for Authentication
            verify (bool): Enable SSL Verification for requests to and from the Splunk SOAR instance

        """
        colorama.init()
        self.base_url: str = url + "/" if not url.endswith("/") else url
        self.rest_url = self.base_url + "rest/"
        # Cache for actions builder query
        self.action_builder: dict = []
        # Cache of requests & responses
        self.requests_log: list = []
        self._TLS_VERIFY: bool = kwargs.get("verify", False)

        # Detect if provided an incomplete username/password pairing
        if bool(kwargs.get("username")) ^ bool(kwargs.get("password")):
            raise AuthenticationError(
                "Username or password not detected. Provide both a username and password for authentication"
            )

        if (
            not kwargs.get("session")
            and not kwargs.get("username")
            and not kwargs.get("splunkToken")
        ):
            raise ConnectionError(
                "No arguments for connection provided. Provide either a username & password, an API token, or an authenticated session"
            )

        self.session = (
            kwargs.get("session") if kwargs.get("session") else requests.Session()
        )

        if not kwargs.get("session"):
            self.connect(**kwargs)
        else:
            self.test_authorization()

    def connect(
        self,
        **kwargs,
    ):
        """Initializes a Splunk SOAR connection by either password or token based authentication.

        Keyword Args:
            username (str): username to authenticate to server
            password (str): password to authenticate to server
            splunkToken (str): Splunk SOAR generated token
        """
        if kwargs.get("username") and kwargs.get("password"):
            self.session = self.password_authenticate(
                kwargs["username"], kwargs["password"]
            )
        if kwargs.get("splunkToken"):
            self.session = self.token_authenticate(kwargs["splunkToken"])

        self.test_authorization()

    def test_authorization(self) -> bool:
        """Make a request to get the Splunk SOAR version. Test the authorization of the client.

        Returns:
            success: Determine if we can get data out of Phantom.
        """
        url: str = self.base_url + "rest/version"
        response: requests.Response = self.session.get(url, verify=False)
        if not response.status_code == 200:
            raise AuthenticationError(
                f"Failed to authenticate to {self.base_url} with provided credentials"
            )

    def password_authenticate(self, username: str, password: str):
        """Authenticates to the Splunk SOAR instance using username and password

        Args:
            username (str): username for authentication
            password (str): password for authentication
        """
        url: str = self.base_url + "browse"
        response: requests.Response = self.session.get(
            self.base_url, auth=(username, password), verify=False
        )
        response.raise_for_status()
        self._set_session_headers(self.base_url, self.session)
        self.test_authorization(self.base_url, self.session)
        username = None
        password = None

    def token_authenticate(self, token: str) -> None:
        """Updates the session headers with the provided token. Attempts to test and establish a connection with the Splunk SOAR.

        Args:
            token (str):
        """
        self.session.headers.update({"ph-auth-token": token, "server": self.base_url})
        self.test_authorization()

    def _set_session_headers(self) -> None:
        """Sets the session headers with a user agent and CSRF token for future requests"""
        for cookie in self.session.cookies:
            if cookie.name == "csrftoken":
                self.session.headers.update(
                    {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
                        "X-CSRFToken": cookie.value,
                        "Referrer": f"{self.base_url}rest",
                    }  # type: ignore
                )

    def create_container(self, container: Container):
        """Creates a container and any associated artifacts

        Args:
            container (Container): container with name and label variables set

        Raises:
            ValueError: if an already existing container is provided, or if the container
                        and its artifacts are missing their respective names & labels
        """
        if container.id:
            raise AttributeError(
                f"create_container() cannot use an existing container. Container ID {container.id}"
            )

        if not container.name and not container.label:
            raise ObjectMissingAttributes(
                "create_container(): provided Container object must have a name and label"
            )

        if container.artifacts:
            for artifact in container.artifacts:
                if not artifact.name and not artifact.label:
                    raise AttributeError(
                        f"create_container(): provided container {container.name} has artifact(s) missing the required name field"
                    )

        valid_container: Container = container.get_creation_container(
            artifacts_included=True, tags_included=True
        )

        # post to the container endpoint to create a container
        container_post: dict = self._handle_request(
            method="POST", url="container?", data=valid_container
        )

        container.id = int(container_post["id"])

        # update the container with post-creation values
        updated_container_values: Container = self.get_containers(
            params={"_filter_id": container.id}
        )[0]
        container.update(updated_container_values)

        # update the artifacts on the container
        self.update_artifacts(container)

    def create_artifacts(self, container: Container, *args: list[Artifact]):
        """Create artifacts on an existing container. Artifacts can be provided as arguments, or appended to
        a container object's artifacts. All artifacts not previously created in the container will be created.

        Args:
            *args (list[Artifact]): Artifact objects to be created on the container
        """
        if not container.id:
            raise ContainerNotInitialized(
                f"create_artifacts() requires an existing Container"
            )

        for artifact in container.artifacts:
            if not artifact.id and not artifact.container:
                args.extend(artifact)

        for artifact in args:
            artifact.container_id = container.id
            artifact_id: int = self._handle_request(
                method="POST", url="artifact?", data=artifact.toJson()
            ).get("id")
            artifact.id = artifact_id
        # update artifacts that have been created
        self.update_artifacts(container)

    def run_playbooks(
        self,
        container: Container,
        *args: list[Playbook],
        **kwargs,
    ) -> None:
        """Runs playbooks configured on the initialized Container. Playbooks can be stored on the container as
        container or provided as an args list.

        Args:
            container (Container): container to execute playbooks against
            args (list[Playbook]): optional list of playbooks to run against the container
            scope (str) : playbook artifact scope to use for playbook run
        """
        scope: str = kwargs.get("scope", "all")
        if not container.id:
            raise ContainerNotInitialized(
                f"run_playbooks() requires an initialized container"
            )

        if not container.playbooks and not args:
            raise AttributeError(
                f"run_playbooks() requires playbooks on the container or as arguments"
            )

        # run playbooks not initialized
        playbooks_not_ran: list[Playbook] = [
            playbook for playbook in container.playbooks if not playbook.run_id
        ]
        playbooks_not_ran.extend(args)

        for playbook in playbooks_not_ran:
            data: dict = {
                "container_id": container.id,
                # fun fact about the API: see below
                "playbook_id": playbook.name
                if not playbook.playbook_id
                else playbook.playbook_id,
                "scope": scope,
                "run": True,
            }

            response = self._handle_request(
                method="POST", url="playbook_run", json=data
            )

            playbook.run_id = response.get("playbook_run_id")

            playbook_running = True

            while playbook_running:
                playbook_running: bool = self.is_playbook_running(container)
                pending_approvals: list[dict] = self.check_approvals(container)
                if pending_approvals:
                    self.answer_approvals(
                        container=container,
                        playbook=playbook,
                        approvals=pending_approvals,
                    )
        self.update_container_values(container)

        for playbook in container.playbooks:
            if playbook.exception_occurred:
                raise PlaybookException(playbook) from None

    def delete_container(self, *args: list[Container]) -> None:
        """Delete one or many containers from Splunk SOAR"""
        self._handle_request(
            method="DELETE",
            url="container",
            params={"ids": [container.id for container in args]},
        )
        for container in args:
            container.id = None

    def is_playbook_running(self, container: Container) -> bool:
        """Returns True/False if any playbooks are actively running on the container

        Args:
            container (Container): Initialized container on the Splunk SOAR server
        """

        playbook_run_params = {
            "_filter_container": container.id,
            "_filter_status": "running",
        }

        response: dict = self._handle_request(
            method="GET",
            url="playbook_run",
            params=playbook_run_params,
        )
        playbooks_running_bool: bool = response.get("count", 0) > 0

        return playbooks_running_bool

    def answer_approvals(
        self,
        container: Container,
        playbook: Playbook,
        approvals: list[dict],
    ) -> None:
        """Answers approvals for a given playbook (stored under the Playbook.prompts) for 60 seconds.
        If a prompt is not found within the given playbook, but an approval is found on the container a MissingApprovalResponse exception will be raised.

        Args:
            container (Container): Initialized container on the Splunk SOAR server
            playbook (Playbook): Playbook object containing the necessary prompt responses
            approvals (list[dict]): Pending approvals from the Splunk SOAR server

        Raises:
            MissingApprovalResponse
        """
        # fetch any ids of approvals on the container
        for approval in approvals:
            approval_name = approval.get("name")
            if approval_name not in playbook.prompts:
                raise MissingApprovalResponse(
                    f"Failed to answer approvals on container {container.id}. Did not find the prompt {approval_name} in the playbook {playbook.name} prompts"
                )
            # answer approval if configured responses
            self.answer_approval(approval.get("id"), playbook.prompts[approval_name])

    def check_approvals(self, container: Container) -> list[dict]:
        """Checks for outstanding approvals on a given container. Returns the list of pending approvals if found

        Args:
            container (Container): Splink SOAR container being processed

        Returns:
            approval_data (list[dict]): containing approval information
        """
        params = {
            "_filter_status": "pending",
            "_filter_action_run__container_id": str(container.id),
            "order": "asc",
            "sort": "start_time",
            "page_size": "200",
            "pretty": True,
        }

        request = self._handle_request(
            method="GET",
            url="approval",
            params=params,
        )
        return request.get("data")

    def answer_approval(self, approval_id: int, approval_data: list[str]) -> None:
        """Answer a given approval with pre-supplied approval_data

        Args:
            approval_id (int): Approval ID from the Splunk SOAR server
            approval_data (list[str]): List of responses for the given approval

        """
        payload = {
            "status": "approve",
            "type": "manual",
            "action": "prompt",
            "message": "",
            "responses": approval_data,
        }

        self._handle_request(
            method="POST",
            url="approval/" + str(approval_id),
            json=payload,
        )

    def get_pins(self, container: Union[Container, int]) -> dict:
        """Returns a JSON object containing information about pins for an associated container and updates the container object
        If a Container object is provided, associates the results under container.pins

        Args:
            container (int | Container): Associated SOAR Container ID or Object with ID set

        Returns:
            pin_results (dict): Dictionary of associated pins with container
        """
        container_id: int = (
            container.id if isinstance(container, Container) else container
        )
        pin_results = self._handle_request(
            url=f"container/{container_id}/pins",
            method="GET",
            return_data_only=True,
        )
        pins = [Pin(**pin) for pin in pin_results]

        if isinstance(container, Container):
            container.pins.extend(pins)
        return pin_results

    def update_container_values(self, container: Container) -> None:
        """Creates a Container object from an existing container in Splunk SOAR

        Args:
            container (Container): Container object initialized on the Splunk SOAR server

        Returns:
            Container: Container object with relevant information about the container

        Raises:
            ContainerNotInitialized
        """
        if not container.id:
            raise ContainerNotInitialized

        container.update(self.get_containers(params={"_filter_id": container.id})[0])

        container.artifacts = self.get_artifacts(
            params={"_filter_container__exact": container.id}
        )
        updated_playbooks: list[Playbook] = self.get_playbook_runs(
            params={"_filter_container__exact": container.id, "include_expensive": True}
        )
        for playbook in updated_playbooks:
            declared_playbook: Playbook = container.get_playbook(name=playbook.name)
            if declared_playbook:
                declared_playbook.update(playbook)
            else:
                container.playbooks.append(playbook)

        self.get_pins(container=container)
        self.get_comments(container=container)
        self.get_notes(container=container)

    def get_playbook_name_from_id(self, id: int) -> str:
        """Returns the playbook name based on its id

        Args:
            id (int): ID of Playbook

        Returns:
            name (str): Playbook name
        """
        url = f"playbook/{id}"
        response = self._handle_request(method="GET", url=url)
        return response.get("name")

    def update_artifacts(self, container: Container, limit: int = 1000) -> None:
        """Updates the container's artifacts with fresh API data.
        Args:
            container (Container): Initialized container object
            limit (int): Maximum amount of artifacts to fetch. Default 1000
        """
        params: dict = {"page_size": 1000, "_filter_container": str(container.id)}
        container.artifacts = self.get_artifacts(params=params)

    def get_container_attachments_ids(self, container: Container) -> list[int]:
        """Returns a list of attachments ids based on the provided container

        Args:
            container (Container): Initialized container on the Splunk SOAR server

        Returns:
            attachments (list[int]): collection of integer attachment ids

        """
        response: dict = self._handle_request(
            method="GET",
            url=f"container/{container.id}/attachments",
            return_data_only=True,
        )
        return [attachment.get("id") for attachment in response]


    def export_container_as_tar(
        self,
        container: Union[Container, int],
        download_path: str = "/tmp/",
        include_attachments=True,
    ) -> pathlib.Path:
        """Download the container object's container, artifacts, and attachments as a tarfile

        Args:
            container (Container): Container object instance or integer ID for an existing container
            download_path (str): Directory to place the downloaded tarfile
            include_attachments (bool): Specify to download vault files, defaults True

        Raises:
            ContainerNotInitialized

        """
        if isinstance(container, Container) and not container.id:
            raise ContainerNotInitialized(
                "export_container_as_tar() requires a Container with the id set"
            )

        self.update_container_values(container=container)

        container_id: int = (
            container.id if isinstance(container, Container) else container
        )

        file_name: str = f"container-{container.id}.tgz"

        params: dict[str, str] = {
            "Filename": file_name,
            "Content-Type": "application/-gzip",
        }

        if include_attachments:
            attachments: list[int] = self.get_container_attachments_ids(container)
            params["file_list[]"] = attachments

        response = self._handle_request(
            method="GET",
            url=f"container/{container_id}/export?",
            params=params,
            return_json=False,
        )

        final_path: pathlib.Path = pathlib.Path(download_path) / file_name

        with open(str(final_path.absolute()), "wb") as container_file:
            container_file.write(response.content)

        return final_path

    def find_by_hash(self, object_hash: str, object_type: str) -> int:
        """Query the API and returns the id of an associated object corresponding to the provided hash

        Args:
            object_hash (str): Hash of the target object
            object_type (str): Type of object, either artifact or container

        Raises:
            ValueError
        """
        if object_type:
            if object_type not in ["artifact", "container"]:
                raise ValueError(
                    f"find_by_hash() type parameter must be either container or artifact"
                )
        params = {"_filter_hash": object_hash}
        response: list = self._handle_request(
            method="GET", url=f"{object_type}?", params=params, return_data_only=True
        )
        existing_object_id: int = response[0].get("id")
        return existing_object_id

    def delete_artifact(self, *args: list[Union[Artifact, int]]) -> None:
        """Delete an artifact object or id from the Splunk SOAR server

        Args:
          args (Artifact | int): Artifact object or integer artifact_id
        """
        for artifact in args:
            artifact_id: int = (
                artifact.id if isinstance(artifact, Artifact) else artifact
            )
            if not artifact_id:
                raise ArtifactNotInitialized
            self._handle_request(method="DELETE", url=f"artifact/{artifact_id}")
            if isinstance(artifact, Artifact):
                artifact.id = None
                artifact.container_id = None

    def modify_container_values(self, container: Container) -> None:
        """Update an existing container in Splunk SOAR with the modified values of the Container object

        Args:
            container (Container): Initialized container on the Splunk SOAR instance

        Raises:
            ContainerNotInitialized
        """
        if not container.id:
            raise ContainerNotInitialized(
                "modify_container_values() requires an initialized container"
            )
        self._handle_request(
            method="POST",
            url=f"container/{container.id}",
            data=container.get_container_only(),
        )

    def upload_file(self, **kwargs) -> None:
        """
        Uploads a file the the Splunk SOAR Server. If provided a container tarball

        Args:
            container (Container): Container object containing the id of the desired container
            file_path(str): Location of the file

        Raises:
            FileNotFound
        """
        file_path: str = kwargs.get("file_path")
        container: Container = kwargs.get("container")
        params: dict = kwargs.get("params", {})
        data: dict = kwargs.get("data", {})

        file_location: pathlib.Path = pathlib.Path(file_path)

        if not file_location.exists():
            raise FileNotFoundError(f"File {file_path} not found. Check path provided")

        file_data: bytes = open(file_location, "rb").read()

        initial_request_url = self.base_url + "upload_chunked"
        files = {"file": (file_location.name, file_data)}

        # Uploading a file to a Container
        if container:
            data = {
                "container_id": str(container.id),
            }
            self.connector.session.headers.update(
                {
                    "Referer": self.rest_url
                    + "mission/"
                    + str(container.id)
                    + "/analyst/files/"
                }
            )
        else:
            # Uploading a Container
            params["import_container"] = True

        response = self._handle_request(
            method="POST",
            url=initial_request_url,
            data=data,
            files=files,
        )

        upload_id = response["upload_id"]
        final_upload_url = self.base_url + "upload_chunked_complete"

        # indicator
        sha256_digest = sha256(file_data).hexdigest()
        data = {"upload_id": upload_id, "sha256": sha256_digest}
        # update headers for file upload
        self.session.headers.update({"Accept-Encoding": "gzip, deflate, br"})
        self._handle_request(method="POST", url=final_upload_url, data=data)

    def get_playbook_id_from_name(self, playbook: Union[str, Playbook]) -> int:
        """Returns the ID of a playbook given its name. Sets the playbook.playbook_id if provided a Playbook object

        Queries the API to find a playbook ID that matches the provided name,

        Args:
            playbook (str | Playbook): Name of the playbook or Playbook object with the name attribute set
        Returns:
            The ID of the most recent playbook version with the specified name.
        Raises:
            LookUpError
        """
        playbook_name: str = (
            playbook.name if isinstance(playbook, Playbook) else playbook
        )
        params: dict = {"_filter_name__exact": playbook_name}
        playbooks: list[Playbook] = self.get_playbooks(params=params)
        if len(playbooks) > 1:
            raise LookupError(
                f"Playbook {playbook_name} has multiple matching playbooks. Provide more specific name"
            )
        if not playbooks:
            raise LookupError(f"Playbook {playbook_name} not found on the server")

        playbook_id: int = playbooks[0].id
        if isinstance(playbook, Playbook):
            playbook.id = playbook_id

        return playbook_id

    def find_containers_from_playbook(
        self,
        playbook: Playbook,
        count: int = 1,
        successful: bool = True,
        params: dict = {},
    ) -> list[Container]:
        """Queries the API and returns a collection of containers that the given playbook has ran against. This function
        returns the most recent containers that the given playbook executed against.

        Params:
        playbook (Playbook): Playbook object with either name or id initialized
        count (int): Requested amount of container objects
        successful (bool): Find either successful playbooks or failed playbooks
        """

        if not playbook.name and not playbook.id:
            raise AttributeError("Playbook object missing a name or id attribute")

        if not playbook.id:
            self.get_playbook_id_from_name(playbook.name)

        params = {
            "sort": "start_time",
            "order": "desc",
            "_filter_playbook__exact": playbook.id,
            "_filter_status__exact": "success",
            "page_size": count,
            "pretty": True,
        }

        containers = self._handle_request(
            url="playbook_run?", method="GET", params=params, return_data_only=True
        )
        object_containers: list[Container] = []

        for response in containers:
            temp_container = Container(id=response.get("container"))
            self.update_container_values(container=temp_container)
            object_containers.append(temp_container)

        return object_containers

    def get_playbook_notes(self, playbook: Playbook) -> str:
        """Returns the notes of the playbook as configured within the VPE.

        Params:
            playbook (Playbook): Playbook object with either playbook.playbook_id or playbook.name attributes set

        """

        if not playbook.playbook_id and not playbook.name:
            raise AttributeError("Playbook missing a name or ID attribute")

        params: dict = {"include_expensive": True, "page-size": 1}

        if playbook.name:
            params["_filter_name__exact"] = playbook.name

        if playbook.id:
            params["_filter_id__exact"] = playbook.id

        response: list = self._handle_request(
            url="playbook?", method="GET", params=params, return_data_only=True
        )
        return response[0].get("coa_data").get("notes")

    def get_asset_ids(self) -> list[int]:
        """Obtains a list of asset ids present in the connected Splunk SOAR environment"""
        return [asset.id for asset in self.get_assets()]

    def get_asset(self, asset_name: str) -> Asset:
        """Returns an asset based on its name attribute"""
        params: dict = {"_filter_name__icontains": asset_name}
        response: dict = self._handle_request(
            method="GET", params=params, url="asset?", return_data_only=True
        )
        return Asset(**response[0])

    def set_playbook_active(self, active: bool, playbook: Union[Playbook, int]) -> None:
        """Updates a given playbook to be "Active" on its corresponding label on the Splunk SOAR instance.

        Args:
            active (bool): Active status. False is inactive and True is active
            playbook (Playbook | int): Playbook object or integer ID of the corresponding playbook
        """
        playbook_id: int = (
            playbook.playbook_id if isinstance(playbook, Playbook) else playbook
        )
        params: dict = {"active": active, "id": playbook_id, "toggle": True}
        self._handle_request(method="POST", url="playbooks", params=params)

    def _init_action_builder(self) -> None:
        """Builds and stores the apps, actions, and asset configurations in Splunk SOAR."""
        self.action_builder = self._handle_request(method="GET", url="build_action")

    def get_apps(self) -> list[App]:
        """Returns a list of apps configured on the Splunk SOAR instance"""
        if not self.action_builder:
            self._init_action_builder()

        apps: list[App] = []
        for app in self.action_builder.get("apps"):
            apps.append(App(**app))
        return apps

    def get_app(self, app_name: str) -> App:
        """Returns an App object based off its name attribute"""
        apps: list[App] = self.get_apps()
        for app in apps:
            if app_name.lower() in app.name.lower():
                return app
        return None

    def get_actions(self) -> list[Action]:
        """Returns a list of actions configured on the Splunk SOAR instance"""
        if not self.action_builder:
            self._init_action_builder()

        actions: list[Action] = []
        for action in self.action_builder.get("actions"):
            actions.append(Action(**action))
        return actions

    def get_assets(self) -> list[Asset]:
        """Returns a simple view of assets configured and available for actions"""
        if not self.action_builder:
            self._init_action_builder()

        assets: list[Asset] = []
        for asset in self.action_builder.get("assets"):
            assets.append(Asset(**asset))
        return assets

    def get_containers(self, params: dict = {}) -> list[Container]:
        """Returns a list of Container objects based on the REST parameters provided"""
        containers: list[dict] = self._handle_request(
            method="GET", url="container?", params=params, return_data_only=True
        )
        return [Container(**container) for container in containers]

    def get_enriched_containers(self, params: dict = {}) -> list[Container]:
        """Returns a list of fully enriched Containers objects based on the REST parameters provided for the container endpoint.
        The fully enriched containers will contain full information about artifacts, playbooks, actions, and logging.
        """
        containers: list[Container] = self.get_containers(params)
        return [self.update_container_values(container) for container in containers]

    def get_artifacts(self, params: dict = {}) -> list[Artifact]:
        """Returns a list of Artifact objects based on the REST parameters provided"""
        artifacts: list[dict] = self._handle_request(
            method="GET", url="artifact?", params=params, return_data_only=True
        )
        return [Artifact(**artifact) for artifact in artifacts]

    def get_playbooks(self, params: dict = {}) -> list[Playbook]:
        """Returns a list of Playbook objects based on the REST parameters provided"""
        playbooks: list[dict] = self._handle_request(
            method="GET", url="playbook?", params=params, return_data_only=True
        )
        return [Playbook(**playbook) for playbook in playbooks]

    def get_playbook_runs(self, params: dict = None) -> list[Playbook]:
        """Returns a list of Playbook Run Objects with actions and logging based on the REST parameters provided for the playbook_run endpoint."""
        params["include_expensive"] = True
        playbooks_data: list[dict] = self._handle_request(
            method="GET", url="playbook_run?", params=params, return_data_only=True
        )
        playbooks: list[Playbook] = []
        for playbook in playbooks_data:
            playbook_object: Playbook = Playbook(**playbook)
            playbook_object.actions = self.get_action_runs(
                {"_filter_playbook_run": playbook_object.id}
            )
            playbook_object.name = self.get_playbook_name_from_id(
                playbook_object.playbook_id
            )
            playbook_object.logs = self.get_playbook_logs(playbook=playbook_object)
            playbooks.append(playbook_object)
        return playbooks

    def get_app_runs(self, params: dict = {}) -> list[dict]:
        """Returns a list[dict] of App Runs. Contains the record of the action_result with parameters"""
        params["pretty"] = True
        params["include_expensive"] = True
        return self._handle_request(
            method="GET", url="app_run?", params=params, return_data_only=True
        )

    def get_action_runs(self, params: dict = {}) -> list[Action]:
        """Returns a list of Actions with preselected fields from its app execution if available. Actions obtained with this method
        will include additional information from the corresponding app_run endpoint related to any given action. This is intended
        to closely replicate the GUI experiencing of selecting a specific action within the mission explorer.
        """
        actions_data: list[dict] = self._handle_request(
            method="GET", url="action_run?", params=params, return_data_only=True
        )
        actions: list[Action] = [Action(**action) for action in actions_data]

        if actions:
            action_ids: list[int] = [action.id for action in actions]

            for action in actions:
                    params: dict = {"_filter_action_run": action.id}
                    app_runs: list[dict] = self.get_app_runs(params=params)
                    for app_run in app_runs:
                        action.app_name = app_run.get("app_name")
                        action.app_run = app_run.get("id")
                        action.app_version = app_run.get("app_version")
                        action.exception_occurred = app_run.get("exception_occurred")
                        action.app_message = app_run.get("message")
                        action.result_summary = app_run.get("result_summary", {})
                        action.result_data = app_run.get("result_data", [])
        return actions

    def get_comments(self, container: Container) -> None:
        """Associates the comments available on the initialized container to the Container object

        Args:
            container (Container): Splunk SOAR container currently initialized on the server

        Raises:
            ContainerNotInitialized

        """
        if not container.id:
            raise ContainerNotInitialized()

        comment_data: list[dict] = self._handle_request(
            method="GET",
            url=f"container/{container.id}/comments",
            return_data_only=True,
        )
        container.comments = [comment.get("comment") for comment in comment_data]

    def add_comment(self, container: Container, comment: str) -> None:
        """Posts a comment to an initialized container

        Args:
            container (Container): Splunk SOAR container currently initialized on the server
            comment (str): Comment to append to the container

        Raises:
            ContainerNotInitialized
        """
        if not container.id:
            raise ContainerNotInitialized(
                f"Failed to add comment to container {container.name}. Container must have the id attribute"
            )
        data: dict = {"container": container.id, "comment": comment}
        self._handle_request(method="POST", url="container_comment", json=data)
        container.comments.append(comment)

    def get_notes(self, container: Container) -> None:
        """Appends the Notes stored on the Container to its respective object"""
        params: dict = {
            "_filter_container_id": container.id,
            "pretty": True,
            "page": 0,
            "page_size": 100,
            "order": "desc",
            "sort": "modified_time",
            "_annotation_container_attachments": True,
        }
        container_notes: list[dict] = self._handle_request(
            method="GET", url="note", params=params, return_data_only=True
        )
        container.notes = [Note(**note) for note in container_notes]

    def create_note(self, container: Container, note: Note):
        """Creates a new note object on the container inside of the Splunk SOAR instance

        Args:
            container (Container): Initialized container on the Splunk SOAR server
            note (Note): Note to be created on the container. See soarsdk.objects.Note for more details

        Raises:
            ContainerNotInitialized
        """
        if not container.id:
            raise ContainerNotInitialized(
                "create_note() requires an initialized container"
            )

        payload: dict = {
            "attachments": [],
            "container_id": container.id,
            "content": note.content,
            "title": note.title,
            "note_format": note.format,
            "note_type": note.type,
        }
        self._handle_request(method="POST", url="note", json=payload)
        self.get_notes(container)

    def get_playbook_logs(self, playbook: Playbook) -> list[dict]:
        """Finds any relevant logs for the playbook object. Ensure logging is enabled on the playbook, otherwise only exceptions
        and app errors will be capture"""
        # Playbook objects utilize the run_id
        if playbook.id:
            params: dict = {"page_size": 0, "sort": "time"}
            return self._handle_request(
                method="GET",
                url=f"playbook_run/{playbook.id}/log",
                params=params,
                return_data_only=True,
            )
        return []

    def _handle_request(
        self,
        method: str,
        url: str,
        **kwargs: dict,
    ) -> Union[dict, Response]:
        """Method to handle interactions with the server. By default, will raise and
           throw HTTP exceptions when non-successful status codes are returned.

        Args:
            method (str): "GET/POST/"DELETE"
            url (str): API endpoint to communicate
            data (dict, optional): Data to post in request
            params (dict, optional): Parameters for encoding in requests
            headers (dict, optional): Headers for HTTP Request
            stream (bool, optional): Obtain raw_socket from the server
            json (dict, optional): Used for passing dicts without serializing
            files (dict, optional): Used for uploading files
            return_json (bool, optional): By default, return the JSON. Otherwise,
                                          return the response object

        Returns:
            Union[dict, Response]: JSON loaded response from the server. Utilize the return_data_only parameter to determine the type.
                                   By default, will return the JSON of the entire response.

        """
        data: dict = kwargs.get("data", {})
        params: dict = kwargs.get("params", {})
        headers: dict = kwargs.get("headers", {"Accept": "application/json"})
        stream: bool = kwargs.get("stream", False)
        json_data: Union[PhantomObject, dict] = kwargs.get("json", {})
        files: dict = kwargs.get("files", {})
        allow_redirects: bool = kwargs.get("allow_redirects", False)
        return_json: bool = kwargs.get("return_json", True)
        return_data_only: bool = kwargs.get("return_data_only", False)

        for key, value in params.items():
            if key not in ["start_time", "sort", "order"] and "__in" not in key:
                if isinstance(value, str):
                    params[key]: str = json.dumps(value)

        # Serialize PhantomObjects to JSON compatible format
        if isinstance(data, PhantomObject):
            data: str = data.toJson()

        if self.base_url not in url:
            url = self.base_url + "rest/" + url

        try:
            request_func = getattr(self.session, method.lower())
        except AttributeError:
            raise AttributeError(
                f"Invalid requests method {method}, use GET/POST/DELETE"
            )

        response = request_func(
            url=url,
            data=data,
            params=params,
            headers=headers,
            stream=stream,
            json=json_data,
            files=files,
            allow_redirects=allow_redirects,
            hooks={"response": self._generate_log},
            verify=self._TLS_VERIFY,
        )

        try:
            response.raise_for_status()
        except HTTPError as http_exception:
            raise ServerException(response=response) from http_exception

        if return_json:
            if return_data_only:
                return response.json().get("data")
            return response.json()

        return response

    def _generate_log(self, response: Response, *args, **kwargs) -> None:
        """Formats logs for usage in error handling and general debugging. Requests are stored in the self.requests_log attribute"""

        def format_headers(arg: CaseInsensitiveDict[str]) -> str:
            return "\n".join(f"{k}: {v}" for k, v in arg.items())

        self.requests_log.append(
            textwrap.dedent(
                """
            ─────────────── Request ───────────────
            {req.method} {req.url}
            {reqhdrs}
            {req_body_json}
            ─────────────── Response ───────────────
            {res.status_code} {res.reason} {res.url}
            {resp_body_json}
            ────────────────────────────────────────
        """
            ).format(
                req=response.request,
                res=response,
                req_body_json=response.request.body,
                reqhdrs=format_headers(response.request.headers),
                reshdrs=format_headers(response.headers),
                resp_body_json=response.text,
            )
        )
