#!/usr/bin/env python3
"""Windows 배포물 만들기 — release\\claude-pet-win.zip + release\\claude-pet-win-setup.exe (PyInstaller onedir + Inno Setup).

실행(Windows, 저장소 루트, venv 활성화: pip install -r windows\\requirements.txt):
    python windows\\build_win.py
결과:
    dist-win\\ClaudePet\\ClaudePet.exe (+ _internal\\)   실행 폴더
    release\\claude-pet-win.zip                         portable zip — 풀어서 ClaudePet\\ClaudePet.exe 실행. 인앱 업데이트(portable) 자산
    release\\claude-pet-win-setup.exe                   설치 파일 (Inno Setup 6, windows\\installer.iss). 인앱 업데이트(inno) 자산
Inno Setup 이 필요하다:  winget install --id JRSoftware.InnoSetup -e   (ISCC.exe 를 아래 경로에서 찾는다)

순서 — 각 단계는 앞 단계가 거절할 수 있는 것을 먼저 둔다:
    build → write_release_marker → verify(REQUIRED) → sign(ClaudePet.exe) → make_zip → make_installer → sign(setup.exe)
    → verify_win_artifact 게이트(zip: 안전한 멤버·레이아웃·버전 마커 == APP_VERSION·exe 의 버전 리소스 / installer: 존재·크기>0). 게이트가 거절하면 빌드는 실패다.
exe 의 버전 리소스(FileDescription/CompanyName/…)는 write_version_resource() 가 빌드마다 새로 써서 --version-file 로 넘긴다 —
없으면 Windows 가 항목 이름을 ClaudePet.exe, 게시자를 빈칸으로 보여 준다(실기 관찰, Windows 11, 2026-09-14. 자세한 것은 VERSION_STRINGS 주석).

번들 구성(모두 _internal 아래, 코어가 __file__ 기준으로 찾는 자리 그대로):
    frames\\            내장 고양이 스프라이트 (claude_pet.PET_DIR)
    fonts\\             Pretendard-SemiBold.ttf + OFL 라이선스 (claude_pet.bundled_font_path)
    .claude_pet\\       동봉 펫 자산 (시작 때 ~/.claude_pet 에 없는 것만 시딩)
    claudepet.ico       트레이·창 아이콘 (macOS 앱 아이콘과 같은 그림)
    claudepet-release.json   버전 마커 {"version": APP_VERSION, "built": <ISO UTC>, …} — 업데이터가 태그와 대조하는 번들 안의 유일한 신원
    fcntl              windows\\compat\\fcntl.py 를 분석 경로에 두어 코어의 `import fcntl` 이 이 shim 으로 묶인다
    win_core           windows\\win_core.py — 코어 import 의 유일한 주인(fcntl shim + CDLL 우회) (hidden-import)
    win_update         windows\\win_update.py — 업데이트/제거 판단의 순수 부분 (hidden-import)
    win_autostart      windows\\win_autostart.py — 로그인 시 자동 실행 판단의 순수 부분 (hidden-import)
코어 claude_pet.py 는 --hidden-import 로 PYZ 에 들어간다(런타임에 importlib 로 읽으므로 자동 감지가 안 된다).

서명 — CLAUDE_PET_WIN_SIGN=off|pfx|store|trusted (기본 off: 서명하지 않고 그 사실을 로그 한 줄로 남긴다).
    공통:    signtool sign /fd SHA256 /td SHA256 /tr $CLAUDE_PET_WIN_TS            (기본 http://timestamp.digicert.com)
    pfx:     /f $CLAUDE_PET_WIN_PFX /p $CLAUDE_PET_WIN_PFX_PASSWORD               (암호는 어디에도 출력하지 않는다 — 테스트/자체 서명용)
    store:   /sha1 $CLAUDE_PET_WIN_CERT_SHA1                                      (인증서 저장소·USB 토큰 — PIN 프롬프트가 뜬다)
    trusted: /dlib $CLAUDE_PET_WIN_DLIB /dmdf $CLAUDE_PET_WIN_DMDF                (Azure Trusted Signing)
    signtool 은 $CLAUDE_PET_WIN_SIGNTOOL, PATH, Windows Kits 순으로 찾는다. 서명 뒤에는 `signtool verify /pa` 로 확인한다.
    인증서·키·Azure 자격 증명은 사용자가 얻어 사용자가 보관한다 — 에이전트는 얻을 수도 쓸 수도 없다 (windows/README.md).
"""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import win_core  # noqa: E402  — 코어 import 의 유일한 주인 (fcntl shim + CDLL 우회). 이것 없이는 Windows 에서 첫 줄에 죽는다
win_core.import_core()

import win_update  # noqa: E402  — REQUIRED / marker / asset names are shared with the updater

DIST = os.path.join(ROOT, "dist-win")
WORK = os.path.join(ROOT, "build-win")
ZIP = os.path.join(ROOT, "release", win_update.ZIP_ASSET)
SETUP = os.path.join(ROOT, "release", win_update.SETUP_ASSET)
ISCC_CANDIDATES = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Inno Setup 6", "ISCC.exe"),
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Inno Setup 6", "ISCC.exe"),
)
# 번들이 반드시 담아야 하는 것. 업데이터의 레이아웃 검사(validate_portable_layout)와 같은 튜플이라 두 곳이 어긋날 수 없다.
REQUIRED = win_update.PORTABLE_REQUIRED
MARKER = win_update.RELEASE_MARKER

SIGN_MODES = ("off", "pfx", "store", "trusted")
DEFAULT_TIMESTAMP_URL = "http://timestamp.digicert.com"


def app_version():
    src = open(os.path.join(ROOT, "claude_pet.py"), encoding="utf-8").read()
    return re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src).group(1)


VERSION_RESOURCE_NAME = "version_info.txt"
# exe 의 버전 리소스에 박히는 고정 문자열 — 이 dict 가 유일한 출처다(게이트의 verify_win_artifact 도 여기서 읽는다).
# 관찰(기기 한 대, Windows 11, 2026-09-14): 화면은 `설정 › 앱 › 시작 앱` 이었다(작업 관리자도, 설정 › 앱 → 설치된 앱도 아니다 —
# 이번 실기에서 확정됐다). 거기서 항목 이름이 "ClaudePet.exe", 게시자가 빈칸으로 보였고, 바로 위 Claude 항목은
# "Claude / Anthropic, PBC" 였다. 고친 뒤 그 줄은 "Claude Pet / Yeongyu Yang" 으로 보인다. 화면과 무관하게 참인 것도 그대로다:
# 시작 앱 목록(설정 › 앱 › 시작 앱, 작업 관리자 › 시작 앱·세부 정보)은 exe 의 FileDescription/CompanyName 을 읽고,
# 설정 › 앱 → 설치된 앱은 Inno 의 ARP 값을 읽는데 그쪽 AppPublisher 는 installer.iss 에 이미 있다 — 그래서 고치는 자리는
# 어느 쪽이든 exe 의 버전 리소스 하나다(windows/README.md "exe 의 버전 리소스").
VERSION_STRINGS = {
    "CompanyName": "Yeongyu Yang",
    "FileDescription": "Claude Pet",
    "InternalName": "ClaudePet",
    "LegalCopyright": "Copyright (c) Yeongyu Yang",
    "OriginalFilename": "ClaudePet.exe",
    "ProductName": "Claude Pet",
}


def _version_quad(version):
    """'0.25' → (0, 25, 0, 0). filevers/prodvers 는 언제나 정수 4개다 — 숫자가 아닌 조각은 0."""
    parts = []
    for chunk in str(version).split(".")[:4]:
        digits = re.match(r"\d+", chunk.strip())
        parts.append(int(digits.group(0)) if digits else 0)
    return tuple(parts + [0] * (4 - len(parts)))


def write_version_resource(path, version):
    """PyInstaller 의 --version-file 로 넘길 버전 리소스 파일을 쓴다 → 쓴 경로.

    빌드할 때마다 새로 쓴다(손으로 만들어 커밋해 두면 버전이 그 자리에 얼어붙는다). 숫자는 인자로 받은 버전
    한 곳에서만 나오고, 문자열은 VERSION_STRINGS 고정이다. 내용은 PyInstaller 가 exec 하는 파이썬 소스다.
    """
    quad = _version_quad(version)
    strings = dict(VERSION_STRINGS)
    strings["FileVersion"] = str(version)
    strings["ProductVersion"] = str(version)
    rows = ",\n".join(f"          StringStruct({k!r}, {v!r})" for k, v in sorted(strings.items()))
    text = (
        "# ClaudePet Windows version resource — generated by windows/build_win.py. Do not edit or commit.\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers={quad},\n"
        f"    prodvers={quad},\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x40004,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable(\n"
        "        '040904B0',\n"
        "        [\n" + rows + ",\n"
        "        ])\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    )
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def build():
    import PyInstaller.__main__ as pyi
    sep = ";" if sys.platform == "win32" else ":"
    data = [("frames", "frames"), (".claude_pet", ".claude_pet"), ("fonts", "fonts"),
            # 제공자 마크. 빠지면 소스 실행은 멀쩡한데 번들에서만 로고가 사라진다 —
            # fonts/ 가 정확히 그 실패를 한 적이 있다. 짝이 되는 자리는
            # win_update.PORTABLE_REQUIRED(= REQUIRED) 이고, 거기 있어야 빌드 게이트와
            # 업데이터의 레이아웃 검사가 같이 덮인다.
            ("logos", "logos"),
            (os.path.join("windows", "claudepet.ico"), ".")]
    # 버전 리소스는 빌드할 때마다 새로 쓴다. WORK 안에 두지 않는 이유는 --clean 이 workpath 를 비우기 때문이다.
    meta = tempfile.mkdtemp(prefix="claudepet-verinfo-")
    try:
        version_file = write_version_resource(os.path.join(meta, VERSION_RESOURCE_NAME), app_version())
        args = ["--noconfirm", "--clean", "--windowed", "--name", "ClaudePet",
                "--version-file", version_file,
                "--icon", os.path.join(ROOT, "windows", "claudepet.ico"),
                "--paths", ROOT, "--paths", os.path.join(ROOT, "windows"),
                "--paths", os.path.join(ROOT, "windows", "compat"),
                "--hidden-import", "claude_pet", "--hidden-import", "win_core",
                "--hidden-import", "win_update", "--hidden-import", "win_autostart",
                "--distpath", DIST, "--workpath", WORK, "--specpath", WORK]
        for src, dst in data:
            args += ["--add-data", f"{os.path.join(ROOT, src)}{sep}{dst}"]
        args.append(os.path.join(ROOT, "windows", "claude_pet_win.py"))
        pyi.run(args)
    finally:
        shutil.rmtree(meta, ignore_errors=True)


def write_release_marker(app_dir, version, built=None):
    """<app_dir>\\_internal\\claudepet-release.json 을 쓴다 → 경로.

    업데이터는 zip 을 풀고 나서 이 파일의 "version" 이 릴리즈 태그와 문자열로 정확히 같을 때만 교체한다
    (win_update.validate_portable_layout). 그 밖의 키는 진단용이다.
    """
    path = os.path.join(app_dir, MARKER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    built = built or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"version": str(version), "built": built, "asset": win_update.ZIP_ASSET,
               "installer": win_update.SETUP_ASSET, "machine": "AMD64"}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def verify(app_dir):
    missing = [p for p in REQUIRED if not os.path.exists(os.path.join(app_dir, p))]
    if missing:
        raise SystemExit("❌ 번들에 빠진 것: " + ", ".join(missing))


def make_zip(app_dir):
    os.makedirs(os.path.dirname(ZIP), exist_ok=True)
    tmp = ZIP + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(app_dir):
            for name in files:
                full = os.path.join(base, name)
                z.write(full, os.path.join(win_update.APP_DIR_NAME, os.path.relpath(full, app_dir)))
    os.replace(tmp, ZIP)


def find_iscc():
    for p in ISCC_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    return shutil.which("ISCC") or shutil.which("iscc")


def make_installer(version):
    """Inno Setup 으로 release\\claude-pet-win-setup.exe 를 만든다. ISCC 가 없으면 실패한다 — 설치 파일은 배포 요건이다."""
    iscc = find_iscc()
    if not iscc:
        raise SystemExit("❌ Inno Setup 6 (ISCC.exe) 을 찾지 못했습니다: winget install --id JRSoftware.InnoSetup -e")
    script = os.path.join(ROOT, "windows", "installer.iss")
    if os.path.exists(SETUP):
        os.remove(SETUP)
    subprocess.run([iscc, f"/DMyAppVersion={version}", f"/O{os.path.dirname(SETUP)}", script], check=True)
    if not os.path.isfile(SETUP):
        raise SystemExit("❌ 설치 파일이 만들어지지 않았습니다: " + SETUP)


# ───────────────────────────── 서명 ─────────────────────────────
def find_signtool(env=None):
    env = os.environ if env is None else env
    p = env.get("CLAUDE_PET_WIN_SIGNTOOL")
    if p and os.path.isfile(p):
        return p
    p = shutil.which("signtool") or shutil.which("signtool.exe")
    if p:
        return p
    kits = os.path.join(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Windows Kits", "10", "bin")
    found = sorted(glob.glob(os.path.join(kits, "*", "x64", "signtool.exe")))
    return found[-1] if found else None


def _need(env, key):
    v = env.get(key)
    if not v:
        raise SystemExit(f"❌ CLAUDE_PET_WIN_SIGN={env.get('CLAUDE_PET_WIN_SIGN')} 에는 {key} 가 필요합니다")
    return v


def signtool_argv(mode, path, env=None, signtool="signtool"):
    """모드별 signtool argv (순수). off → None. 암호는 argv 에 들어가되 어디에도 출력하지 않는다 (redact_argv)."""
    env = os.environ if env is None else env
    if mode not in SIGN_MODES:
        raise SystemExit(f"❌ CLAUDE_PET_WIN_SIGN 은 {'|'.join(SIGN_MODES)} 중 하나여야 합니다: {mode!r}")
    if mode == "off":
        return None
    ts = env.get("CLAUDE_PET_WIN_TS") or DEFAULT_TIMESTAMP_URL
    argv = [signtool, "sign", "/fd", "SHA256", "/td", "SHA256", "/tr", ts]
    if mode == "pfx":
        argv += ["/f", _need(env, "CLAUDE_PET_WIN_PFX"), "/p", _need(env, "CLAUDE_PET_WIN_PFX_PASSWORD")]
    elif mode == "store":
        argv += ["/sha1", _need(env, "CLAUDE_PET_WIN_CERT_SHA1")]
    else:  # trusted
        argv += ["/dlib", _need(env, "CLAUDE_PET_WIN_DLIB"), "/dmdf", _need(env, "CLAUDE_PET_WIN_DMDF")]
    argv.append(str(path))
    return argv


def redact_argv(argv):
    """로그용: /p 뒤의 값을 가린다."""
    out = list(argv)
    for i, a in enumerate(out[:-1]):
        if a == "/p":
            out[i + 1] = "********"
    return out


def sign(path, env=None):
    """CLAUDE_PET_WIN_SIGN 에 따라 path 에 서명하고 검증한다. off 면 서명하지 않는다고 분명히 말한다."""
    env = os.environ if env is None else env
    mode = env.get("CLAUDE_PET_WIN_SIGN", "off").strip().lower() or "off"
    if mode == "off":
        print(f"ℹ️  서명 없음 (CLAUDE_PET_WIN_SIGN=off): {os.path.basename(path)} — SmartScreen 경고가 뜬다 (windows/README.md)")
        return False
    tool = find_signtool(env)
    if not tool:
        raise SystemExit("❌ signtool.exe 를 찾지 못했습니다 (Windows SDK 'Signing Tools for Desktop Apps' 또는 CLAUDE_PET_WIN_SIGNTOOL)")
    argv = signtool_argv(mode, path, env, tool)
    print("🔏 " + " ".join(redact_argv(argv)))
    r = subprocess.run(argv, capture_output=False)
    if r.returncode != 0:
        raise SystemExit(f"❌ 서명 실패 (signtool rc={r.returncode}): {os.path.basename(path)}")
    v = subprocess.run([tool, "verify", "/pa", "/v", str(path)])
    if v.returncode != 0:
        raise SystemExit(f"❌ 서명 검증 실패 (signtool verify rc={v.returncode}): {os.path.basename(path)}")
    print(f"✅ 서명·검증 완료: {os.path.basename(path)}")
    return True


def main():
    if sys.platform != "win32":
        print("Windows 에서만 빌드합니다 (PyInstaller 는 플랫폼별).", file=sys.stderr)
        return 2
    version = app_version()
    print(f"ClaudePet v{version} — Windows onedir 빌드")
    build()
    app_dir = os.path.join(DIST, win_update.APP_DIR_NAME)
    write_release_marker(app_dir, version)
    verify(app_dir)
    sign(os.path.join(app_dir, win_update.EXE_NAME))     # 패키징 전에 — zip 과 설치 파일 둘 다 서명된 exe 를 담는다
    make_zip(app_dir)
    print(f"✅ {ZIP} ({os.path.getsize(ZIP) // 1024} KB)")
    make_installer(version)
    sign(SETUP)                                           # 설치 파일은 만들어진 뒤에
    print(f"✅ {SETUP} ({os.path.getsize(SETUP) // 1024} KB)")
    import verify_win_artifact
    problems = verify_win_artifact.check_all(ZIP, SETUP, version)
    if problems:
        for p in problems:
            print("❌ " + p, file=sys.stderr)
        raise SystemExit("❌ 배포물 게이트 거절 — 위 항목을 고치기 전에는 올리지 않는다")
    print("✅ 배포물 게이트 통과 (zip 멤버·레이아웃·버전 마커, 설치 파일 존재·크기)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
