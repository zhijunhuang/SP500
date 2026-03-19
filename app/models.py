from datetime import datetime, date
import secrets
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .utils.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    tokens: Mapped[list["APIToken"]] = relationship("APIToken", back_populates="user")


class EmailLoginCode(Base):
    __tablename__ = "email_login_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(6), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class APIToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship("User", back_populates="tokens")

    @staticmethod
    def generate_token_plain() -> str:
        # 生成给用户看的纯文本 token
        return secrets.token_urlsafe(32)


class SP500Constituent(Base):
    __tablename__ = "sp500_constituents"
    __table_args__ = (
        UniqueConstraint("code", "effective_from", name="uq_code_effective_from"),
        Index("ix_sp500_effective_dates", "effective_from", "effective_to"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str] = mapped_column(String(255))
    effective_from: Mapped[date] = mapped_column(Date, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, index=True, nullable=True)
    raw_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SP500Meta(Base):
    """
    存储数据源/许可等元信息，便于接口里统一返回。
    """

    __tablename__ = "sp500_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
