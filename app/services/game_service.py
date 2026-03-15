from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database.models import Game, GamePlayer, JoinRequest


async def close_expired_games(session: AsyncSession, timezone_str: str = "America/Bogota") -> None:
    """Close games that start within the next 2 hours or have already passed."""
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(timezone_str))
    cutoff = now + timedelta(hours=2)
    cutoff_date = cutoff.strftime("%Y-%m-%d")
    cutoff_time = cutoff.strftime("%H:%M")

    # Close games where date < today, or date == today and time <= cutoff
    result = await session.execute(
        select(Game).filter(
            Game.status == "open",
        )
    )
    games = result.scalars().all()
    for game in games:
        game_date = game.date
        game_time = game.time or "00:00"
        if game_date < cutoff_date or (game_date == cutoff_date and game_time <= cutoff_time):
            game.status = "closed"

    await session.commit()


async def create_game(
    session: AsyncSession,
    organizer_id: int,
    location: str,
    date: str,
    time: str,
    game_type: str = "5v5",
    grass_type: str = "synthetic",
    players_needed: int = 10,
    positions_needed: str = None,
) -> Game:
    game = Game(
        organizer_id=organizer_id,
        location=location,
        date=date,
        time=time,
        game_type=game_type,
        grass_type=grass_type,
        players_needed=players_needed,
        positions_needed=positions_needed,
        status="open",
    )
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game


async def find_games(
    session: AsyncSession,
    location: str = None,
    date: str = None,
    position: str = None,
) -> list[Game]:
    await close_expired_games(session)

    query = (
        select(Game)
        .options(joinedload(Game.organizer), joinedload(Game.players))
        .filter(Game.status == "open")
    )
    if location:
        query = query.filter(Game.location.ilike(f"%{location}%"))
    if date:
        query = query.filter(Game.date == date)
    if position:
        query = query.filter(Game.positions_needed.ilike(f"%{position}%"))
    result = await session.execute(query)
    return result.scalars().unique().all()


async def add_player_to_game(
    session: AsyncSession,
    game_id: int,
    organizer_user_id: int,
    player_id: int,
    position: str = None,
) -> dict:
    result = await session.execute(
        select(Game)
        .options(joinedload(Game.organizer), joinedload(Game.players))
        .filter(Game.id == game_id)
    )
    game = result.scalars().unique().first()

    if not game:
        return {"success": False, "error": "Game not found"}

    if game.organizer_id != organizer_user_id:
        return {"success": False, "error": "Only the organizer can add players to this game"}

    if game.status != "open":
        return {"success": False, "error": f"Game is {game.status}, not accepting new players"}

    existing_result = await session.execute(
        select(GamePlayer).filter(GamePlayer.game_id == game_id, GamePlayer.player_id == player_id)
    )
    if existing_result.scalars().first():
        return {"success": False, "error": "This player is already in the game"}

    gp = GamePlayer(game_id=game_id, player_id=player_id, position=position)
    session.add(gp)

    current_players = len(game.players) + 1
    if current_players >= game.players_needed:
        game.status = "full"

    await session.commit()

    return {
        "success": True,
        "game_id": game.id,
        "game_location": game.location,
        "game_date": game.date,
        "game_time": game.time,
        "player_added": True,
        "spots_remaining": game.players_needed - current_players,
    }


async def get_game_details(session: AsyncSession, game_id: int) -> Game | None:
    result = await session.execute(
        select(Game)
        .options(
            joinedload(Game.organizer),
            joinedload(Game.players).joinedload(GamePlayer.player),
        )
        .filter(Game.id == game_id)
    )
    return result.scalars().unique().first()


async def create_join_request(
    session: AsyncSession,
    game_id: int,
    player_id: int,
    position: str = None,
    message: str = None,
) -> dict:
    result = await session.execute(
        select(Game)
        .options(joinedload(Game.organizer), joinedload(Game.players))
        .filter(Game.id == game_id)
    )
    game = result.scalars().unique().first()

    if not game:
        return {"success": False, "error": "Game not found"}

    if game.status != "open":
        return {"success": False, "error": f"Game is {game.status}, not accepting requests"}

    # Check if already a player
    existing_player = await session.execute(
        select(GamePlayer).filter(GamePlayer.game_id == game_id, GamePlayer.player_id == player_id)
    )
    if existing_player.scalars().first():
        return {"success": False, "error": "You are already in this game"}

    # Check if already has an existing request
    existing_request = await session.execute(
        select(JoinRequest).filter(
            JoinRequest.game_id == game_id,
            JoinRequest.player_id == player_id,
        )
    )
    existing = existing_request.scalars().first()
    if existing:
        if existing.status == "pending":
            return {"success": False, "error": "You already have a pending request for this game"}
        if existing.status == "rejected":
            return {"success": False, "error": "Your request to join this game was rejected by the organizer"}
        if existing.status == "accepted":
            return {"success": False, "error": "You are already accepted into this game"}

    jr = JoinRequest(game_id=game_id, player_id=player_id, position=position, message=message)
    session.add(jr)
    await session.commit()
    await session.refresh(jr)

    # Load the player to include their info in the response
    from app.database.models import User
    player_result = await session.execute(
        select(User).filter(User.id == player_id)
    )
    player = player_result.scalars().first()

    return {
        "success": True,
        "request_id": jr.id,
        "game_id": game.id,
        "game_location": game.location,
        "game_date": game.date,
        "game_time": game.time,
        "organizer_platform": game.organizer.platform,
        "organizer_platform_user_id": game.organizer.platform_user_id,
        "organizer_name": game.organizer.name or game.organizer.username,
        "player_platform_user_id": player.platform_user_id if player else "",
        "player_name": player.name or player.username if player else "",
        "position": jr.position,
    }


async def accept_join_request(
    session: AsyncSession,
    request_id: int,
    organizer_user_id: int,
) -> dict:
    result = await session.execute(
        select(JoinRequest)
        .options(
            joinedload(JoinRequest.game).joinedload(Game.organizer),
            joinedload(JoinRequest.game).joinedload(Game.players),
            joinedload(JoinRequest.player),
        )
        .filter(JoinRequest.id == request_id)
    )
    jr = result.scalars().unique().first()

    if not jr:
        return {"success": False, "error": "Join request not found"}

    if jr.game.organizer_id != organizer_user_id:
        return {"success": False, "error": "Only the organizer can accept requests"}

    if jr.status != "pending":
        return {"success": False, "error": f"Request is already {jr.status}"}

    if jr.game.status != "open":
        return {"success": False, "error": f"Game is {jr.game.status}, not accepting players"}

    # Add player to game
    gp = GamePlayer(game_id=jr.game_id, player_id=jr.player_id, position=jr.position)
    session.add(gp)
    jr.status = "accepted"

    current_players = len(jr.game.players) + 1
    if current_players >= jr.game.players_needed:
        jr.game.status = "full"

    await session.commit()

    return {
        "success": True,
        "request_id": jr.id,
        "game_id": jr.game_id,
        "player_name": jr.player.name or jr.player.username,
        "player_platform_user_id": jr.player.platform_user_id,
        "position": jr.position,
        "spots_remaining": jr.game.players_needed - current_players,
    }


async def reject_join_request(
    session: AsyncSession,
    request_id: int,
    organizer_user_id: int,
) -> dict:
    result = await session.execute(
        select(JoinRequest)
        .options(
            joinedload(JoinRequest.game).joinedload(Game.organizer),
            joinedload(JoinRequest.player),
        )
        .filter(JoinRequest.id == request_id)
    )
    jr = result.scalars().unique().first()

    if not jr:
        return {"success": False, "error": "Join request not found"}

    if jr.game.organizer_id != organizer_user_id:
        return {"success": False, "error": "Only the organizer can reject requests"}

    if jr.status != "pending":
        return {"success": False, "error": f"Request is already {jr.status}"}

    jr.status = "rejected"
    await session.commit()

    return {
        "success": True,
        "request_id": jr.id,
        "game_id": jr.game_id,
        "player_name": jr.player.name or jr.player.username,
        "player_platform_user_id": jr.player.platform_user_id,
    }


async def get_pending_requests(
    session: AsyncSession,
    game_id: int,
    organizer_user_id: int,
) -> dict:
    game_result = await session.execute(
        select(Game).filter(Game.id == game_id)
    )
    game = game_result.scalars().first()

    if not game:
        return {"success": False, "error": "Game not found"}

    if game.organizer_id != organizer_user_id:
        return {"success": False, "error": "Only the organizer can view requests"}

    result = await session.execute(
        select(JoinRequest)
        .options(joinedload(JoinRequest.player))
        .filter(JoinRequest.game_id == game_id, JoinRequest.status == "pending")
    )
    requests = result.scalars().unique().all()

    return {
        "success": True,
        "requests": [
            {
                "request_id": r.id,
                "player_name": r.player.name or r.player.username,
                "player_platform_user_id": r.player.platform_user_id,
                "position": r.position,
                "message": r.message,
            }
            for r in requests
        ],
        "count": len(requests),
    }
