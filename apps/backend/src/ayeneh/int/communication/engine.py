"""INT-03 Cross-Module Communication Bus — 8-phase message pipeline."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.int.communication.types import (
    AcknowledgmentRecord,
    CommunicationObject,
    CommunicationResult,
    DELIVERY_STATUSES,
    DeliveryAttempt,
    ExplainabilityMetadata,
    MESSAGE_CATEGORIES,
    MessagePayload,
    RoutingRule,
)

logger = structlog.get_logger(__name__)


class CommunicationBus:
    """Handles cross-module message delivery through an 8-phase pipeline.

    Phases:
        1. MessageCreation       — build and validate the message
        2. Validation            — ensure message meets schema and policy
        3. Routing               — determine delivery targets
        4. PriorityAssignment    — assign delivery priority
        5. Delivery              — send to recipient modules
        6. Acknowledgment        — collect recipient acknowledgments
        7. Logging               — record message metadata
        8. HistoricalArchive     — persist for future reference
    """

    def __init__(self) -> None:
        self._routing_rules: list[RoutingRule] = []
        self._archive: list[dict[str, Any]] = []

    def add_routing_rule(self, rule: RoutingRule) -> None:
        self._routing_rules.append(rule)

    def send(
        self,
        sender_module: str = '',
        recipient_modules: list[str] | None = None,
        message_type: str = 'information',
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        correlation_id: str = '',
        context: dict[str, Any] | None = None,
        session_id: str = '',
    ) -> CommunicationResult:
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []
        recipients = recipient_modules or []
        msg_payload = payload or {}

        message_id = str(uuid.uuid4())
        logger.info(
            "communication_started",
            message_id=message_id,
            sender=sender_module,
            recipients=len(recipients),
            message_type=message_id[:8],
        )

        # Phase 1: MessageCreation
        comm_obj = self._phase_message_creation(
            message_id, sender_module, recipients, message_type,
            msg_payload, priority, correlation_id, errors,
        )

        # Phase 2: Validation
        validated = self._phase_validation(comm_obj, errors)

        # Phase 3: Routing
        routed_recipients, routing_decisions = self._phase_routing(
            validated, recipients, ctx, errors,
        )

        # Phase 4: PriorityAssignment
        prioritized_obj = self._phase_priority_assignment(validated, ctx, errors)

        # Phase 5: Delivery
        delivery_attempts = self._phase_delivery(
            prioritized_obj, routed_recipients, errors,
        )

        # Phase 6: Acknowledgment
        acks = self._phase_acknowledgment(delivery_attempts, errors)

        # Phase 7: Logging
        self._phase_logging(prioritized_obj, delivery_attempts, acks, errors)

        # Phase 8: HistoricalArchive
        self._phase_historical_archive(prioritized_obj, errors)

        duration_ms = (time.monotonic() - start) * 1000

        confidence = self._compute_confidence(delivery_attempts, acks)

        logger.info(
            "communication_completed",
            message_id=message_id,
            delivered=len(delivery_attempts),
            acknowledged=len(acks),
            duration_ms=duration_ms,
        )

        return CommunicationResult(
            message_id=message_id,
            communication_object=prioritized_obj,
            delivery_attempts=tuple(delivery_attempts),
            acknowledgments=tuple(acks),
            routing_decisions=tuple(routing_decisions),
            confidence=confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_message_creation(
        self,
        message_id: str,
        sender_module: str,
        recipients: list[str],
        message_type: str,
        payload: dict[str, Any],
        priority: int,
        correlation_id: str,
        errors: list[str],
    ) -> CommunicationObject:
        """Phase 1: Build and validate the message."""
        try:
            if not correlation_id:
                correlation_id = str(uuid.uuid4())

            # Normalize message type
            if message_type not in MESSAGE_CATEGORIES:
                message_type = 'information'

            obj = CommunicationObject(
                message_id=message_id,
                sender_module=sender_module,
                recipient_modules=tuple(recipients),
                message_type=message_type,
                payload=payload,
                priority=priority,
                correlation_id=correlation_id,
                delivery_status='pending',
                version_metadata={'schema_version': '1.0'},
            )

            logger.debug("phase_message_creation_completed", message_id=message_id)
            return obj
        except Exception as exc:
            errors.append(f"Phase 1 (MessageCreation) error: {exc}")
            return CommunicationObject(
                message_id=message_id,
                sender_module=sender_module,
                message_type='information',
            )

    def _phase_validation(
        self,
        obj: CommunicationObject,
        errors: list[str],
    ) -> CommunicationObject:
        """Phase 2: Ensure message meets schema and policy."""
        try:
            validation_issues: list[str] = []

            if not obj.sender_module:
                validation_issues.append("Missing sender module")
            if not obj.recipient_modules:
                validation_issues.append("No recipient modules specified")
            if not obj.message_type:
                validation_issues.append("Missing message type")

            if validation_issues:
                logger.warning(
                    "validation_issues",
                    message_id=obj.message_id,
                    issues=validation_issues,
                )

            logger.debug("phase_validation_completed", issues=len(validation_issues))
            return obj
        except Exception as exc:
            errors.append(f"Phase 2 (Validation) error: {exc}")
            return obj

    def _phase_routing(
        self,
        obj: CommunicationObject,
        explicit_recipients: list[str],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Phase 3: Determine delivery targets."""
        try:
            routing_decisions: list[dict[str, Any]] = []
            final_recipients: list[str] = list(explicit_recipients)

            # Apply routing rules
            for rule in self._routing_rules:
                if not rule.is_active:
                    continue
                if rule.source_pattern != '*' and rule.source_pattern != obj.sender_module:
                    continue
                if rule.message_type_filter != '*' and rule.message_type_filter != obj.message_type:
                    continue

                routing_decisions.append({
                    'rule_id': rule.rule_id,
                    'strategy': rule.strategy,
                    'source_match': obj.sender_module,
                    'message_type_match': obj.message_type,
                })

                # Broadcast strategy adds all known modules
                if rule.strategy == 'broadcast' and 'known_modules' in ctx:
                    for mod in ctx['known_modules']:
                        if mod not in final_recipients and mod != obj.sender_module:
                            final_recipients.append(mod)

            if not routing_decisions_present(routing_decisions):
                routing_decisions.append({
                    'rule_id': 'default',
                    'strategy': 'direct',
                    'source_match': obj.sender_module,
                    'message_type_match': obj.message_type,
                })

            logger.debug("phase_routing_completed", recipients=len(final_recipients))
            return final_recipients, routing_decisions
        except Exception as exc:
            errors.append(f"Phase 3 (Routing) error: {exc}")
            return list(explicit_recipients), []

    def _phase_priority_assignment(
        self,
        obj: CommunicationObject,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> CommunicationObject:
        """Phase 4: Assign delivery priority."""
        try:
            base_priority = obj.priority

            # Adjust based on message type
            type_priority_boost = {
                'governance_command': 10,
                'warning': 8,
                'synchronization': 7,
                'feedback': 6,
                'request': 5,
                'response': 4,
                'event': 3,
                'notification': 2,
                'diagnostic': 1,
                'information': 0,
            }
            boost = type_priority_boost.get(obj.message_type, 0)
            adjusted_priority = base_priority + boost

            # Context-based adjustments
            if ctx.get('urgent'):
                adjusted_priority += 5

            if adjusted_priority != base_priority:
                return CommunicationObject(
                    message_id=obj.message_id,
                    sender_module=obj.sender_module,
                    recipient_modules=obj.recipient_modules,
                    message_type=obj.message_type,
                    payload=obj.payload,
                    priority=adjusted_priority,
                    timestamp=obj.timestamp,
                    correlation_id=obj.correlation_id,
                    delivery_status=obj.delivery_status,
                    acknowledgment_history=obj.acknowledgment_history,
                    version_metadata=obj.version_metadata,
                )

            logger.debug("phase_priority_assignment_completed", priority=adjusted_priority)
            return obj
        except Exception as exc:
            errors.append(f"Phase 4 (PriorityAssignment) error: {exc}")
            return obj

    def _phase_delivery(
        self,
        obj: CommunicationObject,
        recipients: list[str],
        errors: list[str],
    ) -> list[DeliveryAttempt]:
        """Phase 5: Send to recipient modules."""
        try:
            attempts: list[DeliveryAttempt] = []
            for recipient in recipients:
                attempt = DeliveryAttempt(
                    attempt_id=str(uuid.uuid4()),
                    status='delivered',
                    latency_ms=1.0,  # Simulated
                )
                attempts.append(attempt)
                logger.debug(
                    "delivery_attempt",
                    message_id=obj.message_id,
                    recipient=recipient,
                    status='delivered',
                )

            logger.debug("phase_delivery_completed", attempts=len(attempts))
            return attempts
        except Exception as exc:
            errors.append(f"Phase 5 (Delivery) error: {exc}")
            return []

    def _phase_acknowledgment(
        self,
        delivery_attempts: list[DeliveryAttempt],
        errors: list[str],
    ) -> list[AcknowledgmentRecord]:
        """Phase 6: Collect recipient acknowledgments."""
        try:
            acks: list[AcknowledgmentRecord] = []
            for attempt in delivery_attempts:
                if attempt.status == 'delivered':
                    acks.append(AcknowledgmentRecord(
                        ack_id=str(uuid.uuid4()),
                        module_id=f"recipient_{attempt.attempt_id[:8]}",
                        processed=True,
                    ))

            logger.debug("phase_acknowledgment_completed", acks=len(acks))
            return acks
        except Exception as exc:
            errors.append(f"Phase 6 (Acknowledgment) error: {exc}")
            return []

    def _phase_logging(
        self,
        obj: CommunicationObject,
        delivery_attempts: list[DeliveryAttempt],
        acks: list[AcknowledgmentRecord],
        errors: list[str],
    ) -> None:
        """Phase 7: Record message metadata."""
        try:
            log_entry = {
                'message_id': obj.message_id,
                'sender': obj.sender_module,
                'recipients': list(obj.recipient_modules),
                'message_type': obj.message_type,
                'priority': obj.priority,
                'delivery_count': len(delivery_attempts),
                'ack_count': len(acks),
                'timestamp': obj.timestamp.isoformat(),
            }
            logger.info("message_logged", **log_entry)
        except Exception as exc:
            errors.append(f"Phase 7 (Logging) error: {exc}")

    def _phase_historical_archive(
        self,
        obj: CommunicationObject,
        errors: list[str],
    ) -> None:
        """Phase 8: Persist for future reference."""
        try:
            archive_entry = {
                'message_id': obj.message_id,
                'sender': obj.sender_module,
                'recipients': list(obj.recipient_modules),
                'message_type': obj.message_type,
                'priority': obj.priority,
                'correlation_id': obj.correlation_id,
                'timestamp': obj.timestamp.isoformat(),
            }
            self._archive.append(archive_entry)
            logger.debug(
                "phase_historical_archive_completed",
                message_id=obj.message_id,
                archive_size=len(self._archive),
            )
        except Exception as exc:
            errors.append(f"Phase 8 (HistoricalArchive) error: {exc}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_confidence(
        self,
        delivery_attempts: list[DeliveryAttempt],
        acks: list[AcknowledgmentRecord],
    ) -> float:
        if not delivery_attempts:
            return 0.5
        delivered = sum(1 for a in delivery_attempts if a.status == 'delivered')
        delivery_ratio = delivered / len(delivery_attempts)
        ack_ratio = len(acks) / max(len(delivery_attempts), 1)
        return delivery_ratio * 0.6 + ack_ratio * 0.4

    def get_archive(self) -> list[dict[str, Any]]:
        return list(self._archive)


def routing_decisions_present(decisions: list[dict[str, Any]]) -> bool:
    """Check if non-default routing decisions were applied."""
    return any(d.get('rule_id') != 'default' for d in decisions)
