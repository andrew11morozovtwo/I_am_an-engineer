"""
SQLAlchemy ORM models: User, Ban, Warn, Log, Blacklist, ScheduledPost, AiUsage.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import enum

Base = declarative_base()

class UserStatus(enum.Enum):
    """Статусы пользователя"""
    ACTIVE = "active"
    BANNED = "banned"
    RESTRICTED = "restricted"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=False)  # Telegram user_id
    username = Column(String(64), index=True, nullable=True)
    full_name = Column(String(128), nullable=True)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    warn_count = Column(Integer, default=0, nullable=False)  # Количество варнов
    is_banned = Column(Boolean, default=False)  # Для обратной совместимости
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    warns = relationship("Warn", back_populates="user", cascade="all, delete")
    bans = relationship("Ban", back_populates="user", cascade="all, delete")

class Admin(Base):
    """
    Модель администратора с правами.
    """
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)  # Telegram user_id
    username = Column(String(64), nullable=True)  # @username
    full_name = Column(String(128), nullable=True)  # Имя администратора
    role = Column(String(32), default="moderator", nullable=False)  # moderator, senior_admin, owner
    is_active = Column(Boolean, default=True, nullable=False)  # Можно деактивировать
    added_by = Column(Integer, nullable=True)  # user_id кто добавил
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

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
    phrase = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    added_by = Column(Integer, nullable=True)  # admin_id

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(32), nullable=False, index=True)  # Тип события
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Пользователь
    message = Column(Text, nullable=True)  # Сообщение
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)  # Дата

class ScheduledPostStatus(enum.Enum):
    """Статусы отложенного поста"""
    PENDING = "pending"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    FAILED = "failed"

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)  # Текст поста
    scheduled_at = Column(DateTime, nullable=False, index=True)  # Дата/время публикации
    status = Column(SQLEnum(ScheduledPostStatus), default=ScheduledPostStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    published_at = Column(DateTime, nullable=True)  # Когда был опубликован
    channel_id = Column(Integer, nullable=True)  # ID канала для публикации

class AiUsage(Base):
    __tablename__ = "ai_usage"
    id = Column(Integer, primary_key=True)
    request_type = Column(String(32), nullable=False, index=True)  # Тип запроса (FAQ, moderation, comment_generation)
    tokens_used = Column(Integer, nullable=True)  # Количество токенов
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)  # Дата
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Пользователь (если применимо)
    success = Column(Boolean, default=True)  # Успешность запроса
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке (если была)
