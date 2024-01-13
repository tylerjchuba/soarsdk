from .exceptions import PhantomObjectRequired
from typing import Optional
from typing import Union
import json


class PhantomObject:
    """Parent class to implement any type of Phantom objects to ease in API calls

    Features of subclassing:
     - JSON Serializable: method to dump class directly into API calls
     - Allows for usage of the __in__ operator
    """

    def __in__(self, object, arg) -> Union[bool, None]:
        return arg in object.__dict__

    def update(self, object=None, **kwargs) -> None:
        """Allows updating from either unpacking API response or another object"""
        if object:
            for k, v in object.__dict__.items():
                if v:
                    self.__dict__[k] = v
        else:
            for k, v in kwargs.items():
                self.__dict__[k] = v

    def __str__(self) -> str:
        return json.dumps(self.toDict())

    def __repr__(self) -> str:
        return json.dumps(self.toDict(), indent=4)

    def toJson(self) -> str:
        return self.__str__()

    def toDict(self) -> dict:
        data: dict = {}
        for key, value in vars(self).items():
            if value:
                if isinstance(value, dict):
                    data[key] = {
                        k: v.toDict() if isinstance(v, PhantomObject) else v
                        for k, v in value.items()
                    }
                elif isinstance(value, list):
                    data[key] = [
                        v.toDict() if isinstance(v, PhantomObject) else v for v in value
                    ]
                elif isinstance(value, PhantomObject):
                    data[key] = value.toDict()
                else:
                    data[key] = value
        return data


class App(PhantomObject):
    """Represents an App configuration object within Splunk SOAR"""

    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name")
        self.id: int = kwargs.get("id")
        self.tags: list = kwargs.get("tags", [])
        self.appid: str = kwargs.get("appid")
        self.release_tag: str = kwargs.get("release_tag")
        self.app_version: str = kwargs.get("app_version")
        self.contributors: list = kwargs.get("contributors", [])
        self.description: str = kwargs.get("description")
        self.directory: str = kwargs.get("directory")
        self.draft_mode: bool = kwargs.get("draft_mode", False)
        self.custom_made: bool = kwargs.get("custom_made")
        self.install_time: str = kwargs.get("install_time")
        self.known_versions: list = kwargs.get("known_versions", [])
        self.latest_tested_versions: list = kwargs.get("last_tested_versions", [])
        self.product_name: str = kwargs.get("product_name")
        self.product_vendor: str = kwargs.get("product_vendor")
        self.publisher: str = kwargs.get("publisher")
        self.type: str = kwargs.get("type")
        self.python_version: str = kwargs.get("python_version")
        self.product_version_regex: str = kwargs.get("product_version_regex")


class Action(PhantomObject):
    def __init__(self, **kwargs):
        """Simplified Object between Action, ActionResult, & AppRun"""
        super().__init__()
        self.id: int = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.action: str = kwargs.get("action")
        self.app_run: int = kwargs.get("app_run")
        self.app: int = kwargs.get("app")
        self.app_name: str = kwargs.get("_pretty_app")
        self.asset_name: str = kwargs.get("_pretty_asset")
        self.app_version: str = kwargs.get("app_version")
        self.container: int = kwargs.get("container")
        self.container_name: str = kwargs.get("_pretty_container")
        self.create_time: str = kwargs.get("create_time")
        self.creator: str = kwargs.get("creator")
        self.handle: str = kwargs.get("handle")
        self.end_time: str = kwargs.get("end_time")
        self.pretty_end_time: str = kwargs.get("_pretty_end_time")
        self.exception_occurred: bool = kwargs.get("exception_occurred")
        self.message: str = kwargs.get("message")
        self.app_message: str = kwargs.get("app_message")
        self.playbook_run: int = kwargs.get("playbook_run")
        self.extra_data: list = kwargs.get("extra_data", [])
        self.result_summary: dict = kwargs.get("result_summary", {})
        self.result_data: list = kwargs.get("result_data", [])
        self.start_time: str = kwargs.get("start_time")
        self.pretty_start_time: str = kwargs.get("pretty_start_time")
        self.status: str = kwargs.get("status")
        self.version: int = kwargs.get("version")
        self.effective_user: int = kwargs.get("effective_user")
        self.effective_user_name: str = kwargs.get("_pretty_effective_user")
        self.playbook: str = kwargs.get("playbook_run")
        self.status: str = kwargs.get("status")


class Artifact(PhantomObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.label = kwargs.get("label")
        self.name = kwargs.get("name")
        self.id = kwargs.get("id")
        # Check/Retrieve default values
        self.tags = kwargs.get("tags", [])
        self.cef = kwargs.get("cef", {})
        self.data = kwargs.get("data", [])
        self.container: int = kwargs.get("container")
        self.cef_types: dict = kwargs.get("cef_types", {})
        self.data: dict = kwargs.get("data", {})
        self.description: str = kwargs.get("description")
        self.end_time: str = kwargs.get("end_time")
        self.ingest_app_id: int = kwargs.get("ingest_app_id")
        self.kill_chain: str = kwargs.get("kill_chain")
        self.owner_id: str = kwargs.get("owner_id")
        self.playbook_run_id: int = kwargs.get("playbook_run_id")
        self.severity_id: str = kwargs.get("severity_id", "low")
        self.source_data_identifier: str = kwargs.get("source_data_identifier")
        self.start_time: str = kwargs.get("start_time")
        self.type: str = kwargs.get("type")
        self.update_time: str = kwargs.get("update_time")
        self.version: int = kwargs.get("version")
        self.in_case: bool = kwargs.get("in_case", False)
        self.parent_container_id: int = kwargs.get("parent_container_id")
        self.parent_artifact_id: int = kwargs.get("parent_artifact_id")
        self.hash: str = kwargs.get("hash")
        self.create_time: str = kwargs.get("create_time")

    def get_creation_artifact(self):
        """Returns a clean artifact for creation. This is used to accurately place create time"""
        return Artifact(
            name=self.name,
            label=self.label,
            tags=self.tags,
            cef=self.cef,
            data=self.data,
            cef_types=self.cef_types,
            description=self.description,
            owner_id=self.owner_id,
            type=self.type,
            version=self.version,
        )

    def __eq__(self, comp_artifact):
        return all(
            [
                self.name == comp_artifact.name,
                self.label == comp_artifact.label,
                self.container_id == comp_artifact.container_id,
            ]
        )

    def __hash__(self):
        """@todo look through previous scripts to find appropriate hashing for equality comparisons"""
        return hash(self.name + self.label + self.id)

class Indicator(PhantomObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.id: int = kwargs.get("id")
        self.value: str = kwargs.get("value")
        self.value_hash: str = kwargs.get("value_hash")
        self.tenant: int = kwargs.get("tenant")
        self.tags: list = kwargs.get("tags", [])
        self.earliest_time: str = kwargs.get("earliest_time")
        self.latest_time: str = kwargs.get("latest_time")
        self.open_events: int = kwargs.get("open_events")
        self.total_events: int = kwargs.get("total_events")
        self.severity_counts = kwargs.get("severity_counts", [])
        

class Asset(PhantomObject):
    def __init__(self, **kwargs):
        self.action_whitelist: dict = kwargs.get("action_whitelist", {})
        self.automation_broker: str = kwargs.get("automation_broker")
        self.concurrency_limit: int = kwargs.get("concurrency_limit")
        self.configuration: dict = kwargs.get("configuration", {})
        self.description: str = kwargs.get("description")
        self.effective_user: int = kwargs.get("effective_user")
        self.id: int = kwargs.get("id")
        self.name: str = kwargs.get("name")
        self.primary_voting: int = kwargs.get("primary_voting")
        self.secondary_voting: int = kwargs.get("secondary_voting")
        self.tags: list = kwargs.get("tags", [])
        self.tenants: list = kwargs.get("tenants", [])
        self.token: str = kwargs.get("token")
        self.type: str = kwargs.get("type")
        self.validation: dict = kwargs.get("validation", {})
        self.version: float = kwargs.get("version")
        self.apps: list = kwargs.get("apps", [])
        self.product_name: str = kwargs.get("product_name")
        self.product_vendor: str = kwargs.get("product_vendor")
        self.disabled: bool = kwargs.get("disabled")
        self.internal: bool = kwargs.get("internal")
        self.config: dict = kwargs.get("config")
        self.product_version: str = kwargs.get("product_version")
        self.app: int = kwargs.get("app")


class Playbook(PhantomObject):
    def __init__(
        self,
        **kwargs,
    ):
        """
        We use playbook objects to define the storage mechanism of how we want to run and store information
        related to playbooks. Playbooks should store their associated action results as well

         actions: list of actions retrieved from phantom in relation to playbook & container
         name: name of the playbook to run, repo name not required
         run_id: id generated by phantom after running the playbook
         prompts: dictionary of prompts where the key presents the order of operations to be ran
         status: bool representing success or failure within phantom
        """
        super().__init__()
        self.actions = kwargs.get("actions", [])
        # API will return the name via _pretty_playbook field versus user will specify the name
        self.name = (
            kwargs.get("_pretty_playbook")
            if "name" not in kwargs
            else kwargs.get("name")
        )

        # instance of the playbook running
        self.id: int = kwargs.get("id")
        # Playbook_ID refers base playbook
        self.playbook_id: int = kwargs.get("playbook")
        # prompts are defined as a mapping of "prompt_name" to a list strings representing responses in chronological order
        self.prompts: dict[str, list[str]] = kwargs.get("prompts", {})
        self.status: bool = kwargs.get("status", False)
        self.misc: dict = kwargs.get("misc", {})
        self.run_data: dict = kwargs.get("run_data", {})
        self.targets: list[dict] = kwargs.get("targets", [])
        self.start_time: str = kwargs.get("start_time", None)
        self.endpoint: str = "playbook_run"
        self.action_exec: list = kwargs.get("action_exec", [])
        self.container: int = kwargs.get("container")
        self.ip_address: str = kwargs.get("ip_address")
        self.log_level: int = kwargs.get("log_level")
        self.message: str = kwargs.get("message")
        self.test_mode: bool = kwargs.get("test_mode")
        self.last_artifact: int = kwargs.get("last_artifact")
        self.version: int = kwargs.get("version")
        self.effective_user: int = kwargs.get("effective_user")
        self.node_guid: str = kwargs.get("node_guid")
        self.playbook_run_batch: int = kwargs.get("playbook_run_batch")
        self.parent_run: int = kwargs.get("parent_run")
        self.inputs: dict = kwargs.get("inputs", {})
        self.outputs: dict = kwargs.get("outputs", {})
        self.run_id: int = kwargs.get("run_id")
        self.update_time: str = kwargs.get("update_time")
        self.logs: list = kwargs.get("logs", [])

    def append(self, *args) -> None:
        self.actions.append(*args)

    @property
    def get_parent_playbook_id(self) -> int:
        return self.get_parent_playbook("id")

    @property
    def get_parent_playbook_name(self) -> str:
        return self.get_parent_playbook("name")

    @property
    def get_action_ids(self) -> list[int]:
        return [action.id for action in self.actions]

    @property
    def exception_occurred(self) -> bool:
        """Checks for message_type 0 in the playbook logs to indicate if an exception has occurred"""
        return bool(self.get_exceptions())

    def get_exceptions(self) -> list[dict]:
        return [log for log in self.logs if log.get("message_type") == 0]

    def get_parent_playbook(self, *args: str) -> Union[int, str]:
        """Returns either ID or name value of parent_playbook"""

        if len(args) > 1:
            raise SyntaxError(
                f'get_parent_playbook only excepts either "name" or "id" arguments'
            )

        parent_playbook = self.misc.get("parent_playbook_run")
        if not parent_playbook:
            return None

        if "name" in args:
            return parent_playbook.get("parent_playbook_name")

        if "id" in args:
            return parent_playbook.get("parent_playbook_run_id")

        return None

    def get_action(self, name: str) -> Action:
        """Returns a given action from a playbook"""
        for action in self.actions:
            if action.name == name:
                return action
        return None


class Pin(PhantomObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.message = kwargs.get("message")
        self.data = kwargs.get("data")
        self.style = kwargs.get("pin_style")
        self.type = kwargs.get("pin_type")


class Note(PhantomObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.artifact: int = kwargs.get("artifact")
        self.artifact_name: str = kwargs.get("artifact_name")
        self.author: str = kwargs.get("author")
        self.container: int = kwargs.get("container")
        self.container_attachments: list = kwargs.get("container_attachments", [])
        self.content: str = kwargs.get("content")
        self.id: int = kwargs.get("id")
        self.modified_time: str = kwargs.get("modified_time")
        self.format: str = kwargs.get("note_format", "markdown")
        self.type: str = kwargs.get("note_type", "general")
        self.phase: int = kwargs.get("phase")
        self.task: str = kwargs.get("task")
        self.task_name: str = kwargs.get("task_name")
        self.title: str = kwargs.get("title")
        self._pretty_author: str = kwargs.get("_pretty_author")
        self._pretty_container: str = kwargs.get("pretty_container")
        self._pretty_create_time: str = kwargs.get("_pretty_create_time")
        self._pretty_phase: str = kwargs.get("_pretty_phase")
        self._pretty_task: str = kwargs.get("_pretty_task")


class Container(PhantomObject):
    """Represents a container within Splunk SOAR. Creation requires name & label attributes. Optionally, the id attribute may be used to
    reference and existing container a Splunk SOAR instance."""

    def __init__(self, **kwargs):
        super().__init__()
        self.name: str = kwargs.get("name")
        self.label: str = kwargs.get("label")
        self.id: int = kwargs.get("id")
        self.run_auto: bool = kwargs.get("run_auto", False)
        self.tags: list = kwargs.get("tags", [])
        self.custom_fields: dict = kwargs.get("custom_fields", {})
        self.description: str = kwargs.get("description")
        self.artifacts: list[Artifact] = kwargs.get("artifacts", [])
        self.sensitivity: str = kwargs.get("sensitivity", "red")
        self.playbooks: list[Playbook] = kwargs.get("playbooks", [])
        self.pins: list = kwargs.get("pins", [])
        self.create_time: str = kwargs.get("create_time")
        self.open_time: str = kwargs.get("open_time")
        self.end_time: str = kwargs.get("end_time")
        self.owner_id: str = kwargs.get("owner_id")
        self.role_id: str = kwargs.get("role_id")
        self.kill_chain: str = kwargs.get("kill_chain")
        self.severity_id: int = kwargs.get("severity_id")
        self.severity: str = kwargs.get("severity")
        self.source_data_identifier: str = kwargs.get("source_data_identifier")
        self.start_time: str = kwargs.get("source_data_identifier")
        self.status_id: int = kwargs.get("status_id")
        self.workflow_name: str = kwargs.get("workflow_name")
        self.owner_name: str = kwargs.get("owner_name")
        self.container_type: str = kwargs.get("container_type")
        self.in_case: bool = kwargs.get("in_case", False)
        self.current_phase_id: int = kwargs.get("current_phase_id")
        self.tenant_id: int = kwargs.get("tenant_id")
        self.parent_container_id: int = kwargs.get("parent_container_id")
        self.node_guid: str = kwargs.get("node_guid")
        self.status: str = kwargs.get("status", "new")
        self.artifact_update_time: str = kwargs.get("artifact_update_time")
        self.asset_id: int = kwargs.get("asset_id")
        self.close_time: str = kwargs.get("close_time")
        self.closing_owner_id: str = kwargs.get("closing_owner_id")
        self.container_update_time: str = kwargs.get("container_update_time")
        self.create_time: str = kwargs.get("create_time")
        self.kill_Chain: str = kwargs.get("kill_chain")
        self.created: str = kwargs.get("created")
        self.audit_logs: list = kwargs.get("audit_logs", [])
        self.comments: list[str] = kwargs.get("comments", [])
        self.notes: list[Note] = kwargs.get("notes", [])
        self.data: list[dict] = kwargs.get("data", {})
        self.due_time: str = kwargs.get("due_time")

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)
    
    @property
    def artifact_names(self) -> list[str]: 
        return [artifact.name for artifact in self.artifacts]

    @property
    def artifact_ids(self) -> list:
        """Returns a list of artifact IDs associated with the container"""
        return list(set([artifact.id for artifact in self.artifacts]))

    @property
    def action_names(self) -> list[str]:
        """Returns a unique list of action names that have ran on the container"""
        action_names: list[str] = []
        for playbook in self.playbooks:
            [action_names.append(action.name) for action in playbook.actions]
        return list(set(action_names))

    @property
    def playbook_names(self) -> list[str]:
        """Returns a unique list of playbook names that have ran on the container"""
        return list(set([playbook.name for playbook in self.playbooks]))

    def add_artifact(self, *args: list[Artifact]) -> None:
        """Add a series of artifact(s) to the container"""
        for arg in args:
            if not isinstance(arg, Artifact):
                raise PhantomObjectRequired(
                    "container.add_artifact() requires an Artifact object"
                )
            arg.container_id = self.id
            self.artifacts.append(arg)

    def get_creation_container(
        self,
        artifacts_included: Optional[bool] = True,
        tags_included: Optional[bool] = False,
    ):
        """Returns a clean container object for creation in the REST API.
        Artifacts are optionally included. Does not modify base object
        @todo: determine how to handle pins, most likely include with the
        class responsible for creation
        """
        temp_container = Container(
            name=self.name,
            label=self.label,
            severity=self.severity,
            sensitivity=self.sensitivity,
            owner_name=self.owner_name,
            owner_id=self.owner_id,
            description=self.description,
            kill_chain=self.kill_chain,
            workflow_name=self.workflow_name,
            custom_fields=self.custom_fields,
            container_type=self.container_type,
            status=self.status,
            id=self.id,
        )
        if artifacts_included:
            temp_container.artifacts = self.artifacts
        if tags_included:
            temp_container.tags = self.tags
        return temp_container

    def get_container_with_artifacts(self):
        """Returns a clean container with artifacts included"""
        return self.get_creation_container(artifacts_included=True)

    def get_container_only(self):
        """Returns a container with only container-related attributes"""
        return self.get_creation_container(artifacts_included=False)

    def get_playbook(
        self,
        name: Optional[str] = None,
        playbook_run: Optional[int] = None,
        playbook_id: Optional[int] = None,
    ) -> Playbook:
        """Returns the playbook associated with the container. Accepts name, playbook_run, and playbook_id
        If a name of a playbook is given, it will return the most recent instance of the playbook if there are
        multiple playbooks of the same name.
        """
        for playbook in self.playbooks:
            if name:
                # Some API calls require including the repository in the playbook.name attribute.
                # This simplifies finding them later on
                if "/" in name:
                    name = name.split("/")[-1]
                if name in playbook.name:
                    return playbook
            if playbook_run:
                if playbook.id == playbook_run:
                    return playbook
            if playbook_id and playbook_run:
                if playbook_id == playbook.playbook_id and playbook.id == playbook_run:
                    return playbook

    def get_artifact(self, name=None, label=None, id=None) -> Artifact:
        """Returns an artifact contained within the container"""
        for artifact in self.artifacts:
            if name and artifact.name == name:
                return artifact
            if id and artifact.id == id:
                return artifact
            if label and artifact.label == label:
                return artifact
        return None

    def add_playbooks(self, *args: list[Playbook]):
        """Add a given playbook to the container"""
        self.playbooks.extend(args)

    def add_pins(self, *args: list[Pin]):
        """Add pypac.Pins object to container. Accepts multiple pin objects as args"""
        self.pins.extend(args)

    def get_action(self, name: str) -> list[Action]:
        """Returns any action that matches the provided name"""
        actions_list: list[Action] = []
        for playbook in self.playbooks:
            for action in playbook.actions:
                if action.name == name:
                    actions_list.append(action)
        return actions_list
