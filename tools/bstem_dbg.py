#!/usr/bin/env python3
# blastem 内蔵デバッガを pty 経由で駆動する。
# 使い方: bstem_dbg.py <rom.bin> <cmds_file>  (cmds は1行1コマンド; '@N' は N 秒待機)
import os, sys, pty, time, select, subprocess, signal

rom = sys.argv[1]
cmds = open(sys.argv[2]).read().splitlines() if len(sys.argv) > 2 else []

env = dict(os.environ)
env['XDG_RUNTIME_DIR'] = '/run/user/1000'
env['DISPLAY'] = ':0'
# Xauthority
try:
    out = subprocess.check_output("pgrep -a Xwayland | grep -oE '/run/user/1000/[^ ]*auth[^ ]*' | head -1", shell=True).decode().strip()
    if out: env['XAUTHORITY'] = out
except Exception: pass

pid, fd = pty.fork()
if pid == 0:
    os.execvpe('blastem', ['blastem', '-d', rom], env)
    os._exit(1)

def drain(t=0.5):
    buf = b''
    end = time.time() + t
    while time.time() < end:
        r,_,_ = select.select([fd], [], [], 0.1)
        if r:
            try: d = os.read(fd, 65536)
            except OSError: break
            if not d: break
            buf += d
            end = time.time() + t
    return buf.decode(errors='replace')

print(drain(2.0), end='')
for c in cmds:
    if c.startswith('@'):
        time.sleep(float(c[1:])); print(drain(0.3), end=''); continue
    os.write(fd, (c + '\n').encode())
    time.sleep(0.2)
    print('>>> ' + c)
    print(drain(1.5), end='')
print(drain(1.0), end='')
try: os.kill(pid, signal.SIGKILL)
except Exception: pass
