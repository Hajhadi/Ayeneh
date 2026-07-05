"""Segmentation processor for the Ayeneh COG architecture (COG-01).

Splits a raw message list into atomic ConversationSegments — the smallest
unit consumed by downstream linguistic analysis.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from ayeneh.cog.conversation.types import ConversationSegment

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MAX_SEGMENT_LENGTH = 2000  # characters — hard ceiling per segment
MERGE_MIN_LENGTH = 10     # merge very short segments into neighbours


class SegmentationProcessor:
    """Split a message list into atomic ConversationSegments.

    Each message maps to exactly one segment. Messages exceeding
    ``MAX_SEGMENT_LENGTH`` are truncated with a sentinel suffix so that
    downstream processors can detect the truncation.
    """

    def process(
        self,
        messages: list[dict],  # noqa: ANN401 – schema is deliberately loose
        conversation_id: str,
    ) -> list[ConversationSegment]:
        """Return one ``ConversationSegment`` per input message.

        *messages* is a list of dicts with at least ``role`` and ``content``
        keys. Extra keys are ignored. Empty messages are dropped.
        """
        segments: list[ConversationSegment] = []
        seq = 0

        for msg in messages:
            text = msg.get('content', '') or ''
            text = text.strip()
            if not text:
                continue

            if len(text) > MAX_SEGMENT_LENGTH:
                logger.warning(
                    'cog.segment.truncated',
                    original_length=len(text),
                    max_length=MAX_SEGMENT_LENGTH,
                )
                text = text[:MAX_SEGMENT_LENGTH] + '…'

            segment = ConversationSegment(
                segment_id=f'{conversation_id}-seg-{seq}',
                conversation_id=conversation_id,
                speaker=msg.get('role', 'user'),
                text=text,
                timestamp=datetime.now(UTC),
                sequence_number=seq,
                language=msg.get('language', 'en'),
            )
            segments.append(segment)
            seq += 1

        logger.info(
            'cog.segmentation.complete',
            conversation_id=conversation_id,
            segment_count=len(segments),
        )
        return segments

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def merge_short_segments(
        segments: list[ConversationSegment],
        threshold: int = MERGE_MIN_LENGTH,
    ) -> list[ConversationSegment]:
        """Merge consecutive short segments from the same speaker.

        This is an optional post-processing step useful when a speaker's
        utterance has been split across multiple messages (e.g. chat
        applications that split long text).
        """
        if not segments:
            return []

        merged: list[ConversationSegment] = []
        buffer = segments[0]

        for seg in segments[1:]:
            if (
                len(buffer.text) < threshold
                and seg.speaker == buffer.speaker
            ):
                # Merge into the current buffer
                combined_text = f'{buffer.text} {seg.text}'.strip()
                buffer = ConversationSegment(
                    segment_id=buffer.segment_id,
                    conversation_id=buffer.conversation_id,
                    speaker=buffer.speaker,
                    text=combined_text,
                    timestamp=buffer.timestamp,
                    sequence_number=buffer.sequence_number,
                    language=buffer.language,
                )
            else:
                merged.append(buffer)
                buffer = seg

        merged.append(buffer)
        return merged
