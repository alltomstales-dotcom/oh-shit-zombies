"""Deleting a player: every row that names them, in the order the foreign keys need."""
from sqlalchemy import delete, or_, select

from app.models import (BaseInvite, BaseMembership, BaseSelection, Player, PlayerHome, PlayerMemory,
                        SessionToken, Survivor, WorldCorpse)


async def delete_player(session, pid: int) -> None:
    await session.execute(delete(SessionToken).where(SessionToken.player_id == pid))
    await session.execute(delete(BaseInvite).where(BaseInvite.owner_id == pid))
    await session.execute(delete(BaseSelection).where(or_(BaseSelection.player_id == pid, BaseSelection.owner_id == pid)))
    await session.execute(delete(BaseMembership).where(or_(BaseMembership.owner_id == pid, BaseMembership.member_id == pid)))
    await session.execute(delete(PlayerMemory).where(PlayerMemory.player_id == pid))
    await session.execute(delete(PlayerHome).where(PlayerHome.player_id == pid))
    await session.execute(delete(Survivor).where(Survivor.player_id == pid))
    # A recovery pack names its owner inside the JSON; the table is small and expires by itself.
    for row in (await session.execute(select(WorldCorpse))).scalars():
        if (row.state or {}).get('owner') == pid:
            await session.delete(row)
    await session.execute(delete(Player).where(Player.id == pid))
    await session.commit()
