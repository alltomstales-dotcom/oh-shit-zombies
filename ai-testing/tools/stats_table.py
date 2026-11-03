"""The server's minute stats lines as a table: python3 stats_table.py CONTAINER_OR_LOGFILE [every]"""
import ast, re, subprocess, sys, os
src = sys.argv[1]; every = int(sys.argv[2]) if len(sys.argv) > 2 else 1
text = open(src).read() if os.path.exists(src) else subprocess.run(['docker', 'logs', src], capture_output=True, text=True).stderr
print('min | tick | surv | zombies (t) | near | wander | stuck | corpses | drops | frames | view | body | step | step:zombies')
n = 0
for line in text.splitlines():
    m = re.search(r"tick mean (\d+) ms.*?(\d+) survivors \((\d+) alive\); zombies (\{.*?\}); corpses (\d+).*?by part (\{.*?\})(?:; zombies within ~75 m of someone (\d+)(?:, wandering (\d+), stuck (\d+))?; held: drops (\d+))?", line)
    if not m: continue
    n += 1
    if n % every: continue
    z = ast.literal_eval(m[4]); p = ast.literal_eval(m[6])
    print(f"{n:3} | {m[1]:>4} | {m[3]:>4} | {z.get('z',0):>4} ({z.get('t',0):>3}) | {m[7] or '-':>4} | {m[8] or '-':>4} | {m[9] or '-':>4} | {m[5]:>5} | {m[10] or '-':>4} | "
          f"{p.get('frames',0):6.1f} | {p.get('frames:view',0):5.1f} | {p.get('frames:body',0):5.1f} | {p.get('step',0):6.1f} | {p.get('step:zombies',0):6.1f}")
