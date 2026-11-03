#!/usr/bin/env python3
"""One walking client: which keys are in each frame, how big, and how often. Deletes its account."""
import asyncio,json,math,os,random,sys,time,collections
import httpx,websockets
BASE='127.0.0.1:8120';SECS=float(sys.argv[1]);WALK=sys.argv[2]=='walk';START=sys.argv[3] if len(sys.argv)>3 else 'chicago'
async def main():
    hdr={'cf-connecting-ip':'198.18.200.1'}
    async with httpx.AsyncClient(timeout=30) as c:
        tok=(await c.post(f'http://{BASE}/api/session',json={'device_id':os.urandom(16).hex(),'name':'x'},headers=hdr)).json()['token']
        present=collections.Counter();size=collections.Counter();frames=0;total=0;sizes=[];pos=None;t0=time.time();ang=random.random()*6.28;prev={}
        changes=collections.Counter()
        async with websockets.connect(f'ws://{BASE}/ws?token={tok}',additional_headers=hdr,max_size=None,compression='deflate') as ws:
            print('ext',ws.response.headers.get('sec-websocket-extensions'))
            nextm=0
            while time.time()-t0<SECS:
                try:m=await asyncio.wait_for(ws.recv(),.25)
                except asyncio.TimeoutError:m=None
                now=time.time()
                if m:
                    d=json.loads(m)
                    if d.get('t')=='hello':
                        await ws.send(json.dumps({'t':'act','id':1,'a':'place','start':START,'reason':'launch','source':'manual','lat':0,'lng':0,'accuracy':1,'timestamp':now*1000,'ticket':d['placement_ticket'],'request':os.urandom(8).hex()}))
                    elif d.get('t')=='s':
                        frames+=1;total+=len(m);sizes.append(len(m))
                        for k,v in d.items():
                            n=len(json.dumps(v));present[k]+=1;size[k]+=n
                            if prev.get(k)!=v:changes[k]+=1
                            prev[k]=v
                        if 'body' in d:
                            for k,v in d['body'].items():
                                if prev.get('b:'+k)!=v:changes['body.'+k]+=1;size['body.'+k]+=len(json.dumps(v))
                                prev['b:'+k]=v
                        y=d['you']
                        if y['lat'] or y['lng']:pos=[y['lat'],y['lng']]
                if WALK and pos and now>=nextm:
                    ang+=random.uniform(-.2,.2);await ws.send(json.dumps({'t':'pos','lat':pos[0]+math.sin(ang)*4/111320,'lng':pos[1]+math.cos(ang)*4/(111320*math.cos(math.radians(pos[0]))),'acc':1,'mode':'desk','placement_epoch':1,'floor_epoch':0}));nextm=now+.25
        el=time.time()-t0
        print(f'frames {frames} ({frames/el:.1f}/s) mean {total/frames/1024:.1f} kB, {total/el/1024:.1f} kB/s; p50 {sorted(sizes)[len(sizes)//2]/1024:.1f} kB max {max(sizes)/1024:.1f} kB')
        for k,v in size.most_common(22):print(f'{k:24} in {present[k]:4} frames, changed {changes[k]:4}, bytes/frame {v/frames:8.0f}')
        await c.delete(f'http://{BASE}/api/me',headers={'authorization':'Bearer '+tok,**hdr})
asyncio.run(main())
