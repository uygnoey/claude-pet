"""Windows 용 `fcntl` 대체 모듈 — claude_pet.py 의 `import fcntl` 과 `fcntl.flock()` 호출을 그대로 살린다.

macOS 판은 설정 파일 쓰기(_ConfigLock)와 업데이트 잠금에서 flock 을 쓴다. Windows 에는 fcntl 이 없으므로
Windows 진입점(claude_pet_win.py)이 이 폴더를 sys.path 맨 앞에 넣어 이 모듈이 대신 import 된다.
의미론: LOCK_EX/LOCK_SH → msvcrt.locking(LK_LOCK: 블로킹, LK_NBLCK: 비블로킹), LOCK_UN → LK_UNLCK.
LOCK_NB 와 함께 잠겨 있으면 macOS 의 EWOULDBLOCK 처럼 OSError(errno=EWOULDBLOCK) 를 던진다 —
업데이터는 그 OSError 를 '다른 업데이터가 점유 중' 으로 읽는다. 파일의 첫 1 바이트 범위를 잠근다(빈 파일도 가능).
macOS 에서는 이 모듈이 import 되지 않는다(표준 fcntl 이 먼저).
"""
import errno
import os
import sys

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8

if sys.platform == "win32":
    import msvcrt

    def flock(fd, operation):
        if not isinstance(fd, int):
            fd = fd.fileno()
        pos = os.lseek(fd, 0, os.SEEK_CUR)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if operation & LOCK_UN:
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                return
            mode = msvcrt.LK_NBLCK if operation & LOCK_NB else msvcrt.LK_LOCK
            try:
                msvcrt.locking(fd, mode, 1)
            except OSError as e:
                if operation & LOCK_NB:
                    raise OSError(errno.EWOULDBLOCK, "lock held") from e
                raise
        finally:
            os.lseek(fd, pos, os.SEEK_SET)
else:  # 표준 fcntl 이 있는 OS 에서는 이 모듈이 sys.path 에 오르지 않는다 — 올랐다면 설정 오류다
    raise ImportError("windows/compat/fcntl.py is for Windows only; keep it off sys.path elsewhere")
