"""Initial schema – users, profiles, sessions, messages, traces, itineraries

Revision ID: 001
Revises:
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
  # Users
  op.create_table(
    "users",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("user_id", sa.String(255), unique=True, nullable=False),
    sa.Column("name", sa.String(100), server_default=""),
    sa.Column("email", sa.String(255), unique=True, nullable=True),
    sa.Column("avatar_url", sa.String(500), nullable=True),
    sa.Column("member_level", sa.String(50), server_default="standard"),
    sa.Column("total_trips", sa.Integer, server_default="0"),
    sa.Column("total_destinations", sa.Integer, server_default="0"),
    sa.Column("join_date", sa.DateTime, server_default=sa.func.now()),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
  )
  op.create_index("idx_users_user_id", "users", ["user_id"])

  # User profiles
  op.create_table(
    "user_profiles",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("user_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("users.id", ondelete="CASCADE"),
              unique=True, nullable=False),
    sa.Column("travel_style", postgresql.JSONB, server_default="[]"),
    sa.Column("budget_preference", sa.String(50), nullable=True),
    sa.Column("accommodation_pref", sa.String(50), nullable=True),
    sa.Column("transport_pref", sa.String(50), nullable=True),
    sa.Column("dietary_restrictions", postgresql.JSONB, server_default="[]"),
    sa.Column("visited_destinations", postgresql.JSONB, server_default="[]"),
    sa.Column("favorite_brands", postgresql.JSONB, server_default="[]"),
    sa.Column("history_summary", sa.Text, server_default=""),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
  )

  # Sessions
  op.create_table(
    "sessions",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("session_id", sa.String(255), unique=True, nullable=False),
    sa.Column("user_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("title", sa.String(200), nullable=True),
    sa.Column("status", sa.String(20), server_default="active"),
    sa.Column("context_summary", sa.Text, nullable=True),
    sa.Column("state_pool", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
  )
  op.create_index("idx_sessions_session_id", "sessions", ["session_id"])

  # Messages
  op.create_table(
    "messages",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("session_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
    sa.Column("role", sa.String(20), nullable=False),
    sa.Column("content", sa.Text, nullable=False),
    sa.Column("ui_payload", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
  )
  op.create_index("idx_messages_session_id", "messages", ["session_id"])

  # Agent traces
  op.create_table(
    "agent_traces",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("session_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
    sa.Column("agent_name", sa.String(50), nullable=False),
    sa.Column("task_id", sa.String(50), nullable=True),
    sa.Column("goal", sa.Text, nullable=True),
    sa.Column("status", sa.String(20), nullable=False),
    sa.Column("summary", sa.Text, nullable=True),
    sa.Column("duration_ms", sa.Integer, server_default="0"),
    sa.Column("error", sa.Text, nullable=True),
    sa.Column("output_result", postgresql.JSONB, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
  )
  op.create_index("idx_traces_session_id", "agent_traces", ["session_id"])

  # Itineraries
  op.create_table(
    "itineraries",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("session_id", sa.String(255), nullable=True),
    sa.Column("user_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("title", sa.String(200), nullable=False),
    sa.Column("destination", sa.String(200), nullable=False),
    sa.Column("start_date", sa.Date, nullable=True),
    sa.Column("end_date", sa.Date, nullable=True),
    sa.Column("travelers", sa.Integer, server_default="1"),
    sa.Column("total_budget", sa.Numeric(12, 2), nullable=True),
    sa.Column("currency", sa.String(10), server_default="CNY"),
    sa.Column("status", sa.String(20), server_default="draft"),
    sa.Column("version", sa.Integer, server_default="1"),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
  )
  op.create_index("idx_itineraries_user_id", "itineraries", ["user_id"])
  op.create_index("idx_itineraries_session_id", "itineraries", ["session_id"])

  # Itinerary days
  op.create_table(
    "itinerary_days",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("itinerary_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False),
    sa.Column("day_number", sa.Integer, nullable=False),
    sa.Column("date", sa.Date, nullable=True),
    sa.Column("title", sa.String(200), nullable=True),
    sa.Column("items", postgresql.JSONB, server_default="[]"),
    sa.Column("weather_info", postgresql.JSONB, nullable=True),
    sa.Column("tips", sa.Text, nullable=True),
  )
  op.create_index("idx_days_itinerary_id", "itinerary_days", ["itinerary_id"])

  # Budget items
  op.create_table(
    "budget_items",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("itinerary_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False),
    sa.Column("category", sa.String(50), nullable=False),
    sa.Column("name", sa.String(200), nullable=False),
    sa.Column("amount", sa.Numeric(12, 2), nullable=False),
    sa.Column("currency", sa.String(10), server_default="CNY"),
    sa.Column("day", sa.Integer, nullable=True),
    sa.Column("note", sa.Text, nullable=True),
  )
  op.create_index("idx_budget_itinerary_id", "budget_items", ["itinerary_id"])


def downgrade() -> None:
  op.drop_table("budget_items")
  op.drop_table("itinerary_days")
  op.drop_table("itineraries")
  op.drop_table("agent_traces")
  op.drop_table("messages")
  op.drop_table("sessions")
  op.drop_table("user_profiles")
  op.drop_table("users")
