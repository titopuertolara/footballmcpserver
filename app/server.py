import json
from collections.abc import AsyncIterator
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan

from app.database.connection import create_async_db_engine, create_async_session_factory, create_tables
from app.services import game_service, user_service

_ORGANIZER_ARGS = ["platform", "organizer_user_id", "organizer_username", "organizer_name"]
_PLAYER_ARGS = ["platform", "player_user_id", "player_username", "player_name"]
_ORG_ID_ARGS = ["platform", "organizer_user_id"]
_ADD_PLAYER_ARGS = ["platform", "organizer_user_id", "player_user_id", "player_username", "player_name"]


@lifespan
async def db_lifespan(server: FastMCP[Any]) -> AsyncIterator[dict[str, object]]:
    create_tables()
    engine = create_async_db_engine()
    session_factory = create_async_session_factory(engine)
    try:
        yield {"engine": engine, "session_factory": session_factory}
    finally:
        await engine.dispose()


mcp = FastMCP("footballbot", lifespan=db_lifespan)


@mcp.tool(exclude_args=_ORGANIZER_ARGS)
async def create_game(
    ctx: Context,
    location: str,
    date: str,
    time: str,
    game_type: str = "5v5",
    grass_type: str = "synthetic",
    players_needed: int = 10,
    positions_needed: str = "",
    platform: str = "",
    organizer_user_id: str = "",
    organizer_username: str = "",
    organizer_name: str = "",
) -> str:
    """Create a new football/soccer game.

    Args:
        location: Where the game will be played
        date: Date of the game (YYYY-MM-DD)
        time: Time of the game (HH:MM)
        game_type: Type of game (e.g. 5v5, 7v7, 11v11)
        grass_type: Type of surface (synthetic, natural, indoor)
        players_needed: Total number of players needed
        positions_needed: Comma-separated positions needed
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        organizer = await user_service.get_or_create_user(
            session, platform, organizer_user_id, organizer_username, organizer_name
        )
        game = await game_service.create_game(
            session,
            organizer_id=organizer.id,
            location=location,
            date=date,
            time=time,
            game_type=game_type,
            grass_type=grass_type,
            players_needed=players_needed,
            positions_needed=positions_needed or None,
        )
        return json.dumps(
            {
                "success": True,
                "game_id": game.id,
                "location": game.location,
                "date": game.date,
                "time": game.time,
                "game_type": game.game_type,
                "grass_type": game.grass_type,
                "players_needed": game.players_needed,
                "positions_needed": game.positions_needed,
                "status": game.status,
            }
        )


@mcp.tool()
async def find_games(
    ctx: Context,
    location: str = "",
    date: str = "",
    position: str = "",
) -> str:
    """Find open football/soccer games.

    Args:
        location: Filter by location (partial match)
        date: Filter by date (YYYY-MM-DD)
        position: Filter by needed position
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        games = await game_service.find_games(
            session,
            location=location or None,
            date=date or None,
            position=position or None,
        )
        results = []
        for g in games:
            current_players = len(g.players)
            results.append(
                {
                    "game_id": g.id,
                    "location": g.location,
                    "date": g.date,
                    "time": g.time,
                    "game_type": g.game_type,
                    "grass_type": g.grass_type,
                    "players_needed": g.players_needed,
                    "current_players": current_players,
                    "spots_remaining": g.players_needed - current_players,
                    "positions_needed": g.positions_needed,
                    "organizer": g.organizer.name or g.organizer.username,
                    "organizer_platform_user_id": g.organizer.platform_user_id,
                    "organizer_platform": g.organizer.platform,
                    "status": g.status,
                }
            )
        return json.dumps({"games": results, "count": len(results)})


@mcp.tool(exclude_args=_ADD_PLAYER_ARGS)
async def add_player_to_game(
    ctx: Context,
    game_id: int,
    position: str = "",
    platform: str = "",
    organizer_user_id: str = "",
    player_user_id: str = "",
    player_username: str = "",
    player_name: str = "",
) -> str:
    """Add a player to a game. Only the game organizer can use this.

    Args:
        game_id: ID of the game
        position: Position for the player
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        organizer = await user_service.get_or_create_user(
            session, platform, organizer_user_id, "", ""
        )
        player = await user_service.get_or_create_user(
            session, platform, player_user_id, player_username, player_name
        )
        result = await game_service.add_player_to_game(
            session,
            game_id=game_id,
            organizer_user_id=organizer.id,
            player_id=player.id,
            position=position or None,
        )
        return json.dumps(result)


@mcp.tool()
async def get_game_details(ctx: Context, game_id: int) -> str:
    """Get full details of a specific game including all players.

    Args:
        game_id: ID of the game
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        game = await game_service.get_game_details(session, game_id)
        if not game:
            return json.dumps({"error": "Game not found"})

        players = []
        for gp in game.players:
            players.append(
                {
                    "name": gp.player.name or gp.player.username,
                    "position": gp.position,
                    "status": gp.status,
                }
            )

        return json.dumps(
            {
                "game_id": game.id,
                "location": game.location,
                "date": game.date,
                "time": game.time,
                "game_type": game.game_type,
                "grass_type": game.grass_type,
                "players_needed": game.players_needed,
                "current_players": len(players),
                "spots_remaining": game.players_needed - len(players),
                "positions_needed": game.positions_needed,
                "organizer": game.organizer.name or game.organizer.username,
                "organizer_username": game.organizer.username,
                "organizer_platform_user_id": game.organizer.platform_user_id,
                "organizer_platform": game.organizer.platform,
                "status": game.status,
                "players": players,
            }
        )


@mcp.tool(exclude_args=_PLAYER_ARGS)
async def subscribe_player(
    ctx: Context,
    preferred_position: str = "",
    skill_level: str = "",
    location: str = "",
    availability: str = "",
    platform: str = "",
    player_user_id: str = "",
    player_username: str = "",
    player_name: str = "",
) -> str:
    """Subscribe as an available player so organizers can find you.

    Args:
        preferred_position: Preferred position (e.g. goalkeeper, defender, midfielder, forward)
        skill_level: Skill level (e.g. beginner, intermediate, advanced, pro)
        location: Area or neighborhood where they prefer to play
        availability: When available (e.g. "weekends", "weekday evenings")
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        player = await user_service.subscribe_player(
            session,
            platform=platform,
            platform_user_id=player_user_id,
            username=player_username,
            name=player_name,
            preferred_position=preferred_position or None,
            skill_level=skill_level or None,
            location=location or None,
            availability=availability or None,
        )
        return json.dumps(
            {
                "success": True,
                "player_id": player.id,
                "name": player.name,
                "preferred_position": player.preferred_position,
                "skill_level": player.skill_level,
                "location": player.location,
                "availability": player.availability,
                "is_subscribed": True,
            }
        )


@mcp.tool(exclude_args=["platform", "player_user_id"])
async def update_player_profile(
    ctx: Context,
    preferred_position: str = "",
    skill_level: str = "",
    location: str = "",
    availability: str = "",
    platform: str = "",
    player_user_id: str = "",
) -> str:
    """Update a subscribed player's profile.

    Args:
        preferred_position: Preferred position (e.g. goalkeeper, defender, midfielder, forward)
        skill_level: Skill level (e.g. beginner, intermediate, advanced, pro)
        location: Area or neighborhood where they prefer to play
        availability: When available (e.g. "weekends", "weekday evenings")
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        player = await user_service.update_player_profile(
            session,
            platform=platform,
            platform_user_id=player_user_id,
            preferred_position=preferred_position or None,
            skill_level=skill_level or None,
            location=location or None,
            availability=availability or None,
        )
        if not player:
            return json.dumps({"success": False, "error": "Player not found"})
        return json.dumps(
            {
                "success": True,
                "name": player.name,
                "preferred_position": player.preferred_position,
                "skill_level": player.skill_level,
                "location": player.location,
                "availability": player.availability,
            }
        )


@mcp.tool()
async def find_players(
    ctx: Context,
    position: str = "",
    skill_level: str = "",
    location: str = "",
    availability: str = "",
) -> str:
    """Find subscribed players by filters. Useful for organizers looking for players.

    Args:
        position: Filter by preferred position
        skill_level: Filter by skill level
        location: Filter by location/neighborhood (partial match)
        availability: Filter by availability (partial match)
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        players = await user_service.find_players(
            session,
            position=position or None,
            skill_level=skill_level or None,
            location=location or None,
            availability=availability or None,
        )
        results = []
        for p in players:
            results.append(
                {
                    "name": p.name or p.username,
                    "username": p.username,
                    "platform": p.platform,
                    "platform_user_id": p.platform_user_id,
                    "preferred_position": p.preferred_position,
                    "skill_level": p.skill_level,
                    "location": p.location,
                    "availability": p.availability,
                }
            )
        return json.dumps({"players": results, "count": len(results)})


@mcp.tool(exclude_args=_PLAYER_ARGS)
async def request_to_join_game(
    ctx: Context,
    game_id: int,
    position: str = "",
    message: str = "",
    platform: str = "",
    player_user_id: str = "",
    player_username: str = "",
    player_name: str = "",
) -> str:
    """Send a request to join a game. The organizer will be notified and must accept.

    Args:
        game_id: ID of the game to join
        position: Preferred position for this game
        message: Optional message to the organizer
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        player = await user_service.get_or_create_user(
            session, platform, player_user_id, player_username, player_name
        )
        result = await game_service.create_join_request(
            session,
            game_id=game_id,
            player_id=player.id,
            position=position or None,
            message=message or None,
        )
        return json.dumps(result)


@mcp.tool(exclude_args=_ORG_ID_ARGS)
async def accept_join_request(
    ctx: Context,
    request_id: int,
    platform: str = "",
    organizer_user_id: str = "",
) -> str:
    """Accept a player's join request. Only the game organizer can accept.

    Args:
        request_id: ID of the join request to accept
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        organizer = await user_service.get_or_create_user(
            session, platform, organizer_user_id, "", ""
        )
        result = await game_service.accept_join_request(
            session,
            request_id=request_id,
            organizer_user_id=organizer.id,
        )
        return json.dumps(result)


@mcp.tool(exclude_args=_ORG_ID_ARGS)
async def reject_join_request(
    ctx: Context,
    request_id: int,
    platform: str = "",
    organizer_user_id: str = "",
) -> str:
    """Reject a player's join request. Only the game organizer can reject.

    Args:
        request_id: ID of the join request to reject
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        organizer = await user_service.get_or_create_user(
            session, platform, organizer_user_id, "", ""
        )
        result = await game_service.reject_join_request(
            session,
            request_id=request_id,
            organizer_user_id=organizer.id,
        )
        return json.dumps(result)


@mcp.tool(exclude_args=_ORG_ID_ARGS)
async def get_pending_requests(
    ctx: Context,
    game_id: int,
    platform: str = "",
    organizer_user_id: str = "",
) -> str:
    """Get all pending join requests for a game. Only the organizer can view.

    Args:
        game_id: ID of the game
    """
    session_factory = ctx.lifespan_context["session_factory"]
    async with session_factory() as session:
        organizer = await user_service.get_or_create_user(
            session, platform, organizer_user_id, "", ""
        )
        result = await game_service.get_pending_requests(
            session,
            game_id=game_id,
            organizer_user_id=organizer.id,
        )
        return json.dumps(result)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, stateless_http=True)
