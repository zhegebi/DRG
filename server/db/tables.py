"""
Central registry for all SQLModel table models.
"""

# register all database models here to ensure they are imported when creating tables
from ..drg_agent.table import DrgTask
from ..docgen_agent.table import DocgenTask
from ..knowledge_base.table import Document
from ..user.table import User

# make sure Ruff and other tools will not remove them
__all__ = ["User", "DrgTask", "DocgenTask", "Document"]
