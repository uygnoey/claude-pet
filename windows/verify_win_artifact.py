#!/usr/bin/env python3
"""Windows 배포물 게이트 — 올릴 파일 그 자체를 검사한다 (verify_release_artifact.py 의 Windows 판).

    python windows\\verify_win_artifact.py --version 0.25 --zip release\\claude-pet-win.zip --installer release\\claude-pet-win-setup.exe

zip:        풀기 전에 cp._zip_members_are_safe 로 멤버를 훑고(절대경로·'..'·백슬래시 탈출·링크), 임시 폴더에 풀어
            win_update.validate_portable_layout 로 레이아웃(루트 ClaudePet\\ 하나, ClaudePet.exe, _internal\\, REQUIRED 전부)과
            _internal\\claudepet-release.json 의 "version" == APP_VERSION 을 확인한다.
installer:  존재하고 크기 > 0, 그리고 PE 헤더(MZ)로 시작한다.

build_win.py 가 마지막 단계로 부르고, 하나라도 거절되면 빌드는 실패다. 검사는 파일에서만 읽는다 — 빌드 폴더를 보지 않는다.
"""
import argparse
import os
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import win_update  # noqa: E402


def check_zip(zip_path, version):
    """→ 문제 목록(비어 있으면 통과)."""
    problems = []
    if not os.path.isfile(zip_path):
        return [f"zip missing: {os.path.basename(str(zip_path))}"]
    if os.path.getsize(zip_path) <= 0:
        return [f"zip is empty: {os.path.basename(zip_path)}"]
    if not win_update.scan_update_zip(zip_path):
        return [f"zip refused by the archive scan: {os.path.basename(zip_path)}"]
    tmp = tempfile.mkdtemp(prefix="cpw-gate-")
    try:
        try:
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(tmp)
        except Exception as e:
            return [f"zip could not be extracted ({type(e).__name__})"]
        ok, reason = win_update.validate_portable_layout(tmp, version)
        if not ok:
            problems.append(f"zip layout refused: {reason}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


def check_installer(setup_path):
    if not os.path.isfile(setup_path):
        return [f"installer missing: {os.path.basename(str(setup_path))}"]
    if os.path.getsize(setup_path) <= 0:
        return [f"installer is empty: {os.path.basename(setup_path)}"]
    try:
        with open(setup_path, "rb") as f:
            head = f.read(2)
    except OSError as e:
        return [f"installer unreadable ({type(e).__name__})"]
    if head != b"MZ":
        return [f"installer is not a PE executable: {os.path.basename(setup_path)}"]
    return []


def check_all(zip_path, setup_path, version):
    return check_zip(zip_path, version) + check_installer(setup_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", required=True, help="APP_VERSION the artifacts must carry")
    ap.add_argument("--zip", help="claude-pet-win.zip to check")
    ap.add_argument("--installer", help="claude-pet-win-setup.exe to check")
    a = ap.parse_args(argv)
    if not a.zip and not a.installer:
        ap.error("give --zip and/or --installer")
    problems = []
    if a.zip:
        problems += check_zip(a.zip, a.version)
    if a.installer:
        problems += check_installer(a.installer)
    for p in problems:
        print("❌ " + p, file=sys.stderr)
    if problems:
        return 1
    print("✅ artifact gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
