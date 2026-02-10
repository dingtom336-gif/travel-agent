# SQLAlchemy ORM models for TravelMind
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
  Column,
  Date,
  DateTime,
  ForeignKey,
  Integer,
  Numeric,
  String,
  Text,
  func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
  """Shared base for all ORM models."""
  pass


class User(Base):
  __tablename__ = "users"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  user_id = Column(String(255), unique=True, nullable=False, index=True)
  name = Column(String(100), default="")
  email = Column(String(255), unique=True, nullable=True)
  avatar_url = Column(String(500), nullable=True)
  member_level = Column(String(50), default="standard")
  total_trips = Column(Integer, default=0)
  total_destinations = Column(Integer, default=0)
  join_date = Column(DateTime, server_default=func.now())
  created_at = Column(DateTime, server_default=func.now())

  profile = relationship("UserProfile", back_populates="user", uselist=False)
  sessions = relationship("Session", back_populates="user")
  itineraries = relationship("Itinerary", back_populates="user")


class UserProfile(Base):
  __tablename__ = "user_profiles"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  user_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
    unique=True, nullable=False,
  )
  travel_style = Column(JSONB, default=list)
  budget_preference = Column(String(50), nullable=True)
  accommodation_pref = Column(String(50), nullable=True)
  transport_pref = Column(String(50), nullable=True)
  dietary_restrictions = Column(JSONB, default=list)
  visited_destinations = Column(JSONB, default=list)
  favorite_brands = Column(JSONB, default=list)
  history_summary = Column(Text, default="")
  updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

  user = relationship("User", back_populates="profile")


class Session(Base):
  __tablename__ = "sessions"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  session_id = Column(String(255), unique=True, nullable=False, index=True)
  user_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  title = Column(String(200), nullable=True)
  status = Column(String(20), default="active")
  context_summary = Column(Text, nullable=True)
  state_pool = Column(JSONB, nullable=True)
  created_at = Column(DateTime, server_default=func.now())

  user = relationship("User", back_populates="sessions")
  messages = relationship(
    "Message", back_populates="session",
    order_by="Message.created_at", cascade="all, delete-orphan",
  )
  traces = relationship(
    "AgentTrace", back_populates="session",
    order_by="AgentTrace.created_at", cascade="all, delete-orphan",
  )


class Message(Base):
  __tablename__ = "messages"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  session_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"),
    nullable=False,
  )
  role = Column(String(20), nullable=False)
  content = Column(Text, nullable=False)
  ui_payload = Column(JSONB, nullable=True)
  created_at = Column(DateTime, server_default=func.now())

  session = relationship("Session", back_populates="messages")


class AgentTrace(Base):
  __tablename__ = "agent_traces"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  session_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"),
    nullable=False,
  )
  agent_name = Column(String(50), nullable=False)
  task_id = Column(String(50), nullable=True)
  goal = Column(Text, nullable=True)
  status = Column(String(20), nullable=False)
  summary = Column(Text, nullable=True)
  duration_ms = Column(Integer, default=0)
  error = Column(Text, nullable=True)
  output_result = Column(JSONB, nullable=True)
  created_at = Column(DateTime, server_default=func.now())

  session = relationship("Session", back_populates="traces")


class Itinerary(Base):
  __tablename__ = "itineraries"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  session_id = Column(String(255), nullable=True)
  user_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  title = Column(String(200), nullable=False)
  destination = Column(String(200), nullable=False)
  start_date = Column(Date, nullable=True)
  end_date = Column(Date, nullable=True)
  travelers = Column(Integer, default=1)
  total_budget = Column(Numeric(12, 2), nullable=True)
  currency = Column(String(10), default="CNY")
  status = Column(String(20), default="draft")
  version = Column(Integer, default=1)
  created_at = Column(DateTime, server_default=func.now())
  updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

  user = relationship("User", back_populates="itineraries")
  days = relationship(
    "ItineraryDay", back_populates="itinerary",
    order_by="ItineraryDay.day_number", cascade="all, delete-orphan",
  )
  budget_items = relationship(
    "BudgetItem", back_populates="itinerary",
    cascade="all, delete-orphan",
  )


class ItineraryDay(Base):
  __tablename__ = "itinerary_days"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  itinerary_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("itineraries.id", ondelete="CASCADE"),
    nullable=False,
  )
  day_number = Column(Integer, nullable=False)
  date = Column(Date, nullable=True)
  title = Column(String(200), nullable=True)
  items = Column(JSONB, default=list)
  weather_info = Column(JSONB, nullable=True)
  tips = Column(Text, nullable=True)

  itinerary = relationship("Itinerary", back_populates="days")


class BudgetItem(Base):
  __tablename__ = "budget_items"

  id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  itinerary_id = Column(
    PG_UUID(as_uuid=True), ForeignKey("itineraries.id", ondelete="CASCADE"),
    nullable=False,
  )
  category = Column(String(50), nullable=False)
  name = Column(String(200), nullable=False)
  amount = Column(Numeric(12, 2), nullable=False)
  currency = Column(String(10), default="CNY")
  day = Column(Integer, nullable=True)
  note = Column(Text, nullable=True)

  itinerary = relationship("Itinerary", back_populates="budget_items")
