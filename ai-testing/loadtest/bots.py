#!/usr/bin/env python3
"""Fake players against the local stack: real sessions, real placement, walking and swinging.
Usage: bots.py N SECONDS [start]. Prints snapshot rate, bytes, ping. Deletes its accounts afterwards."""
import asyncio,json,math,os,random,statistics as st,sys,time,zlib
import httpx,websockets
BASE=os.environ.get('BASE','127.0.0.1:8120')
N,SECS=int(sys.argv[1]),float(sys.argv[2]);START=sys.argv[3] if len(sys.argv)>3 else 'chicago'
stats=[]
async def bot(i,client,stop):
    ip=f'198.18.{i//250}.{i%250+1}'      # TEST-NET addresses; the app believes this header on this stack
    hdr={'cf-connecting-ip':ip}
    try:
        r=await client.post(f'http://{BASE}/api/session',json={'device_id':os.urandom(16).hex(),'name':'x'},headers=hdr);r.raise_for_status()
    except Exception as e:
        stats.append(dict(frames=0,bytes=0,zbytes=0,keys={},pings=[],gaps=[],err='session: '+repr(e)[:80]));return
    tok=r.json()['token']
    s=dict(frames=0,bytes=0,zbytes=0,keys={},pings=[],gaps=[],placed=False,err=None)
    z=zlib.compressobj(wbits=-15)
    try:
        async with websockets.connect(f'ws://{BASE}/ws?token={tok}',additional_headers=hdr,max_size=None,open_timeout=30,compression='deflate') as ws:
            ticket=None;last=None;pos=None;t0=time.time();nextmove=0;nextping=0;nextswing=time.time()+random.random()*5;angle=random.random()*6.28
            async def rx():
                nonlocal ticket,pos,last
                async for m in ws:
                    d=json.loads(m);
                    if d.get('t')=='hello':
                        ticket=d['placement_ticket']
                        await ws.send(json.dumps({'t':'act','id':1,'a':'place','start':START,'reason':'launch','source':'manual','lat':0,'lng':0,'accuracy':1,'timestamp':time.time()*1000,'ticket':ticket,'request':os.urandom(8).hex()}))
                    elif d.get('t')=='s':
                        now=time.time()
                        if last:s['gaps'].append(now-last)
                        last=now;s['frames']+=1;s['bytes']+=len(m);s['zbytes']+=len(z.compress(m.encode() if isinstance(m,str) else m))+len(z.flush(zlib.Z_SYNC_FLUSH))
                        for k,v in d.items():s['keys'][k]=s['keys'].get(k,0)+len(json.dumps(v))
                        y=d['you'];s.setdefault('seen',[]).append(len(d.get('others') or []))
                        if y['lat'] or y['lng']:pos=[y['lat'],y['lng']]
                    elif d.get('t')=='pong':
                        s['pings'].append(time.time()*1000-d['c'])
                    elif d.get('t')=='full':s['err']='full'
            task=asyncio.create_task(rx())
            while not stop.is_set():
                now=time.time()
                if pos and now>=nextmove:
                    angle+=random.uniform(-.3,.3);pos2=[pos[0]+math.sin(angle)*2/111320,pos[1]+math.cos(angle)*2/(111320*math.cos(math.radians(pos[0])))]
                    await ws.send(json.dumps({'t':'pos','lat':pos2[0],'lng':pos2[1],'acc':1,'mode':'desk','placement_epoch':1,'floor_epoch':0}));nextmove=now+.25
                if now>=nextping:
                    await ws.send(json.dumps({'t':'ping','c':now*1000}));nextping=now+2
                if pos and now>=nextswing:
                    await ws.send(json.dumps({'t':'act','id':2,'a':'swing'}));nextswing=now+random.uniform(3,6)
                await asyncio.sleep(.05)
            task.cancel()
    except Exception as e:s['err']=repr(e)[:120]
    s['token']=tok;stats.append(s)
    try:await client.delete(f'http://{BASE}/api/me',headers={'authorization':'Bearer '+tok,**hdr})
    except Exception as e:s['err']=s['err'] or 'delete: '+repr(e)[:80]
APP=os.environ.get('APP','osz-stack-app-1')
async def sh(*a):
    p=await asyncio.create_subprocess_exec(*a,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT);o,_=await p.communicate();return o.decode()
async def wire():
    # Bytes the app really sent, deflate and framing included, on the interface facing this machine.
    o=await sh('docker','exec',APP,'sh','-c','cat /proc/net/dev');best=0
    for l in o.splitlines():
        if ':' in l and 'lo:' not in l:
            f=l.split(':')[1].split();best=max(best,int(f[8]))
    return best
cpu=[];mem=[]
async def watch(stop):
    while not stop.is_set():
        o=await sh('docker','stats','--no-stream','--format','{{.CPUPerc}} {{.MemUsage}}',APP)
        try:
            c,m=o.split()[0],o.split()[1];cpu.append(float(c.strip('%')));mem.append(float(m.replace('MiB','')))
        except Exception:pass
        await asyncio.sleep(1)
def avail_mb():
    return int(open('/proc/meminfo').read().split('MemAvailable:')[1].split()[0])//1024
async def main():
    stop=asyncio.Event();since=time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime());t0=await wire();low=avail_mb()
    if low<2048:print('refusing: under 2 GB available',low);return
    async with httpx.AsyncClient(timeout=30) as c:
        tasks=[]
        for i in range(N):
            if avail_mb()<2048:print('stopping ramp: under 2 GB available');N_started=i;break
            tasks.append(asyncio.create_task(bot(i,c,stop)));await asyncio.sleep(.1)
        w0=await wire();ts=time.time();wt=asyncio.create_task(watch(stop))
        await asyncio.sleep(SECS);w1=await wire();te=time.time();stop.set();await asyncio.gather(*tasks);await wt
    logs=await sh('docker','logs','--since',since,APP)
    wire_kbs=(w1-w0)/(te-ts)/1024
    print(f"app cpu mean {st.mean(cpu):.0f}% max {max(cpu):.0f}% mem max {max(mem):.0f} MiB (limit 448); wire {wire_kbs:.0f} kB/s total, {wire_kbs/max(1,N):.1f} kB/s per player, {wire_kbs*8/1024:.2f} Mbit/s; slow-tick lines {logs.count('slow tick')}; tick-failed {logs.count('tick failed')}; load {open('/proc/loadavg').read().split()[0]}; avail {avail_mb()} MB")
    ok=[s for s in stats if not s['err'] and s['frames']]
    print(f"N={N} connected_ok={len(ok)} errors={[s['err'] for s in stats if s['err']][:3]}")
    if ok:
        gaps=sorted(g for s in ok for g in s['gaps']);pings=sorted(p for s in ok for p in s['pings'])
        secs=SECS
        print(f"snapshots/s per player {st.mean(s['frames'] for s in ok)/secs:.1f}; gap p50 {gaps[len(gaps)//2]*1000:.0f}ms p95 {gaps[int(len(gaps)*.95)]*1000:.0f}ms max {gaps[-1]*1000:.0f}ms")
        print(f"ping p50 {pings[len(pings)//2]:.0f}ms p95 {pings[int(len(pings)*.95)]:.0f}ms")
        b=st.mean(s['bytes'] for s in ok)/secs;zb=st.mean(s['zbytes'] for s in ok)/secs
        print(f"down per player {b/1024:.1f} kB/s raw, {zb/1024:.1f} kB/s deflated; {N} players {zb*N*8/1e6:.2f} Mbit/s deflated")
        seen=[x for s in ok for x in s.get('seen',[])];ob=sum(s['keys'].get('others',0) for s in ok)/max(1,sum(s['frames'] for s in ok))
        if seen:print(f"others in view per frame: mean {st.mean(seen):.2f}, max {max(seen)}, frames with at least one {100*sum(1 for x in seen if x)/len(seen):.0f}%; 'others' field {ob:.0f} B/frame raw")
        if N<=3:
            print('bytes by key',{k:round(v/sum(s['frames'] for s in ok)) for k,v in sorted(ok[0]['keys'].items(),key=lambda kv:-kv[1])[:12]})
asyncio.run(main())
