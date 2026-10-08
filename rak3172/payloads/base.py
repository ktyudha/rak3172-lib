from abc import ABC, abstractmethod
from typing import Optional


class Payload(ABC):
    """Contract for one message type: what a node sends and what a gateway reads.

    Sender and receiver share this one class, so the two sides cannot drift apart.
    """

    @abstractmethod
    def to_payload(self) -> bytes:
        """Encode for transmission."""

    @classmethod
    @abstractmethod
    def from_payload(cls, payload: bytes) -> Optional["Payload"]:
        """Decode received bytes. Return None for malformed input; never raise."""
