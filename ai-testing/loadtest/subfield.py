import asyncio,json,math,os,random,sys,time,collections
import httpx,websockets
BASE='127.0.0.1:8120';SECS=float(sys.argv[1]);WALK=sys.argv[2]=='walk'
async def main():
    hdr={'cf-connecting-ip':'198.18.200.2'}
    async with httpx.AsyncClient(timeout=30) as c:
        tok=(await c.post(f'http://{BASE}/api/session',json={'device_id':os.urandom(16).hex(),'name':'x'},headers=hdr)).json()['token']
        prev={};ch=collections.Counter();sz={};pos=None;t0=time.time();ang=random.random()*6.28;nextm=0;n=0
        async with websockets.connect(f'ws://{BASE}/ws?token={tok}',additional_headers=hdr,max_size=None) as ws:
            while time.time()-t0<SECS:
                try:m=await asyncio.wait_for(ws.recv(),.25)
                except asyncio.TimeoutError:m=None
                now=time.time()
                if m:
                    d=json.loads(m)
                    if d.get('t')=='hello':await ws.send(json.dumps({'t':'act','id':1,'a':'place','start':'chicago','reason':'launch','source':'manual','lat':0,'lng':0,'accuracy':1,'timestamp':now*1000,'ticket':d['placement_ticket'],'request':os.urandom(8).hex()}))
                    elif d.get('t')=='s':
                        n+=1
                        if 'body' in d:
                            s=d['body'].get('survival') or {}
                            for k,v in s.items():
                                sz[k]=len(json.dumps(v))
                                if prev.get(k)!=v:ch[k]+=1
                                prev[k]=v
                            for k,v in d['body'].items():
                                if k=='survival':continue
                                if prev.get('b'+k)!=v:ch['b.'+k]+=1
                                prev['b'+k]=v;sz['b.'+k]=len(json.dumps(v))
                        y=d['you']
                        if y['lat'] or y['lng']:pos=[y['lat'],y['lng']]
                if WALK and pos and now>=nextm:
                    ang+=random.uniform(-.2,.2);await ws.send(json.dumps({'t':'pos','lat':pos[0]+math.sin(ang)*4/111320,'lng':pos[1]+math.cos(ang)*4/(111320*math.cos(math.radians(pos[0]))),'acc':1,'mode':'desk','placement_epoch':1,'floor_epoch':0}));nextm=now+.25
        print('frames',n);print(sorted(((ch[k],k,sz.get(k)) for k in ch),reverse=True))
        await c.delete(f'http://{BASE}/api/me',headers={'authorization':'Bearer '+tok,**hdr})
asyncio.run(main())
