"""Highlight types -- key points (notes) and action items (tasks)."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import Field

from ._base import BaseSchema


class HighlightType(str, Enum):
    """Discriminator between a key-point (UX label: "note") and an action-item (UX label: "task").

    The recap paper uses "key-points" / "action-items" in the model layer and
    "notes" / "tasks" in the UX layer. We keep the model vocabulary
    (`KEY_POINT` / `ACTION_ITEM`) as the canonical names. The UX labels are
    applied at the UI / i18n boundary, not in the enum, because the
    Vietnamese UI uses "ghi chú" / "việc cần làm" rather than literal
    English aliases.
    """

    KEY_POINT = "key_point"
    ACTION_ITEM = "action_item"


class HighlightSource(str, Enum):
    """Whether a highlight came from the model or the user."""

    AUTO = "auto"
    MANUAL = "manual"


class Highlight(BaseSchema):
    """A key point or action item attached to a segment/chunk.

    Notes are observations; tasks have a checkbox for completion tracking.
    """

    highlight_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this highlight.",
    )
    type: HighlightType = Field(
        default=HighlightType.KEY_POINT,
        description="KEY_POINT (UX: 'note') or ACTION_ITEM (UX: 'task').",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Highlight text content.",
    )
    segment_id: Optional[UUID] = Field(
        default=None,
        description="Owning segment UUID, if scoped to a chapter.",
    )
    chunk_id: Optional[UUID] = Field(
        default=None,
        description="Owning chunk UUID, if scoped to a chunk.",
    )
    starred: bool = Field(
        default=False,
        description="Whether the user marked this highlight as important.",
    )
    checked: bool = Field(
        default=False,
        description="Whether the user has checked off this action item.",
    )
    source: HighlightSource = Field(
        default=HighlightSource.AUTO,
        description="Where the highlight originated (model or user).",
    )

    def toggle_star(self) -> "Highlight":
        """Return a copy with the starred flag flipped."""
        return self.model_copy(update={"starred": not self.starred})

    def toggle_check(self) -> "Highlight":
        """Return a copy with the checked flag flipped."""
        return self.model_copy(update={"checked": not self.checked})
