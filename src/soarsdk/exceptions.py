import requests
import textwrap
import colorama


class ServerException(Exception):
    def __init__(self, response: requests.Response):
        failure_reason: str = response.json().get("message")

        self.error_code = response.status_code
        if self.error_code != 400:
            self.error_msg = f"""{response.request.method} {response.reason}  {failure_reason} {response.request.body}"""
        else:
            self.error_msg = textwrap.dedent(
                f"""
            ─────────────── Request ───────────────
            {response.request.method} {response.request.url}
            {response.request.body}
            ─────────────── Response ───────────────
            {response.status_code} {response.reason} {response.url}
            {response.json()}
            ────────────────────────────────────────
            """
            )
        Exception.__init__(
            self,
            f"{colorama.Fore.RED}{self.error_code}{colorama.Style.RESET_ALL}{self.error_msg}",
        )


class ContainerNotInitialized(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ArtifactNotInitialized(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ObjectMissingAttributes(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MissingApprovalResponse(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class PhantomObjectRequired(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class PlaybookException(Exception):
    def __init__(self, playbook) -> None:
        exceptions: list[dict] = playbook.get_exceptions()
        error_message: str = "".join([exc.get("message") for exc in exceptions])
        super().__init__(
            f"{colorama.Fore.RED}{error_message}{colorama.Style.RESET_ALL}"
        )


class AuthenticationError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
