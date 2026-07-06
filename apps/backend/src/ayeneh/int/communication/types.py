"""INT-03 Cross-Module Communication Bus — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


MESSAGE_CATEGORIES = [
    'information',
    'request',
    'response',
    'notification',
    'event',
    'warning',
    'diagnostic',
    'synchronization',
    'feedback',
    'governance_command',
]

DELIVERY_STATUSES = [
    'pending',
    'in_transit',
    'delivered',
    'acknowledged',
    'failed',
    'expired',
    'cancelled',
]

ROUTING_STRATEGIES = [
    'direct',
    'broadcast',
    'unicast',
    'multicast',
    'priority_based',
    'topic_based',
]


@dataclass(frozen=True)
class MessagePayload:
    """Structured payload within a communication message."""

    content_type: str = 'application/json'
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = '1.0'


@dataclass(frozen=True)
class RoutingRule:
    """Defines how messages are routed between modules."""

    rule_id: str = ''
    source_pattern: str = '*'
    target_pattern: str = '*'
    message_type_filter: str = '*'
    strategy: str = 'direct'
    priority_modifier: int = 0
    is_active: bool = True


@dataclass(frozen=True)
class DeliveryAttempt:
    """Record of a single delivery attempt."""

    attempt_id: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = 'pending'
    error_message: str = ''
    latency_ms: float = 0.0


@dataclass(frozen=True)
class AcknowledgmentRecord:
    """Acknowledgment received from a recipient module."""

    ack_id: str = ''
    module_id: str = ''
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed: bool = False
    error: str = ''


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of communication decisions."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    routing_decisions: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class CommunicationObject:
    """Core domain object for a cross-module communication message."""

    message_id: str
    sender_module: str = ''
    recipient_modules: tuple[str, ...] = ()
    message_type: str = ''
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = ''
    delivery_status: str = 'pending'
    acknowledgment_history: tuple[dict[str, Any], ...] = ()
    version_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.message_type and self.message_type not in MESSAGE_CATEGORIES:
            raise ValueError(
                f"Invalid message type: {self.message_type!r}. "
                f"Must be one of {MESSAGE_CATEGORIES}"
            )
        if self.delivery_status not in DELIVERY_STATUSES:
            raise ValueError(
                f"Invalid delivery status: {self.delivery_status!r}. "
                f"Must be one of {DELIVERY_STATUSES}"
            )


@dataclass(frozen=True)
class CommunicationResult:
    """Complete result from the CommunicationBus pipeline."""

    message_id: str = ''
    communication_object: CommunicationObject | None = None
    delivery_attempts: tuple[DeliveryAttempt, ...] = ()
    acknowledgments: tuple[AcknowledgmentRecord, ...] = ()
    routing_decisions: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()

    @property
    def all_delivered(self) -> bool:
        return all(
            a.status == 'delivered' or a.status == 'acknowledged'
            for a in self.delivery_attempts
        ) if self.delivery_attempts else False

    @property
    def delivery_count(self) -> int:
        return len(self.delivery_attempts)
