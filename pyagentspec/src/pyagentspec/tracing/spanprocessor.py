# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from abc import ABC, abstractmethod

from pyagentspec.tracing.events.event import Event
from pyagentspec.tracing.spans.span import Span


class SpanProcessor(ABC):
    """
    Interface which allows hooks for `Span` start and end method invocations.

    Aligned with OpenTelemetry APIs.
    """

    def __init__(self, mask_sensitive_information: bool = True) -> None:
        self.mask_sensitive_information = mask_sensitive_information

    @abstractmethod
    def on_start(self, span: "Span") -> None:
        """
        Called when a `Span` is started.

        Parameters
        ----------
        span:
            The spans that starts
        """

    @abstractmethod
    async def on_start_async(self, span: "Span") -> None:
        """
        Called when a `Span` is started. Asynchronous method.

        Parameters
        ----------
        span:
            The spans that starts
        """

    @abstractmethod
    def on_end(self, span: "Span") -> None:
        """
        Called when a `Span` is ended.

        Parameters
        ----------
        span:
            The spans that ends
        """

    @abstractmethod
    async def on_end_async(self, span: "Span") -> None:
        """
        Called when a `Span` is ended. Asynchronous method.

        Parameters
        ----------
        span:
            The spans that ends
        """

    @abstractmethod
    def on_event(self, event: Event, span: Span) -> None:
        """
        Called when an `Event` is triggered.

        Parameters
        ----------
        event:
            The event that is happening
        span:
            The spans where the event occurs
        """

    @abstractmethod
    async def on_event_async(self, event: Event, span: Span) -> None:
        """
        Called when an `Event` is triggered. Asynchronous method.

        Parameters
        ----------
        event:
            The event that is happening
        span:
            The spans where the event occurs
        """

    @abstractmethod
    def startup(self) -> None:
        """Called when a `Trace` is started."""

    @abstractmethod
    async def startup_async(self) -> None:
        """Called when a `Trace` is started. Asynchronous method."""

    @abstractmethod
    def shutdown(self) -> None:
        """Called when a `Trace` is shutdown."""

    @abstractmethod
    async def shutdown_async(self) -> None:
        """Called when a `Trace` is shutdown. Asynchronous method."""
