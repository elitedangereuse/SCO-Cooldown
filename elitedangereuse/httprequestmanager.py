"""Background HTTP downloads used solely by the self-update mechanism."""

from queue import Queue
from threading import Thread
from typing import Callable

import requests

from config import config
from elitedangereuse.debug import Debug

TIMEOUT_SECONDS = 10


class ReleaseRequest:
    """A queued GitHub release download."""

    def __init__(self, endpoint: str, callback: Callable | None, stream: bool):
        self.endpoint = endpoint
        self.callback = callback
        self.stream = stream


class HTTPRequestManager:
    """Process release metadata and ZIP downloads outside EDMC's UI thread."""

    def __init__(self, plugin):
        self.plugin = plugin
        self.request_queue: Queue[ReleaseRequest] = Queue()
        self.request_thread = Thread(target=self._worker, name="SCO Cooldown update worker", daemon=True)
        self.request_thread.start()

    def queue_request(self, endpoint: str, callback: Callable | None = None, stream: bool = False) -> None:
        """Queue a GET request for the updater; this plugin performs no uploads."""
        self.request_queue.put(ReleaseRequest(endpoint, callback, stream))

    def _worker(self) -> None:
        while not config.shutting_down:
            request = self.request_queue.get()
            try:
                response = requests.get(
                    request.endpoint,
                    headers={"User-Agent": f"{self.plugin.plugin_name}/{self.plugin.version}"},
                    stream=request.stream,
                    timeout=TIMEOUT_SECONDS,
                )
                response.raise_for_status()
            except requests.RequestException as error:
                Debug.logger.info("Update request failed for %s: %s", request.endpoint, error)
                if request.callback:
                    request.callback(False, None, request)
            else:
                if request.callback:
                    request.callback(True, response, request)
