"""
Central registry for all SQLModel table models.
"""

# register all database models here to ensure they are imported when creating tables
from ..agent.table import Agent
from ..knowledge_base.table import Thread
from ..user.table import User

# make sure Ruff and other tools will not remove them
__all__ = [
    "Agent",
    "User",
    "Thread",
]
