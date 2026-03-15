from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def subscribe_player(
    session: AsyncSession,
    platform: str,
    platform_user_id: str,
    username: str,
    name: str,
    preferred_position: str = None,
    skill_level: str = None,
    location: str = None,
    availability: str = None,
) -> User:
    user = await get_or_create_user(session, platform, platform_user_id, username, name)
    user.is_subscribed = True
    if preferred_position:
        user.preferred_position = preferred_position
    if skill_level:
        user.skill_level = skill_level
    if location:
        user.location = location
    if availability:
        user.availability = availability
    await session.commit()
    await session.refresh(user)
    return user


async def update_player_profile(
    session: AsyncSession,
    platform: str,
    platform_user_id: str,
    preferred_position: str = None,
    skill_level: str = None,
    location: str = None,
    availability: str = None,
) -> User | None:
    result = await session.execute(
        select(User).filter(User.platform == platform, User.platform_user_id == platform_user_id)
    )
    user = result.scalars().first()
    if not user:
        return None
    if preferred_position:
        user.preferred_position = preferred_position
    if skill_level:
        user.skill_level = skill_level
    if location:
        user.location = location
    if availability:
        user.availability = availability
    await session.commit()
    await session.refresh(user)
    return user


async def find_players(
    session: AsyncSession,
    position: str = None,
    skill_level: str = None,
    location: str = None,
    availability: str = None,
) -> list[User]:
    query = select(User).filter(User.is_subscribed == True)
    if position:
        query = query.filter(User.preferred_position.ilike(f"%{position}%"))
    if skill_level:
        query = query.filter(User.skill_level.ilike(f"%{skill_level}%"))
    if location:
        query = query.filter(User.location.ilike(f"%{location}%"))
    if availability:
        query = query.filter(User.availability.ilike(f"%{availability}%"))
    result = await session.execute(query)
    return result.scalars().all()


async def get_or_create_user(
    session: AsyncSession,
    platform: str,
    platform_user_id: str,
    username: str = None,
    name: str = None,
) -> User:
    result = await session.execute(
        select(User).filter(User.platform == platform, User.platform_user_id == platform_user_id)
    )
    user = result.scalars().first()

    if user:
        if username and user.username != username:
            user.username = username
        if name and user.name != name:
            user.name = name
        await session.commit()
        return user

    user = User(
        platform=platform,
        platform_user_id=platform_user_id,
        username=username,
        name=name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
