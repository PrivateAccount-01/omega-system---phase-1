"""Scoped local fault worker guard, separate from unchanged pytest guard."""
from __future__ import annotations
import os
import socket
import sys
from pathlib import Path

def install(root, allowed_command=None):
    root=Path(root).resolve()
    def deny(*args,**kwargs):raise RuntimeError('OD04_PROCESS_GUARD_DENIED')
    for name in ('getaddrinfo','create_connection'):setattr(socket,name,deny)
    for name in ('connect','connect_ex','sendto','sendmsg'):
        if hasattr(socket.socket,name):setattr(socket.socket,name,deny)
    def bounded(path):
        if isinstance(path,int):return
        p=Path(os.fsdecode(path))
        if not p.resolve().is_relative_to(root):deny()
    def audit(event,args):
        if event=='subprocess.Popen':
            if allowed_command is None or not allowed_command(args):deny()
        if event in {'os.system','os.posix_spawn','os.spawn','socket.bind','socket.connect','socket.getaddrinfo'}:deny()
        if event=='open':
            path,mode,flags=args
            if not isinstance(path,int) and 'gnupg' in Path(os.fsdecode(path)).parts:deny()
            if flags & (os.O_CREAT|os.O_WRONLY|os.O_RDWR|os.O_TRUNC|os.O_APPEND):bounded(path)
        if event in {'os.remove','os.rmdir','os.mkdir','os.chmod'}:bounded(args[0])
        if event in {'os.link','os.rename','os.symlink'}:bounded(args[0]);bounded(args[1])
        if event=='sqlite3.connect' and args[0]!=':memory:':bounded(args[0])
    sys.addaudithook(audit)

