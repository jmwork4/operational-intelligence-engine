"""Import all ORM models so Alembic autogenerate can discover them."""

from packages.db.models.alert import Alert
from packages.db.models.audit import AuditLog
from packages.db.models.document import Document, DocumentChunk, Embedding
from packages.db.models.event import Event
from packages.db.models.process import Process
from packages.db.models.prompt import PromptEvaluation, PromptTemplate
from packages.db.models.resource import Resource
from packages.db.models.rule import Rule
from packages.db.models.task_lock import TaskExecutionLock
from packages.db.models.tenant import Tenant
from packages.db.models.transaction import Transaction
from packages.db.models.user import User

__all__ = [
    "Alert",
    "AuditLog",
    "Document",
    "DocumentChunk",
    "Embedding",
    "Event",
    "Process",
    "PromptEvaluation",
    "PromptTemplate",
    "Resource",
    "Rule",
    "TaskExecutionLock",
    "Tenant",
    "Transaction",
    "User",
]
