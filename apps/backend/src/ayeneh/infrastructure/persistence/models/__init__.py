"""SQLAlchemy models package — import all models for Alembic discovery."""

from ayeneh.infrastructure.persistence.models.agent_run import AgentRunModel
from ayeneh.infrastructure.persistence.models.book import (
    BookChapterModel,
    BookChunkModel,
    BookModel,
)
from ayeneh.infrastructure.persistence.models.conversation import ConversationModel
from ayeneh.infrastructure.persistence.models.embedding import EmbeddingModel
from ayeneh.infrastructure.persistence.models.epistemic_profile import EpistemicProfileModel
from ayeneh.infrastructure.persistence.models.execution_plan import ExecutionPlanModel
from ayeneh.infrastructure.persistence.models.execution_plan_template import (
    ExecutionPlanTemplateModel,
)
from ayeneh.infrastructure.persistence.models.habit import HabitModel
from ayeneh.infrastructure.persistence.models.insight import InsightModel
from ayeneh.infrastructure.persistence.models.memory import MemoryModel
from ayeneh.infrastructure.persistence.models.message import MessageModel
from ayeneh.infrastructure.persistence.models.observation import ObservationModel
from ayeneh.infrastructure.persistence.models.pattern import (
    PatternEvidenceModel,
    PatternModel,
    PatternRelationModel,
)
from ayeneh.infrastructure.persistence.models.prompt_template import PromptTemplateModel
from ayeneh.infrastructure.persistence.models.reflection import ReflectionModel
from ayeneh.infrastructure.persistence.models.session import SessionModel
from ayeneh.infrastructure.persistence.models.theme import ThemeEntityModel, ThemeModel
from ayeneh.infrastructure.persistence.models.user import UserModel

__all__ = [
    "AgentRunModel",
    "BookChapterModel",
    "BookChunkModel",
    "BookModel",
    "ConversationModel",
    "EmbeddingModel",
    "EpistemicProfileModel",
    "ExecutionPlanModel",
    "ExecutionPlanTemplateModel",
    "HabitModel",
    "InsightModel",
    "MemoryModel",
    "MessageModel",
    "ObservationModel",
    "PatternEvidenceModel",
    "PatternModel",
    "PatternRelationModel",
    "PromptTemplateModel",
    "ReflectionModel",
    "SessionModel",
    "ThemeEntityModel",
    "ThemeModel",
    "UserModel",
]
