"""Shared base identity and explicit durable permissions. PlayerHome is the stockpile."""
import copy
import hashlib
import secrets
from sqlalchemy import select,delete
from app.models import Player,PlayerHome,BaseInvite,BaseMembership,BaseSelection

def owner(a):return a.home_owner or a.id
def can_build(a):return a.base_role in ('owner','builder')
def publish(w,a):
    w.actors[a.id]=a
    if a.home is not None:
        key=owner(a);w.homes[key]=a.home
        for other in w.actors.values():
            if owner(other)==key:other.home=a.home
    for level in w.levels.values():
        if a.id in level.actors:level.actors[a.id]=a

async def bind(s,w,a):
    selection=await s.get(BaseSelection,a.id)
    key=selection.owner_id if selection else a.id
    membership=await s.get(BaseMembership,(key,a.id)) if key!=a.id else None
    if key!=a.id and membership is None:key=a.id
    row=await s.get(PlayerHome,key)
    a.home_owner=key;a.base_role=membership.role if key!=a.id else 'owner'
    # Never replace a current in-memory base with an older saved snapshot.
    a.home=w.homes.get(key) if key in w.homes else (copy.deepcopy(row.state) if row else None)
    if a.home is not None:w.homes[key]=a.home
    if key==a.id:
        rows=(await s.execute(select(BaseMembership,Player.name).join(Player,Player.id==BaseMembership.member_id).where(BaseMembership.owner_id==key))).all()
        a.base_members=[{'id':r.member_id,'name':name,'role':r.role} for r,name in rows]
    else:a.base_members=[]
    rows=(await s.execute(select(BaseMembership,PlayerHome.state).join(PlayerHome,PlayerHome.player_id==BaseMembership.owner_id).where(BaseMembership.member_id==a.id))).all()
    a.base_choices=[{'owner':a.id,'name':'Personal home'}]+[{'owner':m.owner_id,'name':h.get('name','Shared base')} for m,h in rows]
    return a

def view(a):
    return {'owner':owner(a),'role':a.base_role,'shared':bool(a.home and a.home.get('_shared')),
            'members':copy.deepcopy(a.base_members),'choices':copy.deepcopy(a.base_choices),'can_build':can_build(a)}

async def change(s,w,a,args,now):
    """DB changes only; the Hub rebinds everyone after this transaction commits."""
    op=args.get('op');key=owner(a)
    if a.dead:return {'ok':False,'why':'start a new survivor first'}
    if a.channel or a.pending_work:return {'ok':False,'why':'finish or cancel your work first'}
    if op=='invite':
        if key!=a.id or not a.home:return {'ok':False,'why':'return to your own base before inviting people'}
        role=args.get('role','builder')
        if role not in ('builder','storage'):return {'ok':False,'why':'choose Builder or Storage access'}
        # Enable sharing on the canonical home; do not create another copy of its stock.
        candidate=copy.deepcopy(a)
        candidate.home['_shared']=True;candidate.home.setdefault('_base_version',0)
        from app.game import store
        await store.save(s,candidate,args['_survivor_id'],now,commit=False)
        await s.execute(delete(BaseInvite).where(BaseInvite.owner_id==key))
        code=secrets.token_urlsafe(18)
        s.add(BaseInvite(digest=hashlib.sha256(code.encode()).hexdigest(),owner_id=key,role=role,expires_at=now+86400))
        return {'ok':True,'code':code,'expires_at':now+86400,'message':'Invitation ready for 24 hours. Share it only with the people you want at this base.','_candidate':candidate}
    if op=='join':
        code=str(args.get('invite','')).strip()
        if not 16<=len(code)<=80:return {'ok':False,'why':'enter the invitation code'}
        invite=await s.get(BaseInvite,hashlib.sha256(code.encode()).hexdigest())
        if invite is None or invite.expires_at<=now:return {'ok':False,'why':'invitation is expired or unavailable'}
        if invite.owner_id==a.id:return {'ok':False,'why':'this is your own base'}
        row=await s.get(PlayerHome,invite.owner_id)
        if row is None:return {'ok':False,'why':'base unavailable'}
        member=await s.get(BaseMembership,(invite.owner_id,a.id))
        if member is None:s.add(BaseMembership(owner_id=invite.owner_id,member_id=a.id,role=invite.role))
        # Reusing an older code cannot change a member's current role.
        choice=await s.get(BaseSelection,a.id)
        if choice is None:s.add(BaseSelection(player_id=a.id,owner_id=invite.owner_id))
        else:choice.owner_id=invite.owner_id
        return {'ok':True,'message':'Shared base selected. Your personal home and supplies are preserved.'}
    if op in ('personal','leave'):
        choice=await s.get(BaseSelection,a.id)
        if choice:await s.delete(choice)
        if op=='leave' and key!=a.id:await s.execute(delete(BaseMembership).where(BaseMembership.owner_id==key,BaseMembership.member_id==a.id))
        return {'ok':True,'message':'Personal home selected.' if op=='personal' else 'Left the shared base. Personal home restored.'}
    if op=='select':
        target=args.get('owner',0)
        if target!=a.id and await s.get(BaseMembership,(target,a.id)) is None:return {'ok':False,'why':'you are not a member of that base'}
        choice=await s.get(BaseSelection,a.id)
        if choice:choice.owner_id=target
        else:s.add(BaseSelection(player_id=a.id,owner_id=target))
        return {'ok':True,'message':'Base selected.'}
    if op in ('revoke','close_invites'):
        if key!=a.id:return {'ok':False,'why':'only the owner can manage this base'}
        await s.execute(delete(BaseInvite).where(BaseInvite.owner_id==key))
        if op=='revoke':
            target=args.get('member',0)
            if target==a.id:return {'ok':False,'why':'the owner cannot be revoked'}
            await s.execute(delete(BaseMembership).where(BaseMembership.owner_id==key,BaseMembership.member_id==target))
            await s.execute(delete(BaseSelection).where(BaseSelection.player_id==target,BaseSelection.owner_id==key))
        return {'ok':True,'message':'Access revoked; older invitation codes are also closed.' if op=='revoke' else 'Invitation codes closed.'}
    return {'ok':False,'why':'choose a base action'}
