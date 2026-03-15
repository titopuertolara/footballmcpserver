from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, nullable=False, default="telegram")
    platform_user_id = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True)
    name = Column(String, nullable=True)
    preferred_position = Column(String, nullable=True)
    skill_level = Column(String, nullable=True)
    location = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    is_subscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organized_games = relationship("Game", back_populates="organizer")
    game_participations = relationship("GamePlayer", back_populates="player")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    location = Column(String, nullable=False)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    game_type = Column(String, default="5v5")
    grass_type = Column(String, default="synthetic")
    players_needed = Column(Integer, default=10)
    positions_needed = Column(String, nullable=True)
    status = Column(
        Enum("open", "full", "closed", "cancelled", "completed", name="game_status"),
        default="open",
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    organizer = relationship("User", back_populates="organized_games")
    players = relationship("GamePlayer", back_populates="game")


class GamePlayer(Base):
    __tablename__ = "game_players"
    __table_args__ = (
        UniqueConstraint("game_id", "player_id", name="uq_game_player"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position = Column(String, nullable=True)
    status = Column(
        Enum("confirmed", "pending", "cancelled", name="player_status"),
        default="confirmed",
    )
    joined_at = Column(DateTime, default=datetime.utcnow)

    game = relationship("Game", back_populates="players")
    player = relationship("User", back_populates="game_participations")


class JoinRequest(Base):
    __tablename__ = "join_requests"
    __table_args__ = (
        UniqueConstraint("game_id", "player_id", name="uq_join_request"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position = Column(String, nullable=True)
    message = Column(String, nullable=True)
    status = Column(
        Enum("pending", "accepted", "rejected", name="request_status"),
        default="pending",
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    game = relationship("Game")
    player = relationship("User")
