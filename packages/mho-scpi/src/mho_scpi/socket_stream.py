"""Adapter for a caller-supplied socket; never connects, resolves, or closes it."""

import math
import socket
from collections.abc import Callable

from .session_models import ReadProgress, StreamFailure, StreamProgress, WriteProgress


class SocketStream:
    """The caller must exclusively own the socket for the whole query session.

    Each operation restores the prior timeout. Timeout-restoration failures carry
    any already returned progress. This class does not take close ownership.
    """

    def __init__(self, supplied_socket: socket.socket) -> None:
        self._socket = supplied_socket

    def _operation(self, timeout: float, action: Callable[[], StreamProgress]) -> StreamProgress:
        if not math.isfinite(timeout) or timeout <= 0:
            raise StreamFailure(
                "invalid-timeout", "timeout must be positive and finite", operation_started=False
            )
        try:
            previous = self._socket.gettimeout()
        except OSError as error:
            raise StreamFailure("stream-state", str(error), operation_started=False) from error
        progress: StreamProgress | None = None
        failure: OSError | None = None
        started = False
        try:
            self._socket.settimeout(timeout)
            started = True
            progress = action()
        except OSError as error:
            failure = error
        finally:
            try:
                self._socket.settimeout(previous)
            except OSError as error:
                raise StreamFailure(
                    "timeout-restoration",
                    str(error),
                    progress=progress,
                    operation_started=started,
                    timeout_restoration_failed=True,
                ) from error
        if failure is not None:
            raise StreamFailure(
                "stream-timeout" if isinstance(failure, TimeoutError) else "stream-error",
                str(failure),
                operation_started=started,
            ) from failure
        if progress is None:
            raise RuntimeError("socket operation produced neither progress nor error")
        return progress

    def write(self, data: bytes, timeout: float) -> int:
        result = self._operation(timeout, lambda: WriteProgress(self._socket.send(data)))
        if not isinstance(result, WriteProgress):
            raise RuntimeError("socket write returned wrong progress kind")
        return result.count

    def read(self, size: int, timeout: float) -> bytes:
        result = self._operation(timeout, lambda: ReadProgress(self._socket.recv(size)))
        if not isinstance(result, ReadProgress):
            raise RuntimeError("socket read returned wrong progress kind")
        return result.data
