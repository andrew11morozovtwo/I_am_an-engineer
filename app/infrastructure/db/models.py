"""
SQLAlchemy ORM models: User, Ban, Warn, Log, Blacklist.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=False)  # Telegram user_id
    username = Column(String(64), index=True, nullable=True)
    full_name = Column(String(128), nullable=True)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    warns = relationship("Warn", back_populates="user", cascade="all, delete")
    bans = relationship("Ban", back_populates="user", cascade="all, delete")

class Ban(Base):
    __tablename__ = "bans"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String(255), nullable=True)
    until = Column(DateTime, nullable=True)  # Ban expiry
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="bans")

class Warn(Base):
    __tablename__ = "warns"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="warns")

class BlacklistItem(Base):
    __tablename__ = "blacklist"
    id = Column(Integer, primary_key=True)
    phrase = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    added_by = Column(Integer, nullable=True)  # admin_id

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(32), nullable=False)
    user_id = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
