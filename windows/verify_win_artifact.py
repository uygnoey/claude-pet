#!/usr/bin/env python3
"""Windows 배포물 게이트 — 올릴 파일 그 자체를 검사한다 (verify_release_artifact.py 의 Windows 판).

    python windows\\verify_win_artifact.py --version 0.25 --zip release\\claude-pet-win.zip --installer release\\claude-pet-win-setup.exe

zip:        풀기 전에 cp._zip_members_are_safe 로 멤버를 훑고(절대경로·'..'·백슬래시 탈출·링크), 임시 폴더에 풀어
            win_update.validate_portable_layout 로 레이아웃(루트 ClaudePet\\ 하나, ClaudePet.exe, _internal\\, REQUIRED 전부)과
            _internal\\claudepet-release.json 의 "version" == APP_VERSION 을 확인하고, 풀린 ClaudePet.exe 에 버전 리소스가
            들어 있는지 본다(check_version_resource — Windows 가 그 exe 의 이름·게시자로 보여 주는 값).
installer:  존재하고 크기 > 0, 그리고 PE 헤더(MZ)로 시작한다.

build_win.py 가 마지막 단계로 부르고, 하나라도 거절되면 빌드는 실패다. 검사는 파일에서만 읽는다 — 빌드 폴더를 보지 않는다.
코어는 win_core.import_core() 로 얻는다 — 이 파일을 Windows 에서 직접 돌릴 때 예전에는 첫 import 에서 죽었다.
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

import win_core  # noqa: E402  — 코어 import 의 유일한 주인 (fcntl shim + CDLL 우회). 직접 돌릴 때도 여기서 걸린다
win_core.import_core()

import win_update  # noqa: E402

VERSION_RESOURCE_MARKER = "VS_VERSION_INFO"
# exe 의 버전 리소스가 담고 있어야 하는 고정 문자열은 여기에 베껴 두지 않는다 — 빌더에서 그대로 읽는다.
# 사본을 두면 빌더의 CompanyName 을 고쳤을 때 게이트만 옛 값을 찾게 되고, 그 어긋남을 막아 주는 것은 주석뿐이다.
_VERSION_RESOURCE_KEYS = ("FileDescription", "CompanyName", "OriginalFilename")


def _version_resource_strings():
    """검사할 고정 문자열을 build_win.VERSION_STRINGS 에서 읽어 온다 → 튜플.

    import 를 모듈 꼭대기가 아니라 이 함수 안에서 하는 이유가 둘이다. (1) 이 파일의 import 사슬을 바꾸지 않는다 —
    "Windows 에서 첫 줄에 죽지 않는가" 는 이 모듈을 import 해 보는 것으로 판정하므로, 거기에 빌더를 끌어들이면
    그 시험이 재는 대상이 달라진다. (2) 빌더는 PyInstaller 를 build() 안에서만 읽으므로 여기서 모듈을 읽는 값은
    싸고, 빌드의 마지막 단계에서 불릴 때는 build_win 이 이미 sys.modules 에 있다.
    """
    try:                                # windows.verify_win_artifact — 저장소 루트에서 도는 시험 수트
        from . import build_win as bw
    except ImportError:                 # windows\ 가 sys.path 앞에 있을 때 — 빌드의 마지막 단계, 그리고 직접 실행
        import build_win as bw
    return tuple(bw.VERSION_STRINGS[k] for k in _VERSION_RESOURCE_KEYS)


def check_version_resource(exe_path):
    """ClaudePet.exe 가 버전 리소스를 달고 있는가 → 문제 목록(비어 있으면 통과). 절대 예외를 던지지 않는다.

    없으면 Windows 가 항목 이름을 "ClaudePet.exe", 게시자를 빈칸으로 보여 준다(실기 관찰, 기기 한 대, Windows 11,
    2026-09-14 — 보고에 남은 자리는 "설정/작업 관리자" 까지이고 어느 화면이었는지는 기록되지 않았다. 어느 쪽이든
    고치는 것은 같다: 시작 앱 목록(설정 › 시작 앱, 작업 관리자 › 시작 앱·세부 정보)은 exe 의
    FileDescription/CompanyName 을 읽고, 설정 › 앱 → 설치된 앱은 Inno 의 ARP 값을 읽는데 그쪽 AppPublisher 는
    installer.iss 에 이미 있다. 화면 이름 확정은 다음 실기 몫 — windows/README.md "실기에서 확인할 것").
    PyInstaller 는 --version-file 을 준 경우에만 리소스를 넣으므로, 이 검사는 그 인자가 빠진 빌드를 잡는 것이다.

    검사 방법은 호스트에 기대지 않는다: 버전 리소스의 문자열은 PE 안에 UTF-16LE 로 들어가므로 파일 바이트에서
    ``VS_VERSION_INFO`` 표지와 고정 문자열을 찾는다. 리소스 디렉터리를 파싱하지 않으므로 "그 문자열이 정말 버전
    리소스 안에 있다" 까지는 말하지 않는다 — 무엇을 확인했고 무엇을 확인하지 않았는지 그대로 적어 둔다. macOS
    에서는 그 한계를 stderr 로 크게 알린다(조용한 빈 목록은 통과와 구별되지 않는다 — macOS 판 게이트가 도구 없는
    검사를 시끄럽게 건너뛰는 것과 같은 이유).
    """
    name = os.path.basename(str(exe_path))
    if not os.path.isfile(exe_path):
        return [f"exe missing, cannot check its version resource: {name}"]
    try:
        with open(exe_path, "rb") as f:
            data = f.read()
    except OSError as e:
        return [f"exe unreadable ({type(e).__name__}): {name}"]
    try:
        strings = _version_resource_strings()
    except Exception as e:      # 빌더를 못 읽으면 찾을 문자열이 없다 — 빈 목록(통과)으로 넘어가면 안 된다
        return [f"cannot read build_win.VERSION_STRINGS ({type(e).__name__}): "
                f"the gate has no strings to look for in {name}"]
    if sys.platform != "win32":
        print(f"ℹ️  version resource: byte scan only on {sys.platform} — this host cannot query a PE resource "
              f"directory; the strings are matched as UTF-16LE in {name}", file=sys.stderr)
    problems = []
    for needle in (VERSION_RESOURCE_MARKER,) + strings:
        if needle.encode("utf-16-le") not in data:
            problems.append(f"exe has no version resource string {needle!r}: {name} "
                            f"(PyInstaller --version-file missing?)")
    return problems


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
        else:
            problems += check_version_resource(
                os.path.join(tmp, win_update.APP_DIR_NAME, win_update.EXE_NAME))
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
