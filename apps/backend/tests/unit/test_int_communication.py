"""Unit tests for INT-03 Cross-Module Communication Bus types and engine."""

from __future__ import annotations

import pytest

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
    ROUTING_STRATEGIES,
)
from ayeneh.int.communication.engine import CommunicationBus


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestMessagePayload:
    def test_default_creation(self) -> None:
        payload = MessagePayload()
        assert payload.content_type == 'application/json'
        assert payload.schema_version == '1.0'

    def test_with_data(self) -> None:
        payload = MessagePayload(data={'key': 'value'})
        assert payload.data['key'] == 'value'


class TestRoutingRule:
    def test_default_creation(self) -> None:
        rule = RoutingRule(rule_id='r1')
        assert rule.is_active is True
        assert rule.strategy == 'direct'


class TestDeliveryAttempt:
    def test_default_creation(self) -> None:
        attempt = DeliveryAttempt(attempt_id='d1')
        assert attempt.status == 'pending'
        assert attempt.latency_ms == 0.0


class TestAcknowledgmentRecord:
    def test_default_creation(self) -> None:
        ack = AcknowledgmentRecord(ack_id='a1', module_id='mod1')
        assert ack.processed is False


class TestCommunicationObject:
    def test_valid_creation(self) -> None:
        obj = CommunicationObject(
            message_id='msg1',
            sender_module='sender',
            recipient_modules=('rec1',),
            message_type='information',
        )
        assert obj.message_id == 'msg1'
        assert obj.delivery_status == 'pending'

    def test_all_valid_message_types(self) -> None:
        for msg_type in MESSAGE_CATEGORIES:
            obj = CommunicationObject(
                message_id='msg1',
                message_type=msg_type,
            )
            assert obj.message_type == msg_type

    def test_invalid_message_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid message type"):
            CommunicationObject(
                message_id='msg1',
                message_type='invalid_type',
            )

    def test_all_valid_delivery_statuses(self) -> None:
        for status in DELIVERY_STATUSES:
            obj = CommunicationObject(
                message_id='msg1',
                message_type='information',
                delivery_status=status,
            )
            assert obj.delivery_status == status

    def test_invalid_delivery_status_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid delivery status"):
            CommunicationObject(
                message_id='msg1',
                message_type='information',
                delivery_status='invalid',
            )

    def test_frozen(self) -> None:
        obj = CommunicationObject(
            message_id='msg1',
            message_type='information',
        )
        with pytest.raises(AttributeError):
            obj.message_id = 'msg2'  # type: ignore[misc]


class TestCommunicationResult:
    def test_all_delivered_empty(self) -> None:
        result = CommunicationResult()
        assert result.all_delivered is False

    def test_all_delivered_true(self) -> None:
        result = CommunicationResult(
            delivery_attempts=(
                DeliveryAttempt(status='delivered'),
                DeliveryAttempt(status='acknowledged'),
            ),
        )
        assert result.all_delivered is True

    def test_all_delivered_false(self) -> None:
        result = CommunicationResult(
            delivery_attempts=(
                DeliveryAttempt(status='delivered'),
                DeliveryAttempt(status='failed'),
            ),
        )
        assert result.all_delivered is False

    def test_delivery_count(self) -> None:
        result = CommunicationResult(
            delivery_attempts=(DeliveryAttempt(), DeliveryAttempt(), DeliveryAttempt()),
        )
        assert result.delivery_count == 3


class TestConstants:
    def test_message_categories(self) -> None:
        assert 'information' in MESSAGE_CATEGORIES
        assert 'governance_command' in MESSAGE_CATEGORIES
        assert len(MESSAGE_CATEGORIES) == 10

    def test_delivery_statuses(self) -> None:
        assert 'pending' in DELIVERY_STATUSES
        assert 'delivered' in DELIVERY_STATUSES

    def test_routing_strategies(self) -> None:
        assert 'direct' in ROUTING_STRATEGIES
        assert 'broadcast' in ROUTING_STRATEGIES


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestCommunicationBus:
    def setup_method(self) -> None:
        self.bus = CommunicationBus()

    def test_basic_send(self) -> None:
        result = self.bus.send(
            sender_module='mod_a',
            recipient_modules=['mod_b'],
            message_type='information',
            payload={'data': 'hello'},
        )
        assert result.message_id
        assert result.communication_object is not None
        assert result.duration_ms >= 0

    def test_send_with_all_fields(self) -> None:
        result = self.bus.send(
            sender_module='mod_a',
            recipient_modules=['mod_b', 'mod_c'],
            message_type='request',
            payload={'action': 'query'},
            priority=5,
            correlation_id='corr1',
        )
        assert result.communication_object is not None
        # base priority 5 + request type boost 5 = 10
        assert result.communication_object.priority == 10
        assert result.delivery_count == 2

    def test_send_no_recipients(self) -> None:
        result = self.bus.send(
            sender_module='mod_a',
            message_type='notification',
        )
        assert result.message_id
        assert result.delivery_count == 0

    def test_send_governance_command_priority(self) -> None:
        result = self.bus.send(
            sender_module='governance',
            recipient_modules=['mod_a'],
            message_type='governance_command',
            priority=0,
        )
        assert result.communication_object is not None
        # Governance commands get a priority boost
        assert result.communication_object.priority > 0

    def test_send_with_routing_rules(self) -> None:
        self.bus.add_routing_rule(RoutingRule(
            rule_id='rule1',
            source_pattern='mod_a',
            strategy='direct',
        ))
        result = self.bus.send(
            sender_module='mod_a',
            recipient_modules=['mod_b'],
            message_type='information',
        )
        assert len(result.routing_decisions) >= 1

    def test_archive_grows(self) -> None:
        self.bus.send(
            sender_module='a',
            recipient_modules=['b'],
            message_type='information',
        )
        assert len(self.bus.get_archive()) == 1
        self.bus.send(
            sender_module='a',
            recipient_modules=['c'],
            message_type='event',
        )
        assert len(self.bus.get_archive()) == 2

    def test_completes_all_phases(self) -> None:
        result = self.bus.send(
            sender_module='sender',
            recipient_modules=['recv1', 'recv2'],
            message_type='feedback',
            payload={'rating': 5},
            priority=3,
        )
        assert result.communication_object is not None
        assert len(result.delivery_attempts) == 2
        assert len(result.acknowledgments) == 2
        assert result.duration_ms >= 0

    def test_send_with_context(self) -> None:
        result = self.bus.send(
            sender_module='mod_a',
            recipient_modules=['mod_b'],
            message_type='warning',
            context={'urgent': True, 'known_modules': ['mod_c']},
        )
        # Urgent context should boost priority
        assert result.communication_object is not None
        assert result.communication_object.priority > 0

    def test_frozen_result(self) -> None:
        result = self.bus.send(
            sender_module='a',
            recipient_modules=['b'],
            message_type='information',
        )
        with pytest.raises(AttributeError):
            result.message_id = 'changed'  # type: ignore[misc]
