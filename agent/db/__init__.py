# Database layer – SQLAlchemy async + graceful fallback to in-memory
from agent.db.engine import get_db_session, init_db, close_db, is_db_available
