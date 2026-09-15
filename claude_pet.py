#!/usr/bin/env python3
"""
Claude Pet — Codex Pets 스타일 투명 오버레이 펫 + Claude 토큰 사용량
=====================================================================
- 창 프레임/타이틀 없음, 배경 완전 투명 (펫과 게이지만 화면에 떠 있음)
- 스프라이트: ~/.codex/pet-runs/patch-entp-cat/frames 의 내장 고양이 프레임 사용
- 게이지 3종: 현재 세션(5h) / 주간 전체 / 주간 Opus — 남은량 + 리셋 카운트다운
- 한도 도달 정도에 따라 펫 모션이 변함 (모션별 고유 속도/반복 설정)
    <50%  idle(평온)  /  50~85% waiting(초조)  /  ≥85% failed(패닉)
    드래그하면 방향에 맞춰 running-left/right, 더블클릭 waving, 리셋 감지 시 jumping
    스스로 돌아다님: 걷기 running-left/right, 구경·따라다니기 review, 모니터 사이 점프 jumping

실행:
  pip3 install pyobjc-framework-Cocoa   # 최초 1회
  python3 claude_pet.py                  # 펫 실행
  python3 claude_pet.py --report         # GUI 없이 사용량 출력

렌더링: macOS 네이티브 AppKit (잔상 없는 진짜 투명 오버레이)
"""

import json
import math
import os
import random
import re
import sys
import glob
import time
import ctypes
import errno
import fcntl
import plistlib
import shutil
import threading
import subprocess
import ssl
import stat
import tempfile
import zipfile
import urllib.request
import urllib.error
import urllib.parse
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

# HTTPS 인증서 검증 — 빌드에 쓴 파이썬마다 시스템 CA 위치가 달라(특히 python.org
# universal2 빌드는 CA 번들이 없어) 정확 모드(OAuth)·업데이트 확인 등 모든 HTTPS가
# CERTIFICATE_VERIFY_FAILED로 죽는다. certifi 번들을 명시적으로 써서 어떤 빌드에서도
# 검증되도록 전역 오프너를 설치한다(urlopen/urlretrieve 모두 이 컨텍스트를 사용).
def _install_https_opener():
    ctx = None
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        try:
            ctx = ssl.create_default_context()
        except Exception:
            return
    urllib.request.install_opener(
        urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)))

_install_https_opener()

# ──────────────────────────── 설정 ────────────────────────────
def _default_pet_dir():
    # 1) 환경변수 → 2) 스크립트 옆 frames (앱 번들 내장) → 3) codex 펫 폴더
    env = os.environ.get("CLAUDE_PET_SPRITES")
    if env:
        return os.path.expanduser(env)
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
    if os.path.isdir(here):
        return here
    # 앱 번들(py2app/수동)에서: Contents/Resources/frames
    try:
        from Foundation import NSBundle
        rp = NSBundle.mainBundle().resourcePath()
        if rp:
            cand = os.path.join(str(rp), "frames")
            if os.path.isdir(cand):
                return cand
    except Exception:
        pass
    return os.path.expanduser("~/.codex/pet-runs/patch-entp-cat/frames")

PET_DIR = _default_pet_dir()
PET_SCALE_DOWN = int(os.environ.get("CLAUDE_PET_SCALE_DOWN", 1))  # 1=원본 크기

# 요약 필 글꼴 — Pretendard SemiBold(OFL 1.1, fonts/LICENSE-Pretendard.txt)를 앱에 내장한다.
# 사용자 결정 2026-09-12: "한국어 폰트는 이제 pretendard를 내장해서 사용할 수 있도록 해" + "UI 는 맥과
# Windows 100% 동일" — 두 플랫폼이 같은 파일로 같은 글리프를 그린다(라틴·숫자·기호도 이 글꼴).
# 번들 안에서는 Info.plist 의 ATSApplicationFontsPath(=fonts)가 등록하고, 소스 실행에서는 run_gui 가
# CoreText 로 프로세스 범위에 등록한다. 못 찾으면 시스템 모노 글꼴로 조용히 내려간다.
SUMMARY_FONT_FILE = "Pretendard-SemiBold.ttf"   # TrueType 판(Pretendard 의 alternative/) — CFF(OTF)는 Windows 에서 작은 크기가 거칠게 보였다
SUMMARY_FONT_NAME = "Pretendard-SemiBold"      # PostScript 이름 (NSFont.fontWithName_size_)


def bundled_font_path():
    """내장 요약 글꼴 파일 경로. 스크립트 옆 fonts/ → 앱 번들 Resources/fonts → None."""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", SUMMARY_FONT_FILE)
    if os.path.isfile(here):
        return here
    try:
        from Foundation import NSBundle
        rp = NSBundle.mainBundle().resourcePath()
        if rp:
            cand = os.path.join(str(rp), "fonts", SUMMARY_FONT_FILE)
            if os.path.isfile(cand):
                return cand
    except Exception:
        pass
    return None

# 유저가 직접 펫을 넣는 폴더. 여기 아래에 <이름>/ 폴더를 만들고 그 안에
#   pet.json + spritesheet.webp
# 두 파일을 넣으면 우클릭 → 펫 메뉴에 자동으로 나타난다. (앱 업데이트에도 안 지워짐)
USER_PETS_DIR = os.path.expanduser("~/.claude_pet/pets")
USER_PET_HOME = os.path.expanduser("~/.claude_pet")

# 앱에 동봉해 배포하는 펫 자산 트리(.claude_pet/). 홈에 없는 것만 채워 넣는다.
BUNDLED_PET_README = ("README.md", "README.ko.md", "README.ja.md", "README.es.md")
BUNDLED_PET_IDS = ("dog", "elephant", "fox", "scorpion")
# 펫 하나가 가진 파일 — 레포에 추적되는 것과 정확히 같다. 소스 폴더를 통째로
# 훑지 않고 이 목록만 복사한다(빌드 때 섞여 든 .DS_Store 같은 게 딸려가지 않게).
BUNDLED_PET_SHEET = "spritesheet.webp"      # 배포 펫이 쓰는 유일한 시트 이름
BUNDLED_PET_FILES = ("pet.json", BUNDLED_PET_SHEET, "preview.png")


def _default_bundled_pet_dir():
    """동봉된 .claude_pet 트리 위치. frames 와 같은 방식으로 찾는다.

    1) 스크립트 옆 .claude_pet (레포에서 바로 실행)
    2) 앱 번들 Contents/Resources/.claude_pet
    """
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".claude_pet")
    if os.path.isdir(here):
        return here
    try:
        from Foundation import NSBundle
        rp = NSBundle.mainBundle().resourcePath()
        if rp:
            cand = os.path.join(str(rp), ".claude_pet")
            if os.path.isdir(cand):
                return cand
    except Exception:
        pass
    return here


# ── 덮어쓰기가 '구조적으로' 불가능한 게시(publish) 원시연산 ───────────────
# 무엇이든 "없으면 만든다"를 lexists 확인 뒤 rename/copy 로 구현하면, 확인과
# 실행 사이에 생긴 사용자 파일을 지운다(TOCTOU). 파일은 os.link, 폴더는
# renameatx_np(RENAME_EXCL) 로 — 둘 다 대상이 있으면 커널이 EEXIST 로 거절한다.
RENAME_EXCL = 0x00000004          # sys/stdio.h


def _load_renameatx_np():
    """int renameatx_np(int, const char*, int, const char*, unsigned int)"""
    try:
        fn = ctypes.CDLL(None, use_errno=True).renameatx_np
    except (OSError, AttributeError):
        return None                                   # 이 OS 에는 없음
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p,
                   ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    return fn


_RENAMEATX_NP = _load_renameatx_np()


def _publish_dir_noreplace(dir_fd, src_name, dst_name):
    """dir_fd 안에서 src_name → dst_name. 성공 True / 대상이 이미 있으면 False.

    dir_fd 기준(=경로가 아니라 열어 둔 폴더 기준)이라, 중간에 부모 폴더가
    심볼릭 링크로 바뀌어도 엉뚱한 곳에 쓰지 않는다.
    """
    if _RENAMEATX_NP is not None:
        ctypes.set_errno(0)
        rc = _RENAMEATX_NP(dir_fd, os.fsencode(src_name),
                           dir_fd, os.fsencode(dst_name), RENAME_EXCL)
        if rc == 0:
            return True
        err = ctypes.get_errno()
        if err == errno.EEXIST:
            return False                              # 사용자 것이 이미 있다
        raise OSError(err, os.strerror(err), src_name, None, dst_name)
    # 원자적 게시 수단이 없으면 아무것도 하지 않는다(fail-closed). 여기서
    # '확인 후 rename' 같은 것으로 물러서면, 확인과 rename 사이에 생긴 사용자
    # 폴더를 지운다 — 좁아졌을 뿐 같은 사고다. 안 깔리는 편이 지우는 것보다 낫다.
    raise OSError(errno.ENOSYS,
                  "atomic no-replace directory publish is unavailable")


# ── 이름이 아니라 '그 객체'를 잡는 원시연산 ───────────────────────────────
#
# 이 파일에서 같은 사고가 여러 군데에서 같은 모양으로 났다: **신원을 확인하고,
# 그다음 '이름'으로 행동한다.** 확인과 행동 사이에 그 이름이 다른 객체를
# 가리키게 되면, 지워지거나 게시되는 것은 우리가 승인한 그 객체가 아니다.
# mkdir→open, lstat→rmtree, stat→rm -rf, O_EXCL→link, test ! -e→mv 는 전부
# 같은 결함의 다른 표기다.
#
# 규칙은 하나다. **이름이 아니라 객체를 들고 있는다.** 만들 때
# (st_dev, st_ino) 를 적어 두거나 fd 를 그대로 들고, 이후의 모든 사용(열기·
# 게시·정리)에서 fstat 으로 대조한다. 커널이 핸들 기준 연산을 주는 자리
# (dir_fd/openat, renameatx_np, O_NOFOLLOW)에서는 그 핸들로 행동하고, 주지 않는
# 자리에서는 **행동하지 않는다** — 어긋나면 남의 것도, 밀려난 우리 것도 그대로
# 두고 보고만 남긴다. 지운 것과 게시한 것은 되돌릴 수 없고, 남은 쓰레기는
# 되돌릴 수 있다.
#
# 신원 대조가 '틈을 없앤다'고 읽지 말 것. 틈을 없애는 것은 fd 로 행동하는
# 구조이고, 대조는 그 구조가 닿지 못하는 마지막 한 걸음(unlink/rmdir/rename 의
# 이름 해석)에서 창을 좁히고 fail-closed 로 넘어뜨리는 장치다.

def _ident(st):
    """stat 결과에서 '그 객체'를 가리키는 값. 이름은 여기 들어가지 않는다."""
    return (st.st_dev, st.st_ino)


def _ident_of_fd(fd):
    try:
        return _ident(os.fstat(fd))
    except OSError:
        return None


def _open_dir_ident_at(dir_fd, name, ident):
    """dir_fd 안 name 을 O_NOFOLLOW 로 열고, ident 인 그 폴더일 때만 fd 를 준다.

    ident 가 None 이면 대조하지 않는다(신원을 아직 모르는 첫 열기용).
    """
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                     dir_fd=dir_fd)
    except OSError:
        return None
    if ident is not None and _ident_of_fd(fd) != tuple(ident):
        os.close(fd)
        return None
    return fd


def _open_file_ident_at(dir_fd, name, ident):
    """같은 것을 평범한 파일에 대해. 정규 파일이 아니면 None.

    O_NONBLOCK 은 FIFO·장치 파일에서 open 자체가 매달리는 것을 막는다.
    """
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=dir_fd)
    except OSError:
        return None
    try:
        st = os.fstat(fd)
    except OSError:
        os.close(fd)
        return None
    if (not stat.S_ISREG(st.st_mode)
            or (ident is not None and _ident(st) != tuple(ident))):
        os.close(fd)
        return None
    return fd


def _is_ident_at(dir_fd, name, ident, directory=True):
    """지금 이 이름이 여전히 ident 인 그 객체인가."""
    if ident is None:
        return False
    opener = _open_dir_ident_at if directory else _open_file_ident_at
    fd = opener(dir_fd, name, ident)
    if fd is None:
        return False
    os.close(fd)
    return True


def _unlink_ident_at(dir_fd, name, ident):
    """ident 인 '그 객체'일 때만 dir_fd 안의 name 을 지운다.

    파일에는 fd 기준 unlink 가 없다(unlinkat 도 이름을 받는다). 그래서 열어
    확인한 뒤 이름으로 지우는 이 한 걸음만은 창이 남는다 — 남길 수 있는 최소가
    이것이다. 대신 확인을 통과하지 못하면 아무것도 지우지 않는다. ident 가
    None, 즉 '무엇을 만들었는지 모른다'는 것도 통과하지 못하는 경우다.
    """
    if not _is_ident_at(dir_fd, name, ident, directory=False):
        return False
    try:
        os.unlink(name, dir_fd=dir_fd)
        return True
    except OSError:
        return False


def _fresh_mkdir_ident(fd):
    """방금 mkdir 한 폴더를 연 fd 가 정말 '그 폴더'인지 본다 → 신원 또는 None.

    mkdir 은 핸들을 주지 않는다. 그래서 mkdir 과 open 사이는 이 파일에서 유일하게
    핸들로 닫을 수 없는 틈이다 — 커널이 주지 않는 연산을 만들어 낼 수는 없으니,
    대신 '우리가 방금 만든 빈 폴더'만 가지는 성질로 판별하고 어긋나면 거절한다:
    우리 소유이고, 그룹·기타 권한 비트가 하나도 없고(0o700 으로 만든다 — umask 는
    비트를 지우기만 하므로 어떤 umask 에서도 이 성질은 유지된다), 하위 디렉터리가
    없고(st_nlink == 2), 비어 있다.

    **이것은 판별이지 증명이 아니다.** 같은 사용자가 같은 성질의 폴더를 그 이름에
    놓을 수 있다. 그래도 값이 있는 이유는 넘어지는 방향이 정해져 있기 때문이다:
    거짓 양성의 결과는 '이번에 이 펫을 안 깐다'(다음 실행에서 다시 시도한다)이고,
    거짓 음성의 결과는 '남의 폴더에 쓰고 지운다'다.
    """
    try:
        st = os.fstat(fd)
    except OSError:
        return None
    if not stat.S_ISDIR(st.st_mode):
        return None
    if st.st_uid != os.geteuid():
        return None
    if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        return None
    if st.st_nlink != 2:
        return None
    try:
        if os.listdir(fd):
            return None
    except OSError:
        return None
    return _ident(st)


def _same_dir(fd, path):
    """열어 둔 fd 와 지금 그 경로가 가리키는 것이 같은 폴더인가.

    O_NOFOLLOW 로 안전하게 열어도, 그 '직후' 폴더를 치우고 같은 이름의 심볼릭
    링크를 놓으면 이후의 경로 기반 작업은 링크 너머로 간다. 쓰기 전에 fd 와
    경로의 (inode, device) 가 같은지 대조해 그 바꿔치기를 잡는다.
    """
    try:
        a, b = os.fstat(fd), os.stat(path)
    except OSError:
        return False
    return (a.st_ino, a.st_dev) == (b.st_ino, b.st_dev)


def seed_bundled_pet_assets(source_root=None, dest_root=None):
    """동봉 펫 자산을 ~/.claude_pet 에 "없는 것만" 채운다.

    · 루트 README*.md 는 ~/.claude_pet/ 바로 아래로 (pets/ 아래가 아니다 —
      discover_pets() 가 펫이 아닌 폴더를 무시해서 잘못 넣어도 조용히 묻힌다).
    · 펫은 폴더 단위로 판단한다. ~/.claude_pet/pets/dog 이 이미 있으면 안을
      들여다보지 않고 통째로 건너뛴다 — 사용자가 고친 펫이 반쯤 덮이는 일 방지.
    · 이미 있는 것은 절대 덮어쓰지 않고, 무엇도 지우지 않는다.

    대상 폴더를 O_NOFOLLOW 로 한 번 열고, 그 뒤의 모든 작업(pets 생성·열기,
    README, 스테이징, 게시)을 그 fd 기준으로만 한다. '확인'은 이미 지나간
    순간의 이야기라 아무리 촘촘히 넣어도 확인과 사용 사이가 남지만, fd 는
    이름이 아니라 폴더 그 자체를 잡고 있어서 이름을 심볼릭 링크로 바꿔치기해도
    우리 작업이 링크 너머를 따라가지 않는다. 안전은 검사가 아니라 이 구조가
    보장한다.

    아래 _same_dir 호출 네 개의 역할은 **같지 않다.** 하나는 막고 셋은 보고만
    한다:

    · 루트를 연 직후의 첫 호출은 **막는다.** 어긋나면 그 자리에서 돌아가고
      아무것도 깔지 않는다. 여는 그 순간에 바꿔치기가 있었다는 뜻이라, 뒤따르는
      작업이 사용자가 말한 그 폴더에서 일어난다고 말할 수 없기 때문이다.
    · pets 를 연 직후의 호출은 진단 기준점일 뿐이고 결과를 보지 않는다.
    · 시딩이 끝난 뒤의 두 호출(pets, 루트)은 report["errors"] 에 남기기만 하고
      그대로 진행한다. 그때는 이미 열어 둔 fd 안쪽에 안전하게 다 쓴 뒤라, 남은
      문제는 '안전'이 아니라 '사용자가 기대한 자리인가'다.

    이 구분을 '전부 진단'으로 뭉뚱그려 적어 두면 다음 사람이 첫 호출을 지워도
    되는 중복으로 읽는다. 그 한 줄은 되돌릴 수 없는 조기 반환을 들고 있다.
    """
    src = str(source_root) if source_root else _default_bundled_pet_dir()
    dst = str(dest_root) if dest_root else USER_PET_HOME
    report = {"copied": [], "skipped": [], "errors": []}
    try:
        if os.path.islink(dst):
            report["errors"].append("dest-root-is-symlink")
            return report
        if not os.path.isdir(src):
            report["errors"].append("no-source")
            return report
        pets_dst = os.path.join(dst, "pets")
        # 경로로 하는 마지막 일은 루트를 만드는 것 하나뿐이다. pets 는 아래에서
        # root_fd 기준으로 만든다 — 여기서 경로로 한 번 더 만들면, 그 사이 루트가
        # 심볼릭 링크로 바뀌었을 때 링크 너머에 폴더를 만들어 버린다.
        os.makedirs(dst, exist_ok=True)
        try:
            root_fd = os.open(dst, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as e:
            report["errors"].append(
                f"dest root is not a real directory ({e.strerror})")
            return report
        try:
            if not _same_dir(root_fd, dst):
                report["errors"].append("dest root was replaced while opening it")
                return report
            try:
                os.mkdir("pets", 0o755, dir_fd=root_fd)
            except FileExistsError:
                pass
            try:
                pets_fd = os.open("pets",
                                  os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                  dir_fd=root_fd)
            except OSError as e:
                report["errors"].append(
                    f"pets is not a real directory ({e.strerror})")
                return report
            try:
                _same_dir(pets_fd, pets_dst)   # 진단 기준점(결과에 의존하지 않음)
                _seed_readmes(src, root_fd, report)
                _seed_pets(src, pets_fd, report)
                # 여기까지 쓴 것은 전부 위 fd 안쪽 = 처음에 연 그 폴더다. 그 사이
                # 이름이 바뀌었는지는 안전과는 무관하지만(이미 안전하게 썼다),
                # 사용자가 기대한 자리에 없을 수 있으므로 보고에는 남긴다.
                if not _same_dir(pets_fd, pets_dst):
                    report["errors"].append(
                        "pets was replaced during seeding; assets went to the "
                        "directory that was opened, not to the new one")
            finally:
                os.close(pets_fd)
            if not _same_dir(root_fd, dst):
                report["errors"].append(
                    "dest root was replaced during seeding; assets went to the "
                    "directory that was opened, not to the new one")
        finally:
            os.close(root_fd)
    except Exception as e:
        report["errors"].append(str(e))
    return report


def _copy_into_fd(src_path, dir_fd, name):
    """번들의 파일 하나를 dir_fd 안에 name 으로 새로 만든다 → 그 파일의 신원.

    대상 쪽은 전부 fd 기준이다. 경로 문자열로 쓰면, 안전하게 열어 둔 폴더가
    그 사이 심볼릭 링크로 바뀌었을 때 링크 너머(사용자 홈 밖)에 써 버린다.
    shutil.copy2 는 dir_fd 를 받지 못하므로 우리 소유의 스크래치에 먼저
    복사해(원본 읽기·mtime 보존은 그쪽에 맡기고) 내용만 fd 안으로 옮긴다.

    돌려주는 (st_dev, st_ino) 는 **O_EXCL 이 준 신원**이다. O_EXCL 로 만든
    그 열림은 우리가 만든 객체를 가리키는 것이 커널에 의해 보장되므로, 이
    파일에서 신원을 가장 확실하게 얻을 수 있는 자리다. 호출부는 게시·정리
    직전에 이 값과 대조한다.

    도중에 실패하면 방금 만든 그 파일을 신원 기준으로 되돌리고 예외를 다시
    던진다. 정리를 호출부에 미루면 호출부는 이 신원을 알 방법이 없어 결국
    '이름으로' 지우게 되고, 그 사이 이름이 남의 것을 가리키면 남의 파일을
    지운다.
    """
    scratch = tempfile.mkdtemp()
    ident = None
    ok = False
    try:
        tmp = os.path.join(scratch, os.path.basename(name))
        shutil.copy2(src_path, tmp)          # 소스 읽기 + mtime 보존
        st = os.stat(tmp)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644,
                     dir_fd=dir_fd)
        with os.fdopen(fd, "wb") as out, open(tmp, "rb") as inp:
            ident = _ident_of_fd(out.fileno())
            shutil.copyfileobj(inp, out)
            # 시각도 '이름'이 아니라 열려 있는 fd 에 찍는다. 닫은 뒤 이름으로
            # 찍으면, 그 사이 이름이 바뀌어도 모르는 채 남의 파일 시각을 건드린다
            # — fd 로 바꾼 코드의 맨 끝에 이런 호출 하나가 남기 쉽다.
            os.utime(out.fileno(), ns=(st.st_atime_ns, st.st_mtime_ns))
        ok = True
        return ident
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        if not ok:
            # 만들지 못했으면(예: O_EXCL 이 거절) ident 가 None 이고,
            # _unlink_ident_at 은 그때 아무것도 하지 않는다 — 그 이름에 이미
            # 있던 남의 것을 지우지 않는다는 뜻이다.
            _unlink_ident_at(dir_fd, name, ident)


def _unlink_at(dir_fd, name):
    try:
        os.unlink(name, dir_fd=dir_fd)
    except OSError:
        pass


def _remove_stage_at(dir_fd, stage, ident=None):
    """dir_fd 안의 스테이징 폴더를 통째로 지운다(전부 fd 기준).

    ident 는 그 폴더를 만들 때 적어 둔 (st_dev, st_ino) 다. 지금 그 이름이
    가리키는 것이 그 객체가 아니면 **아무것도 하지 않는다** — 안으로 들어가지도,
    지우지도 않는다. ident 를 모르면(None) 같은 이유로 손대지 않는다: 모르는
    것을 지우는 것이 바로 막으려는 사고다.

    안을 비우는 일은 _empty_dir_at 에 맡긴다 — 전부 '신원을 확인한 그 fd'
    기준이라 이름이 다시 해석되지 않고, 하위 폴더까지 재귀한다.

    한때 여기에 '한 겹만 지우는' 사본이 따로 있었다: listdir 이 준 이름마다
    unlink 를 한 번 부르는 것이 전부여서, 하위 폴더가 하나라도 있으면 unlink 가
    실패하고(삼켜지고) 이어지는 rmdir 도 실패해(삼켜지고) 스테이지가 그대로
    남았다. 그 이름에는 os.urandom(5).hex() 가 들어가 실행마다 달라지므로,
    남은 스테이지는 이후 어떤 실행도 다시 찾아 지울 수 없다. 지금
    BUNDLED_PET_FILES 가 전부 평평한 파일이라 아직 일어난 적이 없을 뿐,
    중첩된 자산이 하나 들어오는 날 바로 일어난다. 그래서 약한 사본을 없애고
    재귀하는 쪽 하나만 남긴다 — 이 docstring 이 말하는 '통째로'가 실제로
    참이 되는 것도 그 덕이다.

    마지막 rmdir 하나만 이름을 쓰고(POSIX 에 '이 아이노드를 지워라'가 없다),
    그 직전에 한 번 더 대조한다. 창이 좁아질 뿐 닫히지는 않지만, 그 시점의
    대상은 우리가 방금 비운 빈 폴더이므로 최악의 경우에 사라지는 것도 남의 빈
    디렉터리 하나지 남의 자료가 아니다.
    """
    fd = _open_dir_ident_at(dir_fd, stage, ident) if ident is not None else None
    if fd is None:
        return
    try:
        _empty_dir_at(fd)
    finally:
        os.close(fd)
    if not _is_ident_at(dir_fd, stage, ident):
        return
    try:
        os.rmdir(stage, dir_fd=dir_fd)
    except OSError:
        pass


def _stage_name(tag):
    return ".seed-%s-%s" % (tag, os.urandom(5).hex())


def _seed_readmes(src, root_fd, report):
    """루트 README 4개를 root_fd 안에 없는 것만 만든다(전부 fd 기준)."""
    for name in BUNDLED_PET_README:
        s = os.path.join(src, name)
        if os.path.islink(s) or not os.path.isfile(s):
            report["skipped"].append(name)
            continue
        try:
            os.lstat(name, dir_fd=root_fd)     # 이미 있으면 손대지 않는다
            report["skipped"].append(name)
            continue
        except FileNotFoundError:
            pass
        except OSError as e:
            report["errors"].append(f"{name}: {e}")
            continue
        tmp = _stage_name(name)
        staged = None
        try:
            # 임시 파일에 다 쓴 뒤 link 로 붙인다. link 는 대상이 있으면 커널이
            # EEXIST 로 거절하므로 덮어쓰기가 원천적으로 불가능하다. link 를 못
            # 쓰면 그냥 포기한다(fail-closed) — 최종 경로에 바로 쓰는 대안은
            # 중간에 죽으면 잘린 파일을 남기고, 그 파일은 "이미 있음" 규칙에
            # 걸려 영영 고쳐지지 않는다.
            #
            # link 는 '이름'을 해석한다. O_EXCL 이 준 신원과 대조하지 않으면,
            # 다 쓴 뒤 게시하기 전 사이에 그 임시 이름이 남의 파일로 바뀌었을 때
            # **남의 내용이 사용자의 README 로 게시되고, 이어지는 정리가 남의
            # 파일을 지운다.** 그래서 게시 직전과 정리 직전에 모두 대조한다.
            staged = _staged_file_ident(root_fd, tmp, s,
                                        _copy_into_fd(s, root_fd, tmp))
            if staged is None:
                report["errors"].append(
                    f"{name}: the staged copy is not the file we wrote, "
                    f"not published")
                continue
            try:
                os.link(tmp, name, src_dir_fd=root_fd, dst_dir_fd=root_fd)
            except FileExistsError:            # 그 사이에 생겼으면 양보
                report["skipped"].append(name)
            else:
                if _is_ident_at(root_fd, name, staged, directory=False):
                    report["copied"].append(name)
                else:
                    # 여기까지 오면 방금 만든 그 이름은 우리 파일이 아니라 남의
                    # 아이노드를 가리키는 링크다. 우리가 만든 그 링크 하나만
                    # 거둔다 — 남의 파일은 자기 이름으로 그대로 남는다.
                    _unlink_at(root_fd, name)
                    report["errors"].append(
                        f"{name}: the published link is not the staged file, "
                        f"withdrawn")
        except Exception as e:
            report["errors"].append(f"{name}: {e}")
        finally:
            _unlink_ident_at(root_fd, tmp, staged)


def _staged_file_ident(dir_fd, name, src_path, made=None):
    """게시 직전, 스테이징한 그 임시 파일이 정말 우리가 쓴 것인지 본다.

    두 가지를 함께 본다.

    1. **신원.** 만들 때 O_EXCL 로 얻은 (st_dev, st_ino) 와, 지금 이 이름이
       가리키는 객체가 같은가. 이쪽이 본래의 대조다.
    2. **내용.** 번들 원본과 바이트 단위로 같은가. 신원을 알 수 없을 때의 보루이자
       (호출부가 신원을 못 받은 경우), 도중에 죽어 잘린 파일을 게시하지 않게
       하는 장치다.

    어느 하나라도 어긋나면 None 이고, 그때 호출부는 게시하지 않으며 그 이름에
    있는 것에도 손대지 않는다.
    """
    fd = _open_file_ident_at(dir_fd, name, made)
    if fd is None:
        return None
    try:
        with os.fdopen(os.dup(fd), "rb") as staged, open(src_path, "rb") as orig:
            while True:
                a, b = staged.read(65536), orig.read(65536)
                if a != b:
                    return None
                if not a:
                    break
        return _ident_of_fd(fd)
    except OSError:
        return None
    finally:
        os.close(fd)


def _log_seed_report(report):
    """시딩 결과를 디버그 로그에 남긴다 — 개수와 분류만.

    거절(원자적 게시 수단이 없어 아무것도 깔지 않은 경우)이 조용하면 아무도
    모른 채 펫만 안 생긴다. 그렇다고 경로나 이름을 찍으면 안 된다 — 오류
    문자열에는 예외가 들고 온 경로가 섞여 있고, 경로는 프로젝트 폴더 이름을
    담고 있다. 그래서 사유는 분류해서 개수로만 센다.
    """
    if not report:
        return
    errors = report.get("errors") or ()
    unsupported = sum(1 for e in errors if "unavailable" in str(e))
    _dbg("seed: %d copied, %d skipped, %d refused (%d no atomic primitive)"
         % (len(report.get("copied") or ()), len(report.get("skipped") or ()),
            len(errors), unsupported))


def _bad_pet_metadata(pet_dir, pet_id):
    """게시 전 pet.json 검사. 문제가 있으면 사유 문자열, 없으면 None.

    깨진/수상한 메타데이터는 게시하지 않는다. 한 번 게시되면 폴더 단위 skip
    때문에 다시는 고쳐지지 않고, 메뉴에는 뜨는데 로드는 실패하는 펫이 된다.
    spritesheetPath 는 펫 폴더 안의 파일 이름이어야 한다 — '../' 로 폴더 밖을
    가리키는 시트는 배포물이 아니라 남의 파일을 읽으라는 뜻이다.
    """
    try:
        with open(os.path.join(pet_dir, "pet.json"), "rb") as f:
            meta = json.load(f)
    except Exception as e:
        return f"unreadable pet.json ({type(e).__name__})"
    if not isinstance(meta, dict):
        return "pet.json is not an object"
    if str(meta.get("id") or pet_id) != pet_id:
        return f"pet.json id {meta.get('id')!r} does not match the folder name"
    sheet = meta.get("spritesheetPath") or "spritesheet.webp"
    if not isinstance(sheet, str) or os.path.isabs(sheet) or os.sep in sheet \
            or sheet in ("", ".", "..") or sheet != os.path.basename(sheet):
        return f"spritesheetPath {sheet!r} escapes the pet folder"
    # 배포 펫의 시트는 정확히 BUNDLED_PET_SHEET 하나다. 다른 이름을 가리키면
    # (안 깔리는 파일이든, pet.json·preview.png 처럼 시트가 아닌 파일이든)
    # 게시된 펫은 못 읽는 시트를 가리키게 된다 — 메뉴에는 뜨는데 고르면 로드에
    # 실패하고, 폴더 단위 skip 때문에 영영 그 상태로 남는다.
    if sheet != BUNDLED_PET_SHEET:
        return (f"spritesheetPath {sheet!r} is not the distributed sheet "
                f"({BUNDLED_PET_SHEET})")
    sheet_path = os.path.join(pet_dir, sheet)
    if os.path.islink(sheet_path) or not os.path.isfile(sheet_path):
        return f"spritesheetPath {sheet!r} is not a file in the pet folder"
    # 규약 버전도 우리가 그릴 수 있는 것이어야 한다. 모르는 버전을 깔아 두면
    # 격자 해석이 어긋나 깨진 그림이 나오거나 아예 못 읽는다.
    ver = meta.get("spriteVersionNumber", meta.get("spriteVersion"))
    if ver is not None and (isinstance(ver, bool) or not isinstance(ver, int)
                            or ver not in PET_LAYOUTS):
        return f"unsupported spriteVersionNumber {ver!r}"
    return None


def _seed_pets(src, pets_fd, report):
    """동봉 펫들을 pets_fd(=~/.claude_pet/pets) 아래에 없는 것만 채운다.

    대상 쪽 작업은 전부 pets_fd 기준이다 — 경로로 만들면 그 사이 pets 가
    심볼릭 링크로 바뀌었을 때 스테이징이 링크 너머에 만들어진다(지웠다 해도
    이미 쓴 것이다).
    """
    for pet in BUNDLED_PET_IDS:
        s = os.path.join(src, "pets", pet)
        rel = "pets/" + pet
        try:
            os.lstat(pet, dir_fd=pets_fd)      # 이미 있으면 통째로 건너뛴다
            report["skipped"].append(rel)
            continue
        except FileNotFoundError:
            pass
        except OSError as e:
            report["errors"].append(f"{rel}: {e}")
            continue
        if os.path.islink(s) or not os.path.isdir(s):
            report["skipped"].append(rel)
            continue
        # fail-closed: 세 파일이 모두 '진짜 파일'로 있어야 게시한다. 하나라도
        # 없거나 심볼릭 링크면 아예 만들지 않는다 — 반쪽 펫을 만들어 버리면
        # 폴더 단위 skip 때문에 다음 실행에서도 고쳐지지 않고, _is_pet_dir 이
        # pet.json 만 보고 유효하다고 판정해 메뉴에 깨진 펫으로 남는다.
        bad = [f for f in BUNDLED_PET_FILES
               if os.path.islink(os.path.join(s, f))
               or not os.path.isfile(os.path.join(s, f))]
        if bad:
            report["errors"].append(
                f"{rel}: incomplete source, not published ({', '.join(bad)})")
            continue
        why = _bad_pet_metadata(s, pet)
        if why:
            report["errors"].append(f"{rel}: {why}, not published")
            continue
        # 옆의 임시 폴더에 세 파일을 다 채운 뒤에야 제자리로 옮긴다. 곧바로
        # pets/dog 을 만들어 놓고 채우면, 도중에 실패했을 때 파일이 반만 든
        # pets/dog 이 남는다 — 폴더 단위로 건너뛰므로 다음 실행에서도 "이미 있는
        # 펫"으로 보여 영영 안 고쳐지고, 메뉴에는 깨진 펫으로 뜬다.
        # 한 펫이 실패해도 나머지는 계속 채운다.
        # mkdir 은 핸들을 주지 않으므로 '만든 것'과 '연 것'이 같다는 보장이
        # 없다. 그 사이에 이름을 빼앗기면, 예전 코드는 남의 폴더에 배포 파일을
        # 쏟아붓고(우리 것인 줄 알고) 마지막에 통째로 지웠다. 그래서 연 직후에
        # _fresh_mkdir_ident 로 판별하고, 그 뒤의 모든 동작(복사·게시·정리)을
        # 그 신원에 묶는다. 판별에 실패하면 그 이름에 있는 것에 손대지 않고
        # 이 펫만 건너뛴다.
        stage = _stage_name(pet)
        stage_ident = None
        published = False
        try:
            os.mkdir(stage, 0o700, dir_fd=pets_fd)
            stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=pets_fd)
            try:
                stage_ident = _fresh_mkdir_ident(stage_fd)
                if stage_ident is None:
                    report["errors"].append(
                        f"{rel}: the staging folder is not the one we created, "
                        f"not published")
                    continue
                for entry in BUNDLED_PET_FILES:      # 배포하는 세 파일만
                    _copy_into_fd(os.path.join(s, entry), stage_fd, entry)
                os.fchmod(stage_fd, 0o755)   # 판별이 끝난 뒤에 제 권한으로
            finally:
                os.close(stage_fd)
            # 대상이 있으면 커널이 거절하므로, 복사하는 사이에 그 펫이
            # 생겼어도(다른 인스턴스/사용자) 양보한다. 옮기는 쪽 이름도 게시
            # 직전에 대조한다 — renameatx_np 는 대상 이름만 지켜 주지, 원본
            # 이름이 그 사이 남의 것으로 바뀐 경우까지 막아 주지는 않는다.
            if not _is_ident_at(pets_fd, stage, stage_ident):
                report["errors"].append(
                    f"{rel}: the staging folder was replaced before publish, "
                    f"not published")
                continue
            if _publish_dir_noreplace(pets_fd, stage, pet):
                published = True
                report["copied"].append(rel)
            else:
                report["skipped"].append(rel)
        except Exception as e:
            report["errors"].append(f"{rel}: {e}")
        finally:
            if not published:        # 실패분·양보분 모두 흔적 없이 치운다
                _remove_stage_at(pets_fd, stage, stage_ident)


# 상태 목록. idle 은 필수, 나머지는 없으면 idle 로 대체된다.
_PET_FALLBACK_STATES = ("waiting", "failed", "waving", "running",
                        "running-left", "running-right", "jumping", "review")

# spritesheet.webp 의 고정 격자 규약. spriteVersionNumber 별로 관리.
#   시트는 8열 × 11행 격자(각 칸=시트폭/8 × 시트높이/11). 각 상태는 한 행의
#   0번 칸부터 count 개 프레임을 차지하고, 나머지 칸은 투명하게 비어 있다.
#   (행 9·10 은 앱이 쓰지 않는 여분 상태 — 무시)
PET_SHEET_COLS = 8
PET_SHEET_ROWS = 11
PET_LAYOUT_V2 = {              # state: (row, frame_count)
    "idle":          (0, 7),
    "running-right": (1, 8),
    "running-left":  (2, 8),
    "waving":        (3, 4),
    "jumping":       (4, 5),
    "failed":        (5, 8),
    "waiting":       (6, 6),
    "running":       (7, 6),
    "review":        (8, 6),
}
PET_LAYOUTS = {2: PET_LAYOUT_V2}


def _pet_layout(meta):
    ver = meta.get("spriteVersionNumber") or meta.get("spriteVersion") or 2
    return PET_LAYOUTS.get(int(ver), PET_LAYOUT_V2)


def _pet_json_path(d):
    return os.path.join(d, "pet.json")


def _read_pet_json(d):
    try:
        with open(_pet_json_path(d), encoding="utf-8") as f:   # pet.json 은 UTF-8 (Windows 기본은 cp949)
            return json.load(f)
    except Exception:
        return None


def _is_pet_dir(d):
    """유효한 펫 폴더인지. 신형(pet.json) 또는 구형(idle/ PNG 폴더) 둘 다 인정."""
    if not os.path.isdir(d):
        return False
    if os.path.isfile(_pet_json_path(d)):
        return True
    idle = os.path.join(d, "idle")
    return os.path.isdir(idle) and bool(glob.glob(os.path.join(idle, "*.png")))


_PETS_README = """\
Claude Pet — 펫 추가하는 법 / How to add a pet
================================================

이 폴더(~/.claude_pet/pets) 안에 펫 이름으로 폴더를 하나 만들고,
그 안에 아래 두 파일을 넣으면 우클릭 → 펫 메뉴에 자동으로 나타납니다.
(앱을 재시작할 필요 없이, 메뉴를 다시 열면 바로 보입니다.)

Make a folder named after your pet inside this directory, put these two
files in it, and it shows up in the right-click → Pet menu automatically.

    pets/
      dog/
        pet.json
        spritesheet.webp

    zip 을 풀어 pets/dog/dog/pet.json 처럼 한 단계 더 깊어져도 인식합니다 (__MACOSX 는 무시).
    A zip extracted one level too deep (pets/dog/dog/pet.json) is recognized too; __MACOSX is ignored.

── pet.json ──────────────────────────────────────────────────────
{
  "id": "dog",
  "displayName": "Dog",          // 메뉴에 보일 이름 (없으면 폴더 이름)
  "description": "...",          // (선택) 설명
  "spriteVersionNumber": 2,      // 스프라이트 규약 버전
  "spritesheetPath": "spritesheet.webp"
}

── spritesheet.webp ──────────────────────────────────────────────
투명 배경(알파)의 한 장짜리 스프라이트시트. spriteVersionNumber 2 규약:
· 8열 × 11행 격자 (각 칸 = 시트폭/8 × 시트높이/11, 보통 1536×2288 → 192×208)
· 각 상태는 한 행의 왼쪽부터 채워지고 남는 칸은 비워 둡니다:
    행0 idle(7)  행1 running-right(8)  행2 running-left(8)
    행3 waving(4)  행4 jumping(5)  행5 failed(8)
    행6 waiting(6)  행7 running(6)  행8 review(6)

Transparent single-image sheet, spriteVersionNumber 2 convention:
8 cols × 11 rows grid; each state fills a row left-to-right (counts above).
"""


def _write_pets_readme(base):
    """펫 폴더 포맷 안내를 폴더 안에 남긴다(없거나 비어 있을 때만 생성).

    UTF-8 을 명시한다 — Windows 의 기본 인코딩(cp949)으로는 안내문의 문자 일부를 못 써서 0 바이트 파일만
    남았다(실기기 관찰 2026-09-12). 그래서 비어 있는 README 는 없는 것으로 보고 다시 쓴다.
    """
    path = os.path.join(base, "README.txt")
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(_PETS_README)
    except Exception:
        pass


_PET_JUNK_DIRS = ("__MACOSX",)   # zip 을 풀면 딸려 오는 부산물 — 펫 후보로 보지 않는다


def _nested_pet_dir(d):
    """pets/<이름>/ 자체가 펫 폴더가 아닐 때, 한 단계 아래의 펫 폴더 → 경로 또는 None.

    zip 안에 이미 <이름>/ 폴더가 들어 있는 채로 "<이름>" 폴더에 풀면 pets/<이름>/<이름>/pet.json 이 된다
    (사용자 사례 2026-09-12: hello-kitty/hello-kitty/, 옆에 __MACOSX/). 그 한 단계만 내려가 본다 —
    점으로 시작하는 폴더와 __MACOSX 는 무시하고, 펫 폴더가 정확히 하나면 그것, 여럿이면 바깥 이름과 같은
    것, 그래도 못 고르면 None(어느 것인지 짐작하지 않는다). 두 단계 이상은 보지 않는다.
    """
    try:
        subs = sorted(os.listdir(d))
    except Exception:
        return None
    cands = []
    for sub in subs:
        if sub.startswith(".") or sub in _PET_JUNK_DIRS:
            continue
        p = os.path.join(d, sub)
        if os.path.isdir(p) and not os.path.islink(p) and _is_pet_dir(p):
            cands.append(p)
    if len(cands) == 1:
        return cands[0]
    same = [p for p in cands if os.path.basename(p) == os.path.basename(d)]
    return same[0] if len(same) == 1 else None


def discover_pets():
    """선택 가능한 펫 목록 [{'id','name','dir'}]. 첫 항목이 기본(내장) 펫.

    · 내장 : 앱에 포함된 frames/ (PET_DIR) — 기존 고양이
    · 사용자: ~/.claude_pet/pets/<이름>/ 아래 각 폴더 (유저가 직접 넣음).
             예) pets/dog/ 안에 pet.json + spritesheet.webp
             pets/dog/dog/ 처럼 한 단계 더 깊어도(zip 을 그대로 푼 경우) 인식한다 — _nested_pet_dir.
             id 는 언제나 바깥 폴더 이름이고, dir 은 실제 pet.json 이 있는 폴더다.
    """
    pets = []
    seen = set()
    if _is_pet_dir(PET_DIR):
        pets.append({"id": "default", "name": t("pet_default"), "dir": PET_DIR})
        seen.add("default")
    try:
        names = sorted(os.listdir(USER_PETS_DIR))
    except Exception:
        names = []
    for name in names:
        if name.startswith(".") or name in _PET_JUNK_DIRS or name in seen:
            continue
        d = os.path.join(USER_PETS_DIR, name)
        if not _is_pet_dir(d):
            d = _nested_pet_dir(d)
            if d is None:
                continue
        meta = _read_pet_json(d) or {}
        disp = meta.get("displayName") or meta.get("name") or name
        pets.append({"id": name, "name": str(disp), "dir": d})
        seen.add(name)
    return pets

SESSION_HOURS = 5
REFRESH_SEC = 30

APP_VERSION = "0.25"                 # CFBundleShortVersionString 과 일치해야 한다
GITHUB_REPO = "uygnoey/claude-pet"  # 자동 업데이트 확인용
UPDATE_CHECK_SEC = 3600             # 새 릴리즈 확인 주기(1시간). 시작 시엔 확인하지 않고 한 주기 뒤부터 — run_gui 참조
_upd_cache = {"t": 0.0, "busy": False}

# 교체 스크립트가 '새 앱이 정말 떴는지' 확인할 때 쓰는 시간들. 여기 상수로 두는
# 이유는 튜닝이 아니라 시험 가능성이다 — 예전에는 스크립트 본문의 `sleep 0.5`
# 같은 문자열을 밖에서 찾아 바꿔야만 빨리 돌릴 수 있었고, 그러면 확인 대상인
# 스크립트와 실제로 돌린 스크립트가 달라진다(치환이 빗나가면 조용히 20초를
# 기다리다 죽는다). 값만 낮춰서 '같은 스크립트'를 돌릴 수 있어야 한다.
#
# 기본값은 지금까지의 운영값 그대로다: 0.5초 간격으로 40번(=최대 20초) 기다려
# 새 pid 를 찾고, 찾은 뒤 3초 두었다가 그 pid 가 아직 살아 있는지 본다.
UPDATE_ACK_POLLS = int(os.environ.get("CLAUDE_PET_ACK_POLLS", 40))
UPDATE_ACK_INTERVAL = float(os.environ.get("CLAUDE_PET_ACK_INTERVAL", 0.5))
UPDATE_ACK_SETTLE = float(os.environ.get("CLAUDE_PET_ACK_SETTLE", 3))

# 업데이트 zip 내려받기의 한계값.
#
# 이 셋은 '느린 회선을 배려하는 값'이 아니라 '거래가 끝나기는 하는가'를 보장하는
# 값이다. 내려받기는 업데이트 잠금 '안'에서 일어나므로(그건 의도된 것이다 —
# install_github_update 의 주석 참고), 여기서 영영 멈추면 잠금이 프로세스가
# 사는 내내 붙들린다. 그러면 이후의 모든 업데이트가 잠금을 못 잡고 조용히
# 실패하고, 사용자가 버튼을 몇 번을 눌러도 아무 일도 일어나지 않는다 — 앱을
# 껐다 켜는 것 말고는 빠져나갈 길이 없다. 서명 도구에 타임아웃을 두는 이유와
# 같은 이유이고(_run_signing_tool), 그쪽에는 있고 여기에는 없었다.
#
#  · TIMEOUT  소켓 한 번의 읽기/연결에 걸리는 한계. 연결이 죽은 경우를 잡는다.
#  · DEADLINE 내려받기 전체의 벽시계 한계. 소켓 타임아웃만으로는 '아주 느리게
#             조금씩 보내는' 서버를 못 막는다 — 매 읽기가 제때 오면 타임아웃은
#             영원히 안 걸린다. 끝나는 것을 보장하는 건 이쪽이다.
#  · MAX      받을 수 있는 최대 바이트. 우리 배포물은 100MB 를 넘지 않는다.
#             크기를 안 막으면 응답 하나로 디스크를 채울 수 있다.
UPDATE_DOWNLOAD_TIMEOUT = float(
    os.environ.get("CLAUDE_PET_DOWNLOAD_TIMEOUT", 30))
UPDATE_DOWNLOAD_DEADLINE = float(
    os.environ.get("CLAUDE_PET_DOWNLOAD_DEADLINE", 600))
UPDATE_DOWNLOAD_MAX = int(
    os.environ.get("CLAUDE_PET_DOWNLOAD_MAX", 400 * 1024 * 1024))

# 런타임 설정 — 환경변수가 기본값, ~/.claude_pet.json(설정 UI)이 덮어씀
RUNTIME = {
    "mode": "sub",   # "sub"=구독(Claude Code 로그) / "api"=Admin API 비용
    # 한도(토큰) 추정치 — 공식 공개값 아님. Settings > Usage와 비교해 보정.
    "session_limit": int(os.environ.get("CLAUDE_PET_SESSION_LIMIT", 8_000_000)),
    "weekly_limit":  int(os.environ.get("CLAUDE_PET_WEEKLY_LIMIT", 60_000_000)),
    "opus_limit":    int(os.environ.get("CLAUDE_PET_OPUS_LIMIT", 15_000_000)),
    "spike_mult": 1.0,          # 급증 민감도 배율 (0.5=민감, 1=보통, 2=둔감)
    "greet": os.environ.get("CLAUDE_PET_FOLLOW", "1") != "0",
    # 조용한 동행: 펫이 가끔 스스로 돌아다니고, 활동이 있으면 다가와 바라본다.
    # 우클릭 메뉴의 체크 항목으로 켜고 끈다(설정 창 키가 아니라 자기 키만 쓴다).
    "roam": os.environ.get("CLAUDE_PET_ROAM", "1") != "0",
    "admin_key": os.environ.get("ANTHROPIC_ADMIN_KEY", ""),
    "api_budget": 0.0,          # API 모드 월 예산($), 0이면 게이지 없음
    # 모델별 한도 게이지의 모델 키워드. "auto"면 로그에서 상위 티어 자동 감지
    # (앱의 모델별 한도 대상이 Opus → Fable 처럼 시기마다 바뀌므로 auto 권장)
    "model_keyword": os.environ.get("CLAUDE_PET_MODEL", "auto"),
    # 주간 리셋 요일/시각 (앱의 "(토) 오후 8:00에 재설정" 같은 것)
    # None이면 롤링 7일. 0=월 ... 5=토, 6=일
    "weekly_reset_day": None,
    "weekly_reset_hour": 20,
}

def apply_config(cfg):
    for k in ("mode", "session_limit", "weekly_limit", "opus_limit",
              "spike_mult", "greet", "roam", "admin_key", "api_budget",
              "model_keyword", "weekly_reset_day", "weekly_reset_hour", "lang"):
        if k in cfg:
            RUNTIME[k] = cfg[k]
    set_lang(RUNTIME.get("lang"))

# ─────────────────────── 다국어 (i18n) ───────────────────────
SUPPORTED_LANGS = ("en", "ko", "ja", "es")
LANG_NAMES = {"en": "English", "ko": "한국어", "ja": "日本語", "es": "Español"}

def _system_lang():
    try:
        from Foundation import NSLocale
        for pl in (NSLocale.preferredLanguages() or []):
            code = str(pl).split("-")[0].split("_")[0].lower()
            if code in SUPPORTED_LANGS:
                return code
    except Exception:
        pass
    return "en"

L = {"lang": _system_lang()}

def set_lang(code):
    L["lang"] = code if code in SUPPORTED_LANGS else _system_lang()

def t(key, **kw):
    d = TR.get(L["lang"]) or TR["en"]
    s = d.get(key)
    if s is None:
        s = TR["en"].get(key, key)
    return s.format(**kw) if kw else s

WEEKDAYS_FULL = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "ko": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"],
    "ja": ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"],
    "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
}

TR = {
  "en": {
    "session": "Session", "weekly": "Weekly", "credit": "Credit", "model": "Model",
    "reset_done": "reset", "cd_days": "in {d}d {h}h", "cd_hm": "in {h}h {m}m",
    "cd_m": "in {m}m", "reset_prefix": "reset ", "used": "used", "exact_mode_server": "Exact mode (server values)", "today_api": "Today API",
    "loading": "loading…", "today": "Today", "this_month": "This month", "token_expired": "⚠ Token expired — run Claude Code once to restore Exact mode",
    "need_admin_key": "Right-click → Settings to enter an Admin API key",
    "scanning": "Scanning usage…",
    "onb_install": "Claude Code not installed",
    "onb_login": "Claude Code — sign-in needed",
    "menu_install_cc": "⬇︎ Install Claude Code…",
    "menu_login_cc": "🔑 Sign in to Claude Code…",
    "term_installing": "▶ Installing Claude Code…",
    "term_login": "▶ Signing in — a browser will open, please log in.",
    "term_done": "✅ Done. You can close this window; Claude Pet will show usage shortly.",
    "menu_settings": "Settings…", "menu_toggle": "Show/hide the usage pill",
    "menu_reset_size": "Reset size", "menu_quit": "Quit Claude Pet",
    "menu_roam": "Roam the screen",
    "menu_autostart": "Start at sign-in",
    "autostart_title": "Start at sign-in",
    "autostart_approval": "macOS needs your approval: System Settings → General → Login Items.",
    "autostart_open_settings": "Open Login Items",
    "autostart_fail": "Could not change the sign-in setting.",
    "autostart_unavailable": "Start at sign-in (not available here)",
    "menu_update": "⬆︎ Install v{v}",
    "menu_check_update": "⬆︎ Check for updates…",
    "upd_title": "Claude Pet update",
    "upd_current": "You're on the latest version (v{v}).",
    "upd_failed": "Could not check for updates. Try again later.",
    "upd_install_failed": "The update could not be installed. Try again later.",
    "upd_busy": "An update check is already running.",
    "menu_uninstall": "Uninstall completely…",
    "menu_pets": "Pet", "pet_default": "Cat 🐱",
    "pet_add": "➕ Add a pet… (open folder)",
    "unin_title": "Uninstall Claude Pet?",
    "unin_body": ("This deletes the app and all of its settings:\n\n{items}\n\n"
                  "Your Claude Code login and its data (~/.claude) are NOT touched.\n"
                  "This cannot be undone."),
    "unin_ok": "Delete", "unin_cancel": "Cancel",
    "unin_fail": "Uninstall failed. Drag Claude Pet to the Trash manually.",
    "unin_devmode": ("Running from source, not an installed app — nothing to "
                     "uninstall. Settings files were removed."),
    "settings_title": "Claude Pet Settings", "s_data_source": "Data source",
    "s_mode_sub": "Subscription (Claude Code logs)", "s_mode_api": "API (Admin API cost)",
    "s_model_kw": "Model gauge keyword", "s_auto_detect": "(auto = auto-detect)",
    "s_weekly_reset": "Weekly reset", "s_rolling7": "Rolling 7 days", "s_hour": "h",
    "s_calib1": "🔧 Calibrate: enter the % from Claude app > Settings > Usage",
    "s_calib2": "      and limits are back-solved (only fields you fill)",
    "s_calib_session": "Current session used (%)", "s_calib_weekly_all": "Weekly all models (%)",
    "s_calib_weekly_model": "Weekly per-model (%)", "s_limit_session": "Session limit (M tokens)",
    "s_limit_weekly": "Weekly limit (M tokens)", "s_limit_model": "Model limit (M tokens)",
    "s_spike_sens": "Spike alert sensitivity", "s_sens_high": "High (alert on small use)",
    "s_sens_normal": "Normal", "s_sens_low": "Low (alert only on heavy use)",
    "s_greet": "Wave when the mouse comes close", "s_admin_key": "Admin API key",
    "s_budget": "API monthly budget ($)", "s_save": "Save", "s_language": "Language",
    "s_pet": "Pet",
    "s_limit_note1": "※ Leave a field blank to keep the limit currently in effect.",
    "s_limit_note2": ("     Exact-mode gauges come from the server; no calibration.\n"
                      "     Spike detection still uses these estimated limits."),
    "s_limit_note3": "※ The % wins over an absolute limit.",
    "s_limit_advanced": "▸ Advanced: enter absolute limits",
    "s_limit_advanced_button": "Advanced…",
    "s_limit_current": "now: {value}M",
    "s_g_session": "Session limit", "s_g_weekly": "Weekly limit",
    "s_g_opus": "Model limit",
    "s_err_title": "Settings were not saved",
    "s_err_limit": ("{field}: enter a number greater than 0 (in M tokens). "
                    "Nothing was saved."),
    "s_err_calib": ("{field}: the calibration % must be greater than 0 and at "
                    "most 100. Nothing was saved."),
    "s_err_calib_zero": ("{field}: usage is 0 right now, so a limit cannot be "
                         "derived from a %. Clear the field or use the limit "
                         "in M tokens. Nothing was saved."),
    "s_err_calib_zero_pct": ("{field}: a limit cannot be derived from 0%. If "
                             "Claude shows 0%, this window has no usage yet — "
                             "calibrate once some has built up, or clear the "
                             "field to keep the current limit. Nothing was saved."),
    "s_err_save": "Could not write the settings file. Nothing was changed.",
    "s_err_calib_used": ("{field}: the current usage figure is unusable, so a "
                         "limit cannot be derived from a %. Nothing was saved."),
    "s_err_hour": ("Weekly reset hour: enter a whole number from 0 to 23. "
                   "Nothing was saved."),
    "s_err_budget": ("API monthly budget: enter a number of 0 or more. "
                     "Nothing was saved."),
    "r_title": "Claude Pet usage report", "r_exact": "Exact mode (server values)",
    "r_used": "used", "r_left": "left", "r_reset": "reset",
    "r_last_activity": "Last activity", "r_today_cost": "Today API cost",
  },
  "ko": {
    "session": "세션", "weekly": "주간", "credit": "크레딧", "model": "모델",
    "reset_done": "리셋됨", "cd_days": "{d}일 {h}시간 후", "cd_hm": "{h}시간 {m}분 후",
    "cd_m": "{m}분 후", "reset_prefix": "리셋 ", "used": "사용", "exact_mode_server": "정확 모드 (서버 계산 값)", "today_api": "오늘 API",
    "loading": "조회 중…", "today": "오늘", "this_month": "이번 달", "token_expired": "⚠ 토큰 만료 — Claude Code 한번 실행하면 정확 모드 복구",
    "need_admin_key": "우클릭 → 설정에서 Admin API 키를 입력하세요",
    "scanning": "사용량 스캔 중…",
    "onb_install": "Claude Code 미설치",
    "onb_login": "Claude Code 로그인 필요",
    "menu_install_cc": "⬇︎ Claude Code 설치…",
    "menu_login_cc": "🔑 Claude Code 로그인…",
    "term_installing": "▶ Claude Code를 설치합니다…",
    "term_login": "▶ 로그인합니다 — 브라우저가 열리면 로그인하세요.",
    "term_done": "✅ 완료됐습니다. 이 창은 닫아도 되며, 곧 Claude Pet에 사용량이 표시됩니다.",
    "menu_settings": "설정…", "menu_toggle": "사용량 필 접기/펴기",
    "menu_reset_size": "크기 원래대로", "menu_quit": "Claude Pet 종료",
    "menu_roam": "화면 돌아다니기",
    "menu_autostart": "로그인 시 자동 실행",
    "autostart_title": "로그인 시 자동 실행",
    "autostart_approval": "macOS 승인이 필요합니다: 시스템 설정 → 일반 → 로그인 항목",
    "autostart_open_settings": "로그인 항목 열기",
    "autostart_fail": "로그인 시 자동 실행 설정을 바꾸지 못했습니다.",
    "autostart_unavailable": "로그인 시 자동 실행 (여기서는 사용 불가)",
    "menu_uninstall": "완전 삭제…",
    "menu_pets": "펫", "pet_default": "고양이 🐱",
    "pet_add": "➕ 펫 추가… (폴더 열기)",
    "unin_title": "Claude Pet을 완전히 삭제할까요?",
    "unin_body": ("앱과 모든 설정을 지웁니다:\n\n{items}\n\n"
                  "Claude Code 로그인과 데이터(~/.claude)는 건드리지 않습니다.\n"
                  "되돌릴 수 없습니다."),
    "unin_ok": "삭제", "unin_cancel": "취소",
    "unin_fail": "삭제 실패. Claude Pet을 휴지통으로 직접 옮겨주세요.",
    "unin_devmode": ("설치된 앱이 아니라 소스에서 실행 중이라 지울 앱이 없습니다. "
                     "설정 파일은 삭제했습니다."),
    "menu_update": "⬆︎ 새 버전 v{v} 설치",
    "menu_check_update": "⬆︎ 업데이트 확인…",
    "upd_title": "Claude Pet 업데이트",
    "upd_current": "최신 버전입니다 (v{v}).",
    "upd_failed": "업데이트를 확인하지 못했습니다. 잠시 후 다시 시도하세요.",
    "upd_install_failed": "업데이트를 설치하지 못했습니다. 잠시 후 다시 시도하세요.",
    "upd_busy": "이미 업데이트를 확인하는 중입니다.",
    "settings_title": "Claude Pet 설정", "s_data_source": "데이터 소스",
    "s_mode_sub": "구독 (Claude Code 로그)", "s_mode_api": "API (Admin API 비용)",
    "s_model_kw": "모델 게이지 키워드", "s_auto_detect": "(auto=자동감지)",
    "s_weekly_reset": "주간 리셋", "s_rolling7": "롤링 7일", "s_hour": "시",
    "s_calib1": "🔧 보정: Claude 앱 설정 > 사용량의 %를 입력하면",
    "s_calib2": "      한도를 자동으로 계산해요 (입력한 것만 반영)",
    "s_calib_session": "현재 세션 사용됨 (%)", "s_calib_weekly_all": "주간 모든 모델 (%)",
    "s_calib_weekly_model": "주간 모델별 (%)", "s_limit_session": "세션 한도 (백만 토큰)",
    "s_limit_weekly": "주간 한도 (백만 토큰)", "s_limit_model": "모델 한도 (백만 토큰)",
    "s_spike_sens": "급증 알림 민감도", "s_sens_high": "민감 (조금만 써도 경보)",
    "s_sens_normal": "보통", "s_sens_low": "둔감 (많이 써야 경보)",
    "s_greet": "마우스가 가까이 오면 인사하기", "s_admin_key": "Admin API 키",
    "s_budget": "API 월 예산 ($)", "s_save": "저장", "s_language": "언어",
    "s_pet": "펫",
    "s_limit_note1": "※ 비워 두면 지금 적용 중인 한도를 그대로 씁니다.",
    "s_limit_note2": ("     정확 모드 게이지는 서버 값이라 보정이 필요 없습니다.\n"
                      "     급증 감지는 이 추정 한도를 그대로 사용합니다."),
    "s_limit_note3": "※ %가 절대 한도보다 우선합니다.",
    "s_limit_advanced": "▸ 고급: 절대 한도 직접 입력",
    "s_limit_advanced_button": "고급…",
    "s_limit_current": "현재: {value}M",
    "s_g_session": "세션 한도", "s_g_weekly": "주간 한도",
    "s_g_opus": "모델 한도",
    "s_err_title": "설정을 저장하지 못했습니다",
    "s_err_limit": "{field}: 0보다 큰 숫자(M 토큰)를 입력하세요. 저장하지 않았습니다.",
    "s_err_calib": "{field}: 보정 %는 0 초과 100 이하만 됩니다. 저장하지 않았습니다.",
    "s_err_calib_zero": ("{field}: 지금 사용량이 0이라 %로 한도를 역산할 수 "
                         "없습니다. 칸을 비우거나 M 토큰 한도로 입력하세요. "
                         "저장하지 않았습니다."),
    "s_err_calib_zero_pct": ("{field}: 0%로는 한도를 계산할 수 없습니다. Claude "
                             "앱에 0%로 보인다면 이번 창의 사용량이 아직 없다는 "
                             "뜻이니, 조금 쓰신 뒤에 보정하거나 칸을 비워 지금 "
                             "한도를 그대로 두세요. 저장하지 않았습니다."),
    "s_err_save": "설정 파일을 쓰지 못했습니다. 아무것도 바뀌지 않았습니다.",
    "s_err_calib_used": ("{field}: 현재 사용량 값이 이상해서 %로 한도를 역산할 수 "
                         "없습니다. 저장하지 않았습니다."),
    "s_err_hour": "주간 리셋 시각: 0~23 사이 정수를 입력하세요. 저장하지 않았습니다.",
    "s_err_budget": "API 월 예산: 0 이상 숫자를 입력하세요. 저장하지 않았습니다.",
    "r_title": "Claude Pet 사용량 리포트", "r_exact": "정확 모드 (서버 계산 값)",
    "r_used": "사용", "r_left": "남음", "r_reset": "리셋",
    "r_last_activity": "마지막 활동", "r_today_cost": "오늘 API 비용",
  },
  "ja": {
    "session": "セッション", "weekly": "週間", "credit": "クレジット", "model": "モデル",
    "reset_done": "リセット済み", "cd_days": "{d}日{h}時間後", "cd_hm": "{h}時間{m}分後",
    "cd_m": "{m}分後", "reset_prefix": "リセット ", "used": "使用", "exact_mode_server": "正確モード（サーバー値）", "today_api": "本日API",
    "loading": "取得中…", "today": "今日", "this_month": "今月", "token_expired": "⚠ トークン期限切れ — Claude Code を一度実行すると正確モード復帰",
    "need_admin_key": "右クリック → 設定で Admin API キーを入力してください",
    "scanning": "使用量をスキャン中…",
    "onb_install": "Claude Code 未インストール",
    "onb_login": "Claude Code ログインが必要",
    "menu_install_cc": "⬇︎ Claude Code をインストール…",
    "menu_login_cc": "🔑 Claude Code にログイン…",
    "term_installing": "▶ Claude Code をインストールします…",
    "term_login": "▶ ログインします — ブラウザが開いたらログインしてください。",
    "term_done": "✅ 完了しました。このウィンドウは閉じて構いません。まもなく使用量が表示されます。",
    "menu_settings": "設定…", "menu_toggle": "使用量ピルの表示/非表示",
    "menu_reset_size": "サイズを元に戻す", "menu_quit": "Claude Pet を終了",
    "menu_roam": "画面を歩き回る",
    "menu_autostart": "サインイン時に自動起動",
    "autostart_title": "サインイン時に自動起動",
    "autostart_approval": "macOS の承認が必要です: システム設定 → 一般 → ログイン項目",
    "autostart_open_settings": "ログイン項目を開く",
    "autostart_fail": "サインイン時の起動設定を変更できませんでした。",
    "autostart_unavailable": "サインイン時に自動起動（ここでは利用不可）",
    "menu_uninstall": "完全に削除…",
    "menu_pets": "ペット", "pet_default": "ネコ 🐱",
    "pet_add": "➕ ペットを追加…（フォルダを開く）",
    "unin_title": "Claude Pet を完全に削除しますか？",
    "unin_body": ("アプリとすべての設定を削除します:\n\n{items}\n\n"
                  "Claude Code のログインとデータ (~/.claude) には触れません。\n"
                  "元に戻せません。"),
    "unin_ok": "削除", "unin_cancel": "キャンセル",
    "unin_fail": "削除に失敗しました。Claude Pet を手動でゴミ箱に移動してください。",
    "unin_devmode": ("インストール済みアプリではなくソースから実行中のため、"
                     "削除するアプリはありません。設定ファイルは削除しました。"),
    "menu_update": "⬆︎ 新バージョン v{v} をインストール",
    "menu_check_update": "⬆︎ アップデートを確認…",
    "upd_title": "Claude Pet アップデート",
    "upd_current": "最新バージョンです (v{v})。",
    "upd_failed": "アップデートを確認できませんでした。しばらくしてからもう一度お試しください。",
    "upd_install_failed": "アップデートをインストールできませんでした。しばらくしてからもう一度お試しください。",
    "upd_busy": "すでにアップデートを確認中です。",
    "settings_title": "Claude Pet 設定", "s_data_source": "データソース",
    "s_mode_sub": "サブスク (Claude Code ログ)", "s_mode_api": "API (Admin API コスト)",
    "s_model_kw": "モデルゲージのキーワード", "s_auto_detect": "(auto=自動検出)",
    "s_weekly_reset": "週間リセット", "s_rolling7": "7日ローリング", "s_hour": "時",
    "s_calib1": "🔧 補正: Claude アプリ 設定 > 使用状況 の % を入力すると",
    "s_calib2": "      上限を自動計算します（入力した項目のみ）",
    "s_calib_session": "現在のセッション使用 (%)", "s_calib_weekly_all": "週間 全モデル (%)",
    "s_calib_weekly_model": "週間 モデル別 (%)", "s_limit_session": "セッション上限 (百万トークン)",
    "s_limit_weekly": "週間上限 (百万トークン)", "s_limit_model": "モデル上限 (百万トークン)",
    "s_spike_sens": "急増アラート感度", "s_sens_high": "高 (少しの使用でも警告)",
    "s_sens_normal": "普通", "s_sens_low": "低 (大量使用時のみ警告)",
    "s_greet": "マウスが近づいたら手を振る", "s_admin_key": "Admin API キー",
    "s_budget": "API 月次予算 ($)", "s_save": "保存", "s_language": "言語",
    "s_pet": "ペット",
    "s_limit_note1": "※ 空欄にすると、現在適用中の上限をそのまま使います。",
    "s_limit_note2": ("     正確モードのゲージはサーバー値なので補正は不要です。\n"
                      "     急増検知はこの推定上限をそのまま使います。"),
    "s_limit_note3": "※ % が絶対上限より優先されます。",
    "s_limit_advanced": "▸ 詳細: 絶対上限を直接入力",
    "s_limit_advanced_button": "詳細…",
    "s_limit_current": "現在: {value}M",
    "s_g_session": "セッション上限", "s_g_weekly": "週間上限",
    "s_g_opus": "モデル上限",
    "s_err_title": "設定を保存できませんでした",
    "s_err_limit": ("{field}: 0 より大きい数値（百万トークン）を入力してください。"
                    "保存していません。"),
    "s_err_calib": ("{field}: 補正の % は 0 より大きく 100 以下にしてください。"
                    "保存していません。"),
    "s_err_calib_zero": ("{field}: 現在の使用量が 0 のため % から上限を逆算でき"
                         "ません。欄を空にするか、百万トークンで上限を入力して"
                         "ください。保存していません。"),
    "s_err_calib_zero_pct": ("{field}: 0% からは上限を計算できません。Claude アプリ"
                             "で 0% と表示されている場合、この期間の使用量がまだ"
                             "ないという意味です。少し使ってから補正するか、欄を"
                             "空にして今の上限をそのままにしてください。保存して"
                             "いません。"),
    "s_err_save": "設定ファイルを書き込めませんでした。何も変更していません。",
    "s_err_calib_used": ("{field}: 現在の使用量の値が不正なため % から上限を逆算"
                         "できません。保存していません。"),
    "s_err_hour": ("週間リセット時刻: 0〜23 の整数を入力してください。"
                   "保存していません。"),
    "s_err_budget": ("API 月次予算: 0 以上の数値を入力してください。"
                     "保存していません。"),
    "r_title": "Claude Pet 使用量レポート", "r_exact": "正確モード（サーバー値）",
    "r_used": "使用", "r_left": "残り", "r_reset": "リセット",
    "r_last_activity": "最終アクティビティ", "r_today_cost": "本日のAPIコスト",
  },
  "es": {
    "session": "Sesión", "weekly": "Semanal", "credit": "Crédito", "model": "Modelo",
    "reset_done": "reiniciado", "cd_days": "en {d}d {h}h", "cd_hm": "en {h}h {m}m",
    "cd_m": "en {m}m", "reset_prefix": "reinicio ", "used": "usado", "exact_mode_server": "Modo exacto (valores del servidor)", "today_api": "API hoy",
    "loading": "cargando…", "today": "Hoy", "this_month": "Este mes", "token_expired": "⚠ Token expirado — ejecuta Claude Code una vez para restaurar el modo Exacto",
    "need_admin_key": "Clic derecho → Ajustes para introducir una clave de Admin API",
    "scanning": "Escaneando uso…",
    "onb_install": "Claude Code no instalado",
    "onb_login": "Claude Code: inicia sesión",
    "menu_install_cc": "⬇︎ Instalar Claude Code…",
    "menu_login_cc": "🔑 Iniciar sesión en Claude Code…",
    "term_installing": "▶ Instalando Claude Code…",
    "term_login": "▶ Iniciando sesión — se abrirá el navegador, inicia sesión.",
    "term_done": "✅ Listo. Puedes cerrar esta ventana; Claude Pet mostrará el uso en breve.",
    "menu_settings": "Ajustes…", "menu_toggle": "Mostrar/ocultar la píldora",
    "menu_reset_size": "Restablecer tamaño", "menu_quit": "Salir de Claude Pet",
    "menu_roam": "Pasear por la pantalla",
    "menu_autostart": "Abrir al iniciar sesión",
    "autostart_title": "Abrir al iniciar sesión",
    "autostart_approval": "macOS necesita tu aprobación: Ajustes del Sistema → General → Ítems de inicio",
    "autostart_open_settings": "Abrir Ítems de inicio",
    "autostart_fail": "No se pudo cambiar el inicio al iniciar sesión.",
    "autostart_unavailable": "Abrir al iniciar sesión (no disponible aquí)",
    "menu_uninstall": "Desinstalar por completo…",
    "menu_pets": "Mascota", "pet_default": "Gato 🐱",
    "pet_add": "➕ Añadir mascota… (abrir carpeta)",
    "unin_title": "¿Desinstalar Claude Pet?",
    "unin_body": ("Se eliminarán la app y todos sus ajustes:\n\n{items}\n\n"
                  "Tu sesión de Claude Code y sus datos (~/.claude) no se tocan.\n"
                  "Esto no se puede deshacer."),
    "unin_ok": "Eliminar", "unin_cancel": "Cancelar",
    "unin_fail": "Error al desinstalar. Arrastra Claude Pet a la Papelera manualmente.",
    "unin_devmode": ("Se está ejecutando desde el código fuente, no como app "
                     "instalada. Se eliminaron los archivos de ajustes."),
    "menu_update": "⬆︎ Instalar v{v}",
    "menu_check_update": "⬆︎ Buscar actualizaciones…",
    "upd_title": "Actualización de Claude Pet",
    "upd_current": "Ya tienes la última versión (v{v}).",
    "upd_failed": "No se pudo comprobar si hay actualizaciones. Inténtalo más tarde.",
    "upd_install_failed": "No se pudo instalar la actualización. Inténtalo más tarde.",
    "upd_busy": "Ya se está comprobando si hay actualizaciones.",
    "settings_title": "Ajustes de Claude Pet", "s_data_source": "Fuente de datos",
    "s_mode_sub": "Suscripción (registros de Claude Code)", "s_mode_api": "API (coste de Admin API)",
    "s_model_kw": "Palabra clave del medidor de modelo", "s_auto_detect": "(auto = detección automática)",
    "s_weekly_reset": "Reinicio semanal", "s_rolling7": "7 días rodantes", "s_hour": "h",
    "s_calib1": "🔧 Calibrar: introduce el % de Ajustes > Uso de la app de Claude",
    "s_calib2": "      y los límites se despejan (solo los campos que rellenes)",
    "s_calib_session": "Sesión actual usada (%)", "s_calib_weekly_all": "Semanal todos los modelos (%)",
    "s_calib_weekly_model": "Semanal por modelo (%)", "s_limit_session": "Límite de sesión (M tokens)",
    "s_limit_weekly": "Límite semanal (M tokens)", "s_limit_model": "Límite de modelo (M tokens)",
    "s_spike_sens": "Sensibilidad de alerta de pico", "s_sens_high": "Alta (alerta con poco uso)",
    "s_sens_normal": "Normal", "s_sens_low": "Baja (alerta solo con uso alto)",
    "s_greet": "Saludar cuando el ratón se acerca", "s_admin_key": "Clave de Admin API",
    "s_budget": "Presupuesto mensual de API ($)", "s_save": "Guardar", "s_language": "Idioma",
    "s_pet": "Mascota",
    "s_limit_note1": "※ Deja un campo vacío para conservar el límite vigente.",
    "s_limit_note2": ("     Modo exacto: medidores del servidor, sin calibrar.\n"
                      "     La detección de picos sí usa estos límites estimados."),
    "s_limit_note3": "※ El % manda sobre el límite absoluto.",
    "s_limit_advanced": "▸ Avanzado: introducir límites absolutos",
    "s_limit_advanced_button": "Avanzado…",
    "s_limit_current": "ahora: {value}M",
    "s_g_session": "Límite de sesión", "s_g_weekly": "Límite semanal",
    "s_g_opus": "Límite de modelo",
    "s_err_title": "No se guardó la configuración",
    "s_err_limit": ("{field}: introduce un número mayor que 0 (en M tokens). "
                    "No se guardó nada."),
    "s_err_calib": ("{field}: el % de calibración debe ser mayor que 0 y como "
                    "máximo 100. No se guardó nada."),
    "s_err_calib_zero": ("{field}: el uso actual es 0, así que no se puede "
                         "deducir el límite a partir de un %. Deja el campo "
                         "vacío o usa el límite en M tokens. No se guardó nada."),
    "s_err_calib_zero_pct": ("{field}: no se puede deducir un límite a partir de "
                             "0%. Si Claude muestra 0%, esta ventana aún no tiene "
                             "uso: calibra cuando se haya acumulado algo, o deja "
                             "el campo vacío para conservar el límite actual. "
                             "No se guardó nada."),
    "s_err_save": ("No se pudo escribir el archivo de configuración. No se "
                   "cambió nada."),
    "s_err_calib_used": ("{field}: la cifra de uso actual no es válida, así que "
                         "no se puede deducir el límite de un %. No se guardó nada."),
    "s_err_hour": ("Hora de reinicio semanal: introduce un entero de 0 a 23. "
                   "No se guardó nada."),
    "s_err_budget": ("Presupuesto mensual de API: introduce un número mayor o "
                     "igual que 0. No se guardó nada."),
    "r_title": "Informe de uso de Claude Pet", "r_exact": "Modo exacto (valores del servidor)",
    "r_used": "usado", "r_left": "resta", "r_reset": "reinicio",
    "r_last_activity": "Última actividad", "r_today_cost": "Coste de API hoy",
  },
}

# 모션별 (프레임 간격 ms, 반복, 루프 후 휴식 ms) — 평소엔 얌전히!
# 휴식 중엔 첫 프레임으로 정지. idle은 8초에 한 번만 숨쉬기/깜빡임.
STATE_CFG = {
    "idle":          (430, True,  25000),  # 25초에 한 번만 숨쉬기
    "waiting":       (340, True,  12000),  # 가끔만 꼼지락
    "failed":        (260, True,  6000),   # 패닉도 6초에 한 번만
    "waving":        (200, False, 0),      # 인사 — 한 번만
    "jumping":       (150, False, 0),      # 점프 — 한 번만
    "running-left":  (90,  True,  0),      # 달릴 때만 연속 재생
    "running-right": (90,  True,  0),
    "running":       (90,  True,  0),
    "review":        (360, True,  20000),
}
DEFAULT_CFG = (400, True, 15000)

# 소비 급증 기본 임계치(%): 최근 5분 소비가 한도의 몇 %를 넘으면 경보
# 실제 임계치 = 기본값 × RUNTIME["spike_mult"] (설정 UI의 민감도)
# 세션 1%는 활발한 정상 사용의 5분 burn과 거의 붙어 있어 오탐이 잦았다 →
# 2%로 올려 안전마진 확보. (base=활동 버킷 평균으로 2.5배 게이트도 정상화)
SPIKE_BASE = {"session": 2.0, "weekly": 0.5, "opus": 2.0}

CONFIG_PATH = os.path.expanduser("~/.claude_pet.json")

def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_UNCHECKED = object()          # save_config(expect_stamp=...) 의 "확인 안 함"


def _config_stamp():
    """설정 파일의 정체(inode, mtime, 크기). 없으면 None."""
    try:
        st = os.stat(CONFIG_PATH)
        return (st.st_ino, st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def save_config(cfg, expect_stamp=_UNCHECKED):
    """설정을 원자적으로 저장한다. 성공 True / 실패 False.

    같은 디렉터리에 임시 파일을 쓰고 flush+fsync 한 뒤 os.replace 로 바꾼다.
    (다른 디렉터리에 쓰면 rename 이 원자적이지 않다.) 중간에 실패해도 기존
    파일은 그대로 남는다 — 저장이 실패했는데 설정만 반쯤 날아가는 일 방지.

    expect_stamp 를 주면 compare-and-swap 이 된다: 바꿔치기 직전에 파일이
    그 정체 그대로일 때만 쓰고, 그 사이 누가 썼으면 아무것도 하지 않고 False.
    (읽고 → 합치고 → 쓰는 사이에 남이 쓴 값을 덮어쓰는 것을 막는다.)
    """
    tmp = None
    try:
        d = os.path.dirname(CONFIG_PATH) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".claude_pet.", suffix=".tmp", dir=d)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
            f.flush()
            os.fsync(f.fileno())
        if expect_stamp is not _UNCHECKED and _config_stamp() != expect_stamp:
            return False           # 그 사이에 누가 썼다 → 덮어쓰지 않는다
        os.replace(tmp, CONFIG_PATH)
        return True
    except Exception:
        return False
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


# 설정 창이 '소유'하는 키 — 저장할 때 이 키들만 디스크에 얹는다.
# x/y(드래그)·scale(크기)은 여기 없다: 그 경로들이 각자 자기 키만 쓴다.
SETTINGS_OWNED_KEYS = ("pet", "lang", "mode", "model_keyword",
                       "weekly_reset_day", "weekly_reset_hour",
                       "session_limit", "weekly_limit", "opus_limit",
                       "spike_mult", "greet", "admin_key", "api_budget")


def _config_lock_path():
    return CONFIG_PATH + ".lock"


class _config_lock:
    """설정 읽기→쓰기 전체를 감싸는 프로세스 간 잠금(flock).

    설정 파일 자체에 걸면 안 된다 — 우리 저장이 os.replace 로 inode 를 바꾸는
    순간 잠금은 사라진 옛 inode 에 남고, 다른 인스턴스가 새 inode 를 그냥
    잠글 수 있다. 그래서 절대 지우거나 바꾸지 않는 별도 파일에 건다.
    flock 은 프로세스가 죽으면 커널이 풀어 주므로 잠금이 영구히 남지 않는다
    (O_EXCL 잠금 파일은 크래시 한 번에 영영 잠긴 채로 남는다).
    """

    def __enter__(self):
        self.fd = None
        try:
            self.fd = os.open(_config_lock_path(),
                              os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(self.fd, fcntl.LOCK_EX)
        except OSError:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None      # 잠글 수 없어도 저장은 진행(CAS 가 남는다)
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
        return False


CONFIG_MERGE_RETRIES = 4


def merge_config_updates(updates):
    """디스크의 최신 설정을 다시 읽어 updates 만 얹어 저장한다 → (ok, merged).

    설정 dict 는 앱 시작 때 한 번 읽은 스냅샷이라, 통째로 다시 쓰면 그 뒤에
    다른 경로(다른 인스턴스/외부 편집)가 바꾼 키가 옛 값으로 되돌아간다
    (lost update). 드래그는 x/y, 크기는 scale, 펫 교체는 pet, 설정 창은 자기
    필드만 넘기고, 나머지 키는 디스크에 있는 최신 값을 그대로 살린다.

    실제로 보장하는 것만 적는다(넘겨짚은 보장은 다음 사람이 그대로 믿는다):
      · os.replace  : 찢어진 파일(쓰다 만 JSON)은 생기지 않는다 — 보장.
      · flock       : ClaudePet 인스턴스끼리는 상호 배제된다 — 보장.
                      단, 이 잠금을 따르는 쪽에만 해당한다.
      · CAS + 재시도: 잠금을 따르지 않는 쪽(외부 편집기 등)이 읽기와 쓰기 사이에
                      쓴 값을 '대체로' 살려 낸다 — best-effort 이지 보장이 아니다.
                      확인과 replace 사이는 여전히 남고, 재시도 횟수도 유한하다.
    """
    merged = None
    with _config_lock():
        for _ in range(CONFIG_MERGE_RETRIES):
            stamp = _config_stamp()
            merged = dict(load_config())
            merged.update(updates)      # UI 가 가진 키는 UI 가 이긴다
            if save_config(merged, expect_stamp=stamp):
                return True, merged
    return False, None


# ─────────────── 설정값 검증 (설정 창 저장 전) ───────────────
# 게이지 키 → 설정 키. 설정 창의 "직접 입력(M 토큰)"과 "보정(%)" 둘 다 이 순서.
GAUGE_LIMIT_KEYS = (("session", "session_limit"),
                    ("weekly", "weekly_limit"),
                    ("opus", "opus_limit"))

# 한도(토큰)를 M 단위로 표시할 때의 소수 자릿수. 6자리면 1토큰 단위까지 표현되어
# 손대지 않은 필드가 저장 후에도 정확히 같은 토큰 수로 되돌아온다(반올림 손실 없음).
LIMIT_M_DECIMALS = 6


def fmt_limit_m(tokens):
    """토큰 수 → 설정 창에 넣을 M 단위 문자열(최대 6자리, 뒤 0 제거)."""
    try:
        q = (Decimal(int(tokens)) / Decimal(10) ** 6).quantize(
            Decimal(1).scaleb(-LIMIT_M_DECIMALS))
    except Exception:
        return "0"
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


# 받아들이는 숫자 표기: 부호 + 숫자 + (소수점 숫자). 지수(1e999999999)도,
# 자릿수 구분/오타로 섞인 기호(8,5 · 1%2)도 받지 않는다. 예전처럼 ','·'%'를
# 그냥 빼 버리면 "8,5"가 85로, "1%2"가 12로 조용히 둔갑해 한도가 엉뚱해졌다.
_NUM_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")
_MAX_NUM_DIGITS = 18            # 상식 밖 자릿수는 입력 실수로 본다


def _to_decimal(raw, allow_percent=False):
    """설정 창 입력 → Decimal. 허용 표기가 아니면 None.

    allow_percent 는 보정(%) 칸에서만 켠다. M 토큰 칸에 '8%' 를 적었다면 칸을
    잘못 본 것이므로 8 로 받아 주면 안 된다 — 되묻는 편이 낫다.
    """
    txt = str(raw).strip()
    if allow_percent and txt.endswith("%"):   # 보정 칸엔 '%'까지 적는 사람이 많다
        txt = txt[:-1].strip()
    if not txt or not _NUM_RE.match(txt):
        return None
    if sum(ch.isdigit() for ch in txt) > _MAX_NUM_DIGITS:
        return None
    try:
        v = Decimal(txt)
    except (InvalidOperation, ValueError, ArithmeticError):
        return None
    if not v.is_finite():          # 방어적 — 위 정규식이면 이미 유한하다
        return None
    return v


def _finite_decimal(value):
    """추정기가 준 수치 → 유한한 Decimal. 아니면 None (예외를 내지 않는다)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(value) if isinstance(value, (int, Decimal)) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return None
    return d if d.is_finite() else None


def _calibration_percent_error(raw):
    """보정 % 원문 → Decimal, 또는 오류 메시지 **키**(문자열).

    반환형으로 둘을 구분하는 이유는 이 검사가 두 곳에서 쓰이기 때문이다:
    사용량을 구하기 '전'(plan_settings_save)과 역산 직전(prepare_settings_config).
    사용량 조회는 남의 로그를 읽는 일이라 실패할 수 있으므로, 사용자가 친 값이
    이미 틀렸다면 그 전에 돌려보내야 한다 — 안 그러면 '내 입력이 틀렸다' 대신
    '앱이 사용량을 못 읽었다'는 엉뚱한 메시지가 나간다.

    0 은 범위 오류와 따로 다룬다. 0 은 오타가 아니라 사용자가 Claude 앱에서
    실제로 본 값일 수 있고, 그때 필요한 안내는 '0~100 을 입력하라'가 아니라
    '아직 역산할 사용량이 없다'이다.
    """
    pct = _to_decimal(raw, allow_percent=True)
    if pct is None:
        return "s_err_calib"
    if pct == 0:
        return "s_err_calib_zero_pct"
    if pct < 0 or pct > 100:
        return "s_err_calib"
    return pct


def prepare_settings_config(base_cfg, direct_by_gauge, calibration_by_gauge,
                            usage_stats):
    """설정 창의 한도 입력을 검증해 (새 설정 dict, 오류 메시지) 를 만든다.

    **입력은 게이지마다 독립이고, 셋 다 선택 사항이다.** 일반 사용자는 토큰
    숫자를 알 수 없다 — Claude 앱에 보이는 것은 %뿐이다. 그래서 한 칸도 채우지
    않고 저장할 수 있어야 하고, 그때는 기존 한도가 그대로 남아야 한다.

    게이지별 해결 순서:
    · 보정(%)이 채워졌으면 → 사용량으로 역산한 값이 그 게이지의 한도가 된다.
    · %가 비고 직접 입력(M 토큰)이 채워졌으면 → 그 값을 쓴다(종전 검증 그대로).
    · 둘 다 비었으면 → **base_cfg 의 기존 값을 그대로 둔다.** base_cfg 에 그 키가
      없으면 만들지도 않는다 — 안 건드린 게이지 때문에 없던 override 가 새로
      생기면, 사용자는 손댄 적 없는 값이 고정돼 버린 것을 알 길이 없다.

    '비었다'와 '틀렸다'는 다르다. 비면 건너뛰지만, 값이 들어왔는데 이상하면
    저장 전체를 거부한다(부분 적용 금지 — 거부 시 아무것도 적용하지 않은 복사본).
    입력으로 받은 base_cfg 는 절대 건드리지 않는다.
    """
    candidate = dict(base_cfg)
    limits = {}
    for gkey, ckey in GAUGE_LIMIT_KEYS:
        raw = (direct_by_gauge or {}).get(gkey, "")
        # 빈 칸 판정은 손대지 않은 원문으로만 한다(아래 % 쪽과 같은 이유).
        if not str(raw).strip():
            continue                                   # 비워 두면 기존 한도 유지
        v = _to_decimal(raw)
        if v is None or v <= 0:
            return dict(base_cfg), t("s_err_limit", field=t("s_g_" + gkey))
        tokens = int((v * (Decimal(10) ** 6)).to_integral_value(rounding="ROUND_HALF_UP"))
        if tokens <= 0:
            return dict(base_cfg), t("s_err_limit", field=t("s_g_" + gkey))
        limits[ckey] = tokens

    for gkey, ckey in GAUGE_LIMIT_KEYS:
        raw = (calibration_by_gauge or {}).get(gkey, "")
        # '비었는가'는 손대지 않은 원문으로만 판단한다. 여기서 '%'를 먼저 빼고
        # 보면 '%' 나 '% %' 같은 입력이 빈 칸으로 둔갑해, 사용자는 값을 넣었는데
        # 앱은 "안 건드림"으로 처리하고 오류도 내지 않는다(가장 나쁜 모양).
        # 문자열이 무엇인지 정하기 전에 글자를 지우면 안 된다.
        if not str(raw).strip():
            continue                                   # 비워 두면 보정 안 함
        pct = _calibration_percent_error(raw)
        if isinstance(pct, str):
            return dict(base_cfg), t(pct, field=t("s_g_" + gkey))
        # used 는 사용자가 친 값이 아니라 추정기가 준 값이다. 그래도 nan/inf/문자가
        # 섞여 들어오면 Decimal 변환에서 예외가 터져 저장 경로가 통째로 죽는다 —
        # 사용자 입장에선 '내 입력이 거절됐다'가 아니라 '앱이 고장났다'로 보인다.
        # 계산에 넣기 '전에' 유한한 수인지 본다(변환 후 검사는 도달하지 못한다).
        used = _finite_decimal(((usage_stats or {}).get(gkey) or {}).get("used"))
        if used is None:
            return dict(base_cfg), t("s_err_calib_used", field=t("s_g_" + gkey))
        if used <= 0:
            return dict(base_cfg), t("s_err_calib_zero", field=t("s_g_" + gkey))
        tokens = int((used * 100 / pct).to_integral_value(
            rounding="ROUND_HALF_UP"))                 # 보정이 직접 입력을 덮는다
        # 사용량이 1토큰도 안 되는데 100%라고 하면 한도가 0으로 떨어진다.
        # 0 한도는 게이지를 0으로 나누게 만드는 값이라 저장 자체를 거부한다.
        if tokens <= 0:
            return dict(base_cfg), t("s_err_calib_zero", field=t("s_g_" + gkey))
        limits[ckey] = tokens

    candidate.update(limits)
    return candidate, None


def prepare_settings_numbers(hour_raw, budget_raw):
    """주간 리셋 시각·API 예산 검증 → (값 dict, 오류 메시지).

    예전에는 숫자가 아니면 조용히 기본값(20 / 0)으로 떨어뜨리고 시각은 0~23 으로
    잘라 냈다. 사용자는 저장했다고 믿는데 값은 다른 것이 들어가 있었다.
    이제 이상하면 저장 전체를 거부한다(값 dict 는 비어서 돌아온다).
    """
    h = _to_decimal(hour_raw)
    if h is None or h != h.to_integral_value() or h < 0 or h > 23:
        return {}, t("s_err_hour")
    b = _to_decimal(budget_raw)
    if b is None or b < 0:
        return {}, t("s_err_budget")
    return {"weekly_reset_hour": int(h), "api_budget": float(b)}, None


# ─────────── 설정 저장 트랜잭션 (AppKit 없이 검증 가능) ───────────
# 폼에서 읽은 '문자열/기본형'만으로 계획을 세우고, 그 계획이 통째로 성공했을
# 때만 반영한다. 창(위젯)에 붙어 있으면 전체 원자성·상태 갱신·창 수명주기를
# 시험할 수가 없어서, 검증과 반영을 이렇게 떼어 놓는다.
# 폼 키: pet, lang, mode, model_keyword, weekly_reset_day, weekly_reset_hour,
#        api_budget, spike_mult, greet, admin_key,
#        <gauge>_limit_m (M 토큰 직접 입력), <gauge>_pct (보정 %)
_SETTINGS_SNAPSHOT_KEYS = ("mode", "model_keyword", "weekly_reset_day",
                           "weekly_reset_hour", "spike_mult")


def plan_settings_save(base_cfg, form, usage_stats=None, stats_for=None):
    """폼 → (plan, error). 전부 통과해야 plan 이 나온다(부분 적용은 존재 불가).

    plan = {"updates": {설정 창이 소유한 키만}, "pet": 선택된 펫 id 또는 None}
    error 가 있으면 plan 은 None 이고, 호출자는 아무것도 건드리지 않은 채
    창을 열어 둔다. 예외는 던지지 않는다 — 거절은 반환값이다.
    usage_stats 를 직접 주면 그걸 쓰고, stats_for 를 주면 검증된 draft 로
    호출해 사용량을 구한다(보정 %는 새 키워드/리셋 기준으로 역산해야 하므로).
    """
    form = form or {}
    numbers, err = prepare_settings_numbers(form.get("weekly_reset_hour", ""),
                                            form.get("api_budget", ""))
    if err:
        return None, err
    # 설정 창이 소유한 키만 가져온다 — 통째로 쓰면 드래그(x/y)·크기(scale)가
    # 그 사이 디스크에 쓴 값을 시작 스냅샷으로 되돌린다.
    draft = {k: base_cfg[k] for k in SETTINGS_OWNED_KEYS if k in base_cfg}
    for key in ("lang", "mode", "model_keyword", "weekly_reset_day",
                "spike_mult", "greet", "admin_key"):
        if key in form:
            draft[key] = form[key]
    if form.get("pet"):
        draft["pet"] = form["pet"]
    draft.update(numbers)
    direct = {g: form.get(g + "_limit_m", "") for g, _ in GAUGE_LIMIT_KEYS}
    calib = {g: form.get(g + "_pct", "") for g, _ in GAUGE_LIMIT_KEYS}
    # 사용량은 보정(%)을 역산할 때만 필요하다. 한 칸도 안 채웠으면 아예 구하지
    # 않는다 — 굳이 구하면, 우리가 쓰지도 않을 값을 만들려다 로그 한 줄이 이상해서
    # 저장 전체가 실패할 수 있다. 그 로그는 Claude Code 가 쓰는 남의 파일이다.
    # (try/except 로 감싸는 것으로는 부족하다: 필요도 없는 의존이 그대로 남는다)
    filled = [g for g, _ in GAUGE_LIMIT_KEYS if str(calib.get(g, "")).strip()]
    # 사용량을 구하기 '전에' 사용자가 친 %부터 본다. 0% 나 범위 밖 값은 사용량이
    # 무엇이든 역산이 불가능하므로, 남의 로그를 읽어 볼 이유가 없다 — 읽었다가
    # 실패하면 사용자는 자기 입력이 아니라 앱이 고장난 것으로 읽는다.
    for gkey in filled:
        checked = _calibration_percent_error(calib.get(gkey, ""))
        if isinstance(checked, str):
            return None, t(checked, field=t("s_g_" + gkey))
    if filled and stats_for is not None:
        try:
            usage_stats = stats_for({k: draft.get(k)
                                     for k in _SETTINGS_SNAPSHOT_KEYS})
        except Exception:
            # 사용량을 못 구했으면(로그가 깨졌다든지) 예외를 밖으로 던지지 않는다.
            # 이 함수는 거절을 '반환값'으로 주는 함수이고, 예외는 호출자에게
            # '앱이 고장났다'로 보인다 — 사용자가 친 %는 멀쩡했는데도.
            return None, t("s_err_calib_used", field=t("s_g_" + filled[0]))
    candidate, err = prepare_settings_config(draft, direct, calib,
                                             usage_stats or {})
    if err:
        return None, err
    return {"updates": candidate, "pet": form.get("pet") or None}, None


def apply_settings_plan(plan, cfg, apply_fn=None, set_pet_fn=None, prev_pet=None):
    """계획을 실제로 반영한다 → (ok, merged).

    디스크 기록이 성공한 뒤에야 cfg 를 건드린다. 실패하면 cfg 는 한 글자도
    바뀌지 않고 (False, None) — 창을 닫지 않고 오류만 보여 주면 된다.
    """
    if not plan:
        return False, None
    ok, merged = merge_config_updates(plan["updates"])
    if not ok:
        return False, None
    cfg.clear()
    cfg.update(merged)              # 메모리 설정을 디스크와 일치시킨다
    if apply_fn is not None:
        apply_fn(cfg)
    pet = plan.get("pet")
    if pet and pet != prev_pet and set_pet_fn is not None:
        set_pet_fn(pet)             # 라이브 교체는 바뀐 경우에만
    return True, merged

LOG_DIRS = [
    os.path.expanduser("~/.claude/projects"),
    os.path.expanduser("~/.config/claude/projects"),
]

# ─────────────────────── 로그 파싱 ───────────────────────

def _iter_log_files():
    for d in LOG_DIRS:
        if os.path.isdir(d):
            yield from glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True)


def _usage_number(src, key):
    """usage 안의 수치 하나 → 유한한 수. 없으면 0, 못 쓰는 값이면 None.

    이 파일들은 Claude Code 가 쓰고 우리는 읽기만 한다. 그래서 문자열이나
    nan/inf 가 한 칸 들어오는 일을 '있을 수 없는 일'로 두면 안 된다 — 예전에는
    그런 줄 하나가 곱셈에서 TypeError 를 내며 집계 전체를 죽였다.
    bool 을 걸러 내는 것은 파이썬에서 True 가 int 이기 때문이다(True*5 = 5).
    """
    v = src.get(key)
    if v is None:
        return 0                       # 없는 칸은 0 — 정상이다
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None                    # 문자열 등 — 이 줄은 못 쓴다
    if v != v or v in (float("inf"), float("-inf")):
        return None                    # nan / ±inf
    if v < 0:
        return None                    # 음수 토큰 수는 있을 수 없다
    if isinstance(v, int):
        # 파이썬 int 는 자릿수 제한이 없어서 float 로 못 옮기는 값이 올 수 있다.
        # 그대로 두면 곱셈에서 OverflowError 가 나며 집계가 죽는다.
        try:
            float(v)
        except OverflowError:
            return None
    return v


def _weigh_usage(usage):
    """usage → (total, noncache) 비용 가중 토큰. 못 쓰는 줄이면 None.

    실제 한도는 비용 기준으로 차감되는 것으로 보이므로 API 단가 비율로 가중
    (입력1/출력5/캐시읽기0.1) → 사용 패턴(캐시 비중)이 바뀌어도 % 보정이 유지됨.
    캐시 쓰기는 TTL별 단가가 달라(5m 1.25 / 1h 2.0) usage["cache_creation"]
    세부 값으로 나눠 가중하고, 없으면 구버전 로그로 보고 평면 필드×1.25.

    수치 칸 중 하나라도 수가 아니거나 유한하지 않으면 (0 이나 추측값으로
    때우지 않고) None 을 돌려준다 — 그 줄만 버리고 나머지는 그대로 센다.
    """
    w_in = _usage_number(usage, "input_tokens")
    out = _usage_number(usage, "output_tokens")
    cw_flat = _usage_number(usage, "cache_creation_input_tokens")
    cr = _usage_number(usage, "cache_read_input_tokens")
    if None in (w_in, out, cw_flat, cr):
        return None
    w_out = out * 5.0
    cc = usage.get("cache_creation")
    if cc is not None and not isinstance(cc, dict):
        return None                    # 있는데 dict 가 아니면 못 쓰는 줄
    if isinstance(cc, dict):
        cw_5m = _usage_number(cc, "ephemeral_5m_input_tokens")
        cw_1h = _usage_number(cc, "ephemeral_1h_input_tokens")
        if None in (cw_5m, cw_1h):
            return None
        rest = max(0, cw_flat - cw_5m - cw_1h)   # 분류 안 된 나머지는 5m 단가로
        w_cw = cw_5m * 1.25 + cw_1h * 2.0 + rest * 1.25
    else:
        w_cw = cw_flat * 1.25                    # 구버전 로그 호환
    w_cr = cr * 0.1
    noncache = w_in + w_out + w_cw
    total = noncache + w_cr
    # 각 칸은 유한해도 곱하고 더하다 inf 가 될 수 있다(예: 1e308 × 5).
    # 그런 줄을 합계에 넣으면 그 뒤 게이지가 전부 inf 가 된다.
    if total != total or total in (float("inf"), float("-inf")):
        return None
    return total, noncache


def parse_usage_entries(since: datetime):
    """since 이후의 (timestamp, total_tokens, model, noncache). 메시지 중복 제거.

    Claude Code는 콘텐츠 블록마다 한 줄씩 기록해서 같은
    (message.id, requestId)가 여러 번 나오는데, 앞줄은 스트리밍 도중의
    부분 스냅샷이다. 그래서 먼저 온 줄이 아니라 가중 합이 가장 큰 줄
    (동률이면 더 늦은 timestamp)만 남긴다.
    """
    entries, seen = [], {}
    for path in _iter_log_files():
        try:
            if datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc) < since:
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # 한 줄의 '모양'부터 확인한다. 이 파일은 Claude Code 가 쓰고
                    # 우리는 읽기만 하므로, 예상 못 한 타입이 들어오면 그 줄만
                    # 버리고 나머지는 계속 센다 — 예외로 집계를 통째로 죽이지 않는다.
                    if not isinstance(obj, dict):
                        continue
                    msg = obj.get("message")
                    if msg is None:
                        msg = {}
                    if not isinstance(msg, dict):
                        continue
                    usage = msg.get("usage")
                    if usage is None:
                        usage = obj.get("usage")
                    if not isinstance(usage, dict) or not usage:
                        continue
                    ts_raw = obj.get("timestamp")
                    if not isinstance(ts_raw, str) or not ts_raw:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    # 시간대 없는 값은 창(aware)과 비교하면 TypeError 가 난다
                    if ts.tzinfo is None:
                        continue
                    # 창 밖 레코드가 중복 키를 먼저 선점하면 창 안의 같은
                    # 메시지가 통째로 사라지므로 시간 검사를 먼저 한다
                    if ts < since:
                        continue
                    # 못 쓰는 줄은 여기서 버린다 — seen[key] 를 건드리기 전에.
                    # 나중에 버리면 그 줄이 (message.id, requestId) 를 선점해
                    # 같은 메시지의 멀쩡한 줄이 '중복'으로 사라진다.
                    weighed = _weigh_usage(usage)
                    if weighed is None:
                        continue
                    total, noncache = weighed
                    if total <= 0:
                        continue
                    model = msg.get("model")
                    if model is None:
                        model = ""
                    if not isinstance(model, str):
                        continue          # 모델 이름이 문자열이 아니면 못 쓰는 줄
                    entry = (ts, total, model.lower(), noncache)
                    mid, rid = msg.get("id"), obj.get("requestId")
                    # 키로 쓸 값은 문자열이어야 한다. 리스트/딕셔너리가 오면
                    # seen 에 넣는 순간 TypeError 로 집계가 통째로 죽는다.
                    if not all(x is None or isinstance(x, str) for x in (mid, rid)):
                        continue
                    key = (mid, rid)
                    if key == (None, None):   # 키가 없으면 중복 판단 불가 → 그대로 집계
                        entries.append(entry)
                        continue
                    idx = seen.get(key)
                    if idx is None:
                        seen[key] = len(entries)
                        entries.append(entry)
                    else:
                        prev = entries[idx]
                        if (total, ts) > (prev[1], prev[0]):
                            entries[idx] = entry
        except OSError:
            continue
    entries.sort(key=lambda e: e[0])
    return entries


def _weekly_window_start(runtime=None):
    """설정된 주간 리셋 요일/시각 기준 이번 주 시작(UTC). 미설정이면 None(롤링)."""
    rt = RUNTIME if runtime is None else runtime
    wday = rt.get("weekly_reset_day")
    if wday is None:
        return None
    try:
        hh = int(rt.get("weekly_reset_hour", 20))
        nl = datetime.now().astimezone()
        back = (nl.weekday() - int(wday)) % 7
        ls = (nl - timedelta(days=back)).replace(hour=hh, minute=0,
                                                 second=0, microsecond=0)
        if ls > nl:
            ls -= timedelta(days=7)
        return ls.astimezone(timezone.utc)
    except Exception:
        return None


# 상위 티어 모델 패밀리, 최신 우선 (모델별 주간 한도가 걸리는 대상)
PREMIUM_FAMILIES = ["fable", "mythos", "opus"]

def _detect_model_keyword(wk_entries, all_entries):
    """모델 게이지 대상 자동 감지 — 앱과 같은 기준:
    이번 주간 창에서 사용된 가장 최신 상위 티어 (없으면 전체 로그에서)."""
    for pool in (wk_entries, all_entries):
        for fam in PREMIUM_FAMILIES:          # 최신 우선
            if any(fam in e[2] and e[1] > 0 for e in pool):
                return fam
    return "opus"


def compute_usage(runtime=None):
    """사용량 스냅샷. runtime 을 주면 RUNTIME 대신 그 설정으로 계산한다.

    (설정 창에서 '저장하면 이 한도로 % 가 얼마가 되는지'를 RUNTIME 을 건드리지
     않고 미리 계산해야 하므로 스냅샷 인자를 받는다.)
    """
    rt = RUNTIME if runtime is None else runtime
    now = datetime.now(timezone.utc)
    entries = parse_usage_entries(now - timedelta(days=7))

    # 스냅샷을 받았을 때만 넘긴다 — 기본 경로는 예전과 똑같이 인자 없이 호출.
    week_start = (_weekly_window_start() if runtime is None
                  else _weekly_window_start(rt))
    wk_entries = [e for e in entries
                  if week_start is None or e[0] >= week_start]
    kw = str(rt.get("model_keyword", "auto")).lower().strip()
    if kw in ("auto", ""):
        kw = _detect_model_keyword(wk_entries, entries)
    weekly = sum(e[1] for e in wk_entries)
    weekly_opus = sum(e[1] for e in wk_entries if kw in e[2])

    # 세션 블록: 앱과 같은 방식으로 5시간 단위 타일링.
    # 블록이 끝난 뒤 첫 활동 시각(정시 스냅)에 새 블록이 시작됨.
    # (연속 사용 시에도 5시간마다 정확히 리셋되어 앱 %와 어긋나지 않음)
    session_tokens, session_reset, last_activity = 0, None, None
    if entries:
        last_activity = entries[-1][0]
        block_start = block_end = None
        for e in entries:
            if block_end is None or e[0] >= block_end:
                block_start = e[0].replace(minute=0, second=0, microsecond=0)
                block_end = block_start + timedelta(hours=SESSION_HOURS)
        if now < block_end:  # 현재 블록이 아직 유효
            session_reset = block_end
            session_tokens = sum(e[1] for e in entries
                                 if block_start <= e[0] < block_end)

    # 주간 리셋: 설정된 요일/시각이 있으면 그 기준.
    # 롤링 7일 모드는 창이 매 순간 밀리므로 단일 리셋 시각이 없다 → None
    weekly_reset = (week_start + timedelta(days=7)
                    if week_start is not None else None)

    # 소비 급증 감지 — "평소보다 갑자기 많이" 쓸 때만.
    # 캐시 읽기 토큰은 제외(항상 커서 오탐 유발)하고,
    # 최근 5분 소비가 (a) 한도 대비 임계치 이상 AND (b) 직전 활동 속도의 2.5배 이상
    five_ago = now - timedelta(minutes=5)
    thirty_ago = now - timedelta(minutes=30)
    burn_all = sum(e[3] for e in entries if e[0] >= five_ago)
    burn_opus = sum(e[3] for e in entries if e[0] >= five_ago and kw in e[2])

    def active_base(model_kw=None):
        """직전 25분을 5분 버킷 5개로 나눠, 활동이 있던 버킷만 평균.
        유휴 구간(0)을 평균에 넣으면 base가 실제 활동 속도보다 낮게 잡혀
        2.5배 게이트가 무력화되므로(정상 사용도 급증 오탐) 활동 버킷만 센다."""
        buckets = [0.0] * 5
        for e in entries:
            if not (thirty_ago <= e[0] < five_ago):
                continue
            if model_kw is not None and model_kw not in e[2]:
                continue
            idx = int((e[0] - thirty_ago).total_seconds() // 300)
            if 0 <= idx < 5:
                buckets[idx] += e[3]
        active = [b for b in buckets if b > 0]
        return sum(active) / len(active) if active else 0.0

    base_all = active_base()
    base_opus = active_base(kw)
    mult = float(rt.get("spike_mult", 1.0)) or 1.0

    def is_spike(burn, base, limit, base_pct):
        floor = limit * base_pct * mult / 100
        return burn >= floor and burn >= 2.5 * max(base, floor / 5)

    spikes = {
        "session": is_spike(burn_all, base_all,
                            rt["session_limit"], SPIKE_BASE["session"]),
        "weekly":  is_spike(burn_all, base_all,
                            rt["weekly_limit"], SPIKE_BASE["weekly"]),
        "opus":    is_spike(burn_opus, base_opus,
                            rt["opus_limit"], SPIKE_BASE["opus"]),
    }

    def gauge(used, limit, reset):
        pct = min(100.0, used / limit * 100) if limit else 0.0
        return {"used": used, "limit": limit, "left": max(0, limit - used),
                "pct": pct, "reset": reset}

    return {
        "session": gauge(session_tokens, rt["session_limit"], session_reset),
        "weekly":  gauge(weekly, rt["weekly_limit"], weekly_reset),
        "opus":    gauge(weekly_opus, rt["opus_limit"], weekly_reset),
        "burn_5m": burn_all,
        "burn_5m_opus": burn_opus,
        "spikes": spikes,
        "model_kw": kw,
        "last_activity": last_activity,
        # 창 안에서 실제로 집계된 항목 수. 0 은 '쓰지 않았다'가 아니라 '읽을 게 없다'는
        # 뜻이고, 게이지 0% 와는 다른 사실이다 — 필이 0% 를 지어내지 않으려면 이 둘을
        # 구분할 근거가 필요하다(roam_summary 참조).
        "entries": len(entries),
        "now": now,
    }

# ─────────────────────── Admin API (선택) ───────────────────────

def fetch_api_cost(start_dt):
    """start_dt(UTC)부터 지금까지 비용(USD). 키 없거나 실패하면 None."""
    key = RUNTIME.get("admin_key", "")
    if not key:
        return None
    url = ("https://api.anthropic.com/v1/organizations/cost_report"
           f"?starting_at={start_dt:%Y-%m-%dT%H:%M:%SZ}&bucket_width=1d")
    req = urllib.request.Request(url, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        total = 0.0
        for b in data.get("data", []):
            for item in b.get("results", []):
                amt = item.get("amount")
                total += float(amt.get("value", 0)) if isinstance(amt, dict) else float(amt or 0)
        return total
    except Exception:
        return None


def fetch_api_cost_today():
    now = datetime.now(timezone.utc)
    return fetch_api_cost(now.replace(hour=0, minute=0, second=0, microsecond=0))


def fetch_api_cost_month():
    now = datetime.now(timezone.utc)
    return fetch_api_cost(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))

# ─────────────── OAuth 사용량 API (정확 모드) ───────────────
# Claude Code의 /usage 명령이 쓰는 것과 같은 엔드포인트.
# 성공하면 서버가 계산한 정확한 %를 그대로 표시 → 보정 불필요.
# 실패(토큰 없음/429 등)하면 로컬 로그 추정으로 폴백.

OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_CACHE_SEC = 180   # 과호출 시 429 → 3분 캐시 필수
# 실패한 조회는 이만큼만 캐시한다(성공과 429는 OAUTH_CACHE_SEC 그대로). 일시적 네트워크
# 장애나 5xx 뒤에 3분 내내 추정 모드에 머물지 않기 위함. 429만은 예외 — 위 캐시가
# 존재하는 이유가 바로 과호출이라, 429 뒤에 더 빨리 다시 두드리면 안 된다.
OAUTH_FAIL_RETRY_SEC = 60
OAUTH_TOKEN_RETRY = 120   # 토큰 못 읽었을 때 재시도 간격(초)
_oauth_cache = {"t": 0.0, "gauges": None}
# 토큰은 성공 시 메모리에 캐시 — 재조회 시 macOS 허용 프롬프트가 반복되기 때문.
# 만료(401)로 실패할 때만 force=True로 다시 읽는다.
# 못 읽으면 "포기"하지 않고 next_retry 이후 다시 시도한다 → 새로 설치/업데이트해
# 아직 Claude Code 인증 전이거나 키체인 허용 전이어도, 나중에 인증/허용하면
# 재시작 없이 정확 모드로 자동 복구된다. declined=사용자가 명시적으로 거부.
#
# src: 토큰이 어디서 왔는지("file"|"cli"|"native"|None). 자동 재검증이 프롬프트 없는
#      경로만 타도록 고르는 근거다.
# file_sig: src=="file"일 때 credentials 파일의 (st_mtime_ns, st_size, st_ino).
#      다음 읽기에서 서명이 달라졌거나 파일이 사라졌으면 캐시를 버리고 새로 읽는다 —
#      Claude Code가 토큰을 갱신해도 재시작 없이 따라가는 신호다. Windows는 파일이
#      유일한 소스라 이것만이 회전 신호다.
# suspect: 인증 외 실패(5xx/429/네트워크/파싱) 뒤 True. 다음 읽기에서 프롬프트 없는
#      소스(파일, 그리고 cli에서 온 토큰이면 security CLI)로만 재검증하고 내린다.
#      네이티브 키체인은 자동 재검증에서 절대 타지 않는다(v0.16의 재프롬프트 회귀).
_oauth_token_cache = {"tok": None, "next_retry": 0.0, "declined": False,
                      "src": None, "file_sig": None, "suspect": False}
_oauth_token_lock = threading.Lock()

# 키체인 API 상태 코드 (Security.framework)
_SEC_ITEM_NOT_FOUND = -25300   # 항목 없음 (아직 Claude Code 로그인 전 등)
_SEC_AUTH_FAILED = -25293      # 사용자가 프롬프트에서 '거부' 클릭
_SEC_USER_CANCELED = -128      # 사용자가 프롬프트를 닫음(취소)
# 아래 둘은 "프롬프트를 띄우지 못하고 조용히 실패"하는 코드다. 사용자가 거부한 게
# 아니므로 반드시 CLI 폴백으로 구제해야 한다. 이걸 거부와 같이 취급해 폴백을
# 막아버린 게 "새 머신에서 권한 요청이 아예 안 뜨고 정확 모드가 안 되던" 원인.
_SEC_INTERACTION_NOT_ALLOWED = -25308
_SEC_INTERACTION_REQUIRED = -25315
# 사용자가 명시적으로 거부/취소한 경우에만 재프롬프트를 자제한다.
_SEC_DENIED = (_SEC_AUTH_FAILED, _SEC_USER_CANCELED)


def _dbg(*a):
    """CLAUDE_PET_DEBUG=1 이면 ~/claudepet_debug.log 에 한 줄 기록.
    새 머신에서 정확 모드가 왜 실패하는지 추측 대신 데이터로 잡기 위한 계측."""
    if not os.environ.get("CLAUDE_PET_DEBUG"):
        return
    try:
        with open(os.path.expanduser("~/claudepet_debug.log"), "a", encoding="utf-8") as f:
            f.write("%.3f " % time.time() + " ".join(str(x) for x in a) + "\n")
    except Exception:
        pass


def _credentials_path():
    """~/.claude/.credentials.json — 일부 설치는 키체인 대신 여기에 토큰을 둔다."""
    return os.path.expanduser("~/.claude/.credentials.json")


def _stat_sig(st):
    return (st.st_mtime_ns, st.st_size, st.st_ino)


def _credentials_sig():
    """credentials 파일의 서명 (st_mtime_ns, st_size, st_ino). 파일이 없으면 None.

    세 필드가 모두 필요하다: 제자리 덮어쓰기는 mtime_ns만, 원자적 rename은 ino만
    바꾸고, 같은 길이의 토큰은 size를 바꾸지 않는다. 초 단위 mtime은 같은 초 안의
    갱신을 놓친다.
    """
    try:
        return _stat_sig(os.stat(_credentials_path()))
    except OSError:
        return None


def _read_credentials_file():
    """(token, sig) — 파일이 없거나 못 읽으면 (None, None). 무프롬프트.

    stat을 open보다 먼저 한다: 그 사이에 파일이 바뀌면 옛 서명 + 새 내용이 되고,
    다음 읽기에서 서명 불일치로 한 번 더 읽을 뿐이다. 반대 순서(읽고 나서 stat)는
    새 서명 + 옛 토큰이 되어 다음 갱신까지 옛 토큰을 계속 낸다.
    """
    path = _credentials_path()
    try:
        sig = _stat_sig(os.stat(path))
        with open(path, encoding="utf-8") as f:
            tok = (json.load(f).get("claudeAiOauth") or {}).get("accessToken")
    except Exception:
        return None, None
    return (tok or None), sig


def _token_from_file():
    """~/.claude/.credentials.json (일부 설치는 키체인 대신 파일에 저장) — 무프롬프트."""
    return _read_credentials_file()[0]


def _token_from_cli():
    """security CLI로 키체인 읽기 — 이미 허용된 머신이면 조용히 성공.
    네이티브가 프롬프트조차 못 띄우고 실패하는 환경의 안전망이다.
    앱이 멈추지 않도록 timeout을 둔다(프롬프트가 뜨면 CLI는 그대로 대기하므로)."""
    try:
        r = subprocess.run(
            ["security", "find-generic-password",
             "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            return (json.loads(r.stdout.strip())
                    .get("claudeAiOauth") or {}).get("accessToken")
    except Exception:
        pass
    return None


def _keychain_token_native():
    """네이티브 Security API로 'Claude Code-credentials' 키체인 항목을 읽는다.

    접근 주체가 앱(ClaudePet) 자신이라, 아직 허용 안 한 새 머신에서는
    "ClaudePet이 키체인에 접근하려 합니다" 프롬프트가 확실히 뜬다(사용자가
    "항상 허용"하면 다음부턴 자동). security CLI를 서브프로세스로 띄우는
    방식은 하드닝 런타임 하 새 머신에서 프롬프트가 안 뜨는 경우가 있어 이
    네이티브 경로를 우선한다. service만으로 매칭(account=NULL).
    반환 (status, token): 0=성공, -25300=항목없음, 그 외=거부/오류.
    """
    try:
        import ctypes
        Sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        Sec.SecKeychainFindGenericPassword.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p,
            ctypes.c_uint32, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p]
        Sec.SecKeychainFindGenericPassword.restype = ctypes.c_int32
        Sec.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        # 이 프로세스에서 키체인 UI를 띄우는 걸 명시적으로 허용한다. 기본값은 보통
        # 허용이지만, 꺼져 있으면 프롬프트 없이 -25308로 조용히 실패한다.
        try:
            Sec.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_bool]
            Sec.SecKeychainSetUserInteractionAllowed.restype = ctypes.c_int32
            Sec.SecKeychainSetUserInteractionAllowed(True)
        except Exception:
            pass
        svc = b"Claude Code-credentials"
        length = ctypes.c_uint32()
        data = ctypes.c_void_p()
        st = Sec.SecKeychainFindGenericPassword(
            None, len(svc), svc, 0, None,
            ctypes.byref(length), ctypes.byref(data), None)
        if st != 0:
            return st, None
        try:
            raw = ctypes.string_at(data.value, length.value)
        finally:
            Sec.SecKeychainItemFreeContent(None, data)
        obj = json.loads(raw.decode("utf-8", "ignore"))
        return 0, (obj.get("claudeAiOauth") or {}).get("accessToken")
    except Exception:
        return -1, None


NATIVE_WAIT_SEC = 25    # 프롬프트 응답을 이만큼만 기다린다(응답 자체엔 타임아웃 없음)
_native_state = {"thread": None, "result": None}


def _keychain_token_native_bounded(wait=None):
    """네이티브 키체인 읽기를 데몬 스레드에 맡기고 wait 초만 기다린다.

    왜 필요한가: 네이티브 호출은 프롬프트가 떠 있는 동안 무한 대기한다. 그런데
    이 앱은 accessory(메뉴바 없는 백그라운드) 앱이라 SecurityAgent 패널이 다른
    창 뒤에 가려 사용자가 못 볼 수 있다. 그러면 호출 스레드가 _oauth_token_lock을
    영원히 쥔 채 멈추고, 이후 모든 폴링이 non-blocking acquire 실패로 즉시
    빠져나가 next_retry조차 세우지 못한다 = 재시도 로직이 통째로 죽는다.

    그래서 기다리는 쪽에만 한도를 둔다. 사용자가 10분 뒤에 '허용'을 눌러도 그
    스레드는 살아서 결과를 _native_state에 남기고, 다음 폴링이 그걸 주워간다.
    반환 (status, token). status가 None이면 '아직 응답 대기 중'이라는 뜻이다.
    """
    # 기본인자로 박으면 정의 시점에 고정돼 조정이 불가능하다 — 여기서 읽는다.
    wait = NATIVE_WAIT_SEC if wait is None else wait
    ns = _native_state
    th = ns["thread"]
    if th is None or not th.is_alive():
        if ns["result"] is not None:        # 지난번 늦게 도착한 결과 수거
            r, ns["result"] = ns["result"], None
            return r
        def work():
            try:
                ns["result"] = _keychain_token_native()
            except Exception:
                ns["result"] = (-1, None)
        th = threading.Thread(target=work, daemon=True)
        ns["thread"] = th
        th.start()
    th.join(wait)
    if th.is_alive():
        return None, None                  # 프롬프트 응답 대기 중 — 이번엔 넘어간다
    r, ns["result"] = ns["result"], None
    return r if r else (-1, None)


def _read_oauth_token(force=False):
    """Claude Code OAuth 토큰: 파일 → security CLI → 네이티브 키체인 API 순.

    순서가 핵심이다. 무프롬프트로 성공하는 경로를 먼저 태우고, 프롬프트가
    필요한 경로를 최후로 미룬다:

      1. 파일 ~/.claude/.credentials.json — 있으면 키체인을 아예 안 건드린다.
      2. security CLI — 이 항목은 Claude Code가 `security` 로 만들기 때문에
         항목 ACL의 신뢰 앱에 /usr/bin/security 가 있고 파티션이 "apple-tool:"
         뿐이다. Apple 서명 툴이라 어느 머신에서든 무프롬프트로 통과한다.
      3. 네이티브 API — 여기서만 "ClaudePet이 키체인에 접근하려 합니다"
         프롬프트가 뜰 수 있다. Developer ID 서명인 이 앱은 파티션이 안 맞아
         키체인 암호를 요구받고, UI를 못 띄우면 -25308로 조용히 죽기 때문에
         1순위로 쓰면 안 된다(예전 버전이 이래서 정확 모드가 안 켜졌다).

    네이티브 호출 자체엔 timeout이 없어 사용자가 언제 누르든 받지만
    (_keychain_token_native_bounded 참고), '기다리는 쪽'은 NATIVE_WAIT_SEC
    초로 제한해 락이 영영 물리지 않게 한다.

    못 읽으면 '영구 포기'하지 않고 OAUTH_TOKEN_RETRY초 뒤 다시 시도한다 —
    아직 Claude Code 인증 전이거나 키체인 허용 전이어도 나중에 인증/허용하면
    재시작 없이 정확 모드로 자동 복구된다. 사용자가 명시적으로 '거부'하면
    (declined) 그 실행 동안 키체인은 다시 묻지 않는다.
    401 만료 시엔 force=True — 이땐 만료된 파일 토큰을 다시 집어 무한루프에
    빠지지 않도록 파일을 건너뛰고 키체인부터 읽는다.

    캐시된 토큰을 그냥 돌려주지 않는 경우가 둘 있다(둘 다 프롬프트 없는 경로만 탄다):
      - src=="file"인데 파일 서명이 바뀌었거나 파일이 사라졌다 → 캐시를 버리고
        새로 읽는다. Claude Code가 토큰을 갱신하면 재시작 없이 따라간다.
      - suspect(인증 외 조회 실패 뒤) → _revalidate_oauth_token()으로 파일과
        (cli 출처면) security CLI만 다시 묻는다. 네이티브 키체인은 타지 않는다.
    force(401)로 걸어서도 대체 토큰을 못 찾으면 거부된 토큰을 캐시에서 지운다 —
    쿨다운 동안 죽은 토큰을 계속 돌려주지 않기 위해서다.
    """
    c = _oauth_token_cache
    if not force and c["tok"] and c["src"] == "file":
        sig = _credentials_sig()
        if sig != c["file_sig"]:
            # 파일이 갱신됐거나(서명 변경) 사라졌다(None). 캐시를 버리고 새로 읽는다.
            _dbg("read_oauth: file sig changed; vanished?", sig is None)
            _forget_oauth_token(c)
    if c["tok"] and not force:
        if c["suspect"]:
            return _revalidate_oauth_token(c)
        return c["tok"]
    if not force and time.time() < c["next_retry"]:
        return None                        # 재시도 쿨다운 중
    # 1) 파일 — 무프롬프트. 락 '밖'에서 먼저 본다. 네이티브가 프롬프트 때문에
    #    락을 쥐고 있어도 이 경로는 막히지 않아야 하기 때문.
    #    단 force(=401 만료)면 건너뛴다. 만료된 파일 토큰을 계속 집어오면
    #    401 → force → 같은 파일 → 401 루프에 빠진다.
    if not force:
        tok, sig = _read_credentials_file()
        _dbg("read_oauth: file tok?", bool(tok))
        if tok:
            _remember_oauth_token(c, tok, "file", sig)
            return tok
    if not _oauth_token_lock.acquire(blocking=False):
        # 다른 스레드가 읽는 중(프롬프트 대기). force(=401)면 지금 캐시된 토큰은
        # 서버가 방금 거부한 그 토큰이므로 돌려주지 않는다.
        return None if force else c["tok"]
    try:
        if c["tok"] and not force:
            return c["tok"]
        tok, src, sig = None, None, None
        if sys.platform == "darwin":
            # 2) security CLI — 이게 1순위여야 한다. 이 키체인 항목은 Claude Code가
            #    `security` 로 만들기 때문에 항목 ACL의 신뢰 앱 목록에 /usr/bin/security
            #    가 들어 있고, 파티션도 "apple-tool:" 하나뿐이다. 즉 Apple 서명 툴인
            #    security 는 어느 머신에서든 프롬프트 없이 통과한다(실측 15ms, rc=0).
            #    반대로 Developer ID로 서명된 ClaudePet 은 파티션(teamid:...)이 안 맞아
            #    키체인 '암호' 프롬프트를 요구하고, UI를 못 띄우면 -25308로 조용히 죽는다.
            #    예전엔 네이티브를 앞에 뒀던 탓에, 프롬프트 없이 성공하던 유일한 경로를
            #    뒤로 밀어내고 프롬프트가 필요한 경로를 먼저 타고 있었다.
            tok, src = _token_from_cli(), "cli"
            _dbg("read_oauth: cli tok?", bool(tok))
            # 3) 네이티브 — 최후 수단. CLI가 막힌 환경에서만 쓴다. 여기서만
            #    "ClaudePet이 키체인에 접근하려 합니다" 프롬프트가 뜰 수 있다.
            if not tok and not c["declined"]:
                st, tok = _keychain_token_native_bounded()
                src = "native"
                _dbg("read_oauth: native st", st, "tok?", bool(tok))
                if st is None:
                    # 프롬프트가 떠 있고 아직 응답이 없다. 실패도 거부도 아니다.
                    c["next_retry"] = time.time() + OAUTH_TOKEN_RETRY
                    if force:
                        _forget_oauth_token(c)   # 거부된 토큰은 쿨다운 동안 내지 않는다
                    return None
                if not tok and st in _SEC_DENIED:
                    c["declined"] = True   # 명시적 거부/취소만 존중
        # 4) force 로 위가 다 실패했으면 마지막으로 파일이라도 본다.
        if not tok and force:
            tok, sig = _read_credentials_file()
            src = "file"
        if tok:
            _remember_oauth_token(c, tok, src, sig)
        else:
            c["next_retry"] = time.time() + OAUTH_TOKEN_RETRY   # 나중에 다시 시도
            if force:
                _forget_oauth_token(c)       # 거부된 토큰은 쿨다운 동안 내지 않는다
        _dbg("read_oauth: final tok?", bool(tok), "src", src if tok else None,
             "declined?", c["declined"])
        return tok
    finally:
        _oauth_token_lock.release()


def _forget_oauth_token(c):
    """캐시된 토큰을 잊는다(출처·서명·suspect 포함). declined와 next_retry는 그대로."""
    c["tok"] = None
    c["src"] = None
    c["file_sig"] = None
    c["suspect"] = False


def _remember_oauth_token(c, tok, src, sig=None):
    c["tok"] = tok
    c["src"] = src
    c["file_sig"] = sig if src == "file" else None
    c["suspect"] = False
    c["next_retry"] = 0.0


def _revalidate_oauth_token(c):
    """인증 외 조회 실패 뒤의 자동 재검증 — 프롬프트 없는 소스만.

    파일을 먼저 본다(키체인 설치에 파일이 새로 생겼을 수 있다). 토큰이 security
    CLI에서 왔으면 CLI도 다시 묻는다(Claude Code가 항목을 다시 썼을 수 있다).
    네이티브 키체인은 여기서 절대 타지 않는다 — 그 경로만 프롬프트를 띄울 수 있고,
    '한 번 허용'한 사용자를 네트워크 장애 때마다 다시 묻는 것이 v0.16의 회귀였다.
    바뀐 토큰이 있으면 교체하고, 없으면 캐시된 토큰을 그대로 쓴다. suspect는
    어느 쪽이든 내린다(같은 실패가 반복되면 다음 실패가 다시 올린다).
    """
    if not _oauth_token_lock.acquire(blocking=False):
        return c["tok"]                    # 다른 스레드가 읽는 중 — 있는 걸로 간다
    try:
        if not c["tok"] or not c["suspect"]:
            return c["tok"]
        old_src = c["src"]
        tok, sig = _read_credentials_file()
        src = "file"
        if not tok and old_src == "cli" and sys.platform == "darwin":
            tok, sig, src = _token_from_cli(), None, "cli"
        c["suspect"] = False
        if tok:
            _dbg("read_oauth: revalidate src", src, "changed?", tok != c["tok"])
            _remember_oauth_token(c, tok, src, sig)
        else:
            _dbg("read_oauth: revalidate found nothing; keep src", old_src)
        return c["tok"]
    finally:
        _oauth_token_lock.release()


def _oauth_label(key):
    k = key.lower()
    if "five_hour" in k or "session" in k:
        return (t("session"), 0)
    if "seven_day" in k or "weekly" in k:
        for fam in PREMIUM_FAMILIES + ["sonnet", "haiku"]:
            if fam in k:
                return (fam.capitalize(), 2)
        return (t("weekly"), 1)
    if "extra" in k or "credit" in k:
        return (t("credit"), 9)   # 추가 사용량(크레딧) — 주요 3개 있으면 잘림
    return (key, 5)


def _parse_reset_ts(raw):
    """resets_at(ISO8601 또는 epoch) → aware datetime. 실패 시 None."""
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except (TypeError, ValueError):
            return None


def _rows_from_limits(data):
    """신규 limits 배열 → [(order, label, pct, reset_dt)].

    서버가 세션/주간/모델별 한도를 limits 배열(kind + percent + scope.model)로
    보낸다. 모델별 주간 한도(kind=weekly_scoped)는 여기에만 있고 레거시
    seven_day_opus 등은 null로 오므로, 이 배열을 정확 모드의 1순위로 읽는다.
    """
    limits = data.get("limits")
    if not isinstance(limits, list):
        return []
    out = []
    for lim in limits:
        if not isinstance(lim, dict):
            continue
        kind = str(lim.get("kind") or "").lower()
        try:
            pct = float(lim.get("percent") or 0)
        except (TypeError, ValueError):
            continue
        rdt = _parse_reset_ts(lim.get("resets_at"))
        if "session" in kind or "five_hour" in kind:
            label, order = t("session"), 0
        elif "extra" in kind or "credit" in kind:
            label, order = t("credit"), 9
        elif "scoped" in kind or "model" in kind:
            # 모델별 주간 한도(최상위 모델). 라벨은 서버가 준 값을 그대로 쓴다
            # (display_name 우선, 없으면 id). 서버 표기를 가공하지 않는다.
            scope_model = (lim.get("scope") or {}).get("model") or {}
            model = scope_model.get("display_name") or scope_model.get("id") or ""
            if not model:
                continue
            label, order = str(model), 2
        elif "weekly" in kind or "seven" in kind:
            label, order = t("weekly"), 1
        else:
            continue
        out.append((order, label, min(100.0, max(0.0, pct)), rdt))
    # 모델별 주간 한도(order 2)는 서버가 resets_at을 null로 주기도 한다.
    # 주간 사이클과 함께 리셋되므로 주간(order 1)의 리셋 시각을 물려준다.
    weekly_rdt = next((r[3] for r in out if r[0] == 1 and r[3]), None)
    if weekly_rdt is not None:
        out = [(o, l, p, (weekly_rdt if o == 2 and rd is None else rd))
               for (o, l, p, rd) in out]
    return out


def _rows_from_utilization(data):
    """레거시 폴백: utilization 필드를 관용적으로 훑는다 (구버전 응답용)."""
    found = []

    def walk(obj, hint):
        if isinstance(obj, list):
            for item in obj:
                walk(item, hint)
            return
        if not isinstance(obj, dict):
            return
        if "utilization" in obj:
            util = obj.get("utilization")
            # 크레딧/추가사용량이 비활성이면 utilization=null, is_enabled=false로 온다.
            # null(=미설정)과 0.0(=설정됐으나 0% 사용)은 다르다 — five_hour/seven_day는
            # 미사용 시 0.0으로 오므로 0% 행을 그대로 보여야 하지만, null은 행 자체를
            # 만들지 않는다. (안 그러면 크레딧 없는 사용자에게 "Credit 0%"가 뜸)
            if util is None or obj.get("is_enabled") is False:
                return
            try:
                pct = float(util)
            except (TypeError, ValueError):
                return
            # utilization은 이미 퍼센트(0~100) 단위. 스케일 변환하지 않는다.
            rdt = _parse_reset_ts(obj.get("resets_at") or obj.get("reset_at")
                                  or obj.get("resets"))
            model_hint = str(obj.get("model") or obj.get("name") or
                             obj.get("label") or "")
            label, order = _oauth_label(f"{hint}_{model_hint}".lower())
            found.append((order, label, min(100.0, max(0.0, pct)), rdt))
        else:
            for k, v in obj.items():
                walk(v, f"{hint}_{k}" if hint else k)

    walk(data, "")
    return found


def _parse_oauth_usage(data):
    """OAuth 응답 → [(label, pct, reset_dt, reset_text)] 최대 PILL_ROWS.

    1순위: 신규 limits 배열(세션/주간/모델별). + extra_usage(크레딧, 활성 시).
    limits가 없는 구버전 응답이면 레거시 utilization 필드로 폴백.
    """
    found = _rows_from_limits(data)

    # 크레딧: extra_usage가 활성이고 값이 있을 때만 (null/비활성이면 행 없음)
    extra = data.get("extra_usage")
    if (isinstance(extra, dict) and extra.get("is_enabled")
            and extra.get("utilization") is not None):
        try:
            cpct = float(extra["utilization"])
            found.append((9, t("credit"), min(100.0, max(0.0, cpct)),
                          _parse_reset_ts(extra.get("resets_at"))))
        except (TypeError, ValueError):
            pass

    if not found:                       # 구버전 응답 폴백
        found = _rows_from_utilization(data)

    found.sort(key=lambda x: x[0])
    # 같은 라벨 중복 제거. (label, pct, reset_dt, reset_text)
    seen, rows = set(), []
    for _, label, pct, rdt in found:
        if label in seen:
            continue
        seen.add(label)
        rows.append((label, pct, rdt, None))
    return rows[:PILL_ROWS] or None


def _label_order(label):
    if label == t("session"):
        return 0
    if label == t("weekly"):
        return 1
    if label == t("credit"):
        return 9
    if label.lower() in PREMIUM_FAMILIES + ["sonnet", "haiku"]:
        return 2
    return 5


# 정확 모드 상태 — 토큰 만료(401 지속) 시 폴백 필에 안내를 띄우기 위함.
# last_error: 마지막 조회 실패의 종류("http:<code>"|"net"|"parse"), 성공하면 None.
#   필에는 그리지 않는다(roam_summary_text의 memo 키도 그대로). fetch_exact_usage가
#   실패 캐시 길이를 정할 때와 디버그 로그에만 쓴다.
OAUTH_STATUS = {"auth_error": False, "last_error": None}


def _fetch_oauth_usage():
    """OAuth 사용량을 한 번 조회한다. 실패하면 None.

    결과에 따른 토큰 캐시 처리:
      200      → suspect·auth_error·last_error 모두 내린다.
      401/403  → 키체인에서 1회 강제 재조회 후 재시도. 그래도 없거나 또 거부되면
                 auth_error. 재조회가 아무것도 못 찾았으면 죽은 토큰은 캐시에서 지운다
                 (_read_oauth_token(force=True)가 락 안에서 지우고, 락이 바빠 재조회를
                 못 한 경우는 여기서 같은 토큰일 때만 지운다).
      그 외     → 토큰은 그대로 두되 suspect를 올린다. 다음 읽기가 프롬프트 없는
                 소스로 재검증한다. last_error에 종류를 남긴다.
    _dbg 줄에는 상태 코드·클래스 이름·불리언만 쓴다. 토큰이나 응답 본문은 절대 안 쓴다.
    """
    tok = _read_oauth_token()
    if not tok:
        return None
    c = _oauth_token_cache
    for attempt in (0, 1):
        req = urllib.request.Request(OAUTH_USAGE_URL, headers={
            "Authorization": f"Bearer {tok}",
            "User-Agent": "claude-code/2.1.0",   # 없으면 429 버킷에 걸림
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            code = e.code
            OAUTH_STATUS["last_error"] = "http:%s" % code
            _dbg("oauth fetch: http", code, "attempt", attempt)
            if code in (401, 403):
                # 토큰 만료 추정 → 키체인에서 1회 재조회 후 재시도 (그래도 실패면 포기)
                if attempt == 0:
                    fresh = _read_oauth_token(force=True)
                    if fresh:
                        tok = fresh
                        continue
                    # 대체 토큰이 없다 — 거부된 토큰을 계속 내지 않는다(락이 바빠
                    # 재조회를 못 했을 때만 여기 남는다; 걸었다면 이미 지워졌다).
                    if c["tok"] == tok:
                        _forget_oauth_token(c)
                # 재조회한 토큰도 거부 = 키체인 토큰 자체가 만료
                OAUTH_STATUS["auth_error"] = True
                return None
            c["suspect"] = True
            return None
        except Exception as e:
            # URLError·socket.timeout·SSL·연결 끊김 등 전송 단계 실패 전부
            OAUTH_STATUS["last_error"] = "net"
            c["suspect"] = True
            _dbg("oauth fetch: net", type(e).__name__, "attempt", attempt)
            return None
        try:
            rows = _parse_oauth_usage(json.loads(raw.decode()))
        except Exception as e:
            OAUTH_STATUS["last_error"] = "parse"
            c["suspect"] = True
            _dbg("oauth fetch: parse", type(e).__name__)
            return None
        OAUTH_STATUS["auth_error"] = False
        OAUTH_STATUS["last_error"] = None
        c["suspect"] = False
        _dbg("oauth fetch: ok rows", len(rows) if rows else 0)
        return rows
    return None


def _find_claude_cli():
    # ~/.local/bin/claude 가 네이티브 설치 기본 위치다. Finder로 띄운 앱은 PATH가
    # 최소(/usr/bin:/bin 등)라 shutil.which 가 이걸 못 찾으므로 명시적으로 넣는다.
    for p in (shutil.which("claude"),
              os.path.expanduser("~/.local/bin/claude"),
              os.path.expanduser("~/.claude/local/claude"),
              "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        if p and os.path.exists(p):
            return p
    return None


CLAUDE_INSTALL_URL = "https://claude.ai/install.sh"   # Anthropic 공식(홈 디렉터리 설치)


def compute_onboard_state(oauth, stats_have_logs):
    """구독 모드에서 온보딩이 필요한지 판정. 반환: None | 'install' | 'login'.

    - API 모드: Claude Code 불필요 → None.
    - 이미 쓸 데이터가 있으면(정확 모드 토큰 or 로그) → None.
    - claude 실행 파일이 없으면 'install', 있으면(로그인만 필요) 'login'.
    """
    forced = os.environ.get("CLAUDE_PET_FORCE_ONBOARD")   # 시각 테스트용: install|login
    if forced in ("install", "login"):
        return forced
    if RUNTIME.get("mode") == "api":
        return None
    if oauth or stats_have_logs:
        return None
    return "login" if _find_claude_cli() else "install"


def _run_in_terminal(cmd):
    """새 Terminal 창에서 cmd(bash)를 실행한다.

    .command 임시 파일을 열어 띄운다. osascript 로 Terminal 을 제어하는 방식은
    '터미널을 제어하려 합니다' 자동화 권한을 또 물어보므로, 그 프롬프트가 없는
    파일 열기 방식을 쓴다. Terminal 은 로그인 셸로 열려 ~/.local/bin 이 PATH에
    들어오므로 방금 설치한 claude 도 바로 잡힌다. 스크립트는 끝나면 자신을 지운다.
    """
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".command", prefix="claudepet-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n" + cmd + '\nrm -f -- "$0"\n')
    os.chmod(path, 0o755)
    subprocess.Popen(["/usr/bin/open", "-a", "Terminal", path])


def start_claude_install():
    """Claude Code 설치 → 이어서 로그인까지 Terminal 에서 진행."""
    q = lambda x: json.dumps(x, ensure_ascii=False)  # bash 안전 인용(한글 유지)
    cmd = (
        f"echo {q(t('term_installing'))}\n"
        f"curl -fsSL {CLAUDE_INSTALL_URL} | bash\n"
        "echo\n"
        f"echo {q(t('term_login'))}\n"
        '"$HOME/.local/bin/claude" auth login\n'
        "echo\n"
        f"echo {q(t('term_done'))}\n"
    )
    _run_in_terminal(cmd)


def start_claude_login():
    """설치돼 있으나 로그인만 필요한 경우."""
    binp = _find_claude_cli() or os.path.expanduser("~/.local/bin/claude")
    q = lambda x: json.dumps(x, ensure_ascii=False)
    cmd = (
        f"echo {q(t('term_login'))}\n"
        f"{q(binp)} auth login\n"
        "echo\n"
        f"echo {q(t('term_done'))}\n"
    )
    _run_in_terminal(cmd)


_CLI_LINE = re.compile(
    r"Current (session|week \(([^)]*)\)):\s*(\d+(?:\.\d+)?)% used"
    r"(?:\s*·\s*resets (.*))?")

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def _parse_cli_reset(txt):
    """'Jul 18 at 8pm' / 'Jul 13 at 2:10pm' → 로컬 타임존 datetime."""
    m = re.match(r"([A-Z][a-z]{2})\.?\s+(\d{1,2})\s+at\s+"
                 r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", txt.strip(), re.I)
    if not m:
        return None
    mon = _MONTHS.get(m.group(1).capitalize())
    if not mon:
        return None
    day = int(m.group(2))
    hour = int(m.group(3)) % 12
    if m.group(5).lower() == "pm":
        hour += 12
    minute = int(m.group(4) or 0)
    now_local = datetime.now().astimezone()
    try:
        dt = now_local.replace(month=mon, day=day, hour=hour,
                               minute=minute, second=0, microsecond=0)
    except ValueError:
        return None
    if dt < now_local - timedelta(days=1):   # 연말 넘어가는 경우
        dt = dt.replace(year=dt.year + 1)
    return dt


def _fetch_cli_usage():
    """`claude -p /usage` 출력 파싱 — OAuth 실패 시 폴백.

    주의: claude CLI는 Claude Code 전체(Node 앱)를 자식으로 띄워 홈/프로젝트/
    여러 폴더를 스캔한다. 그 접근이 부모(ClaudePet)에 귀속돼 macOS가 다운로드/
    사진/네트워크볼륨 등 보호폴더 접근 프롬프트를 띄운다. OAuth 정확 모드가
    이미 세션/주간/모델/크레딧을 주므로 기본은 OFF. 켜려면 CLAUDE_PET_USE_CLI=1.
    """
    if os.environ.get("CLAUDE_PET_USE_CLI", "0") != "1":
        return None
    cli = _find_claude_cli()
    if not cli:
        return None
    try:
        r = subprocess.run([cli, "-p", "/usage"], capture_output=True,
                           text=True, timeout=90)
    except Exception:
        return None
    rows = []
    for line in (r.stdout or "").splitlines():
        m = _CLI_LINE.search(line)
        if not m:
            continue
        if m.group(1) == "session":
            label = t("session")
        else:
            scope = (m.group(2) or "").strip().lower()
            label = t("weekly") if scope.startswith("all") else (m.group(2) or t("model")).strip()
        txt = (m.group(4) or "").strip() or None
        rdt = None
        if txt:
            txt = re.sub(r"\s*\([^)]*\)\s*$", "", txt)  # (Asia/Seoul) 제거
            rdt = _parse_cli_reset(txt)   # 카운트다운 표시용
        rows.append((label, float(m.group(3)), rdt, txt))
    return rows[:PILL_ROWS] or None


def fetch_exact_usage():
    """정확 사용량 [(label, pct, reset_dt, reset_text)] 최대 4줄.
    OAuth 우선, 모델별(Fable 등) 줄이 없으면 CLI(claude -p /usage)에서 보충.
    180초 캐시 (과호출 시 429). 실패한 조회는 OAUTH_FAIL_RETRY_SEC(60초)만 캐시하되
    429는 예외로 180초를 그대로 둔다 — 캐시가 존재하는 이유가 과호출이다."""
    now = time.time()
    if now - _oauth_cache["t"] < OAUTH_CACHE_SEC:
        return _oauth_cache["gauges"]
    _oauth_cache["t"] = now          # 조회 중인 동안 다른 호출자는 이전 값을 받는다
    rows = _fetch_oauth_usage()
    if rows is None:
        err = OAUTH_STATUS.get("last_error")
        if err and err != "http:429":
            # 실패는 짧게 캐시: t를 과거로 물려 OAUTH_FAIL_RETRY_SEC 뒤에 만료되게 한다.
            _oauth_cache["t"] = now - (OAUTH_CACHE_SEC - OAUTH_FAIL_RETRY_SEC)
        rows = _fetch_cli_usage()
    elif not any(_label_order(r[0]) == 2 for r in rows):
        # OAuth 응답에 모델별 항목이 없으면 CLI에서 Fable 줄 보충
        cli = _fetch_cli_usage() or []
        have = {r[0] for r in rows}
        for r in cli:
            if r[0] not in have:
                rows.append(r)
    if rows:
        rows = sorted(rows, key=lambda r: _label_order(r[0]))[:PILL_ROWS]
    _oauth_cache["gauges"] = rows
    return rows


# ─────────────── 자동 업데이트 (GitHub 릴리즈) ───────────────

def _ver_tuple(v):
    out = []
    for part in str(v).split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)


# 아키텍처별 '정확한 파일명' 허용 목록. 거르는 폴백이 아니라 이름을 못 박는다.
# Intel(x86_64)에서 도는 건 universal 뿐이라 arm 전용 zip 으로 내려가면 안 된다
# — 받아서 깔고 나서야 실행이 안 된다. 목록에 없는 이름(diagnostics.zip 등)은
# 앱이 아니므로 어떤 경우에도 업데이트가 되지 않는다.
UPDATE_ASSET_NAMES = {
    "arm64": ("claudepet.zip", "claudepet-universal.zip"),
    "x86_64": ("claudepet-universal.zip",),
}


def select_update_asset(assets, machine):
    """릴리즈 자산 목록에서 이 기기에 설치 가능한 것 하나 → (url, name, arch).

    고를 게 없거나 고르면 안 되는 상황이면 None. 무엇을 왜 골랐는지 호출부에서
    그대로 볼 수 있도록 이름과 아키텍처를 함께 돌려준다.
    """
    allowed = UPDATE_ASSET_NAMES.get(str(machine))
    if not allowed:
        # 모르는 아키텍처에 arm/universal 을 찍어 주는 건 추측이다.
        print(f"[update] rejected: unknown architecture ({machine!r})")
        return None
    by_name = {}
    for a in assets or ():
        name = (a.get("name") or "").strip().lower()
        if name not in allowed:
            continue
        if name in by_name:
            # 두 자산이 같은 허용 이름으로 정규화되면 어느 쪽이 진짜인지 알 수
            # 없다. 임의로 하나를 집는 건 선택이 아니라 추측이다.
            print(f"[update] rejected: two assets normalize to {name!r}")
            return None
        by_name[name] = a.get("browser_download_url") or ""
    for name in allowed:
        url = by_name.get(name)
        if not url:
            continue
        parts = urllib.parse.urlparse(url)
        if parts.scheme != "https" or not parts.netloc:
            # 평문 HTTP 는 중간에서 바꿔치기할 수 있다. 서명 검사가 뒤에 있어도
            # 여기서 막는다 — 받지 않는 게 가장 싸다.
            print(f"[update] rejected: {name} is not served over https")
            return None
        return (url, name, str(machine))
    return None


def _no_update_choice(status):
    """받을 게 없다고 끝나는 경로. 지난 번 고른 자산 기록은 지우고 나간다.

    남겨 두면 '이번에 고른 것'과 '예전에 골랐던 것'을 구분할 수 없다 — 진단을
    보는 쪽에서 이미 지나간 선택을 지금 것으로 읽는다.
    """
    _upd_cache["choice"] = None
    return (status, None, None)


def check_github_update():
    """최신 릴리즈 확인 → (status, tag, url).

    status 는 셋 중 하나:
      'update'  새 버전 있음 — tag, url 둘 다 값이 있다.
      'current' 최신임      — tag, url 은 None.
      'failed'  확인 실패    — tag, url 은 None. (네트워크/파싱 오류, 받을 zip 없음)
    호출부는 'failed' 일 때 재확인 쿨다운을 찍지 않는다. 예전에는 실패도 성공과
    구분되지 않아, 한 번 실패하면 6시간 내내 다시 확인하지 않았다.
    """
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "claude-pet"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        tag = (data.get("tag_name") or "").lstrip("vV")
        if not tag:
            return _no_update_choice("failed")
        if _ver_tuple(tag) <= _ver_tuple(APP_VERSION):
            return _no_update_choice("current")
        import platform
        chosen = select_update_asset(data.get("assets", []), platform.machine())
        # 새 버전인데 이 기기에서 쓸 zip 이 없으면 설치가 불가능하다
        # → 실패로 보고(쿨다운을 태우지 않고) 다음에 다시 확인한다.
        if not chosen:
            return _no_update_choice("failed")
        url, name, arch = chosen
        # 고른 근거를 남긴다. 반환값 모양은 호출부가 의존하므로 건드리지 않고,
        # '무엇을 왜 골랐는지'는 여기로 뺀다.
        _upd_cache["choice"] = {"asset": name, "arch": arch, "url": url,
                                "tag": tag}
        print(f"[update] asset={name} arch={arch}")
        return ("update", tag, url)
    except Exception:
        return _no_update_choice("failed")


# ─────────── 사용량 새로고침 세대 (겹친 요청 정리) ───────────
# 저장 직후처럼 새로고침이 겹치면, 먼저 시작해 늦게 끝난 요청이 새 결과를
# 덮어써 "방금 보정한 값이 옛 값으로 되돌아" 보였다. 요청마다 세대 번호를 받고,
# 커밋 시점에 여전히 최신 세대일 때만 state 에 반영한다.

# 세대 발급과 커밋은 같은 잠금 아래에서 통째로 일어나야 한다. 확인과 반영이
# 나뉘어 있으면, 옛 워커가 "내 세대가 최신"까지 통과한 뒤 반영하기 직전에 새
# 워커가 끼어들어 먼저 반영해 버리고, 그 위를 옛 결과가 덮어쓴다.
_refresh_lock = threading.RLock()


def begin_refresh_generation(state):
    with _refresh_lock:
        gen = int(state.get("refresh_generation") or 0) + 1
        state["refresh_generation"] = gen
        return gen


def commit_refresh_result(state, generation, values):
    """generation 이 아직 최신이면 values 를 state 에 반영하고 True."""
    with _refresh_lock:
        if generation != state.get("refresh_generation"):
            return False
        state.update(values)
        return True


# 두 경로를 '한 번에' 맞바꾼다(renamex_np + RENAME_SWAP). mv 두 번으로 바꾸면
# 그 사이에 설치 경로가 잠깐 비고, 하필 거기서 죽으면 사용자에게는 앱이 아예
# 없다. 교환에는 그 틈이 없다 — 어느 순간에 보아도 설치 경로에는 옛 앱이거나
# 새 앱이 있다. 셸에는 이 기능이 없어 번들에 동봉된 python 으로 부른다.
_EXCHANGE_PY = (
    "import ctypes,ctypes.util,sys;"
    "l=ctypes.CDLL(ctypes.util.find_library('c'),use_errno=True);"
    "f=l.renamex_np;"
    "f.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint];"
    "sys.exit(0 if f(sys.argv[1].encode(),sys.argv[2].encode(),2)==0 else 1)"
)


# 우리가 만든 '그 객체'만 지운다 — 이름이 아니라 (dev,ino) 로, 그리고 경로
# 문자열이 아니라 열어 둔 fd 로.
#
# 셸의 `stat` + `rm -rf` 는 이 일을 할 수 없다. 그 두 줄은 검사와 사용이 갈라진
# 전형적인 check-then-act 이고, 창은 이론이 아니다: stat 이 신원을 확인한 뒤
# rm 이 그 '이름'을 다시 해석하기 전에 그 자리가 남의 트리로 바뀌면, rm -rf 는
# 확인받은 적 없는 트리를 통째로 지운다. 게다가 rm 은 내려가는 도중의 각 하위
# 디렉터리에 대해서도 같은 검사를 하지 않는다 — 트리 중간의 한 폴더만 바꿔치기
# 해도 그 아래가 전부 사라진다. 신원 대조를 '지우기 직전'으로 옮기는 것만으로는
# 부족하고, 대조한 그 객체를 손에 든 채로 지워야 한다.
#
# 그래서 이 프로그램은:
#   - 부모를 O_NOFOLLOW|O_DIRECTORY 로 열고, 자식도 O_NOFOLLOW 로 연 뒤
#     fstat 으로 신원을 확인한다(경로를 다시 해석하지 않는다),
#   - 내려갈 때마다 lstat 으로 본 신원과 실제로 연 fd 의 신원이 같은지 보고,
#     다르면 **그 아래로 내려가지 않는다** — 바꿔치기된 트리를 재귀 삭제하는
#     일은 일어나지 않는다,
#   - 모든 삭제는 dir_fd 기준(unlinkat/rmdir at)이라 이름이 뒤늦게 바뀌어도
#     우리가 연 그 디렉터리 안에서만 일어난다,
#   - 어디서든 어긋나면 **남긴다.** 남은 폴더는 다음에 지울 수 있지만, 남의
#     트리를 지운 것은 되돌릴 수 없다. 실패는 언제나 '지우지 않음'으로 접힌다.
#
# **독립 실행이다 — 설치된 옛 소스를 import 하지 않는다.** 이 코드가 도는
# 시점에는 옛 번들이 이미 옮겨졌거나 교체되었을 수 있어서, `import claude_pet`
# 은 그 자리에 지금 있는 무엇이든(혹은 아무것도 아닌 것을) 불러오게 된다.
# 필요한 것은 표준 모듈 세 개뿐이고, 전부 시작하자마자 불러 둔다.
#
# 인자: argv[1] 지울 경로, argv[2] "dev,ino" 형식의 기대 신원.
# 종료 코드 0 은 '그 객체를 지웠다', 그 밖의 모든 값은 '지우지 않았다'.
_DISCARD_PY = """
import os, stat, sys

O_DIR = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY


def ident(st):
    return "%d,%d" % (st.st_dev, st.st_ino)


def purge(dfd):
    # dfd 는 '신원을 이미 확인한' 디렉터리다. 그 안의 이름만 다룬다.
    for name in os.listdir(dfd):
        st = os.lstat(name, dir_fd=dfd)
        if stat.S_ISDIR(st.st_mode):
            fd = os.open(name, O_DIR, dir_fd=dfd)
            try:
                # 열어서 얻은 것이 방금 lstat 으로 본 그것인가. 아니면 남의
                # 트리다 — 내려가지 않고 통째로 실패한다.
                if ident(os.fstat(fd)) != ident(st):
                    raise OSError("identity changed under traversal")
                purge(fd)
            finally:
                os.close(fd)
            os.rmdir(name, dir_fd=dfd)
        else:
            # 심볼릭 링크도 여기로 온다. unlink 는 링크를 따라가지 않는다.
            os.unlink(name, dir_fd=dfd)


def discard(path, want):
    if not want:
        return 1
    name = os.path.basename(path)
    if not name or name in (".", ".."):
        return 1
    parent = os.path.dirname(path) or "/"
    pfd = os.open(parent, O_DIR)
    try:
        st = os.lstat(name, dir_fd=pfd)
        if not stat.S_ISDIR(st.st_mode):
            # O_NONBLOCK 을 같이 준다 — 그 자리에 FIFO 가 있으면 O_RDONLY 만으로
            # 는 여는 데서 영영 멈춘다.
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=pfd)
            try:
                if ident(os.fstat(fd)) != want:
                    return 1
                os.unlink(name, dir_fd=pfd)
            finally:
                os.close(fd)
            return 0
        fd = os.open(name, O_DIR, dir_fd=pfd)
        try:
            if ident(os.fstat(fd)) != want:
                return 1
            purge(fd)
        finally:
            os.close(fd)
        # 마지막 이름을 지우기 직전에 한 번 더 연다. 비우는 동안에도 이름은
        # 우리 것이 아니었으므로, 방금 비운 그것이 아직 거기 있을 때만 rmdir
        # 한다. rmdir 은 '비어 있는 디렉터리'만 지우므로, 이 대조까지 통과한
        # 뒤에 바뀌더라도 사라질 수 있는 것은 빈 디렉터리 하나뿐이다.
        fd = os.open(name, O_DIR, dir_fd=pfd)
        try:
            if ident(os.fstat(fd)) != want:
                return 1
            os.rmdir(name, dir_fd=pfd)
        finally:
            os.close(fd)
        return 0
    finally:
        os.close(pfd)


try:
    rc = discard(sys.argv[1], sys.argv[2])
except Exception:
    # 무엇이 어긋났든 결론은 하나다: 지우지 않는다.
    rc = 1
sys.exit(rc)
"""


# 같은 APP 을 건드리는 업데이터는 한 번에 하나만. 이름을 다르게 짓는 것으로는
# 부족하다 — 그건 '경로 충돌'만 막고, 두 거래가 검사·교체·확인·정리 사이를
# 서로 끼어드는 것은 그대로 둔다. 잠금은 fd 를 셸이 들고 있는 동안 유지되므로
# 프로세스가 죽으면(SIGKILL 포함) 커널이 놓아 준다. O_EXCL 잠금 파일이었다면
# 죽은 주인의 흔적이 영영 남아, 그걸 걷어내려면 pid/mtime 추측이 필요해지고
# 그 추측이 다시 경합을 만든다 — 설정 저장 쪽에서 이미 같은 이유로 flock 을
# 쓴다.
#
# 잠금은 '셸이 아니라 파이썬에서' 잡는다. 이게 이 파일에서 가장 여러 번 틀렸던
# 자리라 이유를 남긴다.
#
# 셸에서 `exec 9>"$LOCK"` 로 잡으면 두 가지를 할 수 없다.
#
#  1. O_NOFOLLOW. /bin/sh 의 리다이렉션에는 그런 게 없다. 잠금 경로는 앱 이름에서
#     그대로 나와 완전히 예측 가능하므로, 그 자리에 심볼릭 링크를 미리 놓아 두면
#     `9>` 는 링크를 따라가 '대상 파일을 0바이트로 자른다'. 즉 경합을 막으려고
#     넣은 장치가, 공격자 한 명과 동시성 0 으로 남의 파일을 지우는 도구가 된다.
#     막으려던 경합은 업데이터 둘이 겹쳐야 일어난다 — 훨씬 비싼 쪽을 새로 만든
#     셈이다.
#  2. 연 뒤에 그 fd 의 정체를 확인하는 일. O_NOFOLLOW 는 '무엇을 따라갔는가'만
#     막고 '무엇을 얻었는가'는 말해 주지 않는다. 그 자리에 FIFO·장치 파일·
#     디렉터리·남의 소유 파일이 있으면 각각 다른 방식으로 잠금이 무력해진다
#     (FIFO 는 열다가 영영 멈출 수도 있다). 그래서 fstat 으로 '지금 손에 든
#     그 fd' 가 우리가 만든 평범한 파일인지 본다. 경로를 미리 검사하는 것은
#     같은 일이 아니다 — 검사한 경로와 연 객체가 같다는 보장이 없다.
#
# 파이썬 쪽은 둘 다 할 수 있고, 거래가 시작되는 자리도 원래 여기다.
# 잠긴 fd 는 pass_fds 로 교체 셸에 그대로 물려주므로, 잠금은 검사·교체·확인·
# 정리 전체를 덮고 그 셸이 죽으면(SIGKILL 포함) 커널이 놓아 준다. O_EXCL 잠금
# 파일이었다면 죽은 주인의 흔적이 영영 남아, 그걸 걷어내려면 pid/mtime 추측이
# 필요해지고 그 추측이 다시 경합을 만든다 — 설정 저장 쪽에서 이미 같은 이유로
# flock 을 쓴다.
# 잠금 뿌리도 '이름'이 아니라 '열어 둔 그 폴더'로 들고 있는다.
#
# 잎(잠금 파일)에만 신원을 걸면 뿌리에서 무너진다. 거래 A 가 잠금을 잡은 뒤
# 누가 캐시 폴더를 rename 하고 같은 이름으로 새 폴더를 만들면, 거래 B 는 그
# **새** 폴더 안의 **다른** 파일을 flock 하고 통과한다 — 두 업데이터가 서로를
# 전혀 보지 못한 채 같은 앱을 교체한다. 직렬화 장치가 있는 채로 직렬화만
# 사라지는 형태다.
#
# 그래서 확인을 통과한 뿌리 디렉터리 fd 를 프로세스가 사는 동안 들고 있고,
# 이후의 모든 잠금은 경로를 다시 해석하지 않고 그 fd 기준으로(openat) 연다.
# 이름이 바뀌어도 우리는 계속 처음 그 폴더의 같은 잎을 잡으므로 flock 이 실제로
# 부딪친다.
#
# **범위를 분명히 해 둔다: 이것은 한 프로세스 안에서만 성립한다.** 뿌리가
# 바뀐 뒤에 새로 뜬 프로세스는 새 폴더를 열고 새 잎을 잡는다. 그 갈래를 막으려면
# '이름으로 열지 않고도 같은 객체에 닿는 안정된 앵커'가 필요한데, 사용자 홈
# 아래에는 그런 자리가 없다(무엇이든 rename 할 수 있다). 프로세스 밖의 이
# 창은 남겨 둔 채, 프로세스 안의 갈래는 닫는 쪽을 골랐다.
_LOCK_ROOT = {"path": None, "fd": None}
_LOCK_ROOT_MUTEX = threading.Lock()


def _lock_root_fd(root, fresh=False):
    """확인을 통과한 잠금 뿌리의 디렉터리 fd. 못 믿으면 None.

    같은 경로에 대해 한 번 열어 확인한 fd 를 계속 쓴다. fresh=True 면 들고 있던
    것을 버리고 다시 연다 — 그 폴더가 실제로 사라졌을 때만 쓴다.
    """
    with _LOCK_ROOT_MUTEX:
        if not fresh and _LOCK_ROOT["path"] == root and _LOCK_ROOT["fd"] is not None:
            return _LOCK_ROOT["fd"]
        # 자리를 만드는 것은 '실제로 잠글 때'인 여기뿐이다. 경로를 계산하는 쪽은
        # 아무것도 만들지 않는다 — 그 구분이 없으면 잠금 경로를 들여다보기만 하는
        # 코드까지 폴더를 만들어 버린다.
        try:
            os.makedirs(root, mode=0o700, exist_ok=True)
        except OSError:
            pass                # 못 만들면 아래 open 이 실패하고 fail-closed 다
        # O_NOFOLLOW 로 한 번 열고, 연 fd 를 fstat 으로 확인한다. 경로를 미리
        # 검사하는 것은 같은 일이 아니다 — 검사한 경로와 연 객체가 같다는 보장이
        # 없다.
        try:
            dfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            print("[update] refused: the update lock directory is not a plain "
                  "directory we can own")
            return None
        try:
            dst = os.fstat(dfd)
        except OSError:
            os.close(dfd)
            return None
        if (not stat.S_ISDIR(dst.st_mode)
                or dst.st_uid != os.geteuid()
                or dst.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            print("[update] refused: the update lock directory is not a "
                  "private directory we own")
            os.close(dfd)
            return None
        old = _LOCK_ROOT["fd"]
        _LOCK_ROOT["path"], _LOCK_ROOT["fd"] = root, dfd
        if old is not None:
            try:
                os.close(old)   # 뿌리는 한 번에 하나만 들고 있는다
            except OSError:
                pass
        return dfd


def _note_lock_reason(reason, word):
    """실패 이유를 담을 리스트가 주어졌을 때만 한 낱말을 덧붙인다."""
    if reason is not None:
        reason.append(word)


def _acquire_update_lock(app_path, reason=None):
    """업데이트 거래 잠금을 잡는다 → 잠긴 fd, 못 잡으면 None.

    None 은 '다른 업데이터가 진행 중' 또는 '잠금 경로를 믿을 수 없음' 둘 다를
    뜻한다. 둘 다 이번 업데이트를 하지 않는 것이 옳은 답이라, 인앱 갈래는
    구분하지 않는다.

    reason 에 리스트를 주면 실패한 이유를 한 낱말로 덧붙인다 — "busy"(다른
    업데이터가 들고 있다) 또는 "untrusted"(자리를 믿을 수 없다). 이 구분이
    필요한 곳은 그 둘을 서로 다른 종료 상태로 알려야 하는
    --with-update-lock 하나뿐이고, 그래서 두 번째 잠금 경로를 만드는 대신
    이 통로를 여기에 냈다. reason 이 None 이면 동작은 이전과 같다.
    """
    lock = _update_lock_path(app_path)
    root, name = os.path.dirname(lock), os.path.basename(lock)
    for fresh in (False, True):
        dfd = _lock_root_fd(root, fresh=fresh)
        if dfd is None:
            _note_lock_reason(reason, "untrusted")
            return None
        try:
            # O_NONBLOCK 은 FIFO·장치 파일에서 open 자체가 매달리는 것을 막는다.
            # 정규 파일에는 아무 영향이 없다.
            fd = os.open(name,
                         os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
                         | os.O_NONBLOCK,
                         0o600, dir_fd=dfd)
        except OSError as e:
            # O_CREAT 를 주고도 ENOENT 라면 잎이 아니라 '들고 있던 뿌리'가
            # 사라졌다는 뜻이다(지워졌다). 그때만 다시 연다 — 그 외의 실패는
            # 링크였거나(ELOOP) 열 수 없는 무언가였다는 뜻이고, 어느 쪽이든
            # 진행하지 않는다. 이 구분이 없으면 '수상해서 거절'이 '다시 열어
            # 통과'로 바뀌어 위의 보장이 사라진다.
            if e.errno == errno.ENOENT and not fresh:
                continue
            print("[update] refused: the update lock path is not a plain file "
                  "we can own")
            _note_lock_reason(reason, "untrusted")
            return None
        return _lock_verified_fd(fd, reason=reason)
    _note_lock_reason(reason, "untrusted")
    return None


def _lock_verified_fd(fd, reason=None):
    """열려 있는 fd 를 확인하고 잠근다 → 성공하면 fd, 아니면 None(+닫는다).

    reason 은 _acquire_update_lock 의 것과 같다.
    """
    ok = False
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            print("[update] refused: the update lock is not a regular file")
            _note_lock_reason(reason, "untrusted")
            return None
        if st.st_uid != os.geteuid():
            print("[update] refused: the update lock is owned by another user")
            _note_lock_reason(reason, "untrusted")
            return None
        if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            print("[update] refused: the update lock is writable by others")
            _note_lock_reason(reason, "untrusted")
            return None
        # 여기서만 잠근다. 위 확인을 통과하지 못한 fd 에 잠금을 걸면 '무엇을
        # 직렬화하고 있는지 모르는 잠금'이 된다.
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # 대개 다른 업데이터가 이미 들고 있다는 뜻이다(EWOULDBLOCK).
            _note_lock_reason(reason, "busy")
            return None
        ok = True
        return fd
    finally:
        # 잠그지 못하고 나가는 모든 경로에서 fd 를 닫는다. 열어 둔 채 돌아가면
        # 새로고침마다 fd 가 하나씩 쌓여, 업데이트를 못 하는 앱이 결국 fd 를
        # 다 써 버린다.
        if not ok:
            os.close(fd)


def _lock_root_ident():
    """지금 들고 있는 잠금 뿌리 fd 가 가리키는 '그 폴더'의 "dev,ino". 없으면 "".

    경로로 lstat 을 다시 하지 않는다. 그 이름이 지금도 우리가 잠근 그 폴더라는
    보장은 없고, 이 값은 '지워도 되는 것'을 정하는 데 쓰인다 — 이름으로 물어
    이름으로 지우면 대조하는 의미가 없다. fd 는 이름이 아니라 폴더 그 자체를
    잡고 있으므로 여기서 나온 값은 우리가 잠근 그 객체의 것이다.

    빈 문자열은 '모른다'는 뜻이고, 받는 쪽(완전 삭제 셸의 discard)은 모르는
    것을 지우지 않는다.
    """
    with _LOCK_ROOT_MUTEX:
        fd = _LOCK_ROOT["fd"]
    if fd is None:
        return ""
    ident = _ident_of_fd(fd)
    return "" if ident is None else "%d,%d" % ident


# 우리가 소유한 캐시 폴더. UNINSTALL_PATHS 에 이미 들어 있어서 완전 삭제가
# 통째로 지운다 — 잠금 파일을 여기 두면 '이 파일을 지워도 되는가'라는 질문이
# 아예 생기지 않는다.
UPDATE_LOCK_DIR = "~/Library/Caches/me.yeongyu.claudepet"


def _update_lock_path(app_path):
    """이 APP 의 업데이트 거래를 직렬화하는 잠금 파일. APP 하나당 하나.

    번들 '안'에 두지 않는 이유는 분명하다 — 교체는 번들을 통째로 맞바꾸므로
    안에 두면 거래 도중에 잠금 파일이 다른 파일로 바뀐다.

    한동안은 설치본 '옆'(예: /Applications/.claudepet-update-….lock)에 두었는데,
    그 자리는 공개된 데다 이름이 완전히 예측 가능하다. 그래서 그 이름에 이미
    무언가 있을 때 '우리 잠금인지 남의 파일인지' 구분할 방법이 없었고, 완전
    삭제가 그걸 지워도 되는지도 대답할 수 없었다. 두 질문 모두 '우리가 소유한
    자리'에 두면 사라진다: 여기 있는 파일은 우리가 만든 것이고, 지우는 것도
    우리 것을 지우는 것이다. 남의 예측 가능한 이름을 두고 소유권을 다투는 대신
    다투지 않아도 되는 자리로 옮기는 쪽이 맞다.

    경로를 만드는 곳이 두 군데면 한쪽만 바뀌어 지워지지 않는 잔여물이 생기므로
    여기 한 곳에서만 만든다.

    **이 함수는 순수하다 — 아무것도 만들지 않는다.** 한때 여기서 캐시 폴더를
    makedirs 했는데, 그 한 줄 때문에 '잠금 경로가 어디인지 계산해 보는' 모든
    코드가 사용자의 진짜 홈에 폴더를 만들었다. 경로를 묻는 것과 자리를 만드는
    것은 다른 일이다. 폴더는 실제로 잠글 때(_acquire_update_lock)만 만든다.

    기준 폴더는 UPDATE_LOCK_DIR 을 호출 시점에 읽는다 — 모듈을 불러올 때 굳혀
    두지 않으므로, 시험이 그 상수를 임시 폴더로 바꿔 끼우면 그대로 따라간다.
    """
    root = os.path.expanduser(UPDATE_LOCK_DIR)
    return os.path.join(root, "update-%s.lock" % os.path.basename(app_path))


def _path_ident_str(path):
    """지금 그 자리에 있는 객체의 "dev,ino". 없으면 빈 문자열.

    셸에 신원을 넘길 때 쓰는 표기이고, `/usr/bin/stat -f %d,%i` 가 찍는 것과
    같은 모양이다. 빈 문자열은 '모른다'는 뜻이고, 스크립트는 모르는 것을
    지우지도 교체하지도 않는다.
    """
    try:
        st = os.lstat(str(path))
    except OSError:
        return ""
    return "%d,%d" % (st.st_dev, st.st_ino)


def _run_with_update_lock(argv):
    """--with-update-lock <APP_PATH> -- <COMMAND> [ARGS...] → 종료 상태.

    <APP_PATH> 의 업데이트 거래 잠금을 잡고, 그 잠금을 든 채로 <COMMAND> 를
    돌리고, 자식이 끝나면 놓는다. 셸(build_app.sh)이 인앱 업데이트와 '같은
    객체'로 직렬화하는 유일한 통로다.

    **셸은 이 잠금을 직접 들 수 없고, 그것이 이 래퍼가 있는 이유다.** 경로만
    알려 주면(`exec 9> "$(… --update-lock-path …)"`) 셸은 O_NOFOLLOW 없이 이름을
    다시 해석해 열고, 연 fd 를 fstat 으로 확인하지도 않는다 —
    _acquire_update_lock 이 하지 않기로 한 바로 그 열기다. 게다가 macOS 에는
    flock(1) 이 없어서 셸에는 그 객체를 잠글 수단 자체가 없다. 그래서 잠금은
    파이썬이 들고, 셸은 그 안에서 자식으로 돈다.

    잠금은 여기서 잡은 fd 하나뿐이고, **그 fd 는 자식에게 물려주지 않는다**
    (subprocess 가 표준 셋 밖의 디스크립터를 전부 닫는다). 부모가 자식을 기다렸다
    놓으므로 잠금은 자식의 수명 전체를 덮는다 — 자식이 들 필요가 없다. 오히려
    물려주면 자식이 낳은 손자까지 같은 열림을 들게 되어, 래퍼가 끝나 놓았다고
    믿은 뒤에도 살아남은 손자가 잠금을 계속 붙들 수 있다. flock 은 마지막 close
    에 풀리기 때문이다. 놓는 것은 아래 finally 의 close 하나다.

    종료 상태:
      100  다른 업데이터가 이미 잠금을 들고 있다.
      101  잠금 자리를 믿을 수 없거나 안전하게 잡지 못했다.
      127  <COMMAND> 를 실행할 수 없었다.
      2    사용법이 틀렸다(`--` 가 없거나 명령이 비어 있다). 자식은 뜨지 않았다.
      그 외에는 자식의 종료 상태 그대로. 신호로 죽었으면 128+신호.

    **호출하는 쪽에 대한 경고: 자식이 스스로 100 이나 101 로 끝나면 잠금 실패와
    구별되지 않는다.** 종료 상태는 하나뿐이고, 이 래퍼에는 그 둘을 갈라 줄
    통로가 없다. 100/101 을 자기 뜻으로 쓰는 명령을 이 아래에 두지 말 것.
    """
    try:
        i = argv.index("--with-update-lock")
    except ValueError:
        return 2
    rest = argv[i + 1:]
    if len(rest) < 3 or rest[1] != "--":
        print("usage: claude_pet.py --with-update-lock <APP_PATH> -- "
              "<COMMAND> [ARGS...]")
        return 2
    app_path, cmd = rest[0], rest[2:]
    # 잡는 길은 인앱 업데이트가 쓰는 그 하나다. 여기서 두 번째 잠금 경로를
    # 만들면 두 길이 서로 다른 검사를 하게 되고, 직렬화는 있는 것처럼 보이면서
    # 없어진다. 이유만 리스트로 돌려받는다.
    reason = []
    lock_fd = _acquire_update_lock(app_path, reason=reason)
    if lock_fd is None:
        return 100 if "busy" in reason else 101
    try:
        try:
            rc = subprocess.call(cmd)
        except OSError:
            return 127
        # 신호로 죽은 자식은 음수로 온다. 셸이 읽는 표기로 바꾼다.
        return rc if rc >= 0 else 128 - rc
    finally:
        # 자식이 끝난 뒤에 놓는다. 이 fd 가 마지막 사본이므로 여기서 실제로
        # 풀린다 — 자식이 죽어도 부모가 들고 있는 동안은 잠긴 채다.
        try:
            os.close(lock_fd)
        except OSError:
            pass


def _update_replace_script(app_path, newapp, workdir, staged=None,
                           lock_fd=None, stage_id=None, app_id=None,
                           work_id=None):
    """앱 교체 → 재실행 확인 → 임시 폴더 정리까지의 /bin/sh 명령을 만든다.

    lock_fd 는 _acquire_update_lock() 이 이미 잡아 둔 잠금 디스크립터의 번호다.
    이 스크립트는 잠금을 '잡지 않는다' — 물려받아 들고만 있는다. 그래서 잠금은
    이 스크립트가 시작하기 전부터 유효하고, 스크립트가 죽으면 커널이 놓아 준다.
    None 이면 잠금 없이 도는 스크립트가 나온다(직접 호출하는 시험용).

    예전 스크립트는 `rm -rf <설치된 앱>` 으로 시작해 ditto 로 새 앱을 부어 넣고,
    각 단계를 `;` 로 이었다. 복사가 실패하면 앱은 이미 지워진 뒤라 사용자에게는
    아무것도 남지 않았다. 순서를 뒤집는다:

      1. 새 앱을 먼저 옆(같은 볼륨)에 완성해 두고
      2. 같은 볼륨인지 교체 '직전에' 확인한 뒤
      3. 설치본과 원자적으로 맞바꾼다 (설치 경로가 비는 순간이 없다)
      4. 새 앱이 실제로 떠서 살아 있는 걸 확인할 때까지 되돌릴 준비를 유지한다
      5. 어긋나면 되돌리고, 되돌리지 못하면 옛 앱을 '지우지 않고' 남긴다

    `set -e` 라서 어느 단계든 실패하면 즉시 멈추고, trap 이 뒷정리를 한다.
    """
    import shlex
    q = shlex.quote
    parent = os.path.dirname(app_path) or "/"
    # 거래마다 고유한 이름. pid 로 만들면 같은 pid 안에서 두 번 눌렀을 때 두
    # 설치가 같은 STAGE/BACKUP 을 쓰고, 한쪽이 다른 쪽의 backup 을 지운다.
    tag = f"{os.getpid()}-{os.urandom(4).hex()}"
    # 임시 이름은 설치 경로와 '다른 접두어'여야 한다. <app>.new 처럼 이름을
    # 덧붙이면 rm 대상 문자열이 설치 경로를 그대로 품게 된다.
    stage = str(staged) if staged else os.path.join(parent,
                                                    f".claudepet-new-{tag}")
    backup = os.path.join(parent, f".claudepet-old-{tag}")
    # APP 하나당 하나. 거래마다 바뀌면 잠금이 아니다.
    #
    # 스크립트는 이 경로를 '열지 않는다'. 그래도 LOCK= 로 적어 두는 이유는, 이
    # 거래를 어느 잠금이 지키고 있는지가 스크립트만 보고 알 수 있어야 하기
    # 때문이다 — 완전 삭제와 진단이 그 이름을 읽는다.
    lock = _update_lock_path(app_path)
    # 실행 중에 닫아야 할 fd. 잠금을 물려받았으면 그 번호, 아니면 관례상 9.
    close_fd = 9 if lock_fd is None else int(lock_fd)
    # pgrep -f 는 인자를 '정규식'으로 읽는다. 설치 경로를 그대로 끼워 넣으면
    # 경로 안의 문자가 메타문자로 해석된다 — /Applications/ClaudePet.app 의
    # '.' 만으로도 이미 아무 글자에나 맞는 패턴이 되고, 경로에 '+' '(' '['
    # 가 들어가면 패턴이 깨지거나 엉뚱한 프로세스를 잡는다. 매칭에 쓸 때는
    # 반드시 이 이스케이프한 값을 쓰고, 표시나 파일 조작에는 $APP 을 쓴다.
    app_re = re.sub(r"([.^$*+?()\[\]{}|\\])", r"\\\1", str(app_path))
    # 이 거래가 손대도 되는 객체들의 신원. 호출부가 '잠금을 잡은 뒤에' 읽어
    # 넘겨준 값이 우선이고, 넘어오지 않았으면 여기서 읽는다. 어느 쪽이든 값은
    # 스크립트가 뜨기 전에 정해지고, 스크립트는 그 뒤로 이름이 무엇을 가리키게
    # 되든 이 값과 맞을 때만 교체하고 지운다.
    #
    # **호출부가 준 값만 쓴다. 없으면 여기서 죽는다 — stat 으로 지어내지 않는다.**
    # 예전에는 `app_id or _path_ident_str(app_path)` 였다. 그 폴백이 바로 이
    # 방어를 무력하게 만드는 자리다: 신원을 '지금 그 이름에 있는 것'에서 다시
    # 유도하면, 검증한 객체가 아니라 유도한 순간의 객체에 묶인다. 그러면 대조는
    # 자기 자신과 하는 대조가 되어 언제나 통과한다. 신원은 잠금을 잡고 번들을
    # 검증한 그 거래만이 말할 수 있고, 여기서는 받아 적을 뿐이다.
    app_id = str(app_id or "")
    work_id = str(work_id or "")
    if not app_id or not work_id:
        raise ValueError(
            "update script requires the app and work identities from the "
            "caller that holds the lock")
    stage_id = str(stage_id or "") or (_path_ident_str(stage) if staged else "")
    return "\n".join((
        "set -e",
        f"APP={q(app_path)}",
        f"NEW={q(newapp)}",
        f"STAGE={q(stage)}",
        f"BACKUP={q(backup)}",
        f"WORK={q(workdir)}",
        f"LOCK={q(lock)}",
        # 정규식으로 쓸 때의 $APP. 파일을 만지는 자리에는 절대 쓰지 않는다.
        f"APPRE={q(app_re)}",
        # 지워도 되는 것을 '이름'이 아니라 '아이노드'로 안다. 이름은 우리가 만든
        # 뒤에도 남이 차지할 수 있지만, dev+ino 는 우리가 만든 그 객체를 가리킨다.
        # 비어 있으면 '모른다'는 뜻이고, 모르는 것은 지우지 않는다.
        f"STAGEID={q(stage_id)}",
        # 교체되는 '그 설치본'과, 정리해도 되는 '그 임시 폴더'의 신원. 둘 다
        # 이름만으로는 말할 수 없는 것이라 파이썬이 읽어서 넘긴다.
        f"APPID={q(app_id)}",
        f"WORKID={q(work_id)}",
        "BACKUPID=",
        f"SELFPID={os.getpid()}",
        f"EXCHANGE={q(_EXCHANGE_PY)}",
        f"DISCARD={q(_DISCARD_PY)}",
        "KEEP_BACKUP=",
        # 옛 앱이 지금 어느 경로에 있는지. 비어 있으면 아직 교체 전이다.
        # 교환 경로에서는 $STAGE, 이동 폴백에서는 $BACKUP 이 된다.
        "OLD_PATH=",
        # ── 실행 문법(launch grammar). 이 파일 밖에 계약이 있다. ──
        #
        # 이 스크립트가 앱을 띄우는 자리는 **정확히 두 곳뿐이고**, 둘 다 아래
        # $LAUNCH 라는 하나의 정의에서 나온다:
        #
        #     `$LAUNCH "$APP"`            — 성공 경로의 launch
        #     `( $LAUNCH "$RESTORED" )`   — 실패 경로의 relaunch
        #
        # **바깥의 시험 하네스는 이 두 줄을 '이 철자 그대로' 찾아 치환한다.**
        # 그래서 어느 한쪽의 철자를 바꾸면(변수 이름, 따옴표, 서브셸, 무엇이든)
        # 그 치환들이 조용히 아무것도 못 찾게 된다. 그때 일어나는 일은 시험이
        # 빨개지는 것이 **아니다** — 치환에 실패한 하네스는 고장을 넣은 줄 알고
        # 그대로 진행하면서 **실제 번들을 진짜로 띄운다.** 이 저장소는 그렇게
        # 쌓인 LaunchServices 등록을 이미 한 번 치웠다.
        #
        # 따라서 이 줄들을 건드리는 변경은 **바깥의 치환 지점까지 같은 변경 안에서
        # 함께 고치기 전에는 끝난 것이 아니다.** $LAUNCH 를 다른 이름으로 바꾸고
        # 싶다면, 이 파일에서 할 일은 절반뿐이라는 뜻이다.
        #
        # 그리고 **두 줄의 철자는 서로 달라야 한다.** 고장 주입이 '그 문자열이 든
        # **첫** 줄'을 바꾸는데 relaunch 의 정의가 launch 자리보다 위에 나오므로,
        # 두 줄이 같으면 "launch 에 고장을 넣었다"가 실제로는 relaunch 를 바꾼다.
        # 실행 시점에는 RESTORED="$APP" 이라 인자로도 두 호출을 구별할 수 없으니,
        # 남은 구별 수단은 이 철자뿐이다.
        #
        # (예전 주석은 여기까지 오지 못하고 '일부러 다르게 썼다'는 의도만 적었다.
        # 그래서 아무도 스텁할 수 없는 launch 가 이 파일에 오래 살아남았다.
        # 의도를 적는 것으로는 부족하다 — 결과를 적을 것.)
        "LAUNCH=open",
        # $1 은 실행할 python, $2·$3 은 맞바꿀 두 경로.
        #
        # $1 은 반드시 '컴파일된 바이너리'여야 한다. 셸 스크립트를 여기에 두면
        # 교환이 영영 멈춘다: /bin/sh 는 스크립트 파일을 조금씩 읽어 가며
        # 실행하는데, 그 파일이 든 디렉터리가 발밑에서 바뀌면 읽던 자리를
        # 잃는다(로그도 타임아웃도 없이 매달린다). Mach-O 는 커널이 vnode 로
        # 잡고 있어 디렉터리 이름이 바뀌어도 이미지가 살아 있다. 번들의
        # Contents/MacOS/python 이 진짜 바이너리라서 지금 안전한 것이지,
        # 우연이 아니다 — 여기를 셸 래퍼로 '단순화'하면 하필 사용자의 앱이
        # 교체 중인 그 지점에서 진단 없는 무한 대기가 된다.
        "exchange() {",
        '  [ -x "$1" ] || return 1',
        '  "$1" -c "$EXCHANGE" "$2" "$3" 2>/dev/null || return 1',
        "}",
        # 새 앱이 정말 '새로' 떠서 살아 있는지.
        #
        # 두 겹으로 막는다. 첫째, 패턴을 실행 경로 시작에 못 박는다 — 이
        # 스크립트 자신의 명령줄에도 앱 경로가 통째로 들어 있어서(sh -c
        # '<스크립트>'), 앵커가 없으면 업데이터가 자기 자신을 보고 "떴다"고
        # 판정한다. 두 번째 패턴도 같은 이유로 앵커가 필요하다: argv[0] 이
        # python 이고 argv[1] 이 우리 스크립트인 꼴만 받는다(launcher.c 가
        # 번들 밖 python 으로 폴백한 경우). 앵커 없이 두면
        # `sh -c '... /Contents/Resources/claude_pet.py'` 같은 아무 프로세스나
        # 통과한다 — 첫 패턴에서 막은 구멍이 폴백으로 되살아난다.
        #
        # 둘째, 그리고 이쪽이 본질이다. 교환은 '제자리'에서 일어나므로 경로가
        # 그대로다 — 즉 그 경로에서 '이미 돌고 있던' 프로세스는 무엇이든 이
        # 패턴을 만족시킨다. 업데이트를 띄운 바로 그 앱이 그런 프로세스다.
        # 그래서 open 직전에 매칭되는 pid 를 찍어 두고(BEFORE), 그 목록에 없는
        # pid 가 나타났을 때만 인정한다. 앵커는 문자열이 헐겁게 맞는 걸 막고,
        # 스냅숏은 '원래 있던 프로세스'가 답을 대신하는 걸 막는다. 서로 다른
        # 것을 막으므로 둘 다 필요하다.
        #
        # `|| true` 가 둘 다 붙어 있어야 한다. pgrep 은 '못 찾으면' 1 로 끝나는데,
        # 이 스크립트는 set -e 라서 첫 pgrep 이 아무것도 못 찾는 순간 그룹 전체가
        # 거기서 중단된다 — 즉 두 번째 pgrep 이 아예 실행되지 않는다. 그리고
        # 첫 패턴이 못 찾는 상황이야말로 폴백이 필요한 바로 그 상황이므로,
        # 이 두 글자가 없으면 폴백 패턴은 '이미 첫 패턴이 맞았을 때'만 돌 수 있는
        # 죽은 코드가 된다. 실제로 그랬다: 번들 밖 python 으로 뜬 앱은 정상적으로
        # 떴는데도 확인을 못 받아 그대로 롤백됐고, BEFORE 스냅숏에도 그런 pid 는
        # 한 번도 들어간 적이 없어 스냅숏이 그 갈래를 지켜 준 적도 없다.
        #
        # 그리고 pgrep -f 가 보는 것은 커널이 잘라 둔 명령줄이다. 커널은 인자
        # 문자열을 정해진 크기까지만 보관하고, 그 뒤는 애초에 존재하지 않는다 —
        # pgrep 이 자르는 게 아니라서 옵션으로 되돌릴 수 없다. 그래서 여기의
        # 두 패턴은 둘 다 '앞에서부터' 맞도록 앵커를 달았다. 앵커에는 느슨한
        # 매칭을 막는 이유가 이미 있지만, 잘림에 대해서도 같은 앵커가 답이다:
        # 뒤쪽에 오는 조각으로 판정하는 패턴을 쓰면 설치 경로가 긴 사용자에게만
        # 확인이 실패하고, 그 사용자의 정상적인 업데이트가 매번 롤백된다.
        # 이 자리에 패턴을 더할 때는 판정에 쓰는 부분이 명령줄의 앞쪽인지부터
        # 볼 것.
        "matching_pids() {",
        '  { /usr/bin/pgrep -f "^$APPRE/Contents/MacOS/" 2>/dev/null || true;',
        '    /usr/bin/pgrep -f'
        ' "^[^ ]*[Pp]ython[^ ]* $APPRE/Contents/Resources/claude_pet\\.py"'
        " 2>/dev/null || true; } | sort -u",
        "}",
        # 어디서 실패하든: 이미 교체까지 갔으면 원래 앱을 되돌린다. 되돌리기도
        # 원자적 교환이 우선이고, 그때 쓰는 python 은 '옛 앱'의 것이다 — 새
        # 번들이 망가져서 여기까지 왔는데 그 번들에 기대면 안 된다.
        "rollback() {",
        '  if [ -z "$OLD_PATH" ] || [ ! -d "$OLD_PATH" ]; then return 0; fi',
        '  if [ -d "$APP" ] && exchange "$OLD_PATH/Contents/MacOS/python" '
        '"$APP" "$OLD_PATH"; then',
        # 교환은 맞바꿈이다 — 되돌린 뒤 $OLD_PATH 에 들어 있는 것은 옛 앱이
        # 아니라 방금 밀려난 '실패한 새 번들'이다. 지워도 되는 대상의 id 를 그
        # 실체로 다시 세운다. 안 세우면 그 자리의 id 는 지금 $APP 에 있는 옛
        # 앱을 가리키게 되어 정리가 아무것도 못 지우고(그게 discard 의 규칙이다),
        # 실패한 업데이트마다 앱 번들 하나가 설치 폴더에 그대로 쌓인다.
        '    NEWID="$(/usr/bin/stat -f %d,%i "$OLD_PATH" 2>/dev/null || true)"',
        '    if [ "$OLD_PATH" = "$BACKUP" ]; then BACKUPID="$NEWID";',
        '    else STAGEID="$NEWID"; fi',
        "    return 0",
        "  fi",
        # 이동 폴백. 교체 쪽에서는 이 모양을 없앴는데 여기는 남긴다 — 판단이
        # 다르기 때문이다. 앞으로 나아가지 못하는 것은 이번 업데이트를 거르면
        # 그만이지만, 여기서 못 되돌리면 사용자에게 앱이 하나도 남지 않는다.
        # 마지막 수단에는 틈이 있어도 수단이 있는 편이 낫다.
        #
        # 비켜 둘 자리를 실제로 비운다. $BACKUP 은 위에서 mkdir 로 차지해 둔 빈
        # 폴더라 rmdir 로 사라진다. 실패하는 것 자체는 사고가 아니라 바로 아래
        # 존재 검사가 답할 질문이므로 여기서 멈추지 않는다.
        '  rmdir "$BACKUP" 2>/dev/null || true',
        # 자리가 실제로 빈 것을 보고 나서만 옮긴다. 비어 있지 않은 이름으로
        # mv 하면 실패가 아니라 '그 안으로 들어가며 성공'한다 — 실패한 새 번들이
        # 남의 트리 속에 묻히고, APP 은 사라진 것으로 보여 아래 판정이 어긋난다.
        '  if [ -e "$APP" ] && [ ! -e "$BACKUP" ]; then',
        # 비켜 두는 그 객체의 신원을 적어 둔다. 안 적으면 정리는 '모르는 것'에
        # 손대지 않으므로(그게 discard 의 규칙이다) 실패한 업데이트마다 앱 번들
        # 하나가 설치 폴더에 그대로 쌓인다. 실제로 그랬다: 실패한 새 앱이
        # $BACKUP 으로 가는데 BACKUPID 는 끝까지 비어 있어서, 롤백은 제대로
        # 되고 그 번들만 영영 남았다.
        '    DEADID="$(/usr/bin/stat -f %d,%i "$APP" 2>/dev/null || true)"',
        '    if mv "$APP" "$BACKUP" 2>/dev/null; then BACKUPID="$DEADID"; fi',
        "  fi",
        # 여기가 핵심이다. 위에서 옮기지 못했으면 APP 은 '디렉터리로 남아 있고',
        # 그 상태에서 mv "$OLD_PATH" "$APP" 은 실패하지 않는다 — 옛 앱을 APP
        # '안으로' 밀어 넣으며 성공해 버린다. 그러면 옛 앱은 되돌아오지도
        # 남지도 않은 채 새 번들 속에 묻히고 KEEP_BACKUP 도 서지 않는다.
        # 그래서 APP 이 실제로 없어진 걸 확인한 뒤에만 되돌린다.
        '  if [ -e "$APP" ]; then KEEP_BACKUP=1; return 0; fi',
        # 되돌리기가 실패하면 OLD_PATH 가 앱의 '유일한 사본'이다. 그걸 지우면
        # 사용자에게는 아무것도 남지 않고, 앱이 없으니 다시 받을 수도 없다.
        '  mv "$OLD_PATH" "$APP" 2>/dev/null || KEEP_BACKUP=1',
        "}",
        # 우리가 만든 그 객체일 때만 지운다.
        #
        # 예전에는 정리가 `rm -rf "$STAGE" "$BACKUP"` 이었다. 이름만 보고 지우는
        # 것이라, 그 이름을 우리가 만들지 않았거나 중간에 남이 차지했으면 남의
        # 트리를 통째로 날린다. dev+ino 를 적어 두고 지우기 직전에 대조하면
        # '이름이 같은 다른 것'은 절대 지워지지 않는다. id 를 모르면($2 가 비면)
        # 손대지 않는다 — 모르는 것을 지우는 것이 바로 막으려는 사고다.
        # 그리고 그 대조는 셸에서 할 수 없다. `stat` 로 보고 `rm -rf` 로 지우는
        # 것은 검사와 사용이 갈라진 모양이라, 그 사이에 이름이 남의 것으로
        # 바뀌면 확인받은 적 없는 트리를 통째로 지운다. 창을 좁히는 것으로는
        # 답이 되지 않는다 — 대조한 그 객체를 손에 든 채로 지워야 하고, 그러려면
        # openat/unlinkat 이 필요한데 /bin/sh 에는 그것이 없다. 그래서 삭제는
        # $DISCARD 프로그램이 하고(위 _DISCARD_PY 참조) 셸은 부르기만 한다.
        #
        # 실행하는 python 은 서명까지 확인한 **새 번들**의 것이다. 그리고
        # 실패는 전부 한 방향으로 접는다: 도우미가 없거나, 실행하지 못하거나,
        # 0 이 아닌 값으로 끝나면 **그 객체를 남긴다.** 남은 폴더는 다음에
        # 지울 수 있지만 남의 트리를 지운 것은 되돌릴 수 없으므로, '지우기'로
        # 되돌아가는 폴백은 두지 않는다.
        #
        # 잠금 fd 는 이 자식에게 물려주지 않는다. 이 프로세스는 셸보다 오래
        # 살지 않으니 지금은 새는 자리가 아니지만, flock 은 '그 열림을 가리키는
        # 마지막 fd 가 닫힐 때' 풀리므로 한 번이라도 오래 사는 자식에게 새면
        # 모두가 놓았다고 믿는 잠금이 계속 잡혀 있게 된다. 여기서 닫는다.
        "discard() {",
        '  [ -n "$2" ] || return 0',
        '  [ -e "$1" ] || return 0',
        '  [ -x "$NEW/Contents/MacOS/python" ] || return 0',
        f'  "$NEW/Contents/MacOS/python" -c "$DISCARD" "$1" "$2"'
        f' {close_fd}>&- 2>/dev/null || return 0',
        "}",
        # 실패로 끝났을 때 앱을 '다시 띄운다'.
        #
        # 여기까지 오면 사용자에게는 앱이 하나도 떠 있지 않다. 업데이트를 시작할
        # 때 옛 앱은 자리를 비켜 주려고 스스로 종료했고, 새 앱은 뜨지 못했거나
        # 확인을 받지 못해 되돌려졌다. 롤백은 지금까지 '디스크를 원래대로'만
        # 돌려놨을 뿐이라, 파일은 제자리인데 사용자 화면에서는 앱이 그냥 사라진
        # 것으로 보였다. 되돌려 놓을 것에는 '돌고 있던 상태'도 들어간다.
        #
        # 띄우는 방법은 위에서 정한 $LAUNCH 하나에서 온다. 이 줄과 아래 launch
        # 줄의 '글자'를 다르게 두는 이유도 거기 적어 두었다 — 시험 하네스의
        # 첫-등장 치환 때문이고, 이 relaunch 정의가 launch 자리보다 먼저 나온다.
        #
        # **이 스크립트 문자열을 밖에서 고쳐 쓰는 것은 시험뿐이다.** 제품 쪽
        # 호출부는 install_github_update 하나이고, 만들어진 문자열을 그대로
        # Popen(["/bin/sh", "-c", ...]) 에 넘긴다 — 어떤 후처리도 없다. 예전
        # 주석은 이걸 '밖에서 리터럴을 바꿔치기하는 자리가 있다'고만 적어 두어,
        # 제품 경로에도 그런 치환이 있는 것처럼 읽혔다.
        "relaunch() {",
        '  if [ ! -d "$APP" ]; then return 0; fi',
        # 되돌린 '그 앱'일 때만 띄운다.
        #
        # 여기까지 오는 길은 실패한 거래이고, 그 사이 설치 경로의 '이름'은 아무도
        # 잠그지 않았다. 이름만 보고 띄우면, 롤백이 옛 앱을 제자리에 돌려놓지
        # 못한 경우나 그 자리를 다른 무엇이 차지한 경우에 **남의 번들을 우리가
        # 대신 실행한다** — 사용자에게는 우리가 띄운 것으로 보인다.
        #
        # 정상 경로에서 이 대조는 언제나 통과한다: 성공한 롤백은 옛 앱을 제자리에
        # 돌려놓고, 그 옛 앱의 신원이 바로 $APPID 다. 통과하지 못한다는 것은
        # 지금 그 이름에 있는 것이 우리가 되돌린 그것이 아니라는 뜻이므로,
        # 띄우지 않는 쪽이 맞다.
        '  if [ "$(/usr/bin/stat -f %d,%i "$APP" 2>/dev/null || true)"'
        ' != "$APPID" ]; then return 0; fi',
        '  RESTORED="$APP"',
        # 잠금 fd 는 여기서도 물려주지 않는다 — 아래 launch 와 같은 이유다.
        f'  ( $LAUNCH "$RESTORED" ) {close_fd}>&- 2>/dev/null || true',
        "}",
        "cleanup() {",
        "  rc=$?",
        # 되돌린 '뒤에' 다시 띄운다. 순서가 중요하다 — 롤백 전에 띄우면 실패한
        # 새 번들이 뜬다.
        '  if [ "$rc" -ne 0 ]; then rollback; relaunch; fi',
        # 임시 폴더도 다른 모든 삭제와 같은 규율로 지운다: 이름이 아니라 호출부가
        # 넘겨준 신원으로.
        #
        # 한때 이 줄은 `rm -rf "$WORK"` 였고, 그것을 '원칙 있는 예외'로 정당화하는
        # 주장이 있었다 — $WORK 는 0700 인 사용자 전용 $TMPDIR 안이라 남과 이름을
        # 다투는 자리가 아니고, 파이썬과 이 셸이 같은 자리를 두 번 지우지도
        # 않는다는 것이다. 그 주장은 '위험'에 대해서는 옳았지만 결론이 틀렸다:
        # 예외의 근거는 신원을 얻는 비용이었는데, WORKID 는 이미 계산되어 이미 이
        # 스크립트에 적혀 있었다. 값을 손에 들고 쓰지 않는 것이 이 릴리스가
        # 되풀이해서 찾아낸 바로 그 모양이다 — 방어의 모든 조각이 있는데 대조만
        # 없는 것. 비용이 없으면 예외도 없다.
        #
        # **$WORK 는 반드시 맨 마지막에 지운다.** 삭제를 수행하는 프로그램은 새
        # 번들의 python 으로 도는데($NEW/Contents/MacOS/python), $NEW 는 $WORK
        # **안에** 있다. 이 줄이 위에 있으면 $WORK 를 지우는 순간 그 python 이
        # 함께 사라지고, 뒤따르는 $STAGE·$BACKUP 삭제는 도우미가 없어 전부
        # '남긴다'로 접힌다 — 성공한 업데이트마다 옛 앱 번들 하나와 빈 폴더
        # 하나가 설치 폴더에 그대로 쌓인다. 순서가 정책을 조용히 뒤집는 자리다.
        # 되돌리지 못했으면 앱 쪽은 아무것도 지우지 않는다. 이때 $OLD_PATH 는 옛
        # 앱의 유일한 사본이고, 어디 있는지 알려 주지 않으면 사용자 눈에는
        # 쓰레기로 보여 결국 지워진다. ($WORK 는 이 갈래에서도 우리 것이므로
        # 지운다 — 아래 정상 갈래와 같은 이유로 마지막에.)
        '  if [ -n "$KEEP_BACKUP" ]; then',
        "    printf '[update] previous app kept for recovery: %s\\n'"
        ' "$OLD_PATH" >> "$HOME/claudepet_debug.log" 2>/dev/null || true',
        '    discard "$WORK" "$WORKID"',
        "    return 0",
        "  fi",
        # 여기 왔다는 건 제자리의 앱이 우리가 남기려던 그 앱이라는 뜻이다
        # (성공했으면 새 앱, 되돌렸으면 옛 앱). 그때만 임시본을 버린다.
        # 앱이 제자리에 없으면 전부 남긴다 — 지저분한 폴더가 앱을 잃는 것보다
        # 낫다.
        '  if [ -e "$APP" ]; then discard "$STAGE" "$STAGEID";'
        ' discard "$BACKUP" "$BACKUPID"; fi',
        '  discard "$WORK" "$WORKID"',
        "}",
        "trap cleanup EXIT",
        # 이 APP 에 대한 거래는 통째로 직렬화되어 있다 — 다만 그 잠금을 여는 일은
        # 여기서 하지 않는다. _acquire_update_lock() 이 O_NOFOLLOW 로 열고
        # fstat 으로 정체를 확인한 뒤 flock 까지 걸어서 넘겨준 fd 를, 이 셸은
        # pass_fds 로 물려받아 '들고만' 있다. 그래서 잠금은 이 스크립트가 뜨기도
        # 전부터 유효하고, 이 셸이 어떤 식으로 죽든(SIGKILL 포함) 커널이 놓아
        # 준다. 셸이 직접 열려고 하면 O_NOFOLLOW 도 fstat 확인도 할 수 없어,
        # 예측 가능한 경로에 링크 하나만 놓아 두면 남의 파일이 잘려 나갔다.
        #
        # 여기서 잠금에 대해 해야 할 유일한 일은 '아래 launch 에서 물려주지 않는
        # 것'이다. 그건 그 자리에 적혀 있다.
        "sleep 1.5",
        'test -d "$NEW"',                       # 새 앱이 실제로 풀렸는지
        # 교체 대상의 신원을 '모른 채로' 시작하지 않는다.
        #
        # APPID 는 파이썬이 잠금을 잡은 뒤에 읽어 넘긴 (dev,ino) 다. 비어 있다는
        # 것은 그 순간 그 자리에 아무것도 없었거나 읽지 못했다는 뜻이고, 그러면
        # 아래 교체는 '그 이름에 지금 있는 것'을 상대하게 된다. 아직 아무것도
        # 만들지 않은 여기서 멈춘다 — 실제 대조는 교체 직전 $OLDID 자리에서 한다.
        'test -n "$APPID"',
    ) + ((
        # Python 쪽에서 이미 옆에 만들어 두고 검사까지 끝낸 스테이지를 쓴다.
        # 여기서 다시 복사하면 '검사한 트리'와 '설치되는 트리'가 갈라진다.
        'test -d "$STAGE/Contents/MacOS"',
    ) if staged else (
        # 이름을 '치우지' 않고 '차지'한다.
        #
        # 예전에는 여기가 `rm -rf "$STAGE"` 였다 — 이름이 겹쳤다는 이유만으로 그
        # 자리에 있는 것을 통째로 지우는 한 줄이고, 아래 BACKUP 에서 이미 한 번
        # 없앤 바로 그 모양이다. mkdir 에는 그 틈이 없다: '이미 있는지 보는 일'과
        # '만드는 일'이 한 번의 원자적 동작이라, 이미 있으면 실패하고 set -e 가
        # 여기서 멈춘다. 그때까지 우리는 아무것도 지우지도 바꾸지도 않았다.
        'mkdir "$STAGE"',
        # 차지한 그것의 신원을 ditto 로 채우기 '전에' 적는다. 채운 뒤에 읽으면
        # 그 사이 이름이 남의 것으로 바뀐 경우 남의 id 를 적게 되고, 정리가 그
        # 남의 것을 지운다.
        'STAGEID="$(/usr/bin/stat -f %d,%i "$STAGE" 2>/dev/null || true)"',
        'test -n "$STAGEID"',
        # 진짜 ditto 는 '이미 있는' 대상 디렉터리에 내용을 부어 넣는다. 파이썬
        # 쪽 스테이지 예약도 같은 성질에 기대고 있다.
        '/usr/bin/ditto "$NEW" "$STAGE"',       # 옆에 완성본을 먼저 만든다
    )) + (
        'xattr -dr com.apple.quarantine "$STAGE" 2>/dev/null || true',
        'test -d "$STAGE/Contents/MacOS"',      # 복사가 온전한지 확인 후에야 교체
        # 교체 직전에 같은 볼륨인지 본다. 다른 볼륨이면 원자적 교환 자체가
        # 불가능하고, mv 도 복사로 풀려 중간 상태가 길게 노출된다.
        'test "$(/usr/bin/stat -f %d "$STAGE")" = '
        '"$(/usr/bin/stat -f %d "$APP")"',
        # ── 여기가 이 스크립트의 신원 관문이다. 무엇을 차지하거나 만들기 전에 온다.
        #
        # 밀려날 '그 앱'의 신원을 읽고, 그것이 호출부가 잠금 안에서 보고 넘겨준
        # APPID 와 같은지 본다. 이 대조가 없으면 교환은 '그 이름에 지금 있는 것'을
        # 상대한다 — 잠금은 다른 인앱 업데이터는 막아 주지만 설치 폴더의 '이름'을
        # 잠그지는 않으므로, 검증과 교환 사이에 수동 설치(build_app.sh)나 다른
        # 무엇이 그 자리를 차지했다면 **남의 번들이 우리 스테이지와 맞바뀐다.**
        # 그 방어에 필요한 값은 줄곧 계산되어 이 스크립트에 적혀 있었고, 읽는
        # 곳만 없었다.
        #
        # **어긋나면 남의 것에 손대지 않는다.** set -e 가 여기서 멈추고, 그 시점에
        # 우리는 아직 $BACKUP 을 차지하지도 $APP 을 건드리지도 않았다. trap 의
        # 정리는 우리가 만든 것만(신원이 맞는 $STAGE·$BACKUP) 거두므로 그 자리를
        # 차지한 객체는 그대로 남는다 — 남의 번들은 우리가 치울 것이 아니고,
        # 실패한 업데이트보다 남의 것을 지우는 쪽이 나쁘다.
        #
        # 순서를 바꾸지 말 것: 이 대조가 mkdir "$BACKUP" 아래로 내려가면, 거절할
        # 수 있는 단계가 이미 자리를 차지한 단계 뒤에 오게 된다.
        'OLDID="$(/usr/bin/stat -f %d,%i "$APP" 2>/dev/null || true)"',
        'test "$OLDID" = "$APPID"',
        # BACKUP 이름을 '확인'하지 않고 '차지'한다.
        #
        # 처음에는 여기가 `rm -rf "$BACKUP"` 이었다 — 이름이 겹쳤다는 이유만으로
        # 남의 폴더를 통째로 지우는 한 줄이었다. 그다음이 `test ! -e "$BACKUP"`
        # 이었고, 지우지는 않게 됐지만 확인과 사용이 갈라진 것은 그대로였다:
        # 이 test 와 아래 mv 사이에 그 이름이 채워지면 `mv "$APP" "$BACKUP"` 은
        # 실패하지 않고 '그 폴더 안으로' 앱을 밀어 넣으며 성공한다. 그러면 옛
        # 앱은 남의 트리 속에 묻히고, 롤백도 정리도 그걸 찾지 못한다.
        #
        # mkdir 에는 그 틈이 없다 — '이미 있는지 보는 일'과 '만드는 일'이 한 번의
        # 원자적 동작이다. 이미 있으면 실패하고 set -e 가 여기서 멈추므로 접는
        # 결과는 test 와 같다. 다른 것은 성공했을 때다: 그 이름은 거래가 끝날
        # 때까지 우리 것이고, 남이 뒤늦게 차지할 수 없다.
        'mkdir "$BACKUP"',
        # 차지한 그 빈 폴더의 신원. 이걸 적어 두지 않으면 성공한 업데이트가
        # 자기가 만든 빈 폴더를 못 지운 채 설치 폴더에 남긴다 — 정리는 id 를
        # 모르는 것에 손대지 않기 때문이다. 아래 이동 폴백에서는 이 이름에 옛
        # 앱이 들어오므로 그때 옛 앱의 id 로 다시 세운다.
        'BACKUPID="$(/usr/bin/stat -f %d,%i "$BACKUP" 2>/dev/null || true)"',
        # 읽지 못했으면 여기서 멈춘다. 빈 BACKUPID 로 계속 가면 정리는 '모르는
        # 것에 손대지 않는' 규칙에 걸려 방금 만든 폴더를 못 지우고, 무엇보다 그
        # 사실이 APP 을 건드리기 시작한 뒤에야 드러난다. 아직 APP 이 그대로인
        # 지금 멈추는 편이 낫다.
        'test -n "$BACKUPID"',
        # $OLDID 는 위 신원 관문에서 이미 읽고 대조한 값이다 — 밀려나는 '그 앱'의
        # 신원이고, 교환 뒤에는 STAGE 에, 이동 폴백에서는 BACKUP 에 그 객체가
        # 들어간다. 정리는 이 id 와 맞을 때만 지운다. 여기서 다시 stat 하지
        # 않는다: 다시 읽으면 대조한 값과 쓰는 값이 갈라져, 관문을 통과한 뒤
        # 바뀐 것을 그대로 집어 든다.
        # ── 맞바꿀 '이쪽'의 신원 관문. $APPID 쪽과 대칭이고, 교환 직전에 온다.
        #
        # 위에 이미 `stat -f %d` 로 같은 볼륨인지 보는 줄이 있지만 **그것은 신원이
        # 아니다.** 같은 볼륨의 다른 객체는 그 검사를 그대로 통과한다 — 즉 검증을
        # 마친 스테이지가 그 이름에서 밀려나고 남의 트리가 들어와도 볼륨만 같으면
        # 통과하고, 교환은 '그 이름에 지금 있는 것'을 설치 경로와 맞바꾼다.
        # 그러면 사용자의 앱 자리에 우리가 검사한 적 없는 번들이 들어앉는다.
        # 볼륨 검사는 원자적 교환이 가능한지를 묻는 것이고, 여기는 그것이 우리
        # 것인지를 묻는다. 서로 다른 질문이라 둘 다 있어야 한다.
        #
        # 대조 대상은 호출부(또는 위 mkdir 직후)가 적어 둔 $STAGEID 다. 여기서
        # 다시 유도하지 않는다 — 유도한 값과 대조하면 자기 자신과의 대조가 되어
        # 언제나 통과한다. 모르면($STAGEID 가 비면) 멈춘다. 이 시점의 $APP 은
        # 아직 옛 앱 그대로라 trap 이 그것을 다시 띄운다.
        'test -n "$STAGEID"',
        'test "$(/usr/bin/stat -f %d,%i "$STAGE" 2>/dev/null || true)"'
        ' = "$STAGEID"',
        # 설치본의 python 을 먼저 쓴다(지금까지 돌던 것이라 확실하다). 그 번들에
        # python 이 없으면 — 옛 빌드가 그럴 수 있다 — 서명까지 확인한 새 번들의
        # 것으로 한 번 더 시도한다. 둘 다 실패하면 여기서 끝낸다.
        'if exchange "$APP/Contents/MacOS/python" "$STAGE" "$APP" || '
        'exchange "$STAGE/Contents/MacOS/python" "$STAGE" "$APP"; then',
        # 교환 뒤 STAGE 에는 옛 앱이 그대로 들어 있다. 이름을 바꾸지 않는다 —
        # 예전에는 여기서 mv "$STAGE" "$BACKUP" 을 했는데, 그 mv 가 실패하면
        # BACKUP 은 없고 OLD_PATH 도 안 서서 롤백이 아무것도 못 찾고, 정리가
        # STAGE(=옛 앱의 유일한 사본)를 지워 버렸다. 실패할 수 있는 단계를
        # 지키는 것보다 없애는 쪽이 낫다.
        '  OLD_PATH="$STAGE"',
        # 교환은 제자리 맞바꿈이라 STAGE 에 들어 있는 것은 더 이상 우리가 만든
        # 스테이지가 아니라 방금 밀려난 옛 앱이다. 지워도 되는 대상의 id 도
        # 그에 맞춰 옮긴다 — 안 옮기면 성공한 업데이트가 뒷정리를 못 한다.
        '  STAGEID="$OLDID"',
        "else",
        # 원자적 교환이 안 되면 **앞으로 나아가지 않는다.** $APP 을 건드리기
        # 전에 끝낸다.
        #
        # 예전에는 여기에 이동 폴백이 있었다: `rmdir "$BACKUP"` 로 자리를 비우고
        # `mv "$APP" "$BACKUP"`, `mv "$STAGE" "$APP"`. 그 모양은 두 가지를 같이
        # 들여왔다. 하나는 설치 경로가 잠깐 비는 구간이고, 다른 하나 — 이쪽이
        # 실제로 지금 고치는 것 — 은 rmdir 과 mv 사이의 틈이다. rmdir 이 비운
        # 그 이름을 그 사이에 누가 차지하면 `mv "$APP" "$BACKUP"` 은 실패하지
        # 않고 '그 폴더 안으로' 옛 앱을 밀어 넣으며 성공한다. 그러면 옛 앱은
        # 남의 트리 속에 묻히고 롤백도 정리도 그것을 찾지 못한다. mkdir 로
        # 이름을 '차지'해 둔 이유가 바로 그 틈을 없애는 것이었는데, rmdir 이
        # 차지를 되돌려 놓아 같은 틈을 다시 열었다.
        #
        # 이제 새 번들은 검증된 자기 python 을 반드시 갖고 있어야 하므로,
        # 원자적 교환은 기대가 아니라 계약이다. 계약이 지켜지지 않으면 이번
        # 업데이트를 거르는 것이 답이다 — 폴백이 남아서 하는 일은 그 틈을
        # 들여오는 것뿐이다. 못 하면 안 한다.
        #
        # 여기서 exit 하면 trap 이 돈다. $OLD_PATH 는 아직 비어 있어 rollback 은
        # 아무것도 되돌리지 않고(되돌릴 것이 없다), relaunch 가 손대지 않은 옛
        # 앱을 다시 띄우며, 정리는 우리가 만든 $STAGE·$BACKUP·$WORK 만 거둔다.
        #
        # (rollback 쪽의 마지막 수단 이동은 남겨 둔다. 판단이 다르기 때문이다 —
        # 앞으로 못 나아가는 것은 이번 업데이트를 거르면 그만이지만, 되돌리지
        # 못하면 사용자에게 앱이 하나도 남지 않는다.)
        '  exit 1',
        "fi",
        # open 직전에 '이미 이 경로에서 돌고 있던' pid 를 찍어 둔다. 교환은
        # 제자리에서 일어나 경로가 그대로이므로, 이걸 안 찍으면 업데이트를
        # 띄운 그 앱이 자기 자신을 새 앱으로 인정해 버린다.
        'BEFORE="$SELFPID $(matching_pids | tr "\\n" " ")"',
        # 잠금 fd 를 닫은 서브셸 안에서 띄운다.
        #
        # flock 은 '그 열림을 가리키는 마지막 fd 가 닫힐 때' 풀린다. 여기서 뜨는
        # 자식이 잠금 fd 를 물려받으면, 잠금은 이 셸이 끝난 뒤에도 그 자식(=방금
        # 띄운 앱)이 사는 내내 붙들려 있다. 그러면 다음 업데이트부터는 잠금을
        # 영영 못 잡아 아무 일도 일어나지 않고, 프로세스가 죽으면 커널이 풀어
        # 준다는 성질도 같이 사라진다 — 잠금이 있는 채로 잠금이 하는 일만
        # 없어지는, 가장 알아채기 어려운 형태의 고장이다. 그리고 이건 예외 상황이
        # 아니라 업데이트가 '성공'할 때마다 지나가는 정상 경로다.
        #
        # LaunchServices(`open`)로 뜨는 앱은 물려받지 않지만, 이 자리를 직접
        # exec 하는 형태로 바꾸는 순간 그대로 그 사고가 난다. 그래서 '지금은
        # 안전하니 놔둔다'가 아니라 여기서 닫는다.
        #
        # 닫기는 `$LAUNCH` 줄이 아니라 감싼 서브셸에 건다. 그 줄은 시험이 통째로
        # 다른 명령으로 치환하는 자리라, 줄 끝에 리다이렉션을 붙이면 치환된
        # 명령에 딸려 들어간다. 또 ack 는 이 launch '뒤에' 오고 계속 잠금 안에
        # 있어야 하므로, 닫는 범위는 서브셸까지이고 이 셸의 잠금 fd 는 그대로
        # 열려 있다.
        "(",
        '$LAUNCH "$APP"',
        f") {close_fd}>&-",
        # 여기부터가 '띄웠다'가 아니라 '떴다'의 확인이다. 확인될 때까지 롤백
        # 경로를 살려 둔다. 확인 못 하면 set -e 로 빠져나가 trap 이 되돌린다.
        "ACK=",
        "i=0",
        # 숫자는 '%g' 로 찍는다. float 을 그대로 넣으면 3 이 "3.0" 이 되고,
        # 그러면 스크립트 문자열을 들여다보는 쪽에서 "sleep 3" 을 찾다가
        # "sleep 3.0" 의 앞부분만 맞아 뒤에 ".0" 이 남는 식으로 어긋난다.
        f"while [ $i -lt {UPDATE_ACK_POLLS} ]; do",
        f"  sleep {'%g' % UPDATE_ACK_INTERVAL}",
        "  for p in $(matching_pids); do",
        '    case " $BEFORE " in *" $p "*) continue;; esac',
        '    ACK="$p"',
        "    break",
        "  done",
        '  if [ -n "$ACK" ]; then break; fi',
        "  i=$((i+1))",
        "done",
        'test -n "$ACK"',
        # 떴다가 곧바로 죽는 번들도 있다. 잠깐 두고 '같은 그 pid' 가 아직
        # 살아 있는지 본다 — 다른 프로세스가 대신 답하지 못하게.
        f"sleep {'%g' % UPDATE_ACK_SETTLE}",
        'kill -0 "$ACK" 2>/dev/null',
    ))


# 앱 번들 신원 — 업데이트로 받은 것이 정말 이 앱인지 확인할 때 쓴다.
BUNDLE_ID = "me.yeongyu.claudepet"
TEAM_ID = "RXGNVSLYF5"          # Developer ID Application: Yeongyu Yang


# 서명자를 못 박는 요구사항. 권한 문자열을 우리가 파싱해 비교하는 대신
# codesign 자신의 요구사항 언어로 검사시킨다 — 인증서 필드(subject.OU =
# Team ID)를 직접 지정하므로 이름이 비슷한 인증서로는 만족시킬 수 없다.
#
# 앞의 '=' 는 반드시 있어야 한다. "이건 파일 경로가 아니라 요구사항 원문"이라는
# 표시라서, 빠지면 codesign 이 문자열을 파일 경로로 보고
# 'No such file or directory / invalid requirement specification' 으로 죽는다
# — 즉 모든 번들을 거부한다. 서명 검사는 하드 리젝이라 그러면 정상 배포본까지
# 전부 거부되어 업데이트가 영구히 막힌다(그 코드를 고치려면 업데이트가 필요한데
# 그 업데이트가 막힌다). 실제로 그렇게 나간 적이 있다.
#
# OU 를 감싼 따옴표는 '있어도 되고 없어도 되는' 쪽이다. 실측하면
# `-R '=... leaf[subject.OU] = RXGNVSLYF5'` 도 rc=0 이다(Team ID 가 영숫자라
# 요구사항 언어의 식별자로 그대로 읽힌다). 따옴표는 두는 게 안전하니 두되,
# '따옴표가 빠지면 죽는다'고 적어 두지는 않는다 — 사실이 아닌 주석은 다음
# 사람이 재확인 대신 그대로 믿는다는 점에서 위의 '=' 만큼 위험하다.
#
# 바꾸기 전에 반드시 실제 codesign 으로 확인할 것 — mock 은 이 문자열을
# 검증하지 못한다. tests/test_signing_contract.py 가 그 확인을 들고 있다.
CODESIGN_REQUIREMENT = (
    '=anchor apple generic and certificate leaf[subject.OU] = "%s"' % TEAM_ID)


def codesign_argv(app_path):
    return ["/usr/bin/codesign", "--verify", "--deep", "--strict",
            "-R", CODESIGN_REQUIREMENT, str(app_path)]


def spctl_argv(app_path):
    # --type execute 가 없으면 다른 정책으로 평가되고, -vv 가 없으면 origin 이
    # 안 찍힌다 — 누가 서명했는지는 origin 에만 있다.
    return ["/usr/sbin/spctl", "--assess", "--type", "execute", "-vv",
            str(app_path)]


def stapler_argv(app_path):
    # stapler 는 stock 머신의 PATH 에 없다. xcrun 을 거쳐야 한다.
    return ["/usr/bin/xcrun", "stapler", "validate", str(app_path)]


def lipo_argv(path):
    return ["/usr/bin/lipo", "-archs", str(path)]


# Mach-O cputype → lipo 가 쓰는 이름. cpusubtype 까지 봐야 갈라지는 건 arm64 뿐이다.
_MACHO_CPU_NAMES = {
    0x01000007: "x86_64",
    0x00000007: "i386",
    0x0100000C: "arm64",
    0x0000000C: "arm",
}
# 'arm64' 를 요구할 때 만족시키는 슬라이스 이름들.
#
# arm64e 는 포인터 인증이 켜진 arm64 변종이고, Apple Silicon 에서 돈다.
# platform.machine() 은 그런 기기에서도 'arm64' 를 돌려주므로, 이름을 글자
# 그대로 비교하면 arm64e 만 든 번들이 '돌지 않는다'고 거부된다 — 실제로는 돈다.
# 우리 배포물은 x86_64 + arm64 라서 지금 이 갈래로 들어오는 번들은 없지만,
# 그때 우연히 맞는 것과 일부러 맞는 것은 다르다. 받아 주는 철자를 여기 적어 둔다.
# 반대 방향은 넣지 않는다: arm64e 를 요구하는 기기에 arm64 슬라이스만 있는
# 번들은 실제로 못 돌 수 있다.
_ARCH_ALIASES = {"arm64": ("arm64", "arm64e")}


def _macho_arches(path):
    """파일의 Mach-O 슬라이스 이름들 → set. Mach-O 가 아니면 빈 set.

    lipo 를 부르지 않고 헤더를 직접 읽는 이유는 두 가지다. 첫째, 외부 도구가
    없거나 대답하지 못하는 상황에서도 아키텍처는 판정할 수 있어야 한다. 둘째,
    이 함수는 '이게 Mach-O 이긴 한가'에도 답한다 — 셸 스크립트를 실행 파일
    자리에 놓으면 여기서 빈 set 이 나온다. 교환에 쓰는 헬퍼가 스크립트면
    디렉터리가 발밑에서 바뀔 때 읽던 자리를 잃고 진단 없이 매달리므로, 그건
    반드시 걸러야 하는 모양이다.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(8)
            if len(head) < 8:
                return set()
            magic = int.from_bytes(head[:4], "big")
            # fat 바이너리. 헤더는 항상 big-endian 이다.
            if magic in (0xCAFEBABE, 0xCAFEBABF):
                count = int.from_bytes(head[4:8], "big")
                if count > 64:              # 말이 안 되는 값 — 신뢰하지 않는다
                    return set()
                wide = magic == 0xCAFEBABF
                size = 32 if wide else 20
                blob = f.read(size * count)
                out = set()
                for i in range(count):
                    rec = blob[i * size:(i + 1) * size]
                    if len(rec) < 8:
                        break
                    cpu = int.from_bytes(rec[:4], "big")
                    sub = int.from_bytes(rec[4:8], "big")
                    name = _slice_name(cpu, sub)
                    if name:
                        out.add(name)
                return out
            # thin 바이너리. 64비트만 우리 대상이지만 32비트도 이름은 낸다.
            for endian, magics in (("little", (0xCFFAEDFE, 0xCEFAEDFE)),
                                   ("big", (0xFEEDFACF, 0xFEEDFACE))):
                if magic in magics:
                    cpu = int.from_bytes(head[4:8], endian)
                    sub = int.from_bytes(f.read(4) or b"\0\0\0\0", endian)
                    name = _slice_name(cpu, sub)
                    return {name} if name else set()
    except OSError:
        return set()
    return set()


def _slice_name(cpu, sub):
    name = _MACHO_CPU_NAMES.get(cpu)
    # arm64 는 cpusubtype 하위 바이트가 2 면 arm64e 다(상위 바이트는 능력 플래그).
    if name == "arm64" and (sub & 0x00FFFFFF) == 2:
        return "arm64e"
    return name


def _bundle_exe_name(app_path, plist):
    """Info.plist 가 지목하는 주 실행 파일의 '이름' → str, 이름이 아니면 None.

    CFBundleExecutable 은 Contents/MacOS 안의 '파일 이름'이지 경로가 아니다.
    그런데 값을 그대로 os.path.join 에 넘기면 번들이 자기 신원 검사의 대상을
    직접 고를 수 있게 된다: "../evil" 은 Contents/evil 로 풀리고,
    "../../../../bin/sh" 는 번들 밖으로 나가며, 절대경로는 join 이 앞을 통째로
    버려 그 경로가 그대로 대상이 된다. 세 경우 모두 '번들 안의 주 실행 파일을
    보았다'는 검사의 전제가 무너진다 — 지금 이것들을 막고 있는 건 아키텍처
    검사가 /bin/sh 에서 Mach-O 헤더를 못 찾는다는 무관한 사실뿐이고, 그건
    이 검사가 한 일이 아니다. 그래서 여기서 이름의 모양부터 못 박는다.

    빈 값은 거부가 아니다 — 키가 없으면 macOS 자신이 번들 이름으로 떨어지므로,
    관례대로 만들어진 멀쩡한 번들을 막지 않도록 같은 폴백을 쓴다.
    """
    name = str(plist.get("CFBundleExecutable") or "")
    if not name:                         # 키가 없으면 번들 이름 관례를 따른다
        name = os.path.basename(str(app_path))
        if name.endswith(".app"):
            name = name[:-4]
        return name
    if "/" in name or os.sep in name:
        print("[update] rejected: CFBundleExecutable is a path, not a name")
        return None
    return name


def _has_required_arches(app_path, want, run=None):
    """실행 파일이 이 기기에서 '실제로' 돌 수 있는지 lipo 로 확인한다.

    자산 이름은 라벨일 뿐이다. claudepet-universal.zip 이라는 이름을 달고
    arm 슬라이스만 들어 있어도 이름 검사는 통과하고, 교체가 끝난 뒤에야
    '열리지 않는 앱'으로 드러난다 — 그때는 이미 옛 앱을 치운 뒤다.

    want 는 호출부(=내려받기를 승인한 거래)가 정한다. 번들에게 무엇이어야
    하냐고 묻지 않는다 — 그렇게 물으면 어떤 번들이든 자기 대답으로 통과한다.
    """
    # 빈 want 는 '아무 아키텍처나 좋다'가 아니라 '기준을 못 받았다'는 뜻이다.
    # 그때 True 를 돌려주면 이 함수 전체가 조용히 무력해진다 — 실제로 그렇게
    # 한 번 죽었다(그때는 want 가 None 이었고, 지금 이 자리는 () 다). 같은
    # 모양이 같은 결과를 내지 않도록, 기준이 없으면 거부한다. 기준을 이 함수가
    # 지어내지도 않는다 — 그건 번들에게 묻는 것과 한 걸음 차이다.
    want = [str(a).strip() for a in (want or ()) if str(a).strip()]
    if not want:
        print("[update] rejected: no architecture requirement to check against")
        return False
    app_path = str(app_path)
    try:
        with open(os.path.join(app_path, "Contents", "Info.plist"), "rb") as f:
            plist = plistlib.load(f)
    except Exception as e:
        print(f"[update] rejected: unreadable Info.plist ({type(e).__name__})")
        return False
    exe_name = _bundle_exe_name(app_path, plist)
    if exe_name is None:
        return False
    # 동봉 python 은 '있으면 검사한다'가 아니라 반드시 검사한다. 조건부로
    # 넣으면 그 파일을 빼는 것만으로 이 검사를 건너뛸 수 있고, 없는 번들은
    # 아래에서 '아무도 있다고 말해 주지 않음'으로 떨어져 거부된다 — 그 거부가
    # 옳다. 이유는 _identity_paths_are_regular_files 에 적어 두었다.
    targets = [os.path.join(app_path, "Contents", "MacOS", exe_name),
               os.path.join(app_path, "Contents", "MacOS", "python")]
    for target in targets:
        # 출처가 둘이다.
        #
        #  · 헤더 — 우리가 직접 읽는다. 이게 권威다. 도구가 없어도 답이 나오고,
        #    Mach-O 가 아닌 것(셸 스크립트 등)은 빈 집합으로 드러난다.
        #  · lipo — 두 번째 의견. 아무 말도 못 하면(rc≠0 이거나 출력이 비면)
        #    '기권'으로 본다. 기권을 '슬라이스가 없다'로 읽으면 도구를 못 부르는
        #    환경에서 멀쩡한 번들이 전부 거부된다.
        #
        # 판정: 말을 한 출처 중 하나라도 '없다'고 하면 거부하고, 아무도 '있다'고
        # 말해 주지 않으면(=둘 다 침묵) 역시 거부한다. 침묵을 통과로 두면
        # 실행 파일 자리에 Mach-O 가 아닌 것을 놓아 검사를 건너뛸 수 있다.
        header = _macho_arches(target)
        rc, out = (run or _run_signing_tool)(lipo_argv(target))
        lipo_have = set(out.split()) if rc == 0 else set()

        affirmed = False
        for source in (header, lipo_have):
            if not source:
                continue                    # 기권
            for a in want:
                if not (set(_ARCH_ALIASES.get(a, (a,))) & source):
                    print(f"[update] rejected: bundle has no {a} slice")
                    return False
            affirmed = True
        if not affirmed:
            print("[update] rejected: could not read the architectures of a "
                  "bundled executable")
            return False
    return True


def _identity_paths_are_regular_files(app_path):
    """번들의 '정체'를 정하는 두 파일은 링크가 아닌 보통 파일이어야 한다.

    Info.plist 와 주 실행 파일이 그 둘이다. .claude_pet 트리의 링크 금지
    규칙 밖에 있어서, 여기만 링크로 바꿔 두면 신원 검사가 엉뚱한 파일을 읽는다.
    """
    app_path = str(app_path)
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    if os.path.islink(plist_path) or not os.path.isfile(plist_path):
        print("[update] rejected: Info.plist is not a regular file")
        return False
    try:
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f)
    except Exception as e:
        print(f"[update] rejected: unreadable Info.plist ({type(e).__name__})")
        return False
    exe_name = _bundle_exe_name(app_path, plist)
    if exe_name is None:
        return False
    exe = os.path.join(app_path, "Contents", "MacOS", exe_name)
    if os.path.islink(exe) or not os.path.isfile(exe):
        print("[update] rejected: main executable is not a regular file")
        return False
    # 교환 헬퍼도 '번들의 정체'에 속한다.
    #
    # 교체는 Contents/MacOS/python 으로 renamex_np(RENAME_SWAP) 을 부른다.
    # 그게 없으면 교체는 mv 두 번짜리 폴백으로 내려가고, 그 갈래에는 설치
    # 경로가 실제로 비는 구간이 있다 — 하필 거기서 죽으면 사용자에게는 앱이
    # 아예 없다. 그리고 그 자리에 셸 스크립트가 놓이면 훨씬 나쁘다: /bin/sh 는
    # 스크립트를 조금씩 읽어 가며 실행하는데 디렉터리가 발밑에서 바뀌면 읽던
    # 자리를 잃고, 로그도 타임아웃도 없이 영영 매달린다. 그래서 '있으면 좋은
    # 것'이 아니라 없으면 거부한다. 'Mach-O 인가'는 여기서 묻지 않는다 —
    # _has_required_arches 가 '아무 출처도 슬라이스를 확언하지 못하면 거부'로
    # 이미 그 모양을 걸러낸다.
    #
    # **현실적인 고장은 '없음'이 아니라 '있는데 조금 틀림'이다.** 설치된 v0.19
    # 를 직접 들여다보면 Contents/MacOS/python 이 -rwxr-xr-x 의 Mach-O arm64 로
    # 실제로 들어 있다. 그러니 '옛 빌드에는 없다'를 전제로 이 검사를 무르면 안
    # 된다 — 그 전제는 사실이 아니다. 반대로, 파일이 있고 정규 파일이고 슬라이스
    # 까지 맞는데 실행 비트만 빠진 번들은 얼마든지 만들어질 수 있고, 그때
    # 교환은 그냥 안 된다. os.path.exists() 는 그 넷 중 무엇도 보지 못한다
    # (링크를 따라가고, 디렉터리에도 True 를 준다).
    #
    # 그래서 lstat 으로 본다: 링크가 아니고, 정규 파일이고, 실행 가능해야 한다.
    # 'Mach-O 인가'와 '이 기기의 슬라이스가 있는가'는 _has_required_arches 가
    # 같은 검증 안에서 답한다(그쪽 targets 에 무조건 들어간다). 둘 다
    # validate_update_app 안, 교체 셸을 띄우기 '전'에 끝난다.
    #
    # 하드 리젝이라 빌드가 이 파일을 빼면 모든 클라이언트의 업데이트가 막힌다.
    # 그게 이 검사의 값이기도 하다: 빠진 채로 나가는 것이 더 나쁜 결과다.
    helper = os.path.join(app_path, "Contents", "MacOS", "python")
    try:
        hst = os.lstat(helper)
    except OSError:
        print("[update] rejected: bundled exchange helper "
              "(Contents/MacOS/python) is missing")
        return False
    if not stat.S_ISREG(hst.st_mode):
        # 링크(끊어진 것 포함)·디렉터리·장치 파일이 전부 여기서 걸린다.
        print("[update] rejected: bundled exchange helper "
              "(Contents/MacOS/python) is not a regular file")
        return False
    if not hst.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        print("[update] rejected: bundled exchange helper "
              "(Contents/MacOS/python) is not executable")
        return False
    return True


def _run_signing_tool(argv, timeout=60):
    """서명 도구 한 번 실행 → (returncode, 출력). 못 돌리면 (None, "").

    타임아웃이 있는 이유: 이 함수는 새로고침 스레드에서 불린다. 도구가 멈추면
    예전에는 스레드째로 걸렸다.
    """
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=timeout)
    except Exception as e:
        print(f"[update] rejected: {os.path.basename(argv[0])} could not run "
              f"({type(e).__name__})")
        return (None, "")
    out = p.stdout if isinstance(p.stdout, str) else ""
    err = p.stderr if isinstance(p.stderr, str) else ""
    return (p.returncode, err + out)


def _signature_is_ours(app_path, run=None):
    """서명이 유효하고 '우리 Team ID' 인지. 확인 자체를 못 하면 False."""
    rc, _out = (run or _run_signing_tool)(codesign_argv(app_path))
    if rc != 0:
        print("[update] rejected: signature missing, invalid, or not ours")
        return False
    return True


def _signed_by_us(app_path, run=None):
    """Gatekeeper 평가 + '누구 것인지'까지. 확인 자체를 못 하면 False.

    rc 만 보면 아무 의미가 없다. spctl 은 공증된 남의 앱도 통과시킨다 —
    Chrome 이 rc=0 에 source=Notarized Developer ID 까지 그대로 나온다. 그래서
    origin 의 Team ID 를 확인해야 하고, 그게 이 검사의 유일한 판별 신호다.

    그 신호는 origin '줄'에서 읽어야 한다. 예전에는 출력 전체에 대고
    `TEAM_ID not in out` 를 봤는데, spctl 출력의 첫 줄은 평가한 '경로'다:

        /Applications/ClaudePet.app: accepted
        source=Notarized Developer ID
        origin=Developer ID Application: Yeongyu Yang (RXGNVSLYF5)

    즉 판별 신호를 파일 이름이 대신 낼 수 있었다 — 번들을
    `/tmp/RXGNVSLYF5.app` 로 옮겨 두면 origin 이 무엇이든 통과한다. 우리가
    검사 대상의 경로를 정하는 지금 갈래로는 닿지 않지만, 검사의 유일한
    판별 신호가 검사 대상의 이름으로 만들어질 수 있다는 것 자체가 결함이고,
    닿지 않는다는 사실은 이 함수가 아니라 호출부가 들고 있는 성질이다.

    괄호까지 요구하지는 않는다. 실측한 origin 은 `... (RXGNVSLYF5)` 이지만,
    그 표기를 Apple 이 약속한 적은 없다 — 약속받지 않은 모양에 하드 리젝을
    걸면 표기가 바뀌는 날 모든 클라이언트의 업데이트가 영구히 막힌다(위
    CODESIGN_REQUIREMENT 의 '=' 와 같은 사고다). 줄을 좁히는 것만으로 파일
    이름이 신호를 대신하는 길은 이미 사라진다.
    """
    rc, out = (run or _run_signing_tool)(spctl_argv(app_path))
    if rc != 0:
        print("[update] rejected: not notarized / rejected by Gatekeeper")
        return False
    origin = None
    for line in str(out).splitlines():
        line = line.strip()
        if line.startswith("origin="):
            origin = line[len("origin="):]
            break
    if origin is None:
        # -vv 를 줬는데도 origin 이 없다는 건 '누가 서명했는지 모른다'는 뜻이다.
        print("[update] rejected: Gatekeeper reported no origin")
        return False
    if TEAM_ID not in origin:
        print("[update] rejected: Gatekeeper did not attribute the app to us")
        return False
    return True


def _ticket_is_stapled(app_path, run=None):
    """공증 티켓이 번들에 붙어 있는지. 확인 자체를 못 하면 False.

    공증은 됐지만 티켓이 안 붙은 번들은 네트워크가 없을 때 실행이 막힌다.
    """
    rc, out = (run or _run_signing_tool)(stapler_argv(app_path))
    if rc != 0:
        print("[update] rejected: no stapled notarization ticket")
        return False
    if "The validate action worked" not in out:
        print("[update] rejected: stapler did not confirm the ticket")
        return False
    return True


def _bundle_tree_is_contained(root):
    """번들 트리의 모든 경로가 번들 안에 머무는지.

    심볼릭 링크 자체를 금지하지는 않는다. py2app 번들에는 Python.framework 의
    링크(Versions/Current 등)가 반드시 들어 있어서, 전면 금지는 우리가 내보내는
    배포본을 전부 거부한다 — 위 '=' 빠진 요구사항과 똑같이, 합성 테스트는 다
    통과하면서 업데이트만 영구히 죽는 모양이다. 금지하는 건 '밖으로 나가는'
    링크다: 절대경로 대상, 그리고 번들 밖으로 풀리는 대상.

    **하드링크는 이 검사가 볼 수 없다 — 원리상 그렇다.** 하드링크는 같은
    아이노드에 붙은 또 하나의 '이름'이지 다른 곳을 가리키는 표지가 아니라서,
    번들 안의 하드링크는 realpath 를 취해도 번들 안이다. 즉 아래 봉쇄 검사는
    통과하는데 그 파일의 내용은 번들 밖의 파일과 같은 실체다. 여기에 검사를
    더 붙여서 막을 수 있는 성질이 아니니(st_nlink>1 은 우리 배포물의 정상
    파일에도 붙을 수 있다) 막지 않고 한계로 적어 둔다.

    지금 이 한계로 들어올 길은 없다. 번들은 zip 으로만 오고 zip 포맷에는
    하드링크 멤버가 없어서, 푼 트리에 하드링크가 생길 수 없다. 그러니 이건
    '뚫려 있는 구멍'이 아니라 '전달 수단이 바뀌면 다시 봐야 하는 자리'다 —
    tar 나 ditto 아카이브처럼 하드링크를 실어 나르는 포맷을 받게 되면
    _zip_members_are_safe 자리에서 그 포맷의 링크를 막아야 하고, 이 함수가
    대신 잡아 주리라 기대하면 안 된다.
    """
    root = os.path.abspath(str(root))
    real_root = os.path.realpath(root)
    if os.path.islink(root):
        print("[update] rejected: bundle root is a symlink")
        return False
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in list(dirnames) + list(filenames):
            p = os.path.join(dirpath, name)
            if os.path.islink(p) and os.path.isabs(os.readlink(p)):
                print("[update] rejected: absolute symlink target in bundle")
                return False
            real = os.path.realpath(p)
            if real != real_root and not real.startswith(real_root + os.sep):
                print("[update] rejected: bundle path resolves outside "
                      "the bundle")
                return False
    return True


def _seed_tree_has_no_symlink(res):
    """.claude_pet 트리에는 링크가 하나도 없어야 한다.

    프레임워크 링크와 규칙이 다른 이유는 출처다. 저 링크들은 Apple 과 py2app
    이 만든 것이고 우리가 손대지 않으며 상대경로로 번들 안에 머문다. 이 트리는
    '우리 것'이고 시더가 사용자 홈으로 복사하는 원본이며, 우리가 넣은 링크는
    하나도 없다 — 그러니 여기 링크가 있다는 건 우리가 만든 게 아니라는 뜻이다.
    조상 폴더 하나만 링크여도 그 아래는 전부 평범한 파일로 보이는데 실제로는
    링크 너머 남의 파일이고, _default_bundled_pet_dir 은 isdir() 이 링크를
    따라가 True 가 되므로 그대로 시드 원본이 된다.
    """
    res = str(res)
    if not os.path.lexists(res):
        return True                    # 자산 누락은 경고지 거부가 아니다
    if os.path.islink(res):
        print("[update] rejected: bundled path is a symlink (.claude_pet)")
        return False
    for dirpath, dirnames, filenames in os.walk(res, followlinks=False):
        for name in list(dirnames) + list(filenames):
            p = os.path.join(dirpath, name)
            if os.path.islink(p):
                rel = os.path.relpath(p, res)
                print(f"[update] rejected: bundled path is a symlink ({rel})")
                return False
    return True


def validate_update_app(app_path, expect_version, run=None, expect_arches=None):
    """받은 .app 이 '우리 앱의 그 버전'이 맞는지 교체 전에 확인한다.

    확인하는 것: 번들 ID · 버전 · 트리 봉쇄 · 코드 서명 · 공증 · 티켓.
    하나라도 어긋나면 False — 엉뚱하거나 손상된 번들로 멀쩡한 설치본을
    갈아치우지 않기 위해서다. 동봉 펫 자산이 '빠진' 것만은 진단으로 넘긴다:
    그것 때문에 업데이트를 막으면 옛 클라이언트가 영영 갇힌다(빌드 쪽에서
    막을 수 있는 실수라 여기서 하드 게이트를 걸 이유가 없다).

    run 은 서명 도구를 부르는 자리(argv → (rc, 출력)). 기본은 실제 실행이고,
    테스트가 여기에 끼어들어 '우리가 만든 argv' 를 그대로 확인할 수 있다.
    도구를 못 돌리면 rc 가 None 이라 전부 거부로 떨어진다(fail-closed).
    """
    app_path = str(app_path)
    # 기대 버전 없이는 통과시키지 않는다. 예전에는 None 이면 버전 검사를
    # 통째로 건너뛰었는데, 그건 '아무 버전이나 좋다'와 같은 말이라 태그와
    # 다른 번들이 그대로 설치될 수 있었다.
    if not str(expect_version or "").strip():
        print("[update] rejected: no expected version to verify against")
        return False
    try:
        with open(os.path.join(app_path, "Contents", "Info.plist"), "rb") as f:
            plist = plistlib.load(f)
    except Exception as e:
        print(f"[update] unreadable Info.plist: {type(e).__name__}")
        return False
    if plist.get("CFBundleIdentifier") != BUNDLE_ID:
        print("[update] rejected: bundle identifier does not match")
        return False
    # 두 버전 키가 모두 태그와 같아야 한다. 하나만 봐 주면 한쪽이 낡은 번들이
    # 통과하고, 업데이터는 그 낡은 값을 기준으로 다시 업데이트를 권한다.
    want = str(expect_version).strip()
    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        if str(plist.get(key) or "") != want:
            print(f"[update] rejected: {key} does not match the release tag")
            return False
    # 서명 검사보다 먼저, 트리가 번들 밖으로 새는지부터 본다 — 프로세스를
    # 띄우지 않고 끝나고, 매니페스트에 없는 경로의 링크는 여기서만 걸린다.
    if not _bundle_tree_is_contained(app_path):
        return False
    if not _identity_paths_are_regular_files(app_path):
        return False
    # 이름이 universal 이어도 슬라이스가 없으면 이 기기에서 안 돈다.
    #
    # 호출부가 아무 말이 없으면 '이 기기'를 기준으로 삼는다. 예전에는 그냥
    # 검사를 건너뛰었는데, 그건 '아키텍처는 무엇이든 좋다'와 같은 말이라
    # 여기서 이 기기에서 뜨지도 못할 번들이 그대로 통과했다. 기준을 기기에
    # 묻는 것은 번들에 묻는 것과 다르다 — 번들에 물으면 어떤 번들이든 자기
    # 대답으로 통과한다.
    if expect_arches is None:
        import platform
        expect_arches = (platform.machine(),)
    if not _has_required_arches(app_path, expect_arches, run):
        return False
    # '유효하게 서명됨'만으로는 부족하다 — Developer ID 는 누구나 받을 수 있으니
    # 서명자가 우리인지(Team ID)까지 못 박는다. 그래서 -R 로 요구사항을 준다.
    if not _signature_is_ours(app_path, run):
        return False
    # 서명이 우리 것이어도 공증을 안 받았을 수 있다 → Gatekeeper 평가까지.
    if not _signed_by_us(app_path, run):
        return False
    # 공증됐어도 티켓이 안 붙어 있으면 오프라인에서 실행이 막힌다.
    if not _ticket_is_stapled(app_path, run):
        return False
    # 동봉 자산 점검. 빠진 것과 심볼릭 링크는 무게가 다르다:
    #   · 빠진 파일 → 그 펫만 안 깔릴 뿐이므로 진단만 남기고 통과. 이것 때문에
    #     업데이트 자체를 막으면 사용자는 옛 버전에 갇힌다.
    #   · 심볼릭 링크 → 서명된 배포물에는 있을 이유가 없다. 링크는 번들 밖
    #     아무 곳이나 가리킬 수 있으니 거부한다.
    res = os.path.join(app_path, "Contents", "Resources", ".claude_pet")
    # 잎(파일)만 보면 안 된다. 조상 폴더 하나가 링크면 그 아래 파일은 전부
    # 평범한 정규 파일로 보이지만, 실제로는 링크 너머의 남의 파일이다. 매니페스트
    # 경로만 훑는 것도 부족하다 — 목록에 없는 자리의 링크가 그대로 통과한다.
    # 그래서 이 트리는 통째로 훑고, 링크가 하나라도 있으면 거부한다.
    if not _seed_tree_has_no_symlink(res):
        return False
    members = [(name, os.path.join(res, name)) for name in BUNDLED_PET_README]
    members += [(f"pets/{pet}/{name}", os.path.join(res, "pets", pet, name))
                for pet in BUNDLED_PET_IDS for name in BUNDLED_PET_FILES]
    missing = [rel for rel, p in members if not os.path.isfile(p)]
    if missing:
        print(f"[update] bundled pet assets incomplete ({len(missing)} paths); "
              "seeding will skip them")
    return True


def poll_github_update(state, now=None):
    """새 버전 확인 1회 → status. 쿨다운/보류 상태를 규칙대로 갱신한다.

    · status != 'failed' 일 때만 재확인 쿨다운(_upd_cache["t"])을 찍는다.
      (예전에는 확인 '전에' 찍어서, 한 번 실패하면 6시간 내내 재확인이 막혔다)
    · status == 'update' 일 때만 state["update"] 에 (버전, zip_url) 을 넣는다.
    """
    status, tag, url = check_github_update()
    if status != "failed":
        _upd_cache["t"] = time.time() if now is None else now
    if status == "update":
        # (버전, zip_url) 그대로 둔다. 고른 자산의 이름·아키텍처는
        # _upd_cache["choice"] 가 들고 있고 install_github_update 가 거기서
        # 읽는다 — 이 튜플의 모양은 다른 곳에서 기대하는 계약이라 늘리지 않는다.
        state["update"] = (tag, url)
    return status


def _zip_members_are_safe(zip_path):
    """풀기 '전에' 아카이브를 본다. 밖으로 나가는 게 하나라도 있으면 거부.

    푼 뒤에 검사하면 늦다 — 번들 밖으로 나가는 멤버는 임시 폴더 바깥에 이미
    쓰인 뒤이고, 우리가 훑는 건 풀린 .app 안쪽뿐이라 영영 안 보인다. 즉 풀고
    나서 트리가 깨끗한 것은 '탈출이 없었다'는 증거가 아니라 탈출의 '결과'다.

    이름만 보는 것으로는 부족하다. 심볼릭 링크 멤버는 이름이 아니라 '내용'이
    가리키는 곳으로 나간다: 링크 하나를 멀쩡한 상대 이름으로 넣고, 그 아래
    경로에 멤버를 하나 더 넣으면, 이름에는 '..' 도 절대경로도 없는데 풀 때
    링크를 '통과해' 바깥에 쓰인다. 그래서 링크는 이름이 아니라 external_attr
    의 모드로 찾아내고, 대상까지 읽어 본다.

    py2app 번들이 정상적으로 담고 있는 프레임워크 링크(상대경로, 번들 안)는
    통과시킨다 — 그걸 막으면 우리 배포본이 전부 거부되어 업데이트가 영구히
    죽는다.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = zf.infolist()
            links = {}
            for info in infos:
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    links[info.filename.rstrip("/")] = zf.read(info).decode(
                        "utf-8", "replace")
    except Exception as e:
        print(f"[update] rejected: unreadable archive ({type(e).__name__})")
        return False
    names = [i.filename for i in infos]
    for name in names:
        if name.startswith("/") or os.path.isabs(name):
            print("[update] rejected: archive member is an absolute path")
            return False
        if ".." in name.replace("\\", "/").split("/"):
            print("[update] rejected: archive member escapes the archive root")
            return False
    for link, target in links.items():
        if target.startswith("/") or os.path.isabs(target):
            print("[update] rejected: archive symlink points to an absolute "
                  "path")
            return False
        # 링크가 놓일 자리에서 대상을 풀어 본다. 아카이브 루트 밖으로 나가면
        # 그 링크를 통해 무엇이든 바깥에 쓸 수 있다.
        landing = os.path.normpath(
            os.path.join(os.path.dirname(link), target))
        if landing == ".." or landing.startswith("../"):
            print("[update] rejected: archive symlink escapes the archive root")
            return False
    # 링크를 '통과하는' 멤버. 대상이 안쪽이어도, 링크 밑에 쓰는 것은 우리가
    # 검사한 트리가 아닌 곳에 쓰는 것이다 — 안전을 증명할 수 없으면 거부한다.
    for name in names:
        clean = name.rstrip("/")
        for link in links:
            if clean != link and clean.startswith(link + "/"):
                print("[update] rejected: archive member is written through "
                      "a symlink")
                return False
    return True


def _download_update_zip(zip_url, dest):
    """업데이트 zip 을 받는다. 반드시 '끝난다' — 성공이든 예외든.

    urllib.request.urlretrieve 를 쓰지 않는 이유는 하나다: 그 함수에는 타임아웃을
    줄 자리가 없다. 이 파일의 다른 모든 HTTPS 호출은 timeout=10 을 주는데
    (fetch_api_cost, _fetch_oauth_usage, check_github_update) 여기만 없었고,
    socket.setdefaulttimeout 도 어디에도 없어서 이 한 줄만 None 을 물려받았다.

    그게 왜 보통의 멈춤보다 나쁜지는 위 UPDATE_DOWNLOAD_* 에 적어 두었다 —
    이 호출은 업데이트 잠금 안에 있다.

    **실패는 잠금을 놓는다. 그건 의도한 것이다.** 예외는 호출부의 finally 까지
    올라가 lock_fd 를 닫으므로, 다음 시도는 정상적으로 잠금을 다시 잡는다.
    받다 실패한 것은 되돌릴 상태를 아무것도 남기지 않으니(임시 폴더도 같은
    finally 가 지운다) 재시도를 막을 이유가 없다. 여기서 잠금을 붙들어 두는
    설계는 '한 번 끊긴 회선'을 '영구 고장'으로 바꾸는 것뿐이다.
    """
    deadline = time.monotonic() + UPDATE_DOWNLOAD_DEADLINE
    total = 0
    with urllib.request.urlopen(
            zip_url, timeout=UPDATE_DOWNLOAD_TIMEOUT) as r, \
            open(dest, "wb") as f:
        while True:
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > UPDATE_DOWNLOAD_MAX:
                raise OSError("update download exceeded the size limit")
            if time.monotonic() > deadline:
                # 소켓 타임아웃은 매 읽기가 제때 오면 영원히 안 걸린다.
                # 끝나는 것을 보장하는 건 이 검사다.
                raise OSError("update download exceeded the time limit")
            f.write(chunk)
    return total


def _empty_dir_at(dfd):
    """열려 있는 디렉터리 fd '아래'를 비운다(그 디렉터리 자신은 남긴다).

    모든 동작이 fd 기준(dir_fd=)이라 경로 문자열을 다시 해석하지 않는다.
    중간에 조상 이름이 바뀌어도 우리가 지우는 것은 계속 '열어 둔 그 객체'
    아래다. 하위 디렉터리도 O_NOFOLLOW 로 열어 들어가므로 링크를 따라
    번들 밖으로 나가지 않는다.

    **그 보장은 조상에만 걸려 있었지 자식에는 걸려 있지 않았다.** 여기서 자식을
    고르는 것은 listdir 이 준 '이름'이고, lstat 으로 종류를 본 뒤 다시 그 이름으로
    열거나 지웠다 — 그 사이에 자식 이름이 바뀌면 남의 트리를 지우거나 그 안으로
    내려간다. 그래서 lstat 이 준 신원을 자식마다 들고, 실제 동작 직전에 대조한다:
    디렉터리는 열어서 fstat 으로(이쪽은 핸들이라 확실하다), 파일은 열어서
    fstat 으로 확인한 뒤 지운다. 어긋나면 그 자식은 통째로 건너뛴다.
    """
    for name in os.listdir(dfd):
        try:
            st = os.lstat(name, dir_fd=dfd)
        except OSError:
            continue
        ident = _ident(st)
        if stat.S_ISDIR(st.st_mode):
            sub = _open_dir_ident_at(dfd, name, ident)
            if sub is None:
                continue        # 링크·다른 객체로 바뀌었거나 사라졌다
            try:
                _empty_dir_at(sub)
            finally:
                os.close(sub)
            if not _is_ident_at(dfd, name, ident):
                continue
            try:
                os.rmdir(name, dir_fd=dfd)
            except OSError:
                pass
        elif stat.S_ISREG(st.st_mode):
            if not _unlink_ident_at(dfd, name, ident):
                continue
        else:
            # 심볼릭 링크·FIFO·소켓·장치 노드는 열어서 신원을 볼 수 없다
            # (O_NOFOLLOW 가 링크를 거절하고, FIFO 는 열다가 매달릴 수 있다).
            # 핸들이 없으면 lstat 을 한 번 더 해 대조하는 것이 남은 최선이고,
            # 그것으로 닫히는 것이 아니라 좁아질 뿐이라는 것도 그대로다.
            # 이 갈래에서 사라질 수 있는 최악은 남의 링크·특수 파일 하나다.
            try:
                if _ident(os.lstat(name, dir_fd=dfd)) != ident:
                    continue
                os.unlink(name, dir_fd=dfd)
            except OSError:
                pass


def _discard_owned_dir(path, expect_ino):
    """(st_dev, st_ino) 가 expect_ino 인 '그 디렉터리'만 지운다 → 지웠으면 True.

    lstat 으로 확인한 뒤 shutil.rmtree(path) 하는 방식과 다르다. 그 방식은
    확인한 '이름'을 다시 해석하므로, 확인과 삭제 사이에 그 이름이 남의 것으로
    바뀌면 남의 트리를 통째로 지운다. lstat 을 한 번 더 하는 것으로는 창이
    좁아질 뿐 닫히지 않는다 — 매번 다시 여는 것은 매번 다시 해석하는 것이다.

    그래서 이름이 아니라 '열어 둔 객체'를 지운다: 부모를 O_NOFOLLOW 로 열고,
    그 부모 fd 기준으로 대상을 O_NOFOLLOW 로 열고, fstat 으로 신원을 확인한 뒤,
    그 fd 아래를 통째로 비운다. 확인한 fd 와 비우는 fd 가 같은 것이라 그 사이에
    끼어들 이름이 없다.

    마지막 rmdir 하나만 이름을 쓴다. 그건 피할 수 없다 — POSIX 에는 '이
    아이노드를 지워라'가 없다. 대신 그 시점의 대상은 '비어 있는 디렉터리'이고
    rmdir 은 비어 있을 때만 성공하므로, 최악의 경우에도 사라지는 것은 남의 빈
    디렉터리 하나지 남의 자료가 아니다. 이 남은 창을 없애려면 커널이 주지 않는
    연산이 필요하다.
    """
    path = str(path)
    parent, name = os.path.dirname(path) or "/", os.path.basename(path)
    if not name:
        return False
    try:
        pfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return False
    try:
        # 우리가 만든 그것이 아니면 남긴다 — 폴더 하나가 남는 것이 남의 자료를
        # 지우는 것보다 낫다. 확인과 사용이 같은 fd 라 그 사이에 끼어들 이름이
        # 없다.
        fd = _open_dir_ident_at(pfd, name, expect_ino)
        if fd is None:
            return False
        try:
            _empty_dir_at(fd)
        finally:
            os.close(fd)
        # rmdir 직전에 한 번 더 대조한다. 위에서 적었듯 이 한 걸음의 창은 닫히지
        # 않지만, 좁히지 않을 이유도 없다.
        if not _is_ident_at(pfd, name, expect_ino):
            return False
        try:
            os.rmdir(name, dir_fd=pfd)
        except OSError:
            return False
        return True
    finally:
        os.close(pfd)


def _discard_owned_path(path):
    """지금 그 자리에 있는 '그 객체'만 지운다 → 지웠으면 True.

    종류를 가리지 않는다(파일·폴더·링크·특수 파일). lstat 으로 종류와 신원을
    한 번에 읽고, 실제 삭제 직전에 그 신원과 대조한다 — 이름으로 확인하고
    이름으로 지우면 그 사이에 바뀐 것을 지운다.

    갈래마다 닿을 수 있는 보장이 다르고, 그 차이가 이 함수의 전부다:

    · 폴더  → _discard_owned_dir. 부모를 O_NOFOLLOW 로 열고, 대상을 열어
      fstat 으로 확인한 뒤 '그 fd 아래를' 비운다.
    · 정규 파일 → _unlink_ident_at. 열어서 신원을 확인한 뒤 이름으로 지운다.
    · 링크·FIFO·소켓·장치 노드 → 열어서 신원을 볼 수 없다(O_NOFOLLOW 가 링크를
      거절하고, FIFO 는 열다가 매달릴 수 있다). lstat 을 한 번 더 해 대조하는
      것이 남은 최선이고, 창이 닫히는 게 아니라 좁아질 뿐이라는 것도 그대로다.
      **이 갈래를 빼면 안 된다** — 사용자가 ~/.claude_pet.json 을 다른 곳으로
      심볼릭 링크해 두었을 때 완전 삭제가 그 링크를 남긴다. 지우는 것은 링크
      하나지 그 너머가 아니다.
    """
    path = str(path)
    parent, name = os.path.dirname(path) or "/", os.path.basename(path)
    if not name:
        return False
    try:
        st = os.lstat(path)
    except OSError:
        return False
    ident = _ident(st)
    if stat.S_ISDIR(st.st_mode):
        return _discard_owned_dir(path, ident)
    try:
        pfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return False
    try:
        if stat.S_ISREG(st.st_mode):
            return _unlink_ident_at(pfd, name, ident)
        try:
            if _ident(os.lstat(name, dir_fd=pfd)) != ident:
                return False
            os.unlink(name, dir_fd=pfd)
            return True
        except OSError:
            return False
    finally:
        os.close(pfd)


def install_github_update(zip_url, app_path=None, expect_version=None,
                          expect_arches=None, expect_asset=None):
    """새 zip 다운로드 → 현재 앱 번들 교체 → 재실행 예약. 성공 시 True(=종료해야 함).

    expect_version(릴리즈 태그)은 필수다. 비어 있으면 아무것도 받지 않고
    False — 확인할 기준이 없는 설치는 '아무 번들이나 좋다'와 같은 말이다.

    expect_asset / expect_arches 는 '자산을 고른 그 거래'가 정한 값이고, 여기서
    다시 만들어 내지 않는다. 아래로 내려가며 다시 유도한 값은 결국 번들 자신이
    대답할 수 있는 값이 되고, 번들이 대답할 수 있는 검사는 언제나 통과한다.
    check_github_update() 가 고른 근거를 _upd_cache["choice"] 에 남기므로,
    호출부가 넘겨주지 않았을 때만 그 기록에서 읽는다 — 기록에서 읽는 것은
    '고른 그 거래'를 그대로 쓰는 것이지 다시 유도하는 것이 아니다.
    """
    # 검사 기준이 없으면 내려받기도 전에 멈춘다.
    if not str(expect_version or "").strip():
        print("[update] refused: no expected version to verify against")
        return False
    choice = _upd_cache.get("choice") or {}
    if expect_asset is None:
        expect_asset = choice.get("asset")
    if expect_arches is None and choice.get("arch"):
        expect_arches = (choice["arch"],)
    # 이름과 아키텍처가 서로 맞는지 여기서 한 번 더 못 박는다.
    #
    # 자산은 '이름'으로 고르고, 설치는 '아키텍처'로 검사한다. 그 둘은
    # UPDATE_ASSET_NAMES 라는 하나의 표에서 나왔는데, 고른 뒤로는 따로 여행한다
    # — 중간 어디선가 한쪽만 바뀌어도 알아채는 곳이 없었다. 고를 때 쓴 그 표에
    # 다시 비춰 보면, 이름과 아키텍처가 어긋난 조합은 여기서 멈춘다.
    #
    # URL 의 마지막 경로 조각을 이름과 비교하는 방법은 쓰지 않는다. 그건
    # GitHub 이 자산 URL 을 어떻게 짓는지에 기대는 것이라 우리 불변식이 아니다.
    if expect_asset and expect_arches:
        for arch in expect_arches:
            allowed = UPDATE_ASSET_NAMES.get(str(arch))
            if not allowed or str(expect_asset).strip().lower() not in allowed:
                print("[update] refused: the selected asset name does not "
                      "match the architecture it was selected for")
                return False
    # 서명 검사가 뒤에 있어도 평문 HTTP 는 받지 않는다. 안 받는 게 가장 싸다.
    if urllib.parse.urlparse(str(zip_url)).scheme != "https":
        print("[update] refused: update url is not https")
        return False
    if app_path is None:
        try:
            from Foundation import NSBundle
            app_path = str(NSBundle.mainBundle().bundlePath())
        except Exception:
            return False
    if not str(app_path).endswith(".app"):
        return False
    # 거래를 여는 첫 동작이 잠금이다. 내려받기까지 덮는 것은 의도한 것이다 —
    # 잠금이 스테이징 직전에야 걸리면, 그 전까지 두 업데이터가 나란히 받아
    # 놓고 한쪽만 통과하는 낭비가 생기고, 무엇보다 '거래의 시작'과 '직렬화의
    # 시작'이 어긋나 어디까지가 보호 구간인지 말할 수 없게 된다.
    lock_fd = _acquire_update_lock(app_path)
    if lock_fd is None:
        return False               # 다른 업데이터가 진행 중이거나 잠금이 수상하다
    # mkdtemp 는 반드시 try '안'이다.
    #
    # 밖에 두면 여기서 OSError 가 났을 때(TMPDIR 이 사라졌거나 디스크가 찼거나)
    # 아래 finally 가 아예 실행되지 않아 잠금 fd 가 이 프로세스에 그대로 남는다.
    # 그러면 flock 은 살아 있는데 그걸 들고 아무 일도 하지 않는 상태가 되어,
    # 이 프로세스가 사는 동안 이후의 모든 업데이트가 잠금을 못 잡고 조용히
    # 실패한다 — 잠금이 있는 채로 잠금이 하는 일만 없어지는, 가장 알아채기
    # 어려운 형태의 고장이다. 예외를 던지고 나가는 것도 실패지만, 다음 주기에
    # 다시 시도할 수 있는 실패와 다시는 못 하는 실패는 다르다.
    #
    # d 를 먼저 None 으로 두는 것도 같은 이유다. mkdtemp 가 실패하면 finally 가
    # 아직 만들어지지 않은 이름을 지우려 들면 안 된다.
    d = None
    d_ino = None
    ok = False
    try:
        d = tempfile.mkdtemp()
        # 만들자마자 신원을 잡는다. 아래 finally 는 이 값으로만 지운다 —
        # 신원을 나중에 다시 구하면 그 사이에 바뀐 것을 잡는다.
        d_ino = _ident(os.lstat(d))
        zp = os.path.join(d, "u.zip")
        _download_update_zip(zip_url, zp)
        if not _zip_members_are_safe(zp):
            return False               # 푸는 순간 밖에 쓰이므로 풀기 전에 막는다
        subprocess.run(["/usr/bin/ditto", "-x", "-k", zp, d], check=True)
        newapp = os.path.join(d, "ClaudePet.app")
        if not os.path.isdir(newapp):
            return False
        # 거래도 기록도 아무 말이 없을 때만 이 기기에 묻는다. 번들에는 절대
        # 묻지 않는다 — 번들에게 "너는 무슨 아키텍처여야 하니" 라고 물으면
        # 어떤 번들이든 자기 대답으로 통과한다.
        if expect_arches is None:
            import platform
            expect_arches = (platform.machine(),)
        if not validate_update_app(newapp, expect_version,
                                   expect_arches=expect_arches):
            return False               # 신원/버전/서명/아키텍처 불일치 → 그대로
        # 여기까지는 '푼 것'을 검사했을 뿐이다. 교체되는 건 그게 아니라 설치
        # 경로 옆에 만든 복사본이므로, 그 복사를 여기서 직접 만들고 '그것을'
        # 다시 통째로 검사한다. 검사한 트리와 설치되는 트리가 같아야 한다 —
        # 검사 뒤에 또 한 번 복사하면 그 사이의 변조는 아무도 못 본다.
        #
        # 스테이지 이름을 '차지해서' 얻는다. 예전에는 이름을 짓자마자
        # shutil.rmtree(stage, ignore_errors=True) 를 돌렸는데, 그건 그 이름에
        # 이미 무언가 있으면 통째로 지운다는 뜻이다. 이름에는 pid 가 들어가므로
        # pid 가 재사용되거나 앞선 실행이 남긴 폴더가 있으면 실제로 겹치고,
        # 그때 지워지는 것이 사용자의 것이 아니라는 보장은 어디에도 없다.
        # 겹친 이름은 지우지 않는다 — 비켜서 다른 이름을 고른다.
        #
        # 이름은 '.app' 으로 끝나야 한다. 번들 검사와 macOS 자신이 그 접미사로
        # 번들 여부를 판단하는 자리가 있어서, 접미사가 없으면 검사 대상이 평범한
        # 폴더로 취급되는 갈래가 생긴다.
        parent = os.path.dirname(app_path) or "/"
        stage = None
        stage_ino = None
        for _ in range(8):
            candidate = os.path.join(
                parent,
                f".claudepet-new-{os.getpid()}-{os.urandom(4).hex()}.app")
            try:
                os.mkdir(candidate, 0o700)
            except OSError:
                continue        # 이미 누가 쓰는 이름 — 건드리지 않고 넘어간다
            # 여기서 rmdir 하지 않는다. 한때 '차지했다가 곧바로 비우고' ditto 에게
            # 없는 경로를 넘겼는데, 그러면 비운 순간부터 ditto 가 다시 만들 때까지
            # 이름이 무주공산이 되어 차지한 의미가 사라진다 — 확인과 사용이 갈라진
            # check-then-use 다. 차지한 그 디렉터리를 그대로 쓴다. 진짜 ditto 는
            # 이미 있는 대상 디렉터리에 내용을 부어 넣는다.
            #
            # 차지한 '그것'이 정말 우리가 만든 것인지 여기서 못 박는다. 잠금 fd 에
            # 쓴 것과 같은 규율이다: 만든 직후에 lstat 으로 확인하고 아이노드를
            # 적어 둔다. 아래 정리는 그 아이노드일 때만 지우므로, 중간에 이름이
            # 남의 것으로 바뀌어 있으면 우리는 아무것도 지우지 않는다.
            #
            # **이 검사는 '경합 창을 좁히는 장치'이지 검증이 아니다.** 바로 위
            # os.mkdir 이 성공했다는 건 이 순간 이 이름이 우리 것이라는 뜻이고,
            # 그러니 정상 경로에서 이 lstat 은 언제나 통과한다 — 통과시키려고
            # 있는 게 아니라, mkdir 과 lstat 사이에 이름이 바뀌는 그 좁은 창을
            # 닫으려고 있다. 그러니 이 갈래를 '거짓을 넣으면 거부되는지'로
            # 시험할 수 없고, 시험이 안 된다고 해서 죽은 코드도 아니다. 값은
            # 여기서 나오지 않고 아래 stage_ino 대조에서 나온다: 우리가 만든
            # 아이노드가 아니면 정리가 아무것도 지우지 않는다.
            #
            # 실패하면 만들어 둔 candidate 를 지우지 않고 그대로 나간다.
            # 여기까지 왔다는 건 '그 이름에 있는 것이 우리 것이라고 말할 수
            # 없다'는 뜻이고, 그럴 때 지우는 것이 바로 이 검사가 막으려는
            # 사고다. 빈 폴더 하나가 남는 편이 낫다.
            try:
                st = os.lstat(candidate)
                if (not stat.S_ISDIR(st.st_mode)
                        or st.st_uid != os.geteuid()
                        or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
                    print("[update] refused: the staging reservation is not a "
                          "private directory we own")
                    return False
                stage_ino = (st.st_dev, st.st_ino)
            except OSError:
                return False
            stage = candidate
            break
        if stage is None:
            # 여기까지 왔다면 남의 것을 지우거나 이번 업데이트를 거르거나
            # 둘 중 하나다. 거른다 — 다음 주기에 다시 시도한다.
            print("[update] refused: could not claim a staging name")
            return False
        staged_ok = False
        try:
            # ditto 는 반드시 이 try '안'이다.
            #
            # 밖에 두면 복사가 도중에 실패했을 때(디스크가 차거나 원본이
            # 사라지거나) 아래 finally 가 실행되지 않아, 우리가 예약해서 우리가
            # 절반쯤 채운 스테이지가 설치 폴더 옆에 그대로 남는다. 바깥 finally
            # 는 임시 폴더(d)만 치우지 이 자리는 모른다. mkdtemp 를 try 안으로
            # 옮긴 것과 같은 결함이다: 오래 남는 것을 만드는 줄이, 그것을
            # 치우는 블록 밖에 있었다.
            subprocess.run(["/usr/bin/ditto", newapp, stage], check=True)
            if not validate_update_app(stage, expect_version,
                                       expect_arches=expect_arches):
                print("[update] rejected: the staged copy does not match what "
                      "was validated")
                return False
            # 잠긴 fd 를 그대로 물려준다. pass_fds 는 자식에서 '같은 번호'로
            # 열려 있게 해 주므로, 스크립트가 닫아야 할 번호를 알 수 있다.
            # 이 시점부터 잠금의 주인은 저 셸이다 — 여기서 닫으면 안 된다.
            subprocess.Popen(
                ["/bin/sh", "-c",
                 _update_replace_script(
                     app_path, newapp, d, staged=stage, lock_fd=lock_fd,
                     # 우리가 예약한 그 디렉터리의 신원. 셸의 정리는 이 값과
                     # 맞을 때만 지운다 — 이름만 보고 지우지 않는다.
                     stage_id="%d,%d" % stage_ino,
                     # 셸이 만질 나머지 두 객체의 신원도 여기서 정해서 넘긴다.
                     # 스크립트 안에서 stat 으로 유도하게 두면 '검증한 그것'이
                     # 아니라 '그때 그 이름에 있던 것'에 묶인다 — 넘기지 않으면
                     # _update_replace_script 가 거부한다(폴백 없음).
                     #
                     #  · app_id — 잠금을 잡고 번들을 검증한 이 거래가 본 설치본.
                     #    잠금은 여기서 셸로 그대로 넘어가므로, 이 값과 셸이
                     #    교환 직전에 읽는 값 사이에 우리 쪽 업데이터는 끼어들 수
                     #    없다. 남는 것은 잠금 밖의 침입뿐이고 그게 대조의 대상이다.
                     #  · work_id — 방금 mkdtemp 로 만든 그 폴더. 여기서 셸의
                     #    정리까지 이 이름을 다시 만드는 코드는 없으므로, 이 값은
                     #    셸이 나중에 지우는 바로 그 객체를 가리킨다.
                     app_id=_path_ident_str(app_path),
                     work_id=_path_ident_str(d))],
                pass_fds=(lock_fd,))
            staged_ok = True
            ok = True
            return True
        finally:
            # 스테이지를 넘기지 못했으면 여기서 치운다. 넘겼으면 셸의 것이다.
            # ditto 가 실패해 절반만 채워졌을 때도 여기로 온다.
            #
            # 한때 여기가 `lstat 으로 확인 → shutil.rmtree(stage)` 였다. 확인은
            # 옳았지만 삭제가 '확인한 이름'을 다시 해석했고, 그 사이에 그 이름이
            # 남의 것으로 바뀌면 남의 트리를 통째로 지웠다 — 확인을 한 번 더
            # 하는 것으로는 창이 좁아질 뿐 닫히지 않는다. _discard_owned_dir 은
            # 확인한 fd '그것'을 비우므로 확인과 삭제가 갈라지지 않는다.
            if not staged_ok and stage is not None and stage_ino is not None:
                _discard_owned_dir(stage, stage_ino)
    except Exception:
        return False
    finally:
        # 성공하면 위 셸이 다 쓰고 나서 지운다(여기서 지우면 원본이 사라진다).
        # 다운로드/해제/실행 어디서 실패했든 임시 폴더는 여기서 정리한다.
        # 위 try 안의 return 은 전부 이 자리를 지나므로, 넘기기 전에 빠져나가는
        # 갈래가 임시 폴더를 남기는 일은 없다.
        #
        # 이름이 아니라 mkdtemp 직후에 잡아 둔 신원으로 지운다. 셸 쪽 $WORK 를
        # 넘겨준 신원(WORKID)으로 지우는 것과 같은 규칙이고 이유도 같다 —
        # 이름으로 확인하고 이름으로 지우면 그 사이에 바뀐 것을 지운다.
        #
        # finally 안이므로 여기서는 무엇도 던지면 안 된다. _discard_owned_dir 은
        # 실패를 False 로 돌려주지만, 그 안의 os.open/os.close 가 예상 밖의
        # 예외를 낼 여지까지 여기서 삼킨다. 신원을 잡지 못했으면(d_ino 가 None)
        # 지우지 않는다 — 남는 것은 임시 폴더 하나이고, 이름만 보고 지우는 것보다
        # 낫다.
        if d is not None and d_ino is not None and not ok:
            try:
                _discard_owned_dir(d, d_ino)
            except Exception:
                pass
        # 넘겼든 못 넘겼든 '우리 쪽 사본'은 반드시 닫는다.
        #
        # pass_fds 는 자식에게 같은 열림을 가리키는 별도의 디스크립터를 준다.
        # flock 은 그 열림을 가리키는 '마지막' 디스크립터가 닫힐 때 풀리므로,
        # 부모가 자기 사본을 들고 있으면 자식이 죽어도 잠금이 풀리지 않는다 —
        # 자식 쪽에서 고친 fd 상속 결함과 정확히 같은 것이 부모 쪽에 남는 꼴이다.
        # 넘긴 뒤 잠금의 주인은 자식 하나뿐이어야 한다.
        try:
            os.close(lock_fd)
        except OSError:
            pass


# ─────────────────── 클린 삭제(완전 제거) ───────────────────
# 지우는 건 "ClaudePet이 만든 것"뿐이다. 절대 건드리지 않는 것:
#   ~/.claude/            Claude Code 본체의 설정·자격증명 (이름이 비슷하지만 남의 것)
#   키체인 "Claude Code-credentials"  ClaudePet은 읽기만 한다. 지우면 사용자가
#                                     Claude Code에서 로그아웃돼 버린다.
# ~/.claude_pet.json 과 ~/.claude/ 는 완전히 다른 경로다. 혼동 금지.
UNINSTALL_PATHS = (
    CONFIG_PATH,                                                    # ~/.claude_pet.json
    CONFIG_PATH + ".lock",       # 설정 저장 잠금 파일 (merge_config_updates)
    "~/claudepet_debug.log",
    "~/Library/Preferences/me.yeongyu.claudepet.plist",
    "~/Library/Saved Application State/me.yeongyu.claudepet.savedState",
    # 업데이트 잠금이 사는 폴더. 경로를 여기 다시 적지 않고 상수를 쓴다 —
    # 같은 경로를 두 곳에 적어 두면 한쪽만 바뀌는 날 지워지지 않는 잔여물이
    # 생기고(_update_lock_path 의 주석이 경계하는 바로 그것), 시험이 그 상수를
    # 임시 폴더로 바꿔 끼워도 이쪽만 사용자의 진짜 홈을 가리키게 된다.
    UPDATE_LOCK_DIR,
)


def uninstall_targets():
    """실제로 존재하는 삭제 대상만 추린다(확인창 표시용 겸 삭제용)."""
    out = []
    for p in UNINSTALL_PATHS:
        p = os.path.expanduser(p)
        if os.path.lexists(p):
            out.append(p)
    return out


# 설치본 번들의 이름. 업데이트 잠금 이름이 이 basename 에서 나오므로
# (_update_lock_path), 경로를 모르는 개발 모드에서도 '설치본이 쓰는 그 잠금'을
# 이 이름으로 가리킬 수 있다. 두 곳에 따로 적으면 한쪽만 바뀌는 날 두 실행이
# 서로 다른 파일을 잠그고, 직렬화는 있는 것처럼 보이면서 없어진다.
INSTALLED_BUNDLE_NAME = "ClaudePet.app"


def app_bundle_path():
    """설치된 ClaudePet.app 번들 경로. 아니면 None.

    소스에서 직접 실행하면(개발 모드) NSBundle은 파이썬 자신의 번들
    (예: .../Resources/Python.app)을 돌려준다 — '.app으로 끝나는가'만 보면
    사용자의 파이썬 설치본을 지우는 사고가 난다. 그래서 번들 식별자까지
    확인한다. 이 검사를 통과하지 못하면 아무것도 지우지 않는다.
    """
    try:
        from Foundation import NSBundle
        b = NSBundle.mainBundle()
        p = str(b.bundlePath() or "")
        bid = str(b.bundleIdentifier() or "")
    except Exception:
        return None
    if bid != "me.yeongyu.claudepet":        # ← 가장 중요한 가드
        return None
    if not p.endswith(".app") or os.path.basename(p) != INSTALLED_BUNDLE_NAME:
        return None
    if not os.path.isdir(p) or os.path.islink(p):
        return None
    return p


# ─────────────────────── 로그인 시 자동 실행 (SMAppService) ───────────────────────
# 우클릭 메뉴의 체크 항목 하나가 전부다. 설정 파일에는 아무것도 적지 않는다 — OS 의
# 등록 상태가 유일한 진실이라, 사용자가 시스템 설정에서 끄면 여기서도 꺼진 것으로
# 보이고, 앱이 몰래 다시 켜는 일이 없다.
#
# SMAppService.status() 가 돌려주는 정수. 프레임워크 상수와 같은 값이지만 여기 다시
# 적는다 — 프레임워크가 없는 곳(macOS 12, 시험)에서도 순수 함수들은 돌아가야 한다.
SM_STATUS_NOT_REGISTERED = 0
SM_STATUS_ENABLED = 1
SM_STATUS_REQUIRES_APPROVAL = 2
SM_STATUS_NOT_FOUND = 3

# 3(NotFound) 은 설치본에서 "off" 다 — "unavailable" 이 아니다. SDK 헤더는 NotFound 를
# "An error occurred and no such service could be found" 라고 적어서 첫 구현(794c66f 에서
# 병합)은 그대로 "unavailable" 로 보냈고, 그 결과 새로 설치한 모든 사용자에게 항목이
# '(여기서는 사용 불가)' 로 비활성으로 떠서 켤 수 없었다 — 실제 번들 화면에서 확인됐다.
# 하드웨어 관측(Coordinator, 2026-09-13, macOS 26.5 / Darwin 25.5, Developer ID 서명 번들을
# 번들 자신의 인터프리터에서 조사 — 기기 하나, 조사 한 번): 한 번도 등록한 적 없는 번들의
# status() 는 3 이고, 거기서 registerAndReturnError_ 는 (True, None) 을 돌려주며 상태는
# 1 이 된다; 해제하면 0 이다. 등록이 되는 상태는 '등록 안 됨' 이지 오류가 아니다. 다른
# macOS 가 같은 자리에서 0 을 돌려주는지는 이 관측으로는 모른다 — 그래서 0 과 3 이 같은
# 상태로 간다. 어떤 3 이 정말 헤더가 말하는 오류라면, 사용자는 켤 수 있는 항목을 누르고
# 등록이 (False, err) 로 실패해 autostart_fail 창을 본다 — 켤 수 없는 항목보다 낫다.
# 0~3 밖의 값은 여전히 "unavailable" 이다.
_AUTOSTART_STATE_BY_STATUS = {
    SM_STATUS_NOT_REGISTERED: "off",
    SM_STATUS_ENABLED: "on",
    SM_STATUS_REQUIRES_APPROVAL: "approval",
    SM_STATUS_NOT_FOUND: "off",          # 한 번도 등록한 적 없는 설치본 — 위 주석
}


def autostart_state(status, is_bundle):
    """SMAppService 상태값 → 메뉴 상태 ("on" | "off" | "approval" | "unavailable").

    설치본: 0 → "off", 1 → "on", 2 → "approval", 3 → "off". 3(NotFound) 이 "off" 인
    이유는 _AUTOSTART_STATE_BY_STATUS 위 주석에 있다 — 한 번도 등록한 적 없는 번들이
    돌려주는 값이고, 거기서 등록이 된다. 설치본이 아니면(소스 실행) 상태값이 무엇이든
    "unavailable" 이다: 소스에서 본 mainAppService 는 파이썬 자신의 서비스라 그 값은
    우리 것이 아니다. 0~3 밖의 모르는 상태값도 "unavailable" — 켜져 있다고 단정하고
    해제를 누르게 하지도, 무슨 뜻인지 모르는 값에서 등록을 부르지도 않는다. 3 은
    모르는 값이 아니다.
    """
    if not is_bundle:
        return "unavailable"
    return _AUTOSTART_STATE_BY_STATUS.get(status, "unavailable")


def autostart_service():
    """SMAppService.mainAppService(), 없으면 None.

    프레임워크는 호출 시점에 가져온다(app_bundle_path 의 in-function import 와 같은
    선례). macOS 12 에는 SMAppService 클래스가 없고, py2app 이 프레임워크를 빠뜨린
    번들도 같은 모양으로 실패한다 — 어느 쪽이든 항목이 비활성으로 보일 뿐 앱은
    뜬다. mainAppService 를 부르는 곳은 이 함수 하나다.
    """
    try:
        from ServiceManagement import SMAppService
    except Exception:
        return None
    try:
        return SMAppService.mainAppService()
    except Exception:
        return None


def autostart_current():
    """(service, is_bundle) — 메뉴와 핸들러가 같은 규칙으로 서비스를 고른다.

    설치본이 아니면 서비스는 None 이다: 소스 실행의 mainAppService 는 파이썬 자신의
    서비스라 status() 조차 부르지 않는다. 결과는 그대로 autostart_read_state /
    autostart_toggle 의 인자다.
    """
    is_bundle = bool(app_bundle_path())
    return (autostart_service() if is_bundle else None), is_bundle


def autostart_read_state(service, is_bundle):
    """지금 상태 — 메뉴가 state["autostart_read"] 훅으로 읽는 값.

    설치본이 아니거나 서비스가 없으면 서비스를 전혀 건드리지 않고 "unavailable"
    (status() 조차) — 소스 실행에서 읽히는 값은 파이썬 자신의 것이다. status() 가
    예외를 던져도 "unavailable" — 프레임워크가 오작동한 것이지 상태가 아니다. 새로
    설치해 한 번도 등록한 적 없는 번들은 status() 가 3(NotFound) 을 돌려주고, 그것은
    "off" 다(autostart_state) — 항목은 체크 없이 활성으로 보이고, 누르면 등록된다.
    """
    if not is_bundle or service is None:
        return "unavailable"
    try:
        status = service.status()
    except Exception:
        return "unavailable"
    return autostart_state(status, is_bundle)


def autostart_toggle(service, is_bundle):
    """메뉴 클릭 한 번. 반환 (새 상태, 오류 키 | None).

    꺼져 있으면(상태 0 또는 3) 등록, 켜져 있으면(1) 해제. 3(NotFound) 은 새 설치가
    시작하는 자리다 — 한 번도 등록한 적 없는 번들이 돌려주는 값이고, 하드웨어에서 거기서
    등록이 (True, None) 으로 성공해 1 이 됐다(_AUTOSTART_STATE_BY_STATUS 위 주석). 그래서
    3 에서 이 함수는 registerAndReturnError_ 를 부른다; 3 을 "unavailable" 로 보던 첫
    구현은 여기서 아무것도 부르지 않고 ("unavailable", None) 을 돌려줘 항목을 켤 수
    없었다. 새 상태는 부른 뒤 서비스에서 **다시 읽는다**
    — 등록이 승인 대기(2)로 떨어질 수 있어서, "등록했으니 켜졌다" 고 가정하면 사용자에게
    승인 안내를 못 한다. 실패((False, err))는 상태를 바꾸지 않고 "autostart_fail" 로
    보고한다. 승인 대기 상태에서는 아무것도 부르지 않고 "approval" 을 돌려준다 —
    호출자가 승인 안내창을 띄운다. 해제해 버리면 사용자가 켜려고 누른 등록이 사라진다.
    설치본이 아니거나 서비스가 없으면 ("unavailable", None), 서비스는 건드리지 않는다.
    0~3 밖의 모르는 상태값도 ("unavailable", None) — status() 는 읽었지만 등록·해제는
    부르지 않는다. 설정 파일·RUNTIME 에는 아무것도 쓰지 않는다.
    """
    state = autostart_read_state(service, is_bundle)
    if state in ("unavailable", "approval"):
        return state, None
    try:
        if state == "on":
            ok, err = service.unregisterAndReturnError_(None)
        else:
            ok, err = service.registerAndReturnError_(None)
    except Exception as e:
        ok, err = False, e
    if not ok:
        _dbg("autostart: toggle from", state, "failed:", _autostart_err_summary(err))
        return state, "autostart_fail"
    return autostart_read_state(service, is_bundle), None


def uninstall_autostart(service):
    """완전 삭제 전에 로그인 항목을 해제한다. 반환 오류 키 | None.

    등록돼 있을 때(1, 2)만 해제한다. 등록한 적 없는 사용자(0, 3)에게 해제를 부르면
    OS 가 실패를 돌려주고, 그 실패로 삭제를 거절하면 그 사용자는 지울 수 없다.
    해제 실패는 "autostart_fail" — do_uninstall 은 이것을 받으면 아무것도 지우지
    않는다(로그인 항목이 사라진 번들을 가리키게 두지 않는다).
    """
    if service is None:
        return None
    try:
        status = service.status()
    except Exception:
        return "autostart_fail"      # 등록 여부를 모른 채 지우지 않는다
    if status not in (SM_STATUS_ENABLED, SM_STATUS_REQUIRES_APPROVAL):
        return None
    try:
        ok, err = service.unregisterAndReturnError_(None)
    except Exception as e:
        ok, err = False, e
    if not ok:
        _dbg("autostart: uninstall unregister failed:", _autostart_err_summary(err))
        return "autostart_fail"
    return None


def _autostart_err_summary(err):
    """디버그 로그용 요약 — 도메인과 코드만. 설명문은 경로를 품을 수 있어 적지 않는다."""
    try:
        return "%s/%s" % (err.domain(), err.code())
    except Exception:
        return type(err).__name__


def autostart_open_login_items():
    """시스템 설정 → 일반 → 로그인 항목을 연다(승인 안내창의 버튼). 반환 성공 여부."""
    try:
        from ServiceManagement import SMAppService
        SMAppService.openSystemSettingsLoginItems()
        return True
    except Exception:
        return False


def _uninstall_cleanup_script(app, app_id, lock_dir, lock_id):
    """앱 번들 → 잠금 폴더 순으로, '신원이 맞을 때만' 지우는 /bin/sh 명령.

    실행 중인 자기 번들은 스스로 지울 수 없어서, 분리된 셸이 종료를 기다렸다
    지운다. 그 기다리는 구간이 이 스크립트의 위험한 자리다: 잠금은 다른
    업데이터를 막아 주지만 설치 폴더의 '이름'을 잠그지는 않으므로, 그 사이에
    그 자리를 무엇이 차지하면 `rm -rf <이름>` 은 남의 트리를 지운다. 그래서
    파이썬이 잠금 안에서 읽어 넘긴 (dev,ino) 와 맞을 때만 지운다 — 업데이트
    교체 셸의 discard() 와 같은 규율이고, 이유도 같다. 비어 있으면 '모른다'는
    뜻이고, 모르는 것은 지우지 않는다.

    **순서가 중요하다.** 잠금 폴더를 먼저 지우면 우리가 이 셸에 물려준 잠금이
    이름을 잃어, 뒤이어 오는 업데이터가 새 아이노드에 새 잠금을 잡고 그대로
    통과한다. 앱을 지운 '뒤에' 지운다.

    set -e 는 쓰지 않는다. 두 대상은 서로 독립이라, 앞이 못 지웠다는 이유로
    뒤를 거를 이유가 없다.
    """
    import shlex
    q = shlex.quote
    return "\n".join((
        "sleep 2",
        "discard() {",
        '  [ -n "$2" ] || return 0',
        '  [ -e "$1" ] || return 0',
        '  if [ "$(/usr/bin/stat -f %d,%i "$1" 2>/dev/null)" = "$2" ]; then',
        '    /bin/rm -rf "$1"',
        "  fi",
        "}",
        "discard %s %s" % (q(str(app)), q(str(app_id))),
        "discard %s %s" % (q(str(lock_dir)), q(str(lock_id))),
    ))


def do_uninstall():
    """설정 파일 삭제 + (설치본이면) 앱 번들 삭제 예약.
    반환 (앱_삭제_예약됨, 오류메시지). True면 호출자가 즉시 종료해야 한다.

    완전 삭제와 업데이트는 같은 두 대상(앱 번들, 캐시 폴더)을 반대 방향으로
    만지므로 서로 직렬화되어야 한다. 겹치면 무엇이 남을지 아무도 말할 수 없다:
    업데이트가 원자적 교환을 하는 사이에 `rm -rf`가 들어오면 새 번들의 반쪽만
    지워지고, 반대로 캐시 폴더를 먼저 지우면 진행 중인 업데이트가 쥐고 있던
    잠금 파일이 이름째 사라져 — 뒤이어 오는 업데이터는 새 아이노드에 새 잠금을
    잡고 통과한다. 즉 직렬화 장치 자체가 조용히 없어진다.

    그래서 업데이트와 '같은 잠금'을 여기서도 잡는다. 못 잡으면 지우지 않고
    물러난다 — 업데이트가 진행 중이라는 뜻이고, 그때 옳은 답은 기다리는
    것이지 반쯤 지우는 것이 아니다.

    **순서가 이 함수의 계약이다: 아직 거절할 수 있는 단계는 전부, 되돌릴 수
    없는 단계보다 먼저 온다.**

      1. 잠금을 잡는다. 못 잡으면 아무것도 지우지 않고 물러난다.
      2. 지울 번들의 신원을 잠금 안에서 읽는다. 못 읽으면 역시 아무것도 지우지
         않고 물러난다 — 무엇을 지울지 모르는 채로 시작하지 않는다.
      2½. 로그인 항목을 해제한다(uninstall_autostart). 실패하면 아무것도 지우지
         않고 물러난다 — 앱은 지워졌는데 로그인 항목이 그 자리를 가리키는 상태를
         만들지 않는다. 설치본(app)일 때만이다: 소스 실행이 읽는 서비스는 파이썬
         자신의 것이라 건드리지 않는다.
      3. 번들을 지울 분리된 셸을 **먼저** 띄운다. Popen 이 실패하면 그때까지
         지운 것이 하나도 없으므로 설치는 통째로 그대로다.
      4. 그다음에야 사용자 쪽 파일들을 지운다.

    3과 4의 순서가 예전에는 반대였다. 그래서 Popen 이 실패하면 앱은 그대로인데
    설정·로그·기본 설정만 사라진, 어느 쪽으로도 온전하지 않은 설치가 남았다.
    이 파일이 여러 곳에서 되풀이하는 그 성질과 같다 — 아직 거절할 수 있는 것이
    이미 부순 것 뒤에 오면 안 된다.

    **개발 모드(설치본 없음)에서도 잠금을 잡는다.** 지우는 대상에 업데이트 잠금
    폴더가 들어 있어서다. 잡지 않고 지우면 진행 중인 설치본의 업데이트가 쥐고
    있던 잠금 파일이 이름째 사라지고, 위 docstring 이 경계하는 바로 그 경로가
    열린다 — 소스에서 띄운 실행이 설치본의 직렬화를 조용히 없앤다. 경로를 모를
    뿐 잠금의 이름은 알 수 있다(INSTALLED_BUNDLE_NAME).
    """
    app = app_bundle_path()
    lock_fd = _acquire_update_lock(app or INSTALLED_BUNDLE_NAME)
    if lock_fd is None:
        return False, "update in progress"
    try:
        # 잠금을 들고 있는 동안에는 잠금 폴더를 지우지 않는다. 지우면 그 순간
        # 직렬화가 풀린다 — 분리된 셸이 앱을 지운 뒤에 같이 지운다.
        keep = os.path.expanduser(UPDATE_LOCK_DIR)
        if app:
            # 신원은 잠금을 잡은 '뒤에' 읽는다. 잠금 밖에서 읽은 값은 그 사이
            # 업데이트가 번들을 통째로 맞바꿨을 수 있어 지금 그 자리에 있는
            # 것을 가리키지 않는다.
            app_id = _path_ident_str(app)
            if not app_id:
                # 무엇을 지울지 모르는 채로는 시작하지 않는다. 여기서 물러나면
                # 지운 것이 없으므로 설치는 그대로다.
                return False, "could not identify the installed app bundle"
            # 로그인 항목 해제 — 아직 거절할 수 있는 마지막 단계. 잠금 안에서,
            # 셸을 띄우기 전에. 실패하면 지운 것이 없으므로 설치는 그대로다.
            err = uninstall_autostart(autostart_service())
            if err:
                return False, err
            # 잠긴 fd 를 그 셸에 그대로 물려준다(업데이트 교체 셸과 같은
            # 방식이다). 여기서 놓아 버리면 '앱을 지우는 2초'가 무방비가 되어,
            # 그 사이에 시작한 업데이터가 잠금을 잡고 이미 사라지는 중인 앱을
            # 교체하려 든다. 셸이 어떻게 죽든 커널이 놓아 주므로 잔여 잠금은
            # 남지 않는다.
            sh = _uninstall_cleanup_script(app, app_id, keep,
                                           _lock_root_ident())
            try:
                subprocess.Popen(["/bin/sh", "-c", sh], pass_fds=(lock_fd,))
            except Exception as e:
                # 아직 아무것도 지우지 않았다 — 설치는 통째로 그대로다.
                return False, str(e)
        # 여기부터가 되돌릴 수 없는 구간이다. 이름이 아니라 '지금 그 자리에 있는
        # 그 객체'를 지운다(_discard_owned_path). 예전에는 isdir 로 갈라
        # shutil.rmtree(p) / os.remove(p) 였는데, 둘 다 확인한 '이름'을 다시
        # 해석하므로 그 사이 그 이름이 남의 것이 되면 남의 것을 지웠다.
        for p in uninstall_targets():
            if p == keep:
                continue
            _discard_owned_path(p)
        if not app:
            # 개발 모드에는 뒤처리할 셸이 없다. 잠금 폴더는 다른 대상을 모두
            # 지운 뒤, 잠금을 아직 배타적으로 들고 있는 이 자리에서 마지막으로
            # 지운다 — 우리가 들고 있는 동안에는 다른 거래가 그 안에 있을 수
            # 없고, 이 함수가 돌아간 뒤에 오는 거래는 새로 만들어 쓴다.
            _discard_owned_path(keep)
            return False, None      # 개발 모드 — 지울 앱 없음(설정만 지움)
        return True, None
    finally:
        # 넘겼든 못 넘겼든 우리 쪽 사본은 닫는다. 넘긴 뒤 잠금의 주인은 저 셸
        # 하나여야 한다 — 부모가 사본을 들고 있으면 셸이 죽어도 잠금이 풀리지
        # 않는다. (여기까지 왔으면 앱은 곧 사라지지만, 그래도 규율은 같다.)
        try:
            os.close(lock_fd)
        except OSError:
            pass


# ─────────────────────── 유틸 ───────────────────────

def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(int(n))


def fmt_countdown(reset, now):
    if not reset:
        return "-"
    d = reset - now
    if d.total_seconds() <= 0:
        return t("reset_done")
    h, rem = divmod(int(d.total_seconds()), 3600)
    m = rem // 60
    if h >= 24:
        return t("cd_days", d=h // 24, h=h % 24)
    return t("cd_hm", h=h, m=m) if h else t("cd_m", m=m)


def worst_pct(stats):
    return max(stats["session"]["pct"], stats["weekly"]["pct"], stats["opus"]["pct"])


def mood_for(stats):
    pct = worst_pct(stats)
    if pct >= 85:
        return "failed"
    if pct >= 50:
        return "waiting"
    return "idle"


# ─────────────────── 픽셀 지오메트리 (GUI/미리보기 공용) ───────────────────

PILL_W = 300          # 요약 필 최대 너비 — 실제 폭은 글자 폭에 맞춰 SUMMARY_MIN_W..PILL_W (roam_pill_rect)
PILL_PAD = 13         # 필 내부 패딩
PILL_ROWS = 4         # 서버 응답에서 받아 두는 최대 행 수: 세션 / 주간 / 모델(Fable 등) / 크레딧 (fetch_exact_usage)
def pill_h():
    """논리 창의 필 띠 높이 = 요약 필의 최대 높이(둘째 줄 포함). 표시는 요약 필 하나뿐이다 — 게이지 막대와
    하단 상태줄이 있던 큰 필은 없앴다(사용자 결정 2026-09-12: "그거로 통일하자"). 실제 필은 내용에 따라
    한 줄(SUMMARY_H) 또는 두 줄(SUMMARY_H2, 리셋 시각 줄)이며 띠 안에서 펫 쪽으로 붙는다(roam_pill_rect)."""
    return SUMMARY_H2
GAP = 6               # 펫-필 간격
BTN_R = 13            # 접기 버튼 반지름

PILL_BG = "#1C1C1F"
TXT_MAIN = "#F2F2F7"
TXT_SUB = "#98989F"
COL_OK, COL_WARN, COL_BAD = "#32D74B", "#FFD60A", "#FF453A"


# ─────────────── 조용한 동행(quiet companion) — 순수 상태기계 ───────────────
# 펫이 스스로 화면을 돌아다니는 규칙. AppKit 을 모른다: 시간·커서·경계·플래그를
# 전부 인자로 받고 "어디에 있어야 하고 어떤 애니메이션이어야 하는가" 만 값으로
# 돌려준다. 창을 옮기고 override 를 켜는 것은 run_gui() 안의 어댑터(roam_tick)다.
# 설계 문서: docs-design/quiet-companion.md (따라다니기·모니터 점프: docs-design/companion-play-20260909.md).
# 게이트: tests/test_companion_motion.py, tests/test_free_roaming.py, tests/test_companion_play.py.
#
# 좌표는 **창 중심**의 스크린 포인트(y 는 위로). radius 는 창 전체의 외접원 반지름
# (hypot(W/2, H/2)) 이라, "커서까지 radius + 여백" 은 창의 어느 픽셀도 커서에
# 닿지 않는다는 뜻이다. 시간은 단조 초(float). 난수는 rng.uniform(a, b) 만 쓴다.
#
# 여기 이름들은 AppKit 없이 exec 될 수 있어야 한다 — math/random/namedtuple 과
# 이 절의 정의만 참조한다(다른 모듈 레벨 이름을 끌어오면 그 시험이 깨진다).

ROAM_DEFAULTS = {
    "rest_min_s": 45.0, "rest_max_s": 90.0,   # 쉬는 시간: rng.uniform(min, max)
    "approach_cooldown_s": 180.0,             # 구경(approach) 최소 간격
    "wander_cooldown_s": 300.0,               # 산책(wander) 최소 간격
    "walk_speed": 55.0,                       # pt/s
    "approach_stop": 150.0,                   # 커서와 창 외접원 사이 최소 거리 (radius 를 더해 중심 기준으로 쓴다)
    "approach_max": 360.0,                    # 한 번 이동 상한 — 더 멀면 여기까지만 가서 멀리서 본다
    "look_s": 6.0,                            # 바라보기(review) 지속
    "wander_enabled": True,                   # 산책: 현재 모니터의 허용 rect 전체에서 랜덤 목적지
    "wander_tries": 6,                        # 산책 후보 재추첨 상한(너무 가깝거나 커서·경로와 겹치면 다음 후보)
    "wander_pause_s": 2.0,
    "activity_window_s": 20.0,                # 최근 이 시간 안에 커서 이동/활동 힌트가 있으면 '활동 중'
    "cursor_move_px": 12.0, "cursor_sample_s": 1.0,   # 1 Hz 샘플 사이 이보다 작은 이동은 무시
    "cursor_margin_px": 24.0,                 # 이동 중 창 외접원과 커서 사이의 안전 여백
    "max_dt_s": 0.25,                         # step 당 이동 시간 상한 — 늦은 tick 이 순간이동이 되지 않게
    "gap_s": 5.0,                             # 이보다 긴 공백(잠자기·메뉴)이면 그 자리에 서고 휴식
    "min_trip_px": 60.0, "arrive_px": 2.0,
    # 따라다니기(follow): 가끔 10~20 초 동안 움직이는 커서의 최신 좌표를 여백을 두고 천천히 쫓는다
    "follow_p": 0.35,                         # 자격(활동 중·커서·쿨다운 경과)일 때 follow 를 고를 확률 — 계획 step 에서 uniform(0, 1) 1회
    "follow_min_s": 10.0, "follow_max_s": 20.0,   # 에피소드 길이 rng.uniform(min, max); 시작 때 고정, 10 초 미만 없음
    "follow_cooldown_s": 420.0,               # follow 최소 간격(실제 시작 뒤). 초기값은 now — 첫 정상 휴식부터 자격
    "follow_speed": 45.0,                     # pt/s, 걷기보다 느리게
    "follow_slack_px": 20.0,                  # 여백(approach_stop + radius) 안쪽 이 폭에서는 서서 바라본다 (떨림 방지)
    "follow_turn_px": 8.0,                    # 좌우 방향 전환 히스테리시스
    "follow_cross_s": 3.0,                    # 커서가 같은 다른 화면에 이만큼 머물러야 건너간다 (대상 화면 ID 에 묶인 체류)
    "follow_min_left_s": 5.0,                 # 남은 에피소드가 이보다 짧으면 건너가지 않는다
    "follow_max_jumps": 1,                    # 에피소드당 점프 상한 — 왕복 없음
    # 모니터 사이 점프(jump): 산책 계획 때 다른 화면의 안전한 착지 후보로 건너간다
    "jump_enabled": True,
    "jump_p": 0.5,                            # 다른 화면이 있고 쿨다운이 지났을 때 산책이 점프가 될 확률 — uniform(0, 1) 1회
    "jump_cooldown_s": 600.0,                 # 점프 최소 간격(실제 시작 뒤). 초기값은 now
    "jump_tries": 6,                          # 착지 후보 재추첨 상한 (시도당 uniform x, y 2회)
    "jump_prep_s": 0.75,                      # 출발 효과: jumping 스프라이트 한 바퀴(5 프레임 × 150 ms) + 창 fade-out, pos 불변
    "jump_land_s": 0.5,                       # 착지 효과: 애니메이션 없음 + 창 fade-in
}

# pos    = (x, y) 지금 창 중심 (항상 채움)
# anim   = None | "running-left" | "running-right" | "review" | "jumping"
# moved  = 이 step 에 pos 가 바뀌었는가
# away   = |pos − home| > arrive_px — 수동 재시작 위치에서 떨어져 있는가. 자동 계획(_plan)과 표시 복원(RoamDisplay)
#          은 이 값을 쓰지 않는다. 어댑터의 roam_resync 만 참조한다(나가 있으면 pos 를, 집이면 창 중심을 기준으로 재정렬)
# phase  = "rest" | "out" | "look" | "follow" | "jump"
# effect = None | "takeoff" | "landing" — 점프의 출발/착지 효과. 어댑터가 창 alpha 로 그린다. 끝에 붙은 필드라
#          다섯 인자로 만드는 옛 호출도 그대로 된다(기본값 None)
RoamOut = namedtuple("RoamOut", "pos anim moved away phase effect", defaults=(None,))

# 화면 레코드 — 어댑터가 매 tick 현재 화면을 포함한 모든 화면을 준다.
#   id     = 안정 식별자 (어댑터: NSScreenNumber)
#   frame  = (x0, y0, x1, y1) 실제 화면 rect — 커서가 어느 화면에 있는지는 이걸로 판정한다
#   bounds = (x0, y0, x1, y1) 논리 full 창이 통째로 들어가는 중심 허용 rect — 착지·pos 는 이 안에서만.
# 둘은 분리해 쓴다: bounds 를 radius 로 넓혀 frame 을 짐작하면 화면 사이 빈틈의 커서를 이웃 화면으로 오인한다.
RoamScreen = namedtuple("RoamScreen", "id frame bounds")


def _roam_dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _roam_clamp(p, bounds):
    x0, y0, x1, y1 = bounds
    return (min(max(float(p[0]), x0), x1), min(max(float(p[1]), y0), y1))


def _roam_seg_dist(p, a, b):
    """점 p 에서 선분 ab 까지의 거리."""
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    ln = vx * vx + vy * vy
    if ln <= 0.0:
        return _roam_dist(p, a)
    u = ((p[0] - ax) * vx + (p[1] - ay) * vy) / ln
    u = min(max(u, 0.0), 1.0)
    return _roam_dist(p, (ax + vx * u, ay + vy * u))


def _roam_inside(p, rect):
    x0, y0, x1, y1 = rect
    return x0 <= p[0] <= x1 and y0 <= p[1] <= y1


def _roam_valid_rect(rect):
    """뒤집히지 않은 rect 인가 — 뒤집힌 bounds 는 창이 그 화면보다 크다는 뜻이다."""
    x0, y0, x1, y1 = rect
    return x0 <= x1 and y0 <= y1


def _roam_rect_dist(p, rect):
    """점 p 에서 rect 까지의 거리 (안이면 0)."""
    return _roam_dist(p, _roam_clamp(p, rect))


def _roam_screen_at(screens, p):
    """p 를 실제 frame 에 담는 화면의 id. 화면 사이 빈틈이면 None."""
    for scr in screens:
        if _roam_inside(p, scr.frame):
            return scr.id
    return None


def _roam_find_screen(screens, sid):
    for scr in screens:
        if scr.id == sid:
            return scr
    return None


class Roamer:
    """펫의 자율 이동 상태기계 — rest → (out | follow | jump) → look → rest (그 자리에서).

    · rest   지금 있는 자리에서 쉰다. 휴식이 끝나면 활동이 있고 cooldown 이 지났을 때
             가끔(follow_p) 따라다니기(follow)를, 아니면 구경(approach)을, 아니면 산책
             (wander — 다른 화면이 있으면 가끔(jump_p) 점프)을 계획한다. 계획한 step 에는
             움직이지 않는다. 쉬는 동안 조작(아래 플래그)이 있으면 휴식 시각을 다시 잰다.
    · out    목표를 향해 walk_speed 로 걷는다. 목표는 출발 때 한 번 정하고 다시
             계산하지 않는다(커서를 쫓지 않는다).
    · follow 시작 때 고정한 마감(follow_min_s~follow_max_s)까지 매 step 커서의 최신 좌표를
             쫓는다: 커서에서 approach_stop + radius 만큼 떨어진 자리를 목표로 follow_speed
             로 다가가고, 그 안쪽(+follow_slack_px)이면 서서 바라본다(review). 커서가 다른
             화면에 follow_cross_s 이상 머물면 에피소드당 한 번 같은 jump 경로로 건너가
             이어 간다. 마감이 오면 구경 도착처럼 look(review) 뒤 그 자리에서 쉰다.
             커서가 없어지면 그 자리 정지(자연 완료 아님).
    · jump   다른 화면으로 건너간다: off(jumping 애니메이션 + takeoff 효과, jump_prep_s,
             pos 불변) → 전송 직전 재검사(대상 화면이 아직 있고 착지가 그 최신 bounds 안이며
             최신 커서가 착지의 배제 영역 밖) → 한 step 에 원자적 위치 교체(moved) →
             land(landing 효과, jump_land_s) → 산책이면 look, follow 였으면 follow 계속.
             재검사에 걸리면 취소하고 지금 자리에 선다. 한 화면 안에서는 점프하지 않는다.
    · look   구경/follow 는 review 애니메이션으로 look_s 동안, 산책은 idle 로 잠깐 선다.
             끝나면 **그 자리에서** 쉰다 — 집으로 돌아가는 leg 는 없다.
    home 은 사용자가 드래그로 놓은 '재시작 위치' 일 뿐이다: 자동 이동(점프 포함)은 home 을
    바꾸지도, home 으로 되돌아가지도 않는다. 산책 목적지는 현재 화면 bounds(논리 full 창이
    통째로 들어가는 중심 허용 rect) 전체에서, 착지는 고른 다른 화면의 bounds 안에서 균등 랜덤이다.

    화면: step 의 screens(RoamScreen 목록, 현재 화면 포함)가 비어 있지 않으면 현재 화면은
    이 모델이 확정한다(screen 속성) — pos 를 frame 에 담는 화면, 없으면 bounds 가 가장
    가까운 화면. 처음 screens 를 받을 때, 수동 배치(set_home/release) 뒤, 현재 id 가 목록에서
    사라졌을 때 다시 해석한다. 착지 뒤 현재 화면은 착지 화면이고 다음 경계 검사(R8)도 그
    bounds 를 쓴다 — 어댑터의 win.screen() 이 곧바로 바뀌는지에 기대지 않는다. screens 가
    비어 있으면 bounds 인자의 단일 화면이다(점프 없음).

    **모든 phase 에서 사용자가 우선이다.** enabled=False(설정 off·Reduce Motion),
    dragging, blocked(hover·남의 애니메이션), busy(설정 창·메뉴·spike), 그리고
    gap_s 보다 긴 tick 공백은 **그 자리에 즉시 서고** 휴식을 새로 추첨한다 —
    집으로 순간이동하지도, 옛 목표를 이어 걷지도 않는다(전송 전이면 원래 화면, 뒤면 착지
    화면에 남는다). 걷기(out)에서 현재 커서와 [pos, 목표] 선분의 거리가 radius + 여백보다
    작으면 그 자리에 서고 휴식한다(우회하지 않는다). 커서는 언제든 펫 위로 올 수 있으므로
    보장하는 것은 두 가지다: 펫이 **자기 이동으로** 커서의 배제 영역에 들어가지 않고, 커서가
    경로·자리에 침범한 tick 에는 움직이지 않는다. 자동 이동은 좌표를 저장하지 않는다.
    """

    def __init__(self, home, now, rng=None, cfg=None, radius=0.0):
        self.cfg = dict(ROAM_DEFAULTS)
        if cfg:
            self.cfg.update(cfg)
        self.rng = rng if rng is not None else random.Random()
        self.radius = float(radius)
        self.home = (float(home[0]), float(home[1]))
        self.pos = self.home
        self.phase = "rest"
        self.kind = None                  # None | "approach" | "wander"
        # 마지막으로 rest 가 된 이유가 '자연 완료' 인가. 생성·구경/산책 멈춤 만료·
        # 휴식 끝 재추첨·수동 배치(set_home)면 True, hold·공백·guard·경계·단순 클릭으로
        # 그 자리에 선 것이면 False. 표시 계층이 "구경 중 hover 로 멈춘 것" 과 "구경이
        # 끝난 것" 을 이 값으로 구별한다.
        self.settled = True
        self._target = None
        self._anim = None
        self._last_now = float(now)
        self._next_at = float(now)
        self._look_until = float(now)
        self._approach_ok_at = float(now)
        self._wander_ok_at = float(now)
        self._follow_ok_at = float(now)      # 첫 정상 휴식부터 자격 — 초기 제외 기간 없음
        self._jump_ok_at = float(now)
        self._last_active = float("-inf")
        self._sample = None
        self._sample_at = float("-inf")
        # 화면 — screens 를 받기 전엔 None (단일 화면 bounds 모드)
        self.screen = None
        # follow 에피소드: 마감(시작 때 고정), 이번 에피소드의 점프 횟수, 다른 화면 체류 (id, since)
        self._follow_until = float(now)
        self._follow_jumps = 0
        self._cross = None
        # jump: 단계 "off"|"land", 대상 화면 id, 착지점, 전송 시각, 착지 효과 끝, 착지 뒤 갈 곳("look"|"follow")
        self._jump_stage = None
        self._jump_screen = None
        self._jump_to = None
        self._jump_at = float(now)
        self._land_until = float(now)
        self._jump_next = None
        self._effect = None
        self._arm(float(now))

    # ── 읽기 ──
    @property
    def away(self):
        return _roam_dist(self.pos, self.home) > self.cfg["arrive_px"]

    def _out(self, moved):
        return RoamOut(self.pos, self._anim, bool(moved), self.away, self.phase, self._effect)

    # ── 내부 전이 ──
    def _arm(self, now):
        """휴식 재추첨. next_at 전에는 어떤 step 도 움직이지 않는다."""
        self._next_at = now + self.rng.uniform(self.cfg["rest_min_s"],
                                               self.cfg["rest_max_s"])

    def _stop(self, now, settled=False):
        """그 자리에 선다. 목표·종류·애니메이션을 버리고 휴식으로.

        settled=True 는 '자연 완료'(구경/산책 멈춤 만료·수동 배치), False 는 hold·공백·
        guard·경계·단순 클릭으로 멈춘 것. 값은 self.settled 로 읽힌다.
        """
        self.phase = "rest"
        self.kind = None
        self.settled = bool(settled)
        self._target = None
        self._anim = None
        self._clear_play()
        self._arm(now)

    def _clear_play(self):
        """follow 체류·jump 진행·효과를 버린다 (정지·look 전이에서)."""
        self._cross = None
        self._jump_stage = None
        self._jump_screen = None
        self._jump_to = None
        self._jump_next = None
        self._effect = None

    def _begin(self, kind, target, now):
        """목표를 향한 leg 를 시작한다 (kind = "approach" | "wander")."""
        self.kind = kind
        self._target = target
        if _roam_dist(target, self.pos) <= self.cfg["arrive_px"]:
            self._watch(now)                          # 제자리 구경
            return
        self.phase = "out"
        self._anim = "running-right" if target[0] >= self.pos[0] else "running-left"

    def _watch(self, now):
        self.phase = "look"
        self._clear_play()
        if self.kind in ("approach", "follow"):
            self._anim = "review"
            self._look_until = now + self.cfg["look_s"]
        else:
            self._anim = None
            self._look_until = now + self.cfg["wander_pause_s"]

    def _stand(self):
        """follow 중 그 자리에서 커서를 바라본다 (이 step 은 움직이지 않는다)."""
        self._anim = "review"
        return self._out(False)

    def _start_jump(self, now, sid, landing, next_phase):
        """다른 화면으로 건너가기 시작: 출발 효과 동안 pos 불변, 대상 화면과 착지점은 고정."""
        self.phase = "jump"
        self._target = None
        self._cross = None
        self._jump_stage = "off"
        self._jump_screen = sid
        self._jump_to = (float(landing[0]), float(landing[1]))
        self._jump_next = next_phase
        self._jump_at = now + self.cfg["jump_prep_s"]
        self._jump_ok_at = now + self.cfg["jump_cooldown_s"]
        self._anim = "jumping"
        self._effect = "takeoff"

    def _plan_landing(self, scr, cursor):
        """다른 화면 scr 의 bounds 전체에서 균등 랜덤 착지 후보. 시도마다 uniform 을 x, y 로 정확히 두 번.

        커서와 approach_stop + radius 안이면 버린다. jump_tries 안에 없으면 None — 호출자가
        같은 화면 산책으로 넘어간다.
        """
        x0, y0, x1, y1 = scr.bounds
        stop = self.cfg["approach_stop"] + self.radius
        for _ in range(int(self.cfg["jump_tries"])):
            x = self.rng.uniform(x0, x1)
            y = self.rng.uniform(y0, y1)
            target = _roam_clamp((x, y), scr.bounds)
            if cursor is not None and _roam_dist(target, cursor) < stop:
                continue
            return target
        return None

    def _standoff(self, cursor, rect):
        """커서에서 approach_stop + radius 만큼 떨어진, 펫 쪽의 자리를 rect 로 클램프한 것."""
        stop = self.cfg["approach_stop"] + self.radius
        d = _roam_dist(cursor, self.pos)
        if d <= 0.0:
            ux, uy = -1.0, 0.0
        else:
            ux, uy = (self.pos[0] - cursor[0]) / d, (self.pos[1] - cursor[1]) / d
        return _roam_clamp((cursor[0] + ux * stop, cursor[1] + uy * stop), rect)

    def _note(self, now, cursor, activity):
        """활동 기록. 커서는 cursor_sample_s 마다 한 번만 직전 샘플과 비교한다."""
        if activity:
            self._last_active = now
        if cursor is not None and now - self._sample_at >= self.cfg["cursor_sample_s"]:
            here = (float(cursor[0]), float(cursor[1]))
            if (self._sample is not None
                    and _roam_dist(here, self._sample) >= self.cfg["cursor_move_px"]):
                self._last_active = now
            self._sample = here
            self._sample_at = now

    def _active(self, now):
        return now - self._last_active <= self.cfg["activity_window_s"]

    def _plan_approach(self, cursor, bounds):
        stop = self.cfg["approach_stop"] + self.radius
        d = _roam_dist(cursor, self.pos)
        if d <= stop:
            return self.pos                            # 이미 가까움 → 제자리 구경
        travel = min(d - stop, self.cfg["approach_max"])
        ux, uy = (cursor[0] - self.pos[0]) / d, (cursor[1] - self.pos[1]) / d
        target = _roam_clamp((self.pos[0] + ux * travel, self.pos[1] + uy * travel),
                             bounds)
        if _roam_dist(target, cursor) < stop / 2:
            return None                                # 클램프 때문에 너무 가까워짐
        if _roam_dist(target, self.pos) < self.cfg["min_trip_px"]:
            return self.pos
        return target

    def _wander_on(self):
        # wander_enabled 가 스위치다. 예전 키 wander_radius 를 0 으로 준 설정도 '끔' 으로 읽는다
        # (반경 자체는 더 이상 쓰지 않는다 — 목적지는 bounds 전체에서 고른다).
        return bool(self.cfg.get("wander_enabled", True)) and self.cfg.get("wander_radius", 1.0) != 0

    def _plan_wander(self, cursor, bounds):
        """bounds 전체에서 균등 랜덤 목적지. 시도마다 rng.uniform 을 x, y 로 정확히 두 번 쓴다.

        후보를 버리는 조건: 너무 가깝다(min_trip_px 미만) / 커서에 approach_stop + radius
        안으로 붙는다 / 걷는 선분이 커서와 radius + cursor_margin_px 안으로 스친다(출발
        직후 guard 로 취소될 경로). wander_tries 안에 통과 후보가 없으면 None — 호출자가
        휴식을 다시 추첨하고, 즉시 재시도는 없다.
        """
        x0, y0, x1, y1 = bounds
        stop = self.cfg["approach_stop"] + self.radius
        clearance = self.radius + self.cfg["cursor_margin_px"]
        for _ in range(int(self.cfg["wander_tries"])):
            x = self.rng.uniform(x0, x1)
            y = self.rng.uniform(y0, y1)
            target = _roam_clamp((x, y), bounds)
            if _roam_dist(target, self.pos) < self.cfg["min_trip_px"]:
                continue
            if cursor is not None:
                if _roam_dist(target, cursor) < stop:
                    continue                           # 사용자 작업 위로 걸어 들어가지 않는다
                if _roam_seg_dist(cursor, self.pos, target) < clearance:
                    continue                           # 가는 길에 커서를 스친다
            return target
        return None

    def _plan(self, now, cursor, bounds, screens):
        """휴식 끝. 우선순위: follow(가끔) > approach > wander(다른 화면이 있으면 가끔 jump) > 휴식 재추첨.

        새 행동 선택 난수는 여기서 뽑는다: follow 자격이면 uniform(0, 1) 1회(+ 고르면 길이 1회),
        점프 자격이면 uniform(0, 1) 1회(+ 고르면 화면 index 1회와 착지 후보 시도당 2회).
        follow_p=0 이면 follow 선택 난수를, jump_enabled=False(또는 다른 화면 없음)면 점프 선택
        난수를 생략한다 — 옛 fixture 의 호출 수가 그대로인 이유. jump_p=0 은 자격이 있으면 확률
        난수 1회를 소비하고 거절된다. 휴식 재추첨(_arm)의 난수는 기존대로다.
        """
        active = self._active(now) and cursor is not None
        if (active and self.cfg["follow_p"] > 0 and now >= self._follow_ok_at
                and self.rng.uniform(0, 1) < self.cfg["follow_p"]):
            self.kind = "follow"
            self.phase = "follow"
            self._target = None
            self._anim = None
            self._follow_until = now + self.rng.uniform(self.cfg["follow_min_s"],
                                                        self.cfg["follow_max_s"])
            self._follow_ok_at = now + self.cfg["follow_cooldown_s"]
            self._follow_jumps = 0
            self._cross = None
            return
        if active and now >= self._approach_ok_at:
            target = self._plan_approach(cursor, bounds)
            if target is not None:
                self._approach_ok_at = now + self.cfg["approach_cooldown_s"]
                self._begin("approach", target, now)
                return
        if self._wander_on() and now >= self._wander_ok_at:
            others = [s for s in screens if s.id != self.screen]
            if (others and self.cfg.get("jump_enabled", True) and now >= self._jump_ok_at
                    and self.rng.uniform(0, 1) < self.cfg["jump_p"]):
                i = min(int(self.rng.uniform(0, len(others))), len(others) - 1)
                landing = self._plan_landing(others[i], cursor)
                if landing is not None:
                    self._wander_ok_at = now + self.cfg["wander_cooldown_s"]
                    self.kind = "wander"
                    self._start_jump(now, others[i].id, landing, "look")
                    return
            target = self._plan_wander(cursor, bounds)
            if target is not None:
                self._wander_ok_at = now + self.cfg["wander_cooldown_s"]
                self._begin("wander", target, now)
                return
        self.kind = None                               # 할 일이 없다 — 그 자리에서 쉰다 (귀가 없음)
        self.settled = True
        self._arm(now)

    def _resolve_screen(self, screens, bounds):
        """현재 화면과 그 bounds. screens 가 비면 bounds 인자의 단일 화면이다."""
        if not screens:
            return bounds
        if _roam_find_screen(screens, self.screen) is None:
            sid = _roam_screen_at(screens, self.pos)
            if sid is None:
                sid = min(screens, key=lambda s: _roam_rect_dist(self.pos, s.bounds)).id
            self.screen = sid
        return _roam_find_screen(screens, self.screen).bounds

    def _clamp_home(self, bounds, screens):
        """화면 구성이 바뀌어 pos 를 들일 때 home 도 들인다 — 단, home 이 어느 화면 bounds 안에
        멀쩡히 있으면 그대로 둔다(점프로 다른 화면에 있는 동안 home 을 착지 화면으로 옮기지 않는다)."""
        if screens and any(_roam_inside(self.home, s.bounds) for s in screens):
            return
        self.home = _roam_clamp(self.home, bounds)

    def _step_jump(self, now, cursor, screens):
        if self._jump_next == "follow":
            if cursor is None:
                self._stop(now)                        # follow 의 점프: 커서가 없으면 취소
                return self._out(False)
            if now >= self._follow_until:
                self._watch(now)                       # 마감이 먼저다 — 전송 전이면 원래 화면에서 자연 완료
                return self._out(False)
        if self._jump_stage == "off":
            if now < self._jump_at:
                return self._out(False)
            scr = _roam_find_screen(screens, self._jump_screen)
            landing = self._jump_to
            clearance = self.radius + self.cfg["cursor_margin_px"]
            if (scr is None or not _roam_inside(landing, scr.bounds)
                    or (cursor is not None and _roam_dist(cursor, landing) < clearance)):
                self._stop(now)                        # 대상 화면이 사라졌거나 줄었거나 커서가 착지를 덮었다
                return self._out(False)
            self.pos = landing
            self.screen = scr.id
            self._jump_stage = "land"
            self._land_until = now + self.cfg["jump_land_s"]
            self._anim = None
            self._effect = "landing"
            return self._out(True)
        if now < self._land_until:
            return self._out(False)
        if self._jump_next == "follow":
            self._follow_jumps += 1
            self._clear_play()
            self.phase = "follow"                      # 마감 전이면 새 화면에서 이어 간다
            return self._out(False)
        self._watch(now)                               # 산책 점프: 잠깐 멈춘 뒤 그 자리에서 쉰다
        return self._out(False)

    def _step_follow(self, now, dt, cursor, bounds, screens):
        if cursor is None:
            self._stop(now)                            # 커서가 없다: 취소 (자연 완료 아님)
            return self._out(False)
        if now >= self._follow_until:
            self._watch(now)                           # 마감 — 구경 도착처럼 바라본 뒤 그 자리에서 쉰다
            return self._out(False)
        stop = self.cfg["approach_stop"] + self.radius
        clearance = self.radius + self.cfg["cursor_margin_px"]
        if screens:
            cs = _roam_screen_at(screens, cursor)
            if cs is None:
                self._cross = None                     # 화면 사이 빈틈: 안전 대기, 체류 시계 해제
                return self._stand()
            if cs != self.screen:
                if self._cross is None or self._cross[0] != cs:
                    self._cross = (cs, now)            # 대상 화면이 바뀌면 체류를 새로 잰다
                elif (now - self._cross[1] >= self.cfg["follow_cross_s"]
                      and self._follow_jumps < int(self.cfg["follow_max_jumps"])
                      and self._follow_until - now >= self.cfg["follow_min_left_s"]
                      and self.cfg.get("jump_enabled", True) and now >= self._jump_ok_at):
                    scr = _roam_find_screen(screens, cs)
                    landing = self._standoff(cursor, scr.bounds)
                    if _roam_dist(landing, cursor) >= clearance:
                        self._start_jump(now, cs, landing, "follow")
                        return self._out(False)
            else:
                self._cross = None
        d = _roam_dist(cursor, self.pos)
        if d <= stop + self.cfg["follow_slack_px"]:
            return self._stand()                       # 여백 안: 서서 바라본다 (커서가 들어와도 움직이지 않는다)
        target = self._standoff(cursor, bounds)
        if _roam_seg_dist(cursor, self.pos, target) < clearance:
            return self._stand()                       # 가는 길이 커서를 스친다: 이 step 은 서 있는다
        remaining = _roam_dist(self.pos, target)
        if remaining <= self.cfg["arrive_px"]:
            return self._stand()                       # 클램프된 가장자리에 닿았다
        dx = target[0] - self.pos[0]
        if abs(dx) > self.cfg["follow_turn_px"] or self._anim not in ("running-left", "running-right"):
            self._anim = "running-right" if dx >= 0 else "running-left"
        stride = self.cfg["follow_speed"] * dt
        if stride <= 0.0:
            return self._out(False)
        if remaining <= stride:
            self.pos = target
            return self._out(True)
        ux, uy = (target[0] - self.pos[0]) / remaining, (target[1] - self.pos[1]) / remaining
        self.pos = (self.pos[0] + ux * stride, self.pos[1] + uy * stride)
        return self._out(True)

    # ── 공개 API ──
    def step(self, now, cursor, bounds, *, enabled=True, dragging=False,
             blocked=False, busy=False, activity=False, screens=()):
        """한 tick. cursor=(x, y)|None, bounds=(x0, y0, x1, y1)=허용되는 창 중심 rect.

        blocked = "지금 출발하지 마"(hover, 남의 override 재생 중).
        busy    = "출발 금지"(설정 창·메뉴·spike). 이동 중이면 둘 다 그 자리 정지.
        screens = RoamScreen 목록(현재 화면 포함). 뒤집힌 bounds 의 화면은 여기서 걸러 낸다.
                  비어 있으면 bounds 의 단일 화면이고 점프는 없다. 비어 있지 않으면 현재 화면은
                  이 모델이 확정하고(screen) 그 bounds 를 쓴다 — bounds 인자는 호환용이다.
        """
        now = float(now)
        gap = now - self._last_now
        dt = min(max(gap, 0.0), self.cfg["max_dt_s"])
        self._last_now = now
        self._note(now, cursor, activity)
        # 창보다 작은 화면(bounds 뒤집힘)은 목적지도 착지도 아니다 — 어댑터가 빼지만 여기서도 다시 거른다.
        # 남는 화면이 없으면 bounds 인자의 단일 화면(뒤집혀 있으면 아래 valid 검사가 아무것도 하지 않게 한다).
        screens = tuple(s for s in (screens or ()) if _roam_valid_rect(s.bounds))
        bounds = self._resolve_screen(screens, bounds)
        x0, y0, x1, y1 = bounds
        valid = not (x0 > x1 or y0 > y1)               # 뒤집힌 경계 = 창이 화면보다 크다
        hold = (not enabled) or dragging or blocked or busy

        if self.phase == "rest":
            if hold:
                # 조작이 이어지는 동안 휴식 시각을 계속 뒤로 민다 — 조작이 '끝난' 시점부터
                # 온전한 휴식이 확보된다. 지나간 마감을 따라잡아 곧바로 출발하지 않는다.
                self._arm(now)
                return self._out(False)
            if gap > self.cfg["gap_s"]:
                self._arm(now)                         # 깨어나자마자 출발하지 않게
            if not valid:
                return self._out(False)
            if not _roam_inside(self.pos, bounds):
                self.pos = _roam_clamp(self.pos, bounds)   # 화면이 바뀌어 밖에 남은 창을 들인다
                self._clamp_home(bounds, screens)
                return self._out(True)
            if now < self._next_at:
                return self._out(False)
            self._plan(now, cursor, bounds, screens)
            return self._out(False)                    # 계획한 step 에는 움직이지 않는다

        if hold or gap > self.cfg["gap_s"] or not valid:
            # 사용자 우선: 그 자리 정지, 순간이동 없음. 경계가 뒤집혀도 같은 처리다 —
            # 목표를 남겨 두면 화면이 돌아왔을 때 오래된 경로를 이어 걷게 된다.
            # 점프 중이면 전송 전엔 원래 화면, 뒤엔 착지 화면에 그대로 남는다.
            self._stop(now)
            return self._out(False)

        if not _roam_inside(self.pos, bounds):
            # 화면 구성이 바뀌어 창이 허용 범위 밖에 남았다. 창 전체가 다시 보이도록 안으로
            # 들이고, 하던 이동은 접는다 (계획된 점프와 달리 '복구' 다).
            self.pos = _roam_clamp(self.pos, bounds)
            self._clamp_home(bounds, screens)
            self._stop(now)
            return self._out(True)

        if self.phase == "look":
            if now >= self._look_until:
                self._stop(now, settled=True)          # 구경/산책 멈춤이 끝났다 — 그 자리에서 쉰다
            return self._out(False)

        if self.phase == "jump":
            return self._step_jump(now, cursor, screens)

        if self.phase == "follow":
            return self._step_follow(now, dt, cursor, bounds, screens)

        # out — 목표를 향해 걷는 leg
        leg = _roam_clamp(self._target, bounds)
        if (cursor is not None and _roam_seg_dist(cursor, self.pos, leg)
                < self.radius + self.cfg["cursor_margin_px"]):
            self._stop(now)                            # 커서를 가로지르지 않는다
            return self._out(False)
        remaining = _roam_dist(self.pos, leg)
        stride = self.cfg["walk_speed"] * dt
        if remaining <= max(stride, self.cfg["arrive_px"]):
            moved = leg != self.pos
            self.pos = leg
            self._watch(now)
            return self._out(moved)
        if stride <= 0.0:
            return self._out(False)
        f = stride / remaining
        self.pos = (self.pos[0] + (leg[0] - self.pos[0]) * f,
                    self.pos[1] + (leg[1] - self.pos[1]) * f)
        return self._out(True)

    def set_home(self, pos, now):
        """수동 배치(드래그 끝·크기 변경): 여기가 집이고 지금 자리다. 휴식부터."""
        self.home = (float(pos[0]), float(pos[1]))
        self.pos = self.home
        self.screen = None                             # 수동 배치: 다음 step 에 새 pos 로 화면을 다시 고른다
        self._last_now = float(now)
        self._stop(float(now), settled=True)

    def release(self, now, pos, moved):
        """드래그/클릭 끝. moved 면 새 집(자연 완료), 아니면 집은 그대로 두고 그 자리에
        선다 — 단순 클릭은 자연 완료가 아니다(settled=False)."""
        if moved:
            self.set_home(pos, now)
            return
        self.pos = (float(pos[0]), float(pos[1]))
        self.screen = None
        self._last_now = float(now)
        self._stop(float(now))


# ─────────── 조용한 동행 — 표시(접기/요약/전체) 순수 상태와 요약 내용 ───────────
# 사용자 요구: "이동 중엔 게이지는 접어서 넣어 두고, 와서 펼쳐 주거나 요약으로 작게".
# 사용자의 접기 선택(state["show_panel"])은 자동 표시가 절대 덮어쓰지 않는다 — 화면에
# 그릴 모드는 매번 RoamDisplay.mode(phase, show_panel) 로 유도한다.
# 표시는 한 줄 요약 필 하나뿐이다. full 과 summary 는 **같은 필**(같은 글자, 같은 기하)이고, 무엇이
# 켰는가만 다르다: full = 사용자의 평소 선택(show_panel), summary = 구경·follow 도착 래치(평소 선택이
# 접기여도 잠시 보여 준다). folded = 펫만.
DISPLAY_FULL = "full"           # 평소 선택으로 켜진 요약 필
DISPLAY_FOLDED = "folded"       # 펫만 (걷는 동안, 산책 멈춤, 사용자의 접기 선택)
DISPLAY_SUMMARY = "summary"     # 도착 래치로 켜진 요약 필 — 그리기·기하는 full 과 같다


class RoamDisplay:
    """Roamer 의 phase 를 표시 모드로 옮기는 순수 상태. 상태는 둘이다.

    summary   = 구경(approach)·따라다니기(follow) 도착(look)으로 켜진 요약 래치. 걷기·점프·follow
                시작, 자연 완료(구경 만료), 명시적 중단이 끈다. hover 로 멈춘 것은 중단이 아니라 래치를
                유지한다 — 요약을 보려면 커서를 올려야 하기 때문이다. 도착 자리에서의 구경은 "hover 로 멈춤"
                과 "6초가 끝남" 이 둘 다 rest 라, Roamer.settled 로 구별한다: settled=False(정지)면 유지,
                True(자연 완료)면 평소 선택으로 복원.
    dismissed = 래치 중 사용자가 접기/펴기 조작으로 필을 접어 둔 상태(그 방문 동안만). 평소 선택(show_panel)은
                건드리지 않으므로 자연 완료·중단 뒤엔 그 자리에서 평소 선택이 그대로 돌아온다. 래치가 꺼지면
                같이 꺼진다. 표시가 요약 필 하나로 통일되면서(2026-09-12) 옛 expanded(요약 ↔ 큰 게이지)의
                자리를 이것이 대신한다 — 접힌 평소 선택이 방문 한 번의 클릭으로 펼침으로 뒤집히면 안 된다.

    note() 의 우선순위: 명시적 중단/비활성 > 이동(걷기·점프·follow) > 구경/follow 도착 > 자연 완료 휴식(그 자리).
    note() 는 매 tick 불리며 look 동안 summary 를 계속 켠다 — dismissed 는 그 안에서도 유지된다.
    """

    def __init__(self):
        self.summary = False
        self.dismissed = False

    def reset(self):
        """수동 배치(드래그 끝 moved, set_home, 펫 교체) 와 메뉴 시작: 래치와 접어 둠을 둘 다 끈다."""
        self.summary = False
        self.dismissed = False

    def note(self, phase, kind, away, *, interrupted=False, enabled=True, settled=True):
        """매 tick, Roamer.step 직후. interrupted = 설정 창·메뉴·spike·공백 (dragging 은 아님:
        클릭의 mouseDown 도 한 tick dragging 을 세우므로, 진짜 드래그는 release(moved) 가 reset 한다).
        settled = Roamer.settled — rest 인데 자연 완료가 아니면(hover·클릭 정지) 래치를 유지한다."""
        if interrupted or not enabled:
            self.reset()
            return
        if phase in ("out", "jump", "follow"):
            self.reset()                               # 이동 중엔 접는다
        elif phase == "look" and kind in ("approach", "follow"):
            self.summary = True
        elif phase == "rest" and settled:
            self.reset()                               # 자연 완료 → 그 자리에서 평소 선택 (집이든 아니든)

    def toggle(self, show_panel):
        """접기/펴기 조작(꺾쇠 버튼·메뉴 '접기/펴기') → 새 show_panel.

        래치 중이면 그 방문 동안의 접어 둠(dismissed)만 뒤집고 show_panel 은 그대로 돌려준다(평소 선택 불변).
        아니면 기존처럼 반전한다.
        """
        if self.summary:
            self.dismissed = not self.dismissed
            return show_panel
        return not show_panel

    def mode(self, phase, show_panel):
        if phase in ("out", "jump", "follow"):
            return DISPLAY_FOLDED                  # 걷기·점프·follow 동안엔 무조건 접는다
        if self.summary:
            return DISPLAY_FOLDED if self.dismissed else DISPLAY_SUMMARY
        if phase == "look":
            return DISPLAY_FOLDED                  # 산책 멈춤: 조용히
        return DISPLAY_FULL if show_panel else DISPLAY_FOLDED


def _roam_valid_pct(value):
    """요약에 쓸 수 있는 수치인가 — 실수형(bool 제외), 유한, 0 이상. 아니면 버린다(0 으로 꾸미지 않는다)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value >= 0


def roam_summary(mode, oauth, stats, onboard, cost_today, has_admin_key, cost_month=None,
                 reset_texts=None, spike_first=False, cost_budget=None, auth_error=False):
    """요약 필 내용(Claude 구간) → (kind, payload). 데이터가 없으면 0% 를 지어내지 않고 상태 키를 준다.

    ("status", key)      key 는 TR 의 기존 키: need_admin_key / loading / onb_install / onb_login /
                         scanning / token_expired
    ("cost", (today, month, budget))   API 모드의 오늘·이달 비용과 월 예산. month/budget 은 없으면 None
    ("exact", rows)      정확 모드: 앞 3행(세션·주간·모델) 중 유효 행. 호출자는 크레딧 등 게이지가 아닌 행을
                         빼고 넘긴다(어댑터 roam_summary_text 참조).
    ("estimate", rows)   로그 추정: 세션·주간·모델 게이지 중 유효 행.
    rows 의 원소는 (label, pct, spiking, reset_text):
      label      exact 는 서버 라벨 원문(원문이 "session" 이어도 번역 키가 아니다), estimate 는 "session"/"weekly"
                 (TR 키 — 어댑터가 t() 로 옮긴다) 또는 모델 라벨 원문(예: "Fable").
      spiking    이 게이지의 급증 여부. estimate 는 stats["spikes"][gauge], exact 는 첫 행(세션)만 spike_first.
      reset_text 리셋 시각 문구(호출자가 fmt_countdown 으로 만든 문자열) 또는 None. exact 행은 row[2] 를 그대로
                 쓰고, estimate 는 reset_texts[gauge] 를 쓴다 — 이 함수는 시각을 계산하지 않는다(순수).
    정확 모드 행이 있는데 유효 행이 하나도 없으면 추정으로 내려가지 않고 상태를 준다.

    auth_error 는 '서버가 토큰을 거부했다'는 사실(OAUTH_STATUS["auth_error"])이고, 어댑터가 넘긴다 —
    이 함수는 순수하게 남는다. 창 안에 항목이 하나도 없는데(stats["entries"] == 0) 토큰까지 거부됐다면
    게이지 0% 는 사실이 아니라 무지다. 그때만 token_expired 를 주고, 그 판정은 온보딩 안내보다 앞선다
    (로그인은 이미 했고 토큰만 되살리면 되는 상태라, 'Claude Code 로그인 필요'보다 구체적이다).
    """
    if mode == "api":
        if not has_admin_key:
            return ("status", "need_admin_key")
        if not _roam_valid_pct(cost_today):
            return ("status", "loading")
        month = float(cost_month) if _roam_valid_pct(cost_month) else None
        budget = float(cost_budget) if _roam_valid_pct(cost_budget) and cost_budget > 0 else None
        return ("cost", (float(cost_today), month, budget))
    if oauth:
        rows = []
        for i, row in enumerate(list(oauth)[:3]):
            if not _roam_valid_pct(row[1]):
                continue
            reset_text = row[2] if len(row) > 2 and isinstance(row[2], str) and row[2] else None
            rows.append((row[0], float(row[1]), bool(spike_first) and i == 0, reset_text))
        return ("exact", rows) if rows else ("status", "scanning")
    # 창 안에 집계된 항목이 0개면 추정 게이지의 0% 는 '안 썼다'가 아니라 '모른다'다.
    # entries 키가 아예 없는 스냅샷은 그 사실을 말해 주지 않는 옛 모양이므로 0 으로 치지
    # 않는다 — 여기서 `not stats.get("entries")` 를 쓰면 키 없는 스냅샷과 stats=None 까지
    # '데이터 없음'으로 끌려들어와, 아직 첫 계산이 끝나지 않은 기동 직후에 만료를 외친다.
    no_data = isinstance(stats, dict) and stats.get("entries") == 0
    if auth_error and no_data:
        return ("status", "token_expired")
    if onboard in ("install", "login"):
        return ("status", "onb_" + onboard)
    if stats and not no_data:
        rows = []
        spikes = stats.get("spikes") if isinstance(stats.get("spikes"), dict) else {}
        resets = reset_texts if isinstance(reset_texts, dict) else {}
        model_label = str(stats.get("model_kw") or "opus").capitalize()
        for gauge, label in (("session", "session"), ("weekly", "weekly"), ("opus", model_label)):
            pct = ((stats.get(gauge) or {}).get("pct")
                   if isinstance(stats.get(gauge), dict) else None)
            if _roam_valid_pct(pct):
                rows.append((label, float(pct), bool(spikes.get(gauge)), resets.get(gauge) or None))
        if rows:
            return ("estimate", rows)
    return ("status", "scanning")


SUMMARY_APPROX = "≈"          # 로그 추정치 앞의 표식. 서버 값(exact)에는 붙이지 않는다
# 요약 필 글자색 — 사용자 결정 2026-09-12(같은 날 "텍스트랑 수치랑 색을 반대로" 로 확정). **수치**가 출처를
# 말한다: 정확 모드 에메랄드, 로그 추정 앰버, API 비용 코랄. **라벨**(세션·주간·모델, 오늘·이달)은 흰색이 기본이고
# 잔여량에 따라 경고색(50% 이상)·위험색(85% 이상)으로, 급증이면 ▲와 함께 위험색으로 바뀐다.
# 둘째 줄(리셋 시각)은 보조 글자색. 상태 문구는 기본 글자색.
SUMMARY_COLORS = {
    "exact": "#50C878",       # emerald — 정확 모드 수치
    "estimate": "#FFB300",    # amber — 로그 추정 수치
    "cost": "#FF7F50",        # coral — API 비용 금액
    "value": TXT_MAIN,        # 라벨 기본(흰색)
    "warn": COL_WARN,         # 라벨: 50% 이상
    "bad": COL_BAD,           # 라벨: 85% 이상 또는 급증
    "sub": TXT_SUB,           # 둘째 줄(리셋 시각)
    "status": TXT_MAIN,
}
SUMMARY_SEP = " · "
SUMMARY_SPIKE = "▲"           # 급증 행의 라벨 앞 표식 — 색이 이미 급증을 말하므로 글자(급증)는 붙이지 않는다


def summary_value_kind(pct, spiking=False):
    """잔여량 글자색 종류(라벨에 입힌다) — 옛 게이지 막대의 문턱(50/85)과 같다. 급증이면 위험색."""
    if spiking or pct >= 85:
        return "bad"
    return "warn" if pct >= 50 else "value"


def _summary_label(kind, label, tr):
    return tr(label) if kind == "estimate" and label in ("session", "weekly") else label


def roam_summary_line(kind, payload, tr):
    """roam_summary 결과(구간 하나) → 요약 필 첫 줄의 평문(색 없음). tr 은 번역 콜러블(어댑터는 t).

    exact    라벨 원문 그대로, 표식 없음:      "Session 42% · Weekly 17% · Fable 12%"
    estimate session/weekly 는 tr, 모델 라벨은 원문, 값 앞에 ≈:  "세션 ≈42% · 주간 ≈17% · Fable ≈12%"
    급증 행은 라벨 앞에 ▲(SUMMARY_SPIKE).
    cost     tr("today") 와 달러 두 자리, 이달이 있으면 이어서, 예산이 있으면 " / $예산":   "오늘 $1.23 · 이달 $27.50 / $50"
    status   tr(key)
    """
    return "".join(text for text, _kind in roam_summary_runs([(kind, payload)], tr)[0])


def roam_summary_reset_line(kind, payload, tr):
    """둘째 줄 평문: tr("reset_prefix") 한 번 뒤에 "라벨 남은시간" 을 " · " 로, 같은 문구가 이어지면 한 번만. 없으면 ""."""
    return "".join(text for text, _kind in roam_summary_runs([(kind, payload)], tr)[1])


def _summary_segment_runs(kind, payload, tr):
    """구간 하나 → (첫 줄 run 들, 둘째 줄 run 들)."""
    if kind in ("exact", "estimate"):
        main, sub, last_reset = [], [], None
        approx = SUMMARY_APPROX if kind == "estimate" else ""
        for label, pct, spiking, reset_text in payload:
            if main:
                main.append((SUMMARY_SEP, "status"))
            shown = _summary_label(kind, label, tr)
            # 라벨 = 잔여량 색(급증이면 ▲ + 위험색), 수치 = 출처 색(exact/estimate)
            main.append(((SUMMARY_SPIKE if spiking else "") + shown, summary_value_kind(pct, spiking)))
            main.append((f" {approx}{pct:.0f}%", kind))
            if reset_text and reset_text != last_reset:
                sub.append((SUMMARY_SEP, "sub") if sub else (tr("reset_prefix"), "sub"))
                sub.append((f"{shown} {reset_text}", "sub"))
            last_reset = reset_text or last_reset
        return main, sub
    if kind == "cost":
        today, month, budget = (tuple(payload) + (None, None))[:3]
        # 라벨(오늘·이달) = 잔여량 색 — 이달은 예산 대비(흰 → 노 → 빨), 금액 = 코랄, 예산이 있으면 " / $예산"
        runs = [(f"{tr('today')} ", "value"), (f"${today:.2f}", "cost")]
        if month is not None:
            month_kind = summary_value_kind(min(100.0, month / budget * 100)) if budget else "value"
            runs += [(SUMMARY_SEP, "status"), (f"{tr('this_month')} ", month_kind), (f"${month:.2f}", "cost")]
            if budget:
                runs.append((f" / ${budget:.0f}", "cost"))
        return runs, []
    return [(tr(payload), "status")], []


def roam_summary_runs(segments, tr):
    """구간 목록 → (첫 줄 run 들, 둘째 줄 run 들); run 은 (text, kind), kind 는 SUMMARY_COLORS 의 키.

    첫 줄은 라벨(흰색 → 경고 → 위험, 잔여량)과 수치(출처 색) 조각, 둘째 줄은 리셋 시각(보조색). 구간 사이는 기본색
    구분자. 지금은 Claude 구간 하나다 — GPT·Gemini 등 다른 제공자의 사용량은 (kind, payload) 구간을 뒤에
    붙이면 같은 줄에 이어진다. 그리기(draw_summary_pill)와 폭 계산은 run 단위라 손댈 곳이 없다.
    """
    main, sub = [], []
    for kind, payload in segments:
        m, s_ = _summary_segment_runs(kind, payload, tr)
        if not m:
            continue
        if main:
            main.append((SUMMARY_SEP, "status"))
        main.extend(m)
        if s_:
            if sub:
                sub.append((SUMMARY_SEP, "sub"))
            sub.extend(s_)
    return main, sub


def roam_fit_runs(runs, max_w, measure, ellipsis="…"):
    """폭 max_w 안에 들어가는 run 목록. measure(s) 는 s 의 폭 (그 줄의 폰트 하나로 잰다 — 축소 없음).

    다 들어가면 그대로. 아니면 뒤 run 부터 통째로 떼어 내고 마지막에 남은 run 을 roam_fit_text 로 말줄임한다.
    """
    def width(items):
        return sum(measure(text) for text, _kind in items)
    if width(runs) <= max_w:
        return list(runs)
    kept = list(runs)
    while kept:
        head, (text, kind) = kept[:-1], kept[-1]
        room = max_w - width(head)
        fitted = roam_fit_text(text, room, measure, ellipsis) if room > 0 else ""
        if fitted:
            return head + [(fitted, kind)]
        kept = head
        while kept and kept[-1][0] == SUMMARY_SEP:     # 구분자만 남기지 않는다
            kept = kept[:-1]
    return []


def roam_fit_text(text, max_w, measure, ellipsis="…"):
    """폭 max_w 안에 들어가는 문자열. measure(s) 는 s 의 폭.

    들어가면 원문 그대로. 아니면 실제로 측정해 가며 가장 긴 prefix + ellipsis 를 고른다
    (폰트 축소 없음 — 11pt 가독성 유지). ellipsis 하나도 안 들어가면 빈 문자열.
    """
    if measure(text) <= max_w:
        return text
    for n in range(len(text) - 1, -1, -1):
        candidate = text[:n] + ellipsis
        if measure(candidate) <= max_w:
            return candidate
    return ""


# ─────────── 조용한 동행 — 기하: 실제 창은 논리 full 창의 부분 사각형(crop) ───────────
# Roamer 는 '논리 full 창'(크기 W×H, 중심 roamer.pos, 배치 right/bottom)만 안다 — 중심·radius·
# bounds·집 전부 그대로다. 실제 NSWindow 는 그 창의 부분 사각형이고, 부분 사각형은 표시 모드
# 에서만 유도되므로 펫의 전역 좌표(논리 원점 + (px, py))는 모드와 무관하게 같다. 접기·요약·
# 펼침 전환에서 바뀌는 것은 창의 origin/size 뿐이다.
SUMMARY_H = 30            # 요약 필 높이(한 줄: 상태·비용, 또는 리셋 시각이 없을 때)
SUMMARY_H2 = 46           # 요약 필 높이(두 줄: 게이지 + 리셋 시각)
SUMMARY_MIN_W = 120       # 요약 필 최소 폭. 최대는 PILL_W


def roam_pill_rect(mode, right, bottom, W, PW, PH, pill_h, text_w=0, text_h=SUMMARY_H):
    """표시 모드의 필 사각형 (논리 창 flipped 좌표: 좌상단 원점). "folded" 면 None.

    full 과 summary 는 같은 필이다: 글자 폭에 맞춘(SUMMARY_MIN_W..PILL_W) 필을 펫 쪽에 정렬해 펫 위/아래에
    붙인다. 높이는 text_h(한 줄 SUMMARY_H 또는 두 줄 SUMMARY_H2, 띠 높이 pill_h 를 넘지 않음). 펫이 아래쪽이면
    띠 안에서 아래 맞춤(펫에 붙음), 위쪽이면 펫 바로 아래.
    """
    if mode in (DISPLAY_FULL, DISPLAY_SUMMARY):
        w = min(PILL_W, max(SUMMARY_MIN_W, text_w + 2 * PILL_PAD))
        h = min(pill_h, text_h)
        return (W - w - 4 if right else 4, pill_h + 4 - h if bottom else PH + GAP, w, h)
    return None


def _roam_union(rects):
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[0] + r[2] for r in rects)
    y1 = max(r[1] + r[3] for r in rects)
    return (x0, y0, x1 - x0, y1 - y0)


def roam_frame(center, mode, right, bottom, W, H, PW, PH, pill_h, scale, text_w=0, text_h=SUMMARY_H):
    """논리 full 창 → 표시 모드에 맞는 실제 창.

    center 는 논리 창 중심(스크린 좌표, y 위). 반환 dict:
      crop   (cx, cy, cw, ch)  논리 창 flipped 좌표의 부분 사각형. folded 는 펫 ∪ 꺾쇠 버튼,
                               full/summary 는 펫 ∪ 버튼 ∪ 요약 필 을 2pt 넓힌 것
      origin (x, y)            실제 창 원점(AppKit, y 위)
      size   (w, h)
      sprite / button / pill   실제 창 flipped 좌표의 사각형. folded 의 pill 은 None
    불변: crop ⊆ (0, 0, W, H) 이고, origin + sprite 의 전역 위치는 mode 와 무관하게 같다.
    """
    px = W - PW - 6 if right else 6
    py = pill_h + GAP if bottom else 2
    sprite = (px, py, PW, PH)
    bx = px - BTN_R * 2 - 2 if right else px + PW + 2
    by = py + int(26 * scale)
    button = (bx, by, BTN_R * 2, BTN_R * 2)
    pill = roam_pill_rect(mode, right, bottom, W, PW, PH, pill_h, text_w, text_h)
    # 실제 창은 언제나 펫 ∪ 버튼 (∪ 필) 을 2pt 넓힌 부분 사각형이다 — 필이 하나뿐이라 full 도 예외가 아니다.
    parts = [sprite, button] + ([pill] if pill is not None else [])
    ux, uy, uw, uh = _roam_union(parts)
    x0 = max(0, ux - 2)
    y0 = max(0, uy - 2)
    x1 = min(W, ux + uw + 2)
    y1 = min(H, uy + uh + 2)
    crop = (x0, y0, x1 - x0, y1 - y0)
    cx, cy, cw, ch = crop
    return {
        "crop": crop,
        "origin": (center[0] - W / 2 + cx, center[1] + H / 2 - cy - ch),
        "size": (cw, ch),
        "sprite": (px - cx, py - cy, PW, PH),
        "button": (bx - cx, by - cy, BTN_R * 2, BTN_R * 2),
        "pill": None if pill is None else (pill[0] - cx, pill[1] - cy, pill[2], pill[3]),
    }


def roam_logical_center(origin, size, crop, env):
    """실제 창(origin, size) 과 crop, 논리 크기 env=(W, H) → 논리 창 중심. crop 이 None 이면 창 중심."""
    if crop is None:
        return (origin[0] + size[0] / 2, origin[1] + size[1] / 2)
    cx, cy, cw, ch = crop
    W, H = env
    return (origin[0] - cx + W / 2, origin[1] - (H - cy - ch) + H / 2)


# ─────────────────────── GUI (macOS 네이티브 AppKit) ───────────────────────
# 행동 원칙:
#   · 평소엔 첫 프레임으로 "정지". 25초에 한 번만 숨쉬기
#   · 마우스가 가까이 오면 인사 (쿨다운 30초)
#   · 잡고 끌면 끄는 방향으로 달리기, 더블클릭 점프
#   · 토큰 소비 급증: 경고색 펄스 + 패닉 표정 + 게이지 ▲급증
#   · 스크롤 = 크기 조절 / 우클릭 = 메뉴(설정·접기·종료)

def run_gui():
    import math
    import time as _time
    try:
        from AppKit import (
            NSApplication, NSWindow, NSPanel, NSView, NSColor, NSImage, NSFont,
            NSBezierPath, NSMakeRect, NSMakePoint, NSMakeSize,
            NSScreen, NSTimer, NSEvent, NSWorkspace,
            NSMenu, NSMenuItem, NSTextField, NSSecureTextField, NSPopUpButton,
            NSAlert,
            NSButton, NSWindowStyleMaskBorderless, NSWindowStyleMaskTitled,
            NSWindowStyleMaskClosable, NSBackingStoreBuffered,
            NSFontAttributeName, NSForegroundColorAttributeName,
            NSCompositingOperationSourceOver, NSCompositingOperationSourceAtop,
            NSZeroRect, NSRectFillUsingOperation,
        )
        from Foundation import NSObject, NSAttributedString
        from PyObjCTools import AppHelper
    except ImportError:
        print("macOS 네이티브 렌더링에 pyobjc가 필요합니다. 설치:", file=sys.stderr)
        print("  pip3 install pyobjc-framework-Cocoa", file=sys.stderr)
        sys.exit(1)

    def hexcolor(h, a=1.0):
        h = h.lstrip("#")
        r, g_, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
        return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g_, b, a)

    C_PILL = hexcolor(PILL_BG, 0.96)
    C_MAIN = hexcolor(TXT_MAIN)
    C_SUB = hexcolor(TXT_SUB)
    C_BTNL = hexcolor("#2E2E33")

    def mono(size, bold=False):
        return NSFont.monospacedSystemFontOfSize_weight_(size, 0.4 if bold else 0.0)

    def register_bundled_font():
        """내장 Pretendard 를 이 프로세스에 등록한다(소스 실행용; 번들에선 plist 가 이미 했다 → 중복 등록
        오류는 무시). 등록 뒤 fontWithName 이 None 이면 내장 실패 — 호출자가 모노 글꼴로 내려간다."""
        path = bundled_font_path()
        if not path:
            return None
        try:
            from CoreText import CTFontManagerRegisterFontsForURL, kCTFontManagerScopeProcess
            from Foundation import NSURL
            CTFontManagerRegisterFontsForURL(NSURL.fileURLWithPath_(path),
                                             kCTFontManagerScopeProcess, None)
        except Exception:
            pass
        return NSFont.fontWithName_size_(SUMMARY_FONT_NAME, 11)

    def summary_font(size):
        f = NSFont.fontWithName_size_(SUMMARY_FONT_NAME, size) if _summary_font_ok["ok"] else None
        return f if f is not None else mono(size, True)

    _summary_font_ok = {"ok": register_bundled_font() is not None}
    _dbg("summary font:", SUMMARY_FONT_NAME if _summary_font_ok["ok"] else "fallback mono")

    F_SUMMARY = {NSFontAttributeName: summary_font(11),    # 요약 필 한 줄 — 유일한 필 글꼴 (Pretendard SemiBold)
                 NSForegroundColorAttributeName: C_MAIN}
    # 구간별 글자색(SUMMARY_COLORS)을 입힌 요약 글꼴. kind 가 표에 없으면 기본 글자색.
    F_SUMMARY_BY_KIND = {kind: {NSFontAttributeName: summary_font(11),
                                NSForegroundColorAttributeName: hexcolor(color)}
                         for kind, color in SUMMARY_COLORS.items()}
    F_SUMMARY_SUB = {NSFontAttributeName: summary_font(9.5),   # 둘째 줄(리셋 시각)
                     NSForegroundColorAttributeName: hexcolor(SUMMARY_COLORS["sub"])}
    F_SUMMARY_SUB_BY_KIND = {kind: {NSFontAttributeName: summary_font(9.5),
                                    NSForegroundColorAttributeName: hexcolor(color)}
                             for kind, color in SUMMARY_COLORS.items()}

    def astr(s, attrs):
        return NSAttributedString.alloc().initWithString_attributes_(s, attrs)

    # ── 펫 프레임 로더 ──
    # 두 가지 포맷 지원:
    #  (신형) 폴더에 pet.json + spritesheet.webp — 유저가 넣는 펫
    #  (구형) 폴더 아래 상태별 하위폴더(idle/, running/ …)에 PNG — 내장 고양이
    def _sheet_pixels(sheet):
        rep = sheet.representations()
        if rep:
            return int(rep[0].pixelsWide()), int(rep[0].pixelsHigh())
        s = sheet.size()
        return int(s.width), int(s.height)

    def _slice_sheet(sheet, fw, fh, cols, sheet_h, indices):
        out = []
        for i in indices:
            col, row = i % cols, i // cols
            x = col * fw
            y = sheet_h - (row + 1) * fh      # 좌상단 기준 → NSImage 좌하단 기준
            sub = NSImage.alloc().initWithSize_(NSMakeSize(fw, fh))
            sub.lockFocus()
            sheet.drawInRect_fromRect_operation_fraction_(
                NSMakeRect(0, 0, fw, fh), NSMakeRect(x, y, fw, fh),
                NSCompositingOperationSourceOver, 1.0)
            sub.unlockFocus()
            out.append(sub)
        return out

    def _load_sheet_pet(pet_dir, meta):
        """pet.json + spritesheet.webp (고정 v2 격자 규약) → 상태별 프레임."""
        sp = os.path.join(pet_dir,
                          meta.get("spritesheetPath") or "spritesheet.webp")
        sheet = NSImage.alloc().initWithContentsOfFile_(sp)
        if sheet is None:
            return None
        sheet_w, sheet_h = _sheet_pixels(sheet)
        sheet.setSize_(NSMakeSize(sheet_w, sheet_h))
        cols, rows = PET_SHEET_COLS, PET_SHEET_ROWS
        fw, fh = sheet_w // cols, sheet_h // rows
        if fw <= 0 or fh <= 0:
            return None
        out = {}
        for st, (row, count) in _pet_layout(meta).items():
            idxs = [row * cols + c for c in range(count)]
            imgs = _slice_sheet(sheet, fw, fh, cols, sheet_h, idxs)
            if imgs:
                out[st] = imgs
        return out or None

    def _load_folder_pet(pet_dir):
        out = {}
        for st in os.listdir(pet_dir):
            sd = os.path.join(pet_dir, st)
            if not os.path.isdir(sd):
                continue
            imgs = [NSImage.alloc().initWithContentsOfFile_(p)
                    for p in sorted(glob.glob(os.path.join(sd, "*.png")))]
            imgs = [i for i in imgs if i]
            if imgs:
                out[st] = imgs
        return out or None

    def load_pet_frames(pet_dir):
        """펫 폴더 → 상태별 프레임 dict. idle 없으면 None."""
        meta = _read_pet_json(pet_dir)
        frames_ = (_load_sheet_pet(pet_dir, meta) if meta is not None
                   else _load_folder_pet(pet_dir))
        if not frames_ or not frames_.get("idle"):
            return None
        for need in _PET_FALLBACK_STATES:
            frames_.setdefault(need, frames_["idle"])
        return frames_

    # ── 스프라이트 로드 (설정에 저장된 펫, 없으면 내장 고양이) ──
    cfg = load_config()
    # 동봉 펫 자산을 홈(~/.claude_pet)에 없는 것만 채운다 — 반드시 첫 discover_pets()
    # 전에. (여기서 처음 채워진 펫이 이 실행부터 바로 메뉴에 보이도록)
    _log_seed_report(seed_bundled_pet_assets())
    pet_list = discover_pets()
    if not pet_list:
        print(f"스프라이트를 찾지 못했습니다: {PET_DIR}", file=sys.stderr)
        sys.exit(1)
    sel = next((p for p in pet_list if p["id"] == cfg.get("pet")), None)
    frames = load_pet_frames(sel["dir"]) if sel else None
    if frames is None:                       # 저장된 펫이 사라졌거나 깨졌으면 기본으로
        sel = pet_list[0]
        frames = load_pet_frames(sel["dir"])
    if frames is None:
        print(f"스프라이트를 찾지 못했습니다: {sel['dir']}", file=sys.stderr)
        sys.exit(1)

    sz = frames["idle"][0].size()
    PW0 = int(sz.width // PET_SCALE_DOWN)
    PH0 = int(sz.height // PET_SCALE_DOWN)

    apply_config(cfg)
    g = {"scale": max(0.3, min(2.0, float(cfg.get("scale", 0.5))))}  # 기본 0.5×

    def geom():
        pw = int(PW0 * g["scale"])
        ph = int(PH0 * g["scale"])
        w = max(pw + BTN_R * 2 + 16, PILL_W + 8)
        h = ph + GAP + pill_h() + 4
        return pw, ph, w, h

    PW, PH, W, H = geom()

    state = {"stats": None, "cost": None, "cost_month": None, "oauth": None,
             "frame": 0, "mood": "idle", "override": None, "show_panel": True,
             "elapsed": 0.0, "resting": False, "rest_elapsed": 0.0,
             "last_mood": "idle", "dragging": False, "greet_cool": 0.0,
             "hover": False, "update": None,
             # 조용한 동행(Roamer) 어댑터의 키 — roam_tick() 참조.
             #   roam_layout: 자동 이동이 고정해 둔 (petOnRight, petOnBottom). 수동 드래그가 푼다.
             #   roam_anim:   우리가 켠 override 이름(남의 인사·점프와 구분).
             #   roam_hold:   메뉴 등 상호작용이 있었다는 한 번짜리 표시 → 다음 tick 정지.
             #   roam_release: mouseUp_ 이 부르는 훅(moved) — 창 없는 시험에선 없다.
             "roam_layout": None, "roam_anim": None, "roam_hold": False,
             "menu_open": False, "reduce_motion": False, "roam_release": None,
             # 표시(접기/요약/전체) 계층 — roam_apply_display() 참조. 없으면 실제 창 = 논리 창.
             #   roam_display: RoamDisplay. roam_env: 논리 full 창 (W, H). roam_crop: 실제 창이
             #   논리 창에서 잘려 나온 부분 사각형. roam_rects: roam_frame() 결과(실제 창 좌표).
             #   roam_mode: 마지막으로 적용한 표시 모드. roam_toggle/roam_interrupt: 훅.
             "roam_display": None, "roam_env": None, "roam_crop": None,
             "roam_rects": None, "roam_mode": None,
             "roam_toggle": None, "roam_interrupt": None,
             # 로그인 시 자동 실행: rightMouseDown_ 이 부르는 훅 → "on"|"off"|"approval"|
             # "unavailable". 메뉴를 열 때마다 OS 등록 상태를 다시 읽는다(설정 파일 아님).
             # 창 없는 시험(직접 만든 state)에선 없다 → 항목이 '사용 불가' 로 비활성.
             "autostart_read": lambda: autostart_read_state(*autostart_current()),
             # 구독 모드인데 Claude Code 데이터가 전혀 없을 때: None|'install'|'login'.
             # refresh 워커가 매 주기 갱신한다(아래 compute_onboard_state).
             "onboard": None,
             # 새로고침 워커(백그라운드 스레드)가 stats/oauth를 갱신한 뒤 세우는 플래그.
             # AppKit 뷰를 워커에서 직접 건드리면 안 되므로, 메인 스레드인 tick_이
             # 이 플래그를 보고 다시 그린다(TICK=0.05초 → 최대 50ms 지연).
             "repaint": False,
             # 새로고침 세대 번호(begin_refresh_generation/commit_refresh_result).
             "refresh_generation": 0}
    sticky = {"on": False}
    ui = {}   # 설정 창 위젯 참조 (GC 방지)
    def _run_update_check():
        """새 버전 확인 1회. 쿨다운을 확인 '전에' 찍지 않게 되면서, 확인이 도는
        동안 다음 새로고침이 같은 확인을 또 시작할 수 있다 → 한 번에 하나만."""
        if _upd_cache.get("busy"):
            return None                          # 이미 확인 중 — 호출자가 '바쁨' 으로 읽는다
        _upd_cache["busy"] = True
        try:
            return poll_github_update(state)     # 'update' | 'current' | 'failed'
        finally:
            _upd_cache["busy"] = False

    TICK = 0.05
    NEAR_PX = 100
    GREET_COOLDOWN = 30.0

    def set_override(name, sticky_flag=False):
        if state["override"] != name:
            state["frame"] = 0
            state["elapsed"] = 0.0
            state["resting"] = False
        state["override"] = name
        sticky["on"] = sticky_flag

    def clear_sticky():
        if sticky["on"]:
            sticky["on"] = False
            state["override"] = None
            state["frame"] = 0

    def spike_info(stats):
        if not stats or RUNTIME["mode"] == "api":
            return None
        sp = stats.get("spikes") or {}
        if sp.get("session"):
            return ("#FF453A", t("session"))
        if sp.get("opus"):
            return ("#BF5AF2", "Opus")
        if sp.get("weekly"):
            return ("#FF9F0A", t("weekly"))
        return None

    def current_mood():
        if state["override"]:
            return state["override"]
        stats = state["stats"]
        if stats and spike_info(stats):
            return "failed"
        if state["oauth"]:   # 정확 모드: 서버 %가 기준
            pct = max((row[1] for row in state["oauth"]), default=0)
            return "failed" if pct >= 85 else ("waiting" if pct >= 50 else "idle")
        return mood_for(stats) if stats else "idle"

    # ── 필 그리기 헬퍼 (클래스 밖: PyObjC 셀렉터 변환 회피) ──
    class PetView(NSView):
        def isFlipped(self):
            return True

        def acceptsFirstMouse_(self, event):
            return True

        def petOnRight(self):
            """펫이 화면 오른쪽 절반에 있으면 True → 필이 왼쪽으로 붙음.

            자동 이동 중에는 출발 때 고정한 값을 쓴다 — 창이 중앙선을 넘는 순간 펫이
            창 안에서 튀지 않게. 수동 드래그가 끝날 때만 다시 계산한다.
            """
            frozen = state.get("roam_layout")
            if frozen is not None:
                return frozen[0]
            w = self.window()
            scr = (w.screen() if w else None) or NSScreen.mainScreen()
            vf = scr.frame()
            # 실제 창은 접혀 있을 수 있으므로 실제 origin + 논리 W/2 를 섞지 않고 논리 중심으로 판정
            cx = window_center()[0] if w else vf.origin.x + W / 2
            return cx >= (vf.origin.x + vf.size.width / 2)

        def petOnBottom(self):
            """펫이 화면 아래쪽 절반에 있으면 True → 필이 위로 붙음. (고정 규칙은 petOnRight 와 같다)"""
            frozen = state.get("roam_layout")
            if frozen is not None:
                return frozen[1]
            w = self.window()
            scr = (w.screen() if w else None) or NSScreen.mainScreen()
            vf = scr.frame()
            cy = window_center()[1] if w else vf.origin.y + H / 2
            return cy < (vf.origin.y + vf.size.height / 2)

        # 아래 네 위치는 **실제 창** flipped 좌표다. 표시 계층이 crop 을 적용해 두었으면
        # (state["roam_rects"]) 그 값을 쓰고, 없으면 실제 창 = 논리 창이라 기존 계산과 같다.
        # drawRect_·mouseUp_ 버튼 판정·인사 pet_center 가 모두 여기를 거치므로 자동으로 맞는다.
        def pillRect(self):
            """요약 필 사각형(실제 창 flipped 좌표). 표시 계층이 아직 안 돌았으면 논리 창 = 실제 창이라
            같은 규칙(roam_pill_rect)으로 지금 글자 폭에 맞춰 계산한다. folded 면 None."""
            rects = state.get("roam_rects")
            if rects:
                return rects.get("pill")
            _main, _sub, text_w, text_h = roam_summary_text()
            return roam_pill_rect(roam_mode_now(), self.petOnRight(), self.petOnBottom(),
                                  W, PW, PH, pill_h(), text_w, text_h)

        def petOrigin(self):
            rects = state.get("roam_rects")
            if rects:
                return (rects["sprite"][0], rects["sprite"][1])
            py = pill_h() + GAP if self.petOnBottom() else 2
            # 버튼이 안쪽에 붙으므로 펫은 창 가장자리에 밀착
            if self.petOnRight():
                return (W - PW - 6, py)   # 펫 오른쪽 끝, 버튼은 왼쪽 안쪽
            return (6, py)                # 펫 왼쪽 끝, 버튼은 오른쪽 안쪽

        def btnOrigin(self):
            rects = state.get("roam_rects")
            if rects:
                return (rects["button"][0], rects["button"][1])
            px, py = self.petOrigin()
            by = py + int(26 * g["scale"])
            if self.petOnRight():
                return (px - BTN_R * 2 - 2, by)      # 펫 오른쪽 → 버튼 왼쪽
            return (px + PW + 2, by)                 # 펫 왼쪽 → 버튼 오른쪽

        def drawRect_(self, rect):
            stats = state["stats"]
            mood = state["mood"]
            seq = frames.get(mood, frames["idle"])
            fr = 0 if state["resting"] else state["frame"] % len(seq)
            img = seq[fr]

            # ── 요약 필 (펫 위치 기준 상하 플립 + 좌우 정렬) ──
            # 무엇을 그릴지는 사용자의 접기 선택이 아니라 표시 계층이 유도한 모드가 정한다:
            # 걷는 동안 접힘, 그 밖엔(평소 선택이 펼침이거나 도착 래치) 한 줄 요약 필.
            if roam_mode_now() in (DISPLAY_FULL, DISPLAY_SUMMARY):
                draw_summary_pill()

            # ── 펫 ──
            px, py = self.petOrigin()
            pet_rect = NSMakeRect(px, py, PW, PH)
            img.drawInRect_fromRect_operation_fraction_respectFlipped_hints_(
                pet_rect, NSZeroRect,
                NSCompositingOperationSourceOver, 1.0, True, None)

            spk = spike_info(stats)
            if spk:
                pulse = 0.22 + 0.18 * (0.5 + 0.5 * math.sin(_time.time() * 5))
                hexcolor(spk[0], pulse).set()
                NSRectFillUsingOperation(pet_rect,
                                         NSCompositingOperationSourceAtop)

            # ── 접기 버튼 (마우스 오버 시에만 표시) ──
            if state["hover"]:
                bx, by = self.btnOrigin()
                C_PILL.set()
                NSBezierPath.bezierPathWithOvalInRect_(
                    NSMakeRect(bx, by, BTN_R * 2, BTN_R * 2)).fill()
                C_BTNL.set()
                ring = NSBezierPath.bezierPathWithOvalInRect_(
                    NSMakeRect(bx, by, BTN_R * 2, BTN_R * 2))
                ring.setLineWidth_(1)
                ring.stroke()
                # 꺾쇠: 필이 열리는/닫히는 방향을 가리키도록 직접 그림
                pill_below = not self.petOnBottom()   # 필이 펫 아래에 붙는 배치
                # 열려 있으면(평소 선택이든 도착 래치든) '접는' 방향(필 반대쪽), 닫혀 있으면 '펼치는' 방향(필 쪽).
                is_open = roam_mode_now() in (DISPLAY_FULL, DISPLAY_SUMMARY)
                point_down = (pill_below and not is_open) or \
                             (not pill_below and is_open)
                cx, cy = bx + BTN_R, by + BTN_R
                wdt, hgt = 5.5, 3.0
                chev = NSBezierPath.bezierPath()
                chev.setLineWidth_(2.0)
                chev.setLineCapStyle_(1)   # round
                chev.setLineJoinStyle_(1)  # round
                if point_down:  # flipped 좌표: 아래 = y 증가
                    chev.moveToPoint_(NSMakePoint(cx - wdt, cy - hgt / 2))
                    chev.lineToPoint_(NSMakePoint(cx, cy + hgt))
                    chev.lineToPoint_(NSMakePoint(cx + wdt, cy - hgt / 2))
                else:
                    chev.moveToPoint_(NSMakePoint(cx - wdt, cy + hgt / 2))
                    chev.lineToPoint_(NSMakePoint(cx, cy - hgt))
                    chev.lineToPoint_(NSMakePoint(cx + wdt, cy + hgt / 2))
                C_SUB.set()
                chev.stroke()

        # ── 마우스 ──
        def mouseDown_(self, event):
            self._down = event.locationInWindow()
            state["dragging"] = True
            self._moved = False

        def mouseDragged_(self, event):
            loc = event.locationInWindow()
            dx = loc.x - self._down.x
            dy = loc.y - self._down.y
            if abs(dx) > 1 or abs(dy) > 1:
                self._moved = True
                if abs(dx) >= abs(dy):
                    set_override("running-right" if dx > 0 else "running-left",
                                 sticky_flag=True)
            w = self.window()
            o = w.frame().origin
            w.setFrameOrigin_(NSMakePoint(o.x + dx, o.y + dy))

        def mouseUp_(self, event):
            state["dragging"] = False
            clear_sticky()
            clamp_to_screen()   # 화면 밖으로 나갔으면 다시 안으로
            moved = bool(getattr(self, "_moved", False))
            if moved:
                # 진짜 드래그만 '수동 배치'다. 자동 이동이 고정해 둔 레이아웃을 풀고,
                # 새 자리를 저장한다. 자동으로 나가 있는 동안의 단순 클릭은 자동 위치를
                # 집으로 만들지도, x/y 로 저장하지도 않는다.
                state["roam_layout"] = None
                f = self.window().frame()
                lx, ly = f.origin.x, f.origin.y
                crop, env = state.get("roam_crop"), state.get("roam_env")
                if crop and env:
                    # 실제 창이 접힌 부분 사각형이면 저장하는 x/y 는 논리 full 창의 원점이다 —
                    # 다음 실행에서 full 창이 같은 자리에 뜬다.
                    lx = f.origin.x - crop[0]
                    ly = f.origin.y - (env[1] - crop[1] - crop[3])
                cfg["x"], cfg["y"] = lx, ly
                merge_config_updates({"x": lx, "y": ly})   # 이 경로가 가진 키만
            # Roamer 에는 state 의 훅으로 알린다(창 없는 시험에선 훅이 없다).
            hook = state.get("roam_release")
            if hook is not None:
                hook(moved)
            self.setNeedsDisplay_(True)  # 좌우 플립 반영
            if moved:
                return
            if event.clickCount() == 2:
                set_override("jumping")
                _oauth_cache["t"] = 0.0        # 캐시 무효화 → 즉시 재조회
                tk = state.get("ticker")
                if tk is not None:
                    tk.refresh_(None)           # 사용량 즉시 갱신
                return
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            bx, by = self.btnOrigin()
            if (loc.x - bx - BTN_R) ** 2 + (loc.y - by - BTN_R) ** 2 <= (BTN_R + 6) ** 2:
                # 요약(래치) 중엔 그 방문 동안 접기 ↔ 펴기만 오가고 평소 선택은 그대로(RoamDisplay.toggle).
                # 판정은 클릭 시점의 실제 창 좌표로 했고, 창 성장은 다음 틱이 한다.
                toggle = state.get("roam_toggle")
                state["show_panel"] = (toggle() if toggle is not None
                                       else not state["show_panel"])
                self.setNeedsDisplay_(True)

        def rightMouseDown_(self, event):
            # 메뉴는 '시작 시 복원': 요약 래치를 먼저 끄고 메뉴를 띄운다. 그래서 메뉴의
            # '접기/펴기' 는 래치 없이 평소 선택을 바꾸는 일반 토글이고, 메뉴 뒤에 오는
            # roam_hold 중단은 멱등이라 의도한 펼치기가 되돌려지는 일이 없다.
            interrupt = state.get("roam_interrupt")
            if interrupt is not None:
                interrupt()
            menu = NSMenu.alloc().initWithTitle_("ClaudePet")
            # NSMenu 는 기본(autoenablesItems=YES)으로 표시 직전에 항목을 다시 검증해, target 이
            # action 에 응답하면 enabled 를 YES 로 되돌린다 — 아래 setEnabled_(False) 가 덮인다.
            # 우리는 항목별로 직접 정하므로 자동 활성화를 끈다. 다른 항목은 기본값(YES) 그대로.
            menu.setAutoenablesItems_(False)
            for title, action in ((t("menu_settings"), "openSettings:"),
                                  (t("menu_toggle"), "togglePanel:"),
                                  (t("menu_roam"), "toggleRoam:"),
                                  (t("menu_autostart"), "toggleAutostart:"),
                                  (t("menu_reset_size"), "resetScale:"),
                                  (None, None),
                                  (t("menu_uninstall"), "uninstallApp:"),
                                  (t("menu_quit"), "quitApp:")):
                if title is None:
                    menu.addItem_(NSMenuItem.separatorItem())
                    continue
                mi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    title, action, "")
                mi.setTarget_(handler)
                if action == "toggleRoam:":
                    mi.setState_(1 if RUNTIME.get("roam") else 0)   # 체크 표시
                    # macOS '동작 줄이기' 가 켜져 있으면 어차피 움직이지 않는다 → 비활성
                    mi.setEnabled_(not state["reduce_motion"])
                elif action == "toggleAutostart:":
                    # 체크 표시는 설정 파일이 아니라 OS 등록 상태에서 온다 — 메뉴를 열
                    # 때마다 훅으로 다시 읽으므로 시스템 설정에서 바꾼 것도 그대로 보인다.
                    # 훅은 state 에 있다(roam_interrupt 와 같은 모양): 창 없는 시험에선
                    # 없고, 그때는 '사용 불가' 다.
                    read = state.get("autostart_read")
                    a_state = read() if read is not None else "unavailable"
                    if a_state == "unavailable":
                        # 소스 실행, macOS 12(SMAppService 없음), 또는 서비스가 없음
                        mi.setTitle_(t("autostart_unavailable"))
                        mi.setEnabled_(False)
                    else:
                        # -1 = NSControlStateValueMixed: 등록은 됐지만 승인 대기
                        mi.setState_({"on": 1, "off": 0}.get(a_state, -1))
                menu.addItem_(mi)
            # 펫 선택 서브메뉴 (우클릭 때마다 폴더를 새로 스캔 → 새로 넣은 펫 즉시 반영)
            pet_list = discover_pets()
            if pet_list:
                cur_pet = cfg.get("pet") or pet_list[0]["id"]
                sub = NSMenu.alloc().initWithTitle_("Pets")
                for p in pet_list:
                    it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                        p["name"], "selectPet:", "")
                    it.setTarget_(handler)
                    it.setRepresentedObject_(p["id"])
                    if p["id"] == cur_pet:
                        it.setState_(1)                     # NSControlStateValueOn
                    sub.addItem_(it)
                sub.addItem_(NSMenuItem.separatorItem())
                add_it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    t("pet_add"), "addPet:", "")
                add_it.setTarget_(handler)
                sub.addItem_(add_it)
                pet_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    t("menu_pets"), None, "")
                pet_item.setSubmenu_(sub)
                menu.insertItem_atIndex_(pet_item, 5)       # '크기 원래대로' 다음
            # 버전 표시 (비활성 항목)
            menu.addItem_(NSMenuItem.separatorItem())
            vitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"ClaudePet v{APP_VERSION}", None, "")
            vitem.setEnabled_(False)
            menu.addItem_(vitem)
            # 업데이트 확인… — 지금 확인해서 새 버전이 있으면 바로 내려받아 설치·재실행(한 번에).
            # 주기 확인(1시간)을 기다리지 않아도 되게 한다. 사용자 요구 2026-09-11.
            chk = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                t("menu_check_update"), "checkUpdate:", "")
            chk.setTarget_(handler)
            menu.addItem_(chk)
            upd = state.get("update")
            if upd:   # 새 버전 있으면 최상단에 설치 항목
                top = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    t("menu_update", v=upd[0]), "doUpdate:", "")
                top.setTarget_(handler)
                menu.insertItem_atIndex_(NSMenuItem.separatorItem(), 0)
                menu.insertItem_atIndex_(top, 0)
            ob = state.get("onboard")
            if ob:   # Claude Code 없으면 최상단에 설치/로그인 항목
                title, action = ((t("menu_install_cc"), "installClaude:")
                                 if ob == "install"
                                 else (t("menu_login_cc"), "loginClaude:"))
                top = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    title, action, "")
                top.setTarget_(handler)
                menu.insertItem_atIndex_(NSMenuItem.separatorItem(), 0)
                menu.insertItem_atIndex_(top, 0)
            # 메뉴는 동기 추적 루프라 그동안 틱이 멈춘다. 자동 이동은 명시적으로 막고,
            # 닫힌 뒤 첫 틱이 반드시 '그 자리 정지' 로 처리하도록 한 번짜리 표시를 남긴다.
            state["menu_open"] = True
            try:
                NSMenu.popUpContextMenu_withEvent_forView_(menu, event, self)
            finally:
                state["menu_open"] = False
                state["roam_hold"] = True

        def scrollWheel_(self, event):
            set_scale(g["scale"] + event.scrollingDeltaY() * 0.004)

    # ── 화면 경계 클램프: 창이 모든 모니터 밖으로 나가 증발하는 것 방지 ──
    def clamp_to_screen():
        """논리 full 창 전체가 가장 가까운 화면의 visibleFrame 안에 들어가게 한다.

        실제 창이 접혀 있어도(crop) 기준은 **논리 창**이다. 접힌 창만 화면 안에 두면 논리
        원점이 화면 밖에 저장되고 집도 그리로 잡혀, 다음에 펼쳐질 때 펫이 화면 밖에 놓인다.
        crop 이 없으면(시작 시) 실제 창 = 논리 창이라 기존 동작과 같다.
        """
        lx, ly = roam_logical_origin()
        w_, h_ = roam_env()
        cx = lx + w_ / 2
        cy = ly + h_ / 2
        best, best_d = None, None
        for scr in NSScreen.screens():
            vf = scr.visibleFrame()
            dx = max(vf.origin.x - cx, 0, cx - (vf.origin.x + vf.size.width))
            dy = max(vf.origin.y - cy, 0, cy - (vf.origin.y + vf.size.height))
            d = dx * dx + dy * dy
            if best_d is None or d < best_d:
                best, best_d = vf, d
        if best is None:
            return
        # 논리 창 전체가 화면 안에 있도록 (필은 안쪽으로 플립되므로 이게 자연스러움)
        nx = min(max(lx, best.origin.x), best.origin.x + best.size.width - w_)
        ny = min(max(ly, best.origin.y), best.origin.y + best.size.height - h_)
        if abs(nx - lx) > 0.5 or abs(ny - ly) > 0.5:
            ccx, ccy, ccw, cch = roam_crop_now()
            win.setFrameOrigin_(NSMakePoint(nx + ccx, ny + (h_ - ccy - cch)))

    # ── 조용한 동행: Roamer(순수 상태기계) ↔ 창 사이의 얇은 어댑터 ──
    # 상태기계는 '논리 full 창'(크기 roam_env, 중심 roamer.pos)만 안다 — 중심·radius·
    # bounds·집이 전부 그 창 기준이다. 실제 NSWindow 는 그 창의 부분 사각형(crop)이고,
    # crop 은 표시 모드(접힘/요약/전체)에서만 유도되므로 펫의 전역 좌표는 모드와 무관하다.
    # 여기서 논리 ↔ 실제를 바꾸고, 허용 rect 를 화면에서 읽고, 플래그를 state 에서 모아
    # 넘기고, 결과를 창/애니메이션/표시에 반영한다. roamer 자체는 창이 만들어진 뒤(아래
    # 앱/윈도우 절)에서. roam_env/roam_crop/roam_display 가 없으면(창 없는 시험) 실제
    # 창 = 논리 창으로 동작한다.
    def roam_env():
        """논리 full 창 크기 (W, H). 표시 계층이 없으면 실제 창 크기."""
        env = state.get("roam_env")
        if env:
            return env
        f = win.frame()
        return (f.size.width, f.size.height)

    def roam_crop_now():
        """현재 crop (cx, cy, cw, ch), 논리 창 flipped 좌표. 없으면 논리 창 전체."""
        crop = state.get("roam_crop")
        if crop:
            return crop
        w_, h_ = roam_env()
        return (0.0, 0.0, w_, h_)

    def window_center():
        """논리 full 창의 중심 (스크린, y 위). crop 이 없으면 실제 창 중심과 같다."""
        f = win.frame()
        cx, cy, cw, ch = roam_crop_now()
        w_, h_ = roam_env()
        return (f.origin.x - cx + w_ / 2, f.origin.y - (h_ - cy - ch) + h_ / 2)

    def roam_logical_origin():
        """논리 full 창의 원점 (스크린, y 위)."""
        f = win.frame()
        cx, cy, cw, ch = roam_crop_now()
        w_, h_ = roam_env()
        return (f.origin.x - cx, f.origin.y - (h_ - cy - ch))

    def place_window_center(pos):
        """논리 중심 pos 에 맞춰 실제 창(현재 crop)을 놓는다. 크기가 다르면 크기까지."""
        cx, cy, cw, ch = roam_crop_now()
        w_, h_ = roam_env()
        ox = pos[0] - w_ / 2 + cx
        oy = pos[1] + h_ / 2 - cy - ch
        f = win.frame()
        if abs(f.size.width - cw) > 0.5 or abs(f.size.height - ch) > 0.5:
            win.setFrame_display_(NSMakeRect(ox, oy, cw, ch), True)
            view.setFrame_(NSMakeRect(0, 0, cw, ch))
        else:
            win.setFrameOrigin_(NSMakePoint(ox, oy))

    def roam_bounds():
        """논리 full 창 전체가 화면(visibleFrame) 안에 남는, 논리 중심의 허용 rect."""
        scr = win.screen() or NSScreen.mainScreen()
        return roam_screen_bounds(scr)

    def roam_screen_bounds(scr):
        vf = scr.visibleFrame()
        w_, h_ = roam_env()
        return (vf.origin.x + w_ / 2, vf.origin.y + h_ / 2,
                vf.origin.x + vf.size.width - w_ / 2,
                vf.origin.y + vf.size.height - h_ / 2)

    def roam_screen_id(scr):
        """안정 화면 식별자: NSScreenNumber. 없으면(가짜 화면) frame 튜플 — 화면마다 다르다."""
        desc = getattr(scr, "deviceDescription", None)
        num = desc().get("NSScreenNumber") if desc is not None else None
        if num is not None:
            return int(num)
        f = scr.frame()
        return (float(f.origin.x), float(f.origin.y), float(f.size.width), float(f.size.height))

    def roam_screens():
        """모든 화면의 RoamScreen(id, 실제 frame, 중심 허용 bounds). 창보다 작은 화면은 뺀다.

        frame 은 커서 소속 판정용(메뉴 막대 포함 실제 rect), bounds 는 착지·pos 제약용 —
        상태기계가 둘을 분리해서 쓴다. 현재 화면은 상태기계가 pos 로 확정한다.
        """
        out = []
        for scr in NSScreen.screens():
            b = roam_screen_bounds(scr)
            if b[0] > b[2] or b[1] > b[3]:
                continue
            f = scr.frame()
            out.append(RoamScreen(roam_screen_id(scr),
                                  (f.origin.x, f.origin.y,
                                   f.origin.x + f.size.width, f.origin.y + f.size.height), b))
        return tuple(out)

    def roam_current_bounds():
        """상태기계가 확정한 현재 화면의 bounds. 아직 없으면(첫 tick 전) 창이 있는 화면."""
        for scr in roam_screens():
            if scr.id == roamer.screen:
                return scr.bounds
        return roam_bounds()

    def roam_env_update():
        """geom() 이 바뀐 직후(크기 조절·필 행 수·펫 교체)에 호출한다. 호출자가 실제 창을
        새 full 크기로 되돌려 두었으므로 crop 은 없고, 논리 크기는 새 W×H 다. 표시는
        다음 틱에 다시 잘린다."""
        state["roam_env"] = (float(W), float(H))
        state["roam_crop"] = None
        state["roam_rects"] = None
        state["roam_mode"] = None

    def roam_mode_now():
        """지금 그릴 표시 모드. 표시 계층이 아직 안 돌았으면 사용자 선택 그대로."""
        mode = state.get("roam_mode")
        if mode is None:
            return DISPLAY_FULL if state["show_panel"] else DISPLAY_FOLDED
        return mode

    _summary_memo = {"key": None, "value": None}

    def roam_summary_text():
        """요약 필 내용 → (첫 줄 run 들, 둘째 줄 run 들, 폭, 높이). exact 라벨은 원문, estimate 는 t() + ≈.

        말줄임은 하지 않는다 — 실제 필 폭을 아는 draw_summary_pill 이 같은 폰트로 맞춘다. 여기서 잰 폭은
        roam_frame 의 text_w 가 되고(roam_pill_rect 가 PILL_W 로 캡), 높이는 둘째 줄이 있으면 SUMMARY_H2.
        정확 모드 행은 크레딧(_label_order 9)만 빼고 앞 3행을 넘긴다 — 서버의 모델 라벨이 "Claude Fable 5" 처럼
        패밀리 단어가 아니어도 모델 행이 사라지지 않게. 리셋 시각은 여기서 fmt_countdown 으로 문자열로 만든다
        (roam_summary 는 시각을 계산하지 않는다). 토큰 만료(401 지속)로 추정치로 내려간 상태는 첫 줄 끝 ⚠.
        매 tick(20 Hz) 불리므로 같은 입력·같은 5초 창 안에서는 메모한 값을 돌려준다(글자 폭 측정 비용).
        """
        stats = state["stats"]
        oauth = state["oauth"]
        key = (RUNTIME["mode"], L["lang"], state.get("onboard"), id(stats), id(oauth), state["cost"],
               state["cost_month"], RUNTIME.get("api_budget"), bool(OAUTH_STATUS.get("auth_error")),
               int(_time.time() / 5))
        if _summary_memo["key"] == key:
            return _summary_memo["value"]
        if oauth:
            now_utc = datetime.now(timezone.utc)
            rows = []
            for label, pct, rdt, rtxt in oauth:
                if _label_order(label) >= 9:
                    continue
                reset_s = fmt_countdown(rdt, now_utc) if rdt is not None else (rtxt or None)
                rows.append((label, pct, reset_s))
            oauth = rows
        resets = None
        if stats and isinstance(stats.get("now"), datetime):
            resets = {g: fmt_countdown((stats.get(g) or {}).get("reset"), stats["now"])
                      for g in ("session", "weekly", "opus") if isinstance(stats.get(g), dict)}
        segment = roam_summary(RUNTIME["mode"], oauth, stats, state.get("onboard"), state["cost"],
                               bool(RUNTIME.get("admin_key")), state["cost_month"],
                               reset_texts=resets, spike_first=bool(spike_info(stats)),
                               cost_budget=float(RUNTIME.get("api_budget") or 0),
                               auth_error=bool(OAUTH_STATUS.get("auth_error")))
        main, sub = roam_summary_runs([segment], t)
        if segment[0] == "estimate" and OAUTH_STATUS.get("auth_error"):
            main.append((" ⚠", "status"))
        w_main = sum(astr(text, F_SUMMARY).size().width for text, _kind in main)
        w_sub = sum(astr(text, F_SUMMARY_SUB).size().width for text, _kind in sub)
        value = (main, sub, max(w_main, w_sub), (SUMMARY_H2 if sub else SUMMARY_H))
        _summary_memo["key"], _summary_memo["value"] = key, value
        return value

    def _draw_runs(runs, fonts_by_kind, fallback, x, w, cy):
        """run 들을 가로 가운데 정렬로, 세로는 cy 를 중심으로 그린다."""
        parts = [astr(text, fonts_by_kind.get(kind, fallback)) for text, kind in runs]
        total = sum(p.size().width for p in parts)
        cx = x + (w - total) / 2
        for p in parts:
            sz = p.size()
            p.drawAtPoint_(NSMakePoint(cx, cy - sz.height / 2))
            cx += sz.width

    def draw_summary_pill():
        """요약 필: 펫에 붙은 둥근 필. 첫 줄 = 라벨(잔여량 색)+수치(출처 색), 둘째 줄 = 리셋 시각(보조색).

        run 들이 필의 안쪽 폭(패딩 제외)을 넘으면 같은 폰트로 재면서 뒤에서부터 덜어내고 말줄임한다 — 폰트를
        줄이지 않으므로 측정과 그리기가 같은 글꼴로 일치한다.
        """
        pill = view.pillRect()
        if not pill:
            return
        x, y, w, h = pill
        C_PILL.set()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(x, y, w, h), h / 2, h / 2).fill()
        main, sub, _tw, _th = roam_summary_text()
        inner = w - 2 * PILL_PAD
        main = roam_fit_runs(main, inner, lambda v: astr(v, F_SUMMARY).size().width)
        if sub and h >= SUMMARY_H2:
            sub = roam_fit_runs(sub, inner, lambda v: astr(v, F_SUMMARY_SUB).size().width)
            _draw_runs(main, F_SUMMARY_BY_KIND, F_SUMMARY, x, w, y + 15)
            _draw_runs(sub, F_SUMMARY_SUB_BY_KIND, F_SUMMARY_SUB, x, w, y + h - 12)
        else:
            _draw_runs(main, F_SUMMARY_BY_KIND, F_SUMMARY, x, w, y + h / 2)

    def roam_apply_display(phase):
        """표시 모드 → crop/rect → 실제 창 크기·원점. 경로·집은 건드리지 않는다 → 다시 그릴지."""
        disp = state.get("roam_display")
        if disp is None:
            return False
        mode = disp.mode(phase, state["show_panel"])
        text_w, text_h = (roam_summary_text()[2:] if mode != DISPLAY_FOLDED else (0.0, SUMMARY_H))
        w_, h_ = roam_env()
        lay = roam_frame(roamer.pos, mode, view.petOnRight(), view.petOnBottom(),
                         w_, h_, PW, PH, pill_h(), g["scale"], text_w, text_h)
        crop = tuple(lay["crop"])
        changed = crop != state.get("roam_crop") or mode != state.get("roam_mode")
        if changed:
            # 변경 '직전' 실제 창의 논리 중심(옛 crop 으로 역산)을 기준으로 새 crop 을 놓는다.
            # roamer.pos 가 아니다: 드래그·clamp·필 행 수 변경처럼 창이 밖에서 움직인 뒤에
            # roamer.pos 로 되돌리면 사용자의 이동이 지워진다. 트립 중엔 두 값이 같다.
            center = window_center()
        state["roam_mode"] = mode
        state["roam_crop"] = crop
        state["roam_rects"] = lay
        if changed:
            place_window_center(center)
        return changed

    def _reduce_motion():
        try:
            ws = NSWorkspace.sharedWorkspace()
            return bool(ws.accessibilityDisplayShouldReduceMotion())
        except Exception:
            return False

    def roam_resync():
        """창 크기가 바뀐 뒤(크기 조절·필 행 수·펫 교체): 크기 변경도 조작이다.

        외접원 반지름을 새 크기로 갱신하고, 하던 이동은 그 자리에서 접는다. 나가
        있으면 상태기계의 자리(pos)가 기준이고, 집이면 새 창 중심이 집이다. 어느
        쪽이든 창 전체가 화면 안에 남도록 중심을 허용 범위로 들인 뒤 창을 놓는다.
        """
        w_, h_ = roam_env()
        roamer.radius = math.hypot(w_ / 2, h_ / 2)
        now = _time.monotonic()
        cx, cy = roamer.pos if roamer.away else window_center()
        x0, y0, x1, y1 = roam_current_bounds()      # 점프로 다른 화면에 있으면 그 화면 기준
        if x0 <= x1 and y0 <= y1:
            cx, cy = min(max(cx, x0), x1), min(max(cy, y0), y1)
        if roamer.away:
            roamer.release(now, (cx, cy), False)     # 그 자리 정지 + pos 동기화, 집은 그대로
        else:
            roamer.set_home((cx, cy), now)
        place_window_center((cx, cy))

    def roam_apply_effect(now, effect):
        """점프의 출발/착지 효과를 창 alpha 로 그린다. takeoff: 1 → 0.15 (jump_prep_s 동안),
        landing: 0.15 → 1 (jump_land_s 동안), 그 외(정상 완료·모든 취소 tick)엔 1 로 복원.
        값이 바뀔 때만 창을 건드린다 — 효과가 없던 tick 에는 호출이 없다."""
        fx = roam_clock.setdefault("fx", {"effect": None, "since": now, "alpha": 1.0})
        if effect != fx["effect"]:
            fx["effect"], fx["since"] = effect, now
        if effect == "takeoff":
            f = min(1.0, (now - fx["since"]) / max(roamer.cfg["jump_prep_s"], 1e-6))
            alpha = 1.0 - 0.85 * f
        elif effect == "landing":
            f = min(1.0, (now - fx["since"]) / max(roamer.cfg["jump_land_s"], 1e-6))
            alpha = 0.15 + 0.85 * f
        else:
            alpha = 1.0
        if abs(alpha - fx["alpha"]) > 1e-3:
            fx["alpha"] = alpha
            win.setAlphaValue_(alpha)

    def roam_tick():
        """Roamer 한 step 을 돌리고 창/애니메이션에 반영한다 → 다시 그릴지."""
        now = _time.monotonic()
        if now - roam_clock["rm_at"] >= 1.0:        # Reduce Motion 은 1 Hz 만 읽는다
            roam_clock["rm_at"] = now
            state["reduce_motion"] = _reduce_motion()
        enabled = bool(RUNTIME.get("roam")) and not state["reduce_motion"]
        # 남의 override(인사·점프·드래그 달리기)가 재생 중이면 출발하지 않고, 이동 중이면 선다
        blocked = bool(state["hover"]) or (state["override"] is not None
                                           and state["override"] != state["roam_anim"])
        busy = (bool(ui.get("panel")) or bool(state["menu_open"])
                or bool(state["roam_hold"]) or bool(spike_info(state["stats"])))
        state["roam_hold"] = False
        gap = now - roam_clock.get("last", now)
        roam_clock["last"] = now
        mp = NSEvent.mouseLocation()
        out = roamer.step(now, (mp.x, mp.y), roam_bounds(), enabled=enabled,
                          dragging=bool(state["dragging"]), blocked=blocked, busy=busy,
                          screens=roam_screens())
        roam_apply_effect(now, out.effect)
        disp = state.get("roam_display")
        if disp is not None:
            # 표시 계층: 걷는 동안 접기, 구경 도착 요약, 자연 완료·명시적 중단 시 그 자리에서 평소 선택 복원.
            # hover(blocked)·dragging 은 중단이 아니다 — 요약을 펼치려면 커서를 올려야 한다.
            disp.note(out.phase, roamer.kind, out.away,
                      interrupted=(not enabled) or busy or gap > roamer.cfg["gap_s"],
                      enabled=enabled, settled=roamer.settled)
        dirty = False
        if out.moved:
            if state["roam_layout"] is None:
                # 창을 옮기기 '전'의 배치를 고정한다 — 이동 중 중앙선을 넘어도 펫이 튀지 않게.
                # 수동 드래그(mouseUp_)만 이 고정을 푼다.
                state["roam_layout"] = (view.petOnRight(), view.petOnBottom())
            place_window_center(out.pos)
            dirty = True
        if roam_apply_display(out.phase):
            dirty = True
        if out.anim != state["roam_anim"]:
            if out.anim is not None:
                set_override(out.anim, sticky_flag=True)
            elif state["override"] == state["roam_anim"]:
                clear_sticky()                       # 우리가 켠 것만 끈다
            state["roam_anim"] = out.anim
            dirty = True
        return dirty

    # ── 크기 조절 ──
    def set_scale(value):
        nonlocal PW, PH, W, H
        new = max(0.3, min(2.0, value))
        if abs(new - g["scale"]) < 1e-4:
            return
        g["scale"] = new
        lx, ly = roam_logical_origin()      # 실제 창이 접혀 있어도 논리 full 창 기준
        PW, PH, W, H = geom()
        win.setFrame_display_(NSMakeRect(lx, ly, W, H), True)
        view.setFrame_(NSMakeRect(0, 0, W, H))
        view.setNeedsDisplay_(True)
        cfg["scale"] = round(g["scale"], 3)
        merge_config_updates({"scale": cfg["scale"]})      # 이 경로가 가진 키만
        roam_env_update()
        roam_resync()

    # ── 펫 교체 (라이브) ──
    def set_pet(pet_id):
        nonlocal PW0, PH0, PW, PH, W, H
        p = next((x for x in discover_pets() if x["id"] == pet_id), None)
        if not p:
            return
        nf = load_pet_frames(p["dir"])
        if nf is None:                          # 깨진 펫이면 조용히 무시
            return
        frames.clear()
        frames.update(nf)                       # PetView/Ticker가 참조하는 dict를 제자리 갱신
        sz2 = frames["idle"][0].size()
        PW0 = int(sz2.width // PET_SCALE_DOWN)
        PH0 = int(sz2.height // PET_SCALE_DOWN)
        lx, ly = roam_logical_origin()          # 실제 창이 접혀 있어도 논리 full 창 기준
        top = ly + roam_env()[1]                # 상단 고정한 채 크기만 갱신
        PW, PH, W, H = geom()
        win.setFrame_display_(NSMakeRect(lx, top - H, W, H), True)
        view.setFrame_(NSMakeRect(0, 0, W, H))
        state["frame"] = 0                      # 애니메이션 처음부터
        state["elapsed"] = 0.0
        view.setNeedsDisplay_(True)
        ok, merged = merge_config_updates({"pet": pet_id})  # 이 경로가 가진 키만
        if ok:                                  # 메모리 cfg 도 디스크와 맞춘다
            cfg.clear()
            cfg.update(merged)
        else:
            cfg["pet"] = pet_id
        roam_env_update()
        roam_resync()

    def open_user_pets_dir():
        try:
            os.makedirs(USER_PETS_DIR, exist_ok=True)
            _write_pets_readme(USER_PETS_DIR)   # 포맷 안내 + 예시 pet.json (없을 때만)
        except Exception:
            pass
        subprocess.Popen(["/usr/bin/open", USER_PETS_DIR])

    # ── 설정 창 ──
    def open_settings():
        interrupt = state.get("roam_interrupt")   # 설정 창은 명시적 중단: 요약 래치 해제
        if interrupt is not None:
            interrupt()
        if ui.get("panel"):
            ui["panel"].makeKeyAndOrderFront_(None)
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            return
        # 높이 예산: 1366x768 이 최소 지원 화면이고, 메뉴 바(25)와 Dock 을 빼면
        # 세로로 쓸 수 있는 것은 약 673 이다. 타이틀 바까지 더해도 안전하도록
        # 내용 높이는 **656 을 넘기지 않는다.**
        #   656(원래) − 88(옛 절대 한도 3줄, 별도 창으로 이전) + 44(note2 다줄화)
        #   = 612. 고급 창을 여는 버튼은 note3 와 같은 줄에 얹어 0 을 쓴다.
        # 세 칸을 이 창에 숨겨 두는 방식은 732 가 되어 저장 버튼이 잘렸다.
        PWID, PHT = 420, 612   # 한도 안내(다줄 note2) 포함, 절대 한도는 별도 창
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, PWID, PHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False)
        panel.setTitle_(t("settings_title"))
        # NSPanel 기본값(hidesOnDeactivate=YES)이면 다른 앱으로 전환하는 순간
        # 창이 사라진다. 이 창은 "Claude 앱 설정 > 사용량의 %를 보고 입력하라"고
        # 안내하는데, 그러려면 반드시 앱을 전환해야 한다. 게다가 LSUIElement 라
        # Dock 아이콘이 없어 사라지면 펫을 우클릭하는 것 말고는 되돌릴 길이 없다.
        panel.setHidesOnDeactivate_(False)
        # 자식 창과 같은 이유(아래 open_advanced_limits 참조): 창의 수명을
        # Cocoa 의 '닫으면 release' 에 맡기지 않고 우리가 명시적으로 관리한다.
        panel.setReleasedWhenClosed_(False)
        panel.setDelegate_(handler)   # X → windowWillClose_ → 자식 먼저 정리
        panel.center()
        cv = panel.contentView()

        def label(text, x, y, w=150, h=20):
            l = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            l.setStringValue_(text)
            l.setBezeled_(False)
            l.setDrawsBackground_(False)
            l.setEditable_(False)
            l.setSelectable_(False)
            if h > 20:
                # 여러 줄 라벨. NSTextField 는 기본이 한 줄이라, 문자열에 \n 을
                # 넣어도 그것만으로는 줄이 나뉘지 않고 잘린다 — 셋 다 켜야 한다:
                #   usesSingleLineMode=False  한 줄 강제 해제
                #   cell.wraps=True           줄바꿈 허용
                #   lineBreakMode=0           NSLineBreakByWordWrapping
                # 마지막 줄을 '…' 로 줄이는 동작도 끈다. 실패를 삼키지 않는 것이
                # 중요하다: 조용히 넘어가면 '설정한 것처럼 보이는데 잘리는' 상태가
                # 되고, 그건 지금 고치고 있는 바로 그 버그다.
                l.setUsesSingleLineMode_(False)
                c = l.cell()
                c.setWraps_(True)
                c.setLineBreakMode_(0)
                c.setTruncatesLastVisibleLine_(False)
            cv.addSubview_(l)
            return l

        def field(x, y, w, value, secure=False):
            cls = NSSecureTextField if secure else NSTextField
            f = cls.alloc().initWithFrame_(NSMakeRect(x, y, w, 22))
            f.setStringValue_(str(value))
            cv.addSubview_(f)
            return f

        y = PHT - 40
        label(t("s_pet"), 20, y)
        pet_list_s = discover_pets()
        pet_ids = [p["id"] for p in pet_list_s]
        pet_pop = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 220, 26), False)
        pet_pop.addItemsWithTitles_([p["name"] for p in pet_list_s])
        cur_pet = cfg.get("pet") or (pet_ids[0] if pet_ids else None)
        if cur_pet in pet_ids:
            pet_pop.selectItemAtIndex_(pet_ids.index(cur_pet))
        cv.addSubview_(pet_pop)

        y -= 34
        label(t("s_language"), 20, y)
        lang_pop = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 160, 26), False)
        lang_pop.addItemsWithTitles_([LANG_NAMES[c] for c in SUPPORTED_LANGS])
        lang_pop.selectItemAtIndex_(SUPPORTED_LANGS.index(L["lang"]))
        cv.addSubview_(lang_pop)

        y -= 34
        label(t("s_data_source"), 20, y)
        mode = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 220, 26), False)
        mode.addItemsWithTitles_([t("s_mode_sub"), t("s_mode_api")])
        mode.selectItemAtIndex_(1 if RUNTIME["mode"] == "api" else 0)
        cv.addSubview_(mode)

        y -= 34
        label(t("s_model_kw"), 20, y)
        f_kw = field(180, y - 2, 100, RUNTIME.get("model_keyword", "auto"))
        label(t("s_auto_detect"), 288, y, 120)

        y -= 34
        label(t("s_weekly_reset"), 20, y)
        wreset = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 130, 26), False)
        wreset.addItemsWithTitles_([t("s_rolling7")] + WEEKDAYS_FULL[L["lang"]])
        wd = RUNTIME.get("weekly_reset_day")
        wreset.selectItemAtIndex_(0 if wd is None else int(wd) + 1)
        cv.addSubview_(wreset)
        f_wh = field(318, y - 2, 40, int(RUNTIME.get("weekly_reset_hour", 20)))
        label(t("s_hour"), 362, y, 30)

        # ── 보정: Claude 앱의 % 입력 → 한도 자동 역산 ──
        y -= 40
        label(t("s_calib1"), 20, y, 380)
        y -= 20
        label(t("s_calib2"), 20, y, 380)
        y -= 28
        label(t("s_calib_session"), 20, y)
        f_cs = field(180, y - 2, 60, "")
        y -= 30
        label(t("s_calib_weekly_all"), 20, y)
        f_cw = field(180, y - 2, 60, "")
        y -= 30
        label(t("s_calib_weekly_model"), 20, y)
        f_cm = field(180, y - 2, 60, "")

        # 한도 안내 세 줄 —
        #  (1) 비워 두면 지금 적용 중인 한도가 그대로 유지된다.
        #  (2) 정확 모드에서는 게이지 %가 서버 값이라 보정이 필요 없지만,
        #      **급증 감지는 어느 모드에서든 이 추정 한도를 쓴다.** 예전 문구는
        #      "이 한도는 로그 추정 모드 전용"이었는데 그건 사실이 아니다 —
        #      is_spike() 가 RUNTIME["session_limit"] 로 판단하므로, 정확 모드
        #      사용자도 한도가 틀리면 급증 알림이 틀린다.
        #  (3) 같은 항목에 %와 한도를 모두 넣으면 %가 이긴다.
        # (2)(3) 은 조용히 일어나면 "저장했는데 안 바뀐다"로 보이므로 명시한다.
        #
        # note2 는 어느 언어에서도 한 줄에 들어가지 않는다. 380x20 한 줄에 두면
        # 뒤쪽('급증 감지는 추정 한도를 쓴다')이 잘려 나가는데, 하필 그 잘리는
        # 부분이 이 안내의 핵심이다. 그래서 문자열에 명시적 \n 을 넣는다.
        #
        # 다만 \n 만으로는 부족하다. 명시적 줄바꿈으로 나뉜 '각 줄'도 380px 를
        # 넘으면 다시 wrap 되므로, 2줄 프레임에 3줄이 들어가면 결국 잘린다.
        # 폰트 실측 없이 줄당 폭을 장담할 수 없어(여기서 GUI 를 띄울 수 없다)
        # **3줄 높이(52)로 잡아 한 줄이 한 번 더 접혀도 흡수되게** 한다.
        # 넘치는 쪽이 아니라 남는 쪽으로 틀리는 편이 낫다.
        #
        # 아래 y 간격은 각 라벨의 실제 높이(20/52/20)보다 크게 잡아 서로 겹치지
        # 않게 한다 — 예전에는 20 높이 라벨을 18 간격으로 쌓아 2px 씩 겹쳤다.
        y -= 30
        label(t("s_limit_note1"), 20, y, 380)          # [y, y+20]
        y -= 56
        label(t("s_limit_note2"), 20, y, 380, h=52)    # [y, y+52], 위와 4px 간격
        y -= 24
        label(t("s_limit_note3"), 20, y, 240)          # [y, y+20], 위와 4px 간격

        # 절대 토큰 한도는 '고급'이라 **별도 창**으로 뺀다. 세 칸을 이 창에 자리만
        # 비워 두고 숨기는 방식도 해 봤는데, 그러면 내용 높이가 732 가 되어
        # 1366x768 화면(메뉴 바·Dock 제외 약 673)에서 저장 버튼과 타이틀이 잘린다.
        # 여는 버튼은 note3 와 **같은 줄** 오른쪽에 얹어 세로를 한 줄도 쓰지 않는다.
        adv_btn = NSButton.alloc().initWithFrame_(NSMakeRect(268, y - 3, 132, 24))
        # 버튼은 짧은 키를 쓴다. 긴 s_limit_advanced 는 자식 창 '제목'으로 남는다 —
        # 제목 표시줄은 폭이 넉넉하지만 132px 버튼은 그렇지 않다.
        adv_btn.setTitle_(t("s_limit_advanced_button"))
        adv_btn.setBezelStyle_(1)      # 위 save_btn 과 같은 상수
        adv_btn.setTarget_(handler)
        adv_btn.setAction_("openAdvancedLimits:")
        cv.addSubview_(adv_btn)

        y -= 36
        label(t("s_spike_sens"), 20, y)
        sens = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(180, y - 3, 220, 26), False)
        sens.addItemsWithTitles_([t("s_sens_high"), t("s_sens_normal"), t("s_sens_low")])
        m = RUNTIME.get("spike_mult", 1.0)
        sens.selectItemAtIndex_(0 if m < 0.9 else (2 if m > 1.5 else 1))
        cv.addSubview_(sens)

        y -= 32
        greet = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 340, 22))
        greet.setButtonType_(3)  # 체크박스
        greet.setTitle_(t("s_greet"))
        greet.setState_(1 if RUNTIME.get("greet") else 0)
        cv.addSubview_(greet)

        y -= 34
        label(t("s_admin_key"), 20, y)
        f_key = field(180, y - 2, 220, RUNTIME.get("admin_key", ""), secure=True)
        y -= 30
        label(t("s_budget"), 20, y)
        f_bud = field(180, y - 2, 90, RUNTIME.get("api_budget") or 0)

        vl = label(f"ClaudePet v{APP_VERSION}", 20, 18, 200)
        vl.setTextColor_(NSColor.secondaryLabelColor())

        save_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(PWID - 110, 12, 90, 30))
        save_btn.setTitle_(t("s_save"))
        save_btn.setBezelStyle_(1)
        save_btn.setTarget_(handler)
        save_btn.setAction_("saveSettings:")
        cv.addSubview_(save_btn)

        # ses/wk/op(절대 한도)는 여기 없다 — 별도 '고급' 창이 생길 때 비로소
        # ui 에 들어온다. 그래서 그 창을 한 번도 열지 않았으면 adv_value() 가
        # "" 를 돌려주고, 그건 계약상 '기존 한도 유지'와 정확히 같은 값이다.
        ui.update({"panel": panel, "mode": mode,
                   "sens": sens, "greet": greet,
                   "key": f_key, "bud": f_bud, "kw": f_kw,
                   "wreset": wreset, "whour": f_wh, "lang": lang_pop,
                   "cs": f_cs, "cw": f_cw, "cm": f_cm,
                   "pet": pet_pop, "pet_ids": pet_ids})
        panel.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    # ── 고급: 절대 한도 창 ──
    ADV_FIELD_KEYS = ("ses", "wk", "op")

    def adv_value(key):
        """고급 창의 입력값. **창이 없으면 빈 문자열.**

        이 한 줄이 계약 전체를 떠받친다. 고급 창을 한 번도 열지 않은 사용자는
        '빈 칸'을 낸 것과 정확히 같아지고, 빈 칸은 prepare_settings_config 에서
        '기존 한도 유지'다. 창의 존재 여부가 저장 결과에 새 분기를 만들지 않는다.
        위젯을 미리 잡아 두지 않고 매번 ui 에서 조회하는 이유도 같다 — 창이 죽은
        뒤 참조만 살아남아 유령 값을 읽는 일이 없어야 한다.
        """
        w = ui.get(key)
        return w.stringValue() if w else ""

    def close_advanced():
        """고급 창을 떼어 내리고 참조를 지운다. 창과 참조는 반드시 같이 죽는다.

        세 경로에서 불린다: 저장, 본 창 닫힘, 그리고 **고급 창 자체의 X**.
        마지막 것이 처음 구현에서 빠져 있었다 — addChildWindow_ 는 부모→자식
        방향만 묶어 주므로, 자식의 X 는 이 함수를 지나지 않았다. 그러면 닫힌
        창을 가리키는 참조가 남고 adv_value() 가 그 stringValue() 를 읽어
        저장에 반영한다. 조회 방식만으로는 유령 값을 막지 못한다 — 지워 주는
        쪽이 있어야 비로소 막힌다.

        재진입 방지: 지금은 orderOut_ 이라 close 알림이 다시 오지 않지만,
        누군가 close() 로 바꾸면 delegate → 여기 → close() → delegate 가 된다.
        그 변경이 조용히 무한 재귀가 되지 않도록 깃발로 막아 둔다.
        """
        if ui.get("adv_closing"):
            return
        ui["adv_closing"] = True
        try:
            p = ui.get("adv_panel")
            if p:
                parent = ui.get("panel")
                if parent:
                    parent.removeChildWindow_(p)
                p.setDelegate_(None)
                p.orderOut_(None)
            ui["adv_panel"] = None
            for k in ADV_FIELD_KEYS:
                ui[k] = None
        finally:
            ui["adv_closing"] = False

    def close_main_panel():
        """본 창을 닫는 유일한 경로. 자식을 **먼저** 정리한다.

        순서가 뒤집히면 그 사이 자식이 부모 없이 화면에 남는다. 이 앱은
        LSUIElement 라 Dock 아이콘이 없어, 그렇게 남은 창은 사용자가 되돌릴
        방법이 사실상 없다.
        """
        close_advanced()
        p = ui.get("panel")
        if p:
            p.setDelegate_(None)
            p.orderOut_(None)
        ui["panel"] = None        # 다음에 열 때 새 언어로 재구성

    def open_advanced_limits():
        if ui.get("adv_panel"):
            ui["adv_panel"].makeKeyAndOrderFront_(None)
            return
        parent = ui.get("panel")
        if not parent:
            return                      # 본 창이 없으면 열지 않는다(고아 방지)
        # 폭 500 은 세 칸(라벨·입력·현재값)이 어느 locale 에서도 잘리지 않는
        # 최소치다. 380 일 때는 "Weekly limit (M tokens)" 같은 행 라벨과
        # "now: 98.765432M" 같은 현재값이 함께 잘렸다. 이 창은 본 창과 달리
        # 세로 예산(612/656)과 무관하므로 가로로 넉넉히 준다.
        AW, AH = 500, 190
        ap = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, AW, AH),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False)
        ap.setTitle_(t("s_limit_advanced"))     # 제목은 긴 키를 그대로 쓴다
        # 본 창과 같은 이유로 필요하다: 사용자는 %를 확인하러 Claude 앱으로
        # 전환하는데, 기본값이면 그 순간 창이 사라진다.
        ap.setHidesOnDeactivate_(False)
        # X 를 눌러도 객체가 해제되지 않게 한다. initWithContentRect: 로 만든
        # 창은 기본이 '닫으면 release' 다. windowWillClose_ 자체는 release 보다
        # **먼저** 오므로 그 안에서 해제된 객체를 만질 일은 없지만, 문제는 그
        # 뒤다 — ui 딕셔너리와 정리 흐름이 창을 명시적으로 붙잡고 있는 파이썬
        # 쪽 수명과 Cocoa 쪽 수명이 어긋나면, 이미 해제된 객체를 가리키는
        # 래퍼가 남는다. 수명을 우리가 명시적으로 관리하려고 끈다.
        ap.setReleasedWhenClosed_(False)
        ap.setDelegate_(handler)                # X → windowWillClose_ → 정리
        acv = ap.contentView()

        def alabel(text, x, yy, w=150, h=20):
            l = NSTextField.alloc().initWithFrame_(NSMakeRect(x, yy, w, h))
            l.setStringValue_(text)
            l.setBezeled_(False)
            l.setDrawsBackground_(False)
            l.setEditable_(False)
            l.setSelectable_(False)
            acv.addSubview_(l)
            return l

        def afield(x, yy, w):
            f = NSTextField.alloc().initWithFrame_(NSMakeRect(x, yy, w, 22))
            f.setStringValue_("")       # 항상 빈 칸 = 지금 한도 유지
            acv.addSubview_(f)
            return f

        yy = AH - 34
        alabel(t("s_limit_note1"), 16, yy, AW - 32)
        yy -= 30
        made = []
        for key_l, tokens in (("s_limit_session", RUNTIME["session_limit"]),
                              ("s_limit_weekly", RUNTIME["weekly_limit"]),
                              ("s_limit_model", RUNTIME["opus_limit"])):
            # 좌우 여백 16 대칭, 열 사이는 겹치지 않게 띄운다:
            #   라벨 16..186 | 입력 190..290 | 현재값 300..484 | 우여백 16
            alabel(t(key_l), 16, yy, 170)
            made.append(afield(190, yy - 2, 100))
            # 현재 값은 읽기 전용 라벨로만 보여 준다. 칸에 미리 채우면 '빈 칸이면
            # 안 건드린다'가 창을 열었는지에 따라 달라지는 조건부 성질이 된다.
            # 폭 184 는 "now: 98.765432M" 처럼 6자리까지 쓴 값이 들어가는 크기다.
            alabel(t("s_limit_current", value=fmt_limit_m(tokens)),
                   300, yy, 184)
            yy -= 30

        for k, w in zip(ADV_FIELD_KEYS, made):
            ui[k] = w
        ui["adv_panel"] = ap
        # 부모에 매달아 수명을 묶는다 — 본 창을 내리면 이 창도 함께 내려간다.
        parent.addChildWindow_ordered_(ap, 1)     # NSWindowAbove
        f = parent.frame()
        ap.setFrameOrigin_(NSMakePoint(f.origin.x + 30, f.origin.y + 40))
        ap.makeKeyAndOrderFront_(None)

    def settings_error(msg):
        """저장 실패 안내. 패널은 열어 둔 채, 설정/RUNTIME/state 는 그대로 둔다."""
        a = NSAlert.alloc().init()
        a.setMessageText_(t("s_err_title"))
        a.setInformativeText_(msg)
        a.runModal()

    def save_settings():
        """설정 저장. 검증 → 파일 기록이 모두 성공한 뒤에야 실제로 반영한다.

        예전에는 입력을 곧바로 cfg/RUNTIME 에 밀어 넣고 저장했다. 값 하나가
        이상해도 조용히 무시되거나(=저장했는데 안 바뀜) 반쯤 적용됐다.
        이제는 후보(candidate)를 따로 만들어 검증하고, 저장까지 성공해야
        cfg/RUNTIME/state 를 건드린다. 실패하면 창은 그대로 열려 있다.
        """
        # 위젯에서 '값'만 뽑아 낸다. 검증과 반영은 AppKit 을 모르는
        # plan_settings_save / apply_settings_plan 이 한다 — 그래야 전체
        # 원자성·상태 갱신·창 수명주기를 창 없이도 시험할 수 있다.
        pet_ids = ui.get("pet_ids") or []
        sel_pet = pet_ids[ui["pet"].indexOfSelectedItem()] if pet_ids else None
        prev_pet = cfg.get("pet") or (pet_ids[0] if pet_ids else None)
        widx = ui["wreset"].indexOfSelectedItem()
        form = {
            "pet": sel_pet,
            "lang": SUPPORTED_LANGS[ui["lang"].indexOfSelectedItem()],
            "mode": "api" if ui["mode"].indexOfSelectedItem() == 1 else "sub",
            "model_keyword": (str(ui["kw"].stringValue()).strip().lower()
                              or "auto"),
            "weekly_reset_day": None if widx == 0 else widx - 1,
            "weekly_reset_hour": ui["whour"].stringValue(),
            "api_budget": ui["bud"].stringValue(),
            "spike_mult": [0.5, 1.0, 2.0][ui["sens"].indexOfSelectedItem()],
            "greet": bool(ui["greet"].state()),
            "admin_key": str(ui["key"].stringValue()).strip(),
            # 고급 창을 안 열었으면 "" → 기존 한도 유지(창 존재가 분기를 만들지 않음)
            "session_limit_m": adv_value("ses"),
            "weekly_limit_m": adv_value("wk"),
            "opus_limit_m": adv_value("op"),
            "session_pct": ui["cs"].stringValue(),
            "weekly_pct": ui["cw"].stringValue(),
            "opus_pct": ui["cm"].stringValue(),
        }

        # 보정(%) 역산에 쓸 사용량은 새 키워드/주간 리셋 기준이어야 한다.
        # RUNTIME 을 미리 바꾸는 대신 스냅샷으로 계산한다(실패해도 RUNTIME 은 그대로).
        def stats_for(snapshot):
            snap = dict(RUNTIME)
            snap.update({k: v for k, v in snapshot.items() if v is not None
                         or k == "weekly_reset_day"})
            return compute_usage(runtime=snap)

        plan, err = plan_settings_save(cfg, form, stats_for=stats_for)
        if err:
            settings_error(err)     # 창은 열어 둔 채, 아무것도 바뀌지 않았다
            return
        ok, _merged = apply_settings_plan(plan, cfg, apply_fn=apply_config,
                                          set_pet_fn=set_pet, prev_pet=prev_pet)
        if not ok:
            settings_error(t("s_err_save"))
            return

        # ── 여기부터가 "성공" — 창을 정리하고 화면에 반영한다 ──
        # 적용한 %는 비운다 — 창을 X로 닫으면 패널이 재사용되는데, 남아 있던
        # %가 다음 저장 때 다시 적용돼 한도가 엉뚱하게 덮어써졌다.
        for fld in ("cs", "cw", "cm"):
            ui[fld].setStringValue_("")
        # 보정 결과가 반영된 사용량을 여기서(=반환 전에) state 에 넣는다.
        # 백그라운드 새로고침만 믿으면 "저장했는데 % 가 그대로"로 보였다.
        # 세대를 올려, 저장 전에 시작된 새로고침이 뒤늦게 덮어쓰지 못하게 한다.
        gen = begin_refresh_generation(state)
        commit_refresh_result(state, gen, {"stats": compute_usage()})
        state["repaint"] = True
        _oauth_cache["t"] = 0.0   # 정확 모드 라벨 언어 즉시 반영(캐시 무효화)
        # 저장 성공 경로도 같은 정리 함수를 쓴다 — 자식 먼저, 그다음 본 창.
        close_main_panel()
        ticker.refresh_(None)
        view.setNeedsDisplay_(True)

    # ── 메뉴/설정 핸들러 ──
    class Handler(NSObject):
        def openSettings_(self, sender):
            open_settings()

        def togglePanel_(self, sender):
            toggle = state.get("roam_toggle")      # 요약 중엔 요약 ↔ 전체, 아니면 평소 선택 반전
            state["show_panel"] = (toggle() if toggle is not None
                                   else not state["show_panel"])
            view.setNeedsDisplay_(True)

        def toggleRoam_(self, sender):
            # 우클릭 체크 항목. 끄면 다음 틱에 그 자리에서 선다(집으로 되돌리지 않는다).
            value = not RUNTIME.get("roam")
            RUNTIME["roam"] = value
            ok, merged = merge_config_updates({"roam": value})   # 이 경로가 가진 키만
            if ok:
                cfg.clear()
                cfg.update(merged)
            else:
                cfg["roam"] = value

        def toggleAutostart_(self, sender):
            # 우클릭 체크 항목. 결정은 autostart_toggle 이 하고, 여기서는 결과를 알릴
            # 뿐이다. 설정 파일에는 아무것도 쓰지 않는다 — 다음에 메뉴를 열면 OS 에서
            # 다시 읽는다.
            new_state, err = autostart_toggle(*autostart_current())
            if err:
                a = NSAlert.alloc().init()
                a.setMessageText_(t("autostart_title"))
                a.setInformativeText_(t("autostart_fail"))
                a.setAlertStyle_(2)                      # NSAlertStyleCritical
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
                a.runModal()
                return
            if new_state == "approval":
                # 등록은 됐지만 macOS 가 사용자의 승인을 기다린다. 첫 버튼이 기본값이라
                # 엔터가 곧 '로그인 항목 열기' 다.
                a = NSAlert.alloc().init()
                a.setMessageText_(t("autostart_title"))
                a.setInformativeText_(t("autostart_approval"))
                a.addButtonWithTitle_(t("autostart_open_settings"))
                a.addButtonWithTitle_(t("unin_cancel"))
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
                if a.runModal() == 1000:                 # 1000 = 첫 버튼
                    autostart_open_login_items()

        def resetScale_(self, sender):
            set_scale(0.5)

        def selectPet_(self, sender):
            set_pet(sender.representedObject())

        def addPet_(self, sender):
            open_user_pets_dir()

        def quitApp_(self, sender):
            NSApplication.sharedApplication().terminate_(None)

        def installClaude_(self, sender):
            # Terminal 에서 설치+로그인. 끝나면 다음 refresh 가 자동으로 감지한다.
            start_claude_install()

        def loginClaude_(self, sender):
            start_claude_login()

        def uninstallApp_(self, sender):
            app = app_bundle_path()
            items = list(uninstall_targets())
            if app:
                items.insert(0, app)
            home = os.path.expanduser("~")
            shown = "\n".join(
                "  • " + (p.replace(home, "~", 1) if p.startswith(home) else p)
                for p in items) or "  • (없음 / none)"
            a = NSAlert.alloc().init()
            a.setMessageText_(t("unin_title"))
            a.setInformativeText_(t("unin_body", items=shown))
            # 첫 버튼이 기본값이 되므로 '취소'를 먼저 넣어, 엔터 연타로
            # 실수로 지워지는 일이 없게 한다.
            a.addButtonWithTitle_(t("unin_cancel"))
            a.addButtonWithTitle_(t("unin_ok"))
            a.setAlertStyle_(2)                      # NSAlertStyleCritical
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            if a.runModal() != 1001:                 # 1001 = 두 번째 버튼(삭제)
                return
            quitting, err = do_uninstall()
            if quitting:
                NSApplication.sharedApplication().terminate_(None)
                return
            b = NSAlert.alloc().init()
            b.setMessageText_(t("unin_title"))
            if err == "autostart_fail":
                # 로그인 항목을 못 풀어 삭제를 거절했다 — 앱도 설정도 그대로다.
                msg = t("unin_fail") + "\n\n" + t("autostart_fail")
            else:
                msg = t("unin_fail") if err else t("unin_devmode")
            b.setInformativeText_(msg)
            b.runModal()

        def doUpdate_(self, sender):
            upd = state.get("update")
            if not upd:
                return
            def work():
                # 이름·아키텍처는 install_github_update 가 _upd_cache["choice"]
                # 에서 읽는다. 여기서 다시 만들어 내지 않는다.
                if install_github_update(upd[1], expect_version=upd[0]):
                    self.performSelectorOnMainThread_withObject_waitUntilDone_(
                        "quitApp:", None, False)
            threading.Thread(target=work, daemon=True).start()

        def checkUpdate_(self, sender):
            """우클릭 '업데이트 확인…': 지금 확인 → 새 버전이 있으면 바로 설치하고 재실행한다.

            확인은 GitHub 의 최신 릴리즈 하나만 보므로, 몇 버전을 건너뛰든 중간 버전을 거치지
            않고 곧장 최신으로 간다. 결과(최신임·확인 실패·설치 실패·이미 확인 중)는 알림 창 한
            번으로 알린다 — NSAlert 는 메인 스레드에서만 띄운다.
            """
            def work():
                status = _run_update_check()
                if status == "update":
                    upd = state.get("update")
                    if upd and install_github_update(upd[1], expect_version=upd[0]):
                        self.performSelectorOnMainThread_withObject_waitUntilDone_(
                            "quitApp:", None, False)
                        return
                    msg = t("upd_install_failed")
                elif status == "current":
                    msg = t("upd_current", v=APP_VERSION)
                elif status is None:
                    msg = t("upd_busy")
                else:
                    msg = t("upd_failed")
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "showUpdateMessage:", msg, False)
            threading.Thread(target=work, daemon=True).start()

        def showUpdateMessage_(self, msg):
            a = NSAlert.alloc().init()
            a.setMessageText_(t("upd_title"))
            a.setInformativeText_(str(msg))
            a.runModal()

        def saveSettings_(self, sender):
            save_settings()

        def openAdvancedLimits_(self, sender):
            # 절대 한도(고급) 창을 연다. 이미 열려 있으면 앞으로 가져오기만 한다.
            open_advanced_limits()

        def windowWillClose_(self, notification):
            """창의 X 로 닫힐 때. 어느 창인지는 알림의 object() 로 가른다.

            버튼을 거치지 않는 유일한 닫힘 경로라, 여기가 없으면 참조만 살아남아
            닫힌 창의 값이 저장에 실려 들어간다(고급 창), 또는 자식이 부모 없이
            남는다(본 창).
            """
            w = notification.object()
            if w is ui.get("adv_panel"):
                close_advanced()        # 자식만 정리 — 본 창은 그대로 열려 있다
            elif w is ui.get("panel"):
                close_main_panel()      # 자식 먼저, 그다음 본 창

    # ── 타이머 ──
    class Ticker(NSObject):
        def tick_(self, timer):
            mood = current_mood()
            if mood != state["last_mood"]:
                state["last_mood"] = mood
                state["frame"] = 0
                state["elapsed"] = 0.0
                state["resting"] = False
            state["mood"] = mood
            dur, loop, rest = STATE_CFG.get(mood, DEFAULT_CFG)
            dirty = False

            if state["resting"]:
                state["rest_elapsed"] += TICK * 1000
                if state["rest_elapsed"] >= rest:
                    state["resting"] = False
                    state["rest_elapsed"] = 0.0
                    state["frame"] = 0
                    state["elapsed"] = 0.0
            else:
                state["elapsed"] += TICK * 1000
                if state["elapsed"] >= dur:
                    state["elapsed"] = 0.0
                    seq_len = len(frames.get(mood, frames["idle"]))
                    nxt = state["frame"] + 1
                    if nxt >= seq_len:
                        state["frame"] = 0
                        if not loop and not sticky["on"]:
                            state["override"] = None
                        elif rest > 0 and not sticky["on"]:
                            state["resting"] = True
                    else:
                        state["frame"] = nxt
                    dirty = True

            # 마우스 호버 감지 (접기 버튼 표시용)
            mpos_h = NSEvent.mouseLocation()
            fh_ = win.frame()
            hover = (fh_.origin.x <= mpos_h.x <= fh_.origin.x + fh_.size.width
                     and fh_.origin.y <= mpos_h.y <= fh_.origin.y + fh_.size.height)
            if hover != state["hover"]:
                state["hover"] = hover
                dirty = True

            # 마우스 근접 인사 (평소엔 가만히)
            if (RUNTIME.get("greet") and not state["dragging"]
                    and state["override"] is None
                    and not spike_info(state["stats"])):
                now = _time.time()
                if now >= state["greet_cool"]:
                    mpos = NSEvent.mouseLocation()
                    f = win.frame()
                    px, py = view.petOrigin()          # 실제(접힐 수 있는) 창 좌표
                    cx = f.origin.x + px + PW / 2
                    cy = f.origin.y + (f.size.height - py - PH / 2)
                    if math.hypot(mpos.x - cx, mpos.y - cy) < NEAR_PX + PW / 2:
                        set_override("waving")
                        state["greet_cool"] = now + GREET_COOLDOWN
                        dirty = True

            # 조용한 동행 — 스스로 돌아다니기 (인사 판정 뒤, 같은 틱 안에서)
            if roam_tick():
                dirty = True

            if spike_info(state["stats"]):
                dirty = True
            # 새로고침 워커가 값을 갱신했으면 반드시 다시 그린다. 이게 없으면
            # 쉬는 동안(resting) 위 분기들이 dirty를 세우지 않아, 새 사용량이
            # 들어와도 최대 rest 시간(idle 기준 25초)까지 화면이 멈춰 있었다.
            # 보정(%) 입력이 "저장해도 반영 안 됨"으로 보이던 원인.
            if state["repaint"]:
                state["repaint"] = False
                dirty = True
            if dirty:
                view.setNeedsDisplay_(True)

        def refresh_(self, timer):
            # 이 요청의 세대 번호. 다 계산한 뒤 여전히 최신 세대일 때만 state 에
            # 넣는다 — 느린 옛 요청이 새 요청의 결과를 덮어쓰지 않도록.
            gen = begin_refresh_generation(state)

            def work():
                try:
                    s = compute_usage()
                    oauth = fetch_exact_usage()            # 정확 모드 (180s 캐시)
                    values = {"stats": s, "oauth": oauth,
                              "cost": fetch_api_cost_today()}
                    if RUNTIME["mode"] == "api":
                        values["cost_month"] = fetch_api_cost_month()
                    # Claude Code 데이터가 전혀 없으면 온보딩(설치/로그인) 안내.
                    # '파일이 있느냐'가 아니라 '창 안에 집계된 항목이 있느냐'로 본다 —
                    # 몇 달 전 로그 파일 하나가 남아 있다고 해서 지금 보여 줄 데이터가
                    # 있는 것은 아니고, 그 파일이 안내를 영원히 막고 있었다.
                    values["onboard"] = compute_onboard_state(
                        oauth, bool(s.get("entries")))
                    prev = state["stats"]
                    if not commit_refresh_result(state, gen, values):
                        return                             # 더 새 요청이 있다 → 버림
                    if prev and prev["session"]["pct"] > 5 and s["session"]["pct"] < 1:
                        set_override("jumping")
                    # 주기적 새 버전 확인 — 마지막 확인(또는 앱 시작)에서 UPDATE_CHECK_SEC 가 지났을 때만.
                    # 30초 새로고침에 얹혀 있으므로 실제 확인은 주기가 찬 뒤 첫 새로고침에서 일어난다.
                    if not state.get("update") and time.time() - _upd_cache["t"] > UPDATE_CHECK_SEC:
                        _run_update_check()
                finally:
                    # 값이 바뀌었으니 메인 스레드에 다시 그리라고 알린다.
                    # 중간에 예외가 나도 이미 갱신된 부분은 반영되도록 finally.
                    state["repaint"] = True
            threading.Thread(target=work, daemon=True).start()

    # ── 앱/윈도우 ──
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)

    vf = NSScreen.mainScreen().visibleFrame()
    x = cfg.get("x", vf.origin.x + vf.size.width - W - 36)
    y = cfg.get("y", vf.origin.y + 70)
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, W, H), NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setHasShadow_(False)
    win.setLevel_(25)
    # 모든 스페이스에 표시 + 전체화면 앱 위에도 보조로 표시
    win.setCollectionBehavior_(1 << 0 | 1 << 8)

    view = PetView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
    win.setContentView_(view)
    win.orderFrontRegardless()
    clamp_to_screen()   # 저장된 좌표가 화면 밖이면 안으로 복구

    # 조용한 동행: 집 = 지금(클램프된) 창 중심. 자동 이동은 x/y 를 저장하지 않는다.
    state["roam_env"] = (float(W), float(H))     # 논리 full 창 크기 — 지금은 실제 창도 full
    roamer = Roamer(window_center(), _time.monotonic(),
                    radius=math.hypot(W / 2, H / 2))
    roam_clock = {"rm_at": 0.0}
    roam_display = RoamDisplay()
    state["roam_display"] = roam_display

    def _roam_release(moved):
        roamer.release(_time.monotonic(), window_center(), moved)
        if moved:
            roam_display.reset()                 # 수동 배치 → 평소 선택
    state["roam_release"] = _roam_release
    state["roam_toggle"] = lambda: roam_display.toggle(state["show_panel"])
    state["roam_interrupt"] = roam_display.reset

    # 펫 폴더 안내 README 는 시작 때도 채운다(없거나 비어 있을 때만). '펫 추가…' 를 누르기 전에도
    # 폴더를 직접 열어 본 사용자가 안내를 볼 수 있어야 하고, 예전 판이 남긴 0 바이트 파일도 여기서 고쳐진다.
    try:
        os.makedirs(USER_PETS_DIR, exist_ok=True)
        _write_pets_readme(USER_PETS_DIR)
    except Exception:
        pass

    handler = Handler.alloc().init()
    ticker = Ticker.alloc().init()
    state["ticker"] = ticker   # 더블클릭 즉시 갱신용
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        TICK, ticker, "tick:", None, True)
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        REFRESH_SEC, ticker, "refresh:", None, True)
    ticker.refresh_(None)
    set_override("waving")

    # 새 릴리즈 확인은 시작 시 하지 않는다 — 사용자 요구(2026-09-11). 쿨다운의 기준점을 '지금'으로
    # 찍어 두면 새로고침 워커가 UPDATE_CHECK_SEC(1시간) 뒤부터 주기적으로 확인한다. 새 버전이면
    # 우클릭 메뉴에 노출되는 것은 그대로다.
    _upd_cache["t"] = time.time()

    AppHelper.runEventLoop()




# ─────────────────────── CLI 리포트 ───────────────────────

def print_report():
    exact = fetch_exact_usage()
    if exact:
        print("─" * 60)
        print(" " + t("r_exact"))
        for label, pct, rdt, rtxt in exact:
            reset = fmt_countdown(rdt, datetime.now(timezone.utc)) if rdt else (rtxt or "-")
            print(f" {label:<6} {pct:5.1f}%  · {t('r_reset')} {reset}")
    s = compute_usage()
    def line(name, g):
        print(f" {name:<6} {g['pct']:5.1f}%  {t('r_used')} {fmt_tokens(g['used'])} / {fmt_tokens(g['limit'])}"
              f"  · {t('r_left')} {fmt_tokens(g['left'])}  · {t('r_reset')} {fmt_countdown(g['reset'], s['now'])}")
    print("─" * 60)
    print(f" {t('r_title')}  ·  v{APP_VERSION}")
    print("─" * 60)
    line(t("session"), s["session"])
    line(t("weekly"), s["weekly"])
    line("Opus", s["opus"])
    if s["last_activity"]:
        print(f" {t('r_last_activity')}: {s['last_activity'].astimezone():%Y-%m-%d %H:%M}")
    cost = fetch_api_cost_today()
    if cost is not None:
        print(f" {t('r_today_cost')}: ${cost:.2f}")
    print("─" * 60)


if __name__ == "__main__":
    apply_config(load_config())
    if "--with-update-lock" in sys.argv:
        # 셸이 인앱 업데이트와 같은 객체로 직렬화하는 통로. 잠금은 파이썬이 들고
        # 셸은 그 안에서 자식으로 돈다 — 이유와 종료 상태는 함수의 docstring 에.
        sys.exit(_run_with_update_lock(sys.argv))
    elif "--update-lock-path" in sys.argv:
        # **진단용이다. 이 경로로 셸에서 잠금을 잡지 말 것.**
        # `exec 9> "$(… --update-lock-path …)"` 는 O_NOFOLLOW 도, 연 fd 에 대한
        # fstat 확인도 없이 이름을 다시 해석해 여는 열기이고,
        # _acquire_update_lock 이 하지 않기로 한 것이 정확히 그것이다. 게다가
        # macOS 에는 flock(1) 이 없어 셸은 그 객체를 잠글 수도 없다. 실제로
        # 잠그려면 --with-update-lock 을 쓴다.
        #
        # 그래도 경로를 '알려 주는' 곳은 여기 한 곳뿐이다. 셸 쪽에 경로를 다시
        # 적으면 한쪽만 바뀌는 날 서로 다른 파일을 잠그게 되고, 직렬화는 있는
        # 것처럼 보이면서 없어진다 — 이 파일이 UPDATE_LOCK_DIR 을 한 곳에만
        # 두는 것과 같은 이유다.
        #
        # 아무것도 만들지 않는다. _update_lock_path 는 순수하고, 자리를 만드는
        # 것은 실제로 잠글 때(_lock_root_fd)뿐이다.
        _i = sys.argv.index("--update-lock-path")
        _target = (sys.argv[_i + 1] if len(sys.argv) > _i + 1
                   and not sys.argv[_i + 1].startswith("-")
                   else INSTALLED_BUNDLE_NAME)
        print(_update_lock_path(_target))
    elif "--report" in sys.argv:
        print_report()
    else:
        run_gui()
