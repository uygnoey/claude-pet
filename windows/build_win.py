#!/usr/bin/env python3
"""Windows 배포 zip 만들기 — release\\claude-pet-win.zip (PyInstaller onedir, 서명 없음).

실행(Windows, 저장소 루트, venv 활성화: pip install -r windows\\requirements.txt):
    python windows\\build_win.py
결과:
    dist-win\\ClaudePet\\ClaudePet.exe (+ _internal\\)   실행 폴더
    release\\claude-pet-win.zip                         갱신용 zip — 풀어서 ClaudePet\\ClaudePet.exe 실행
    release\\claude-pet-win-setup.exe                   설치 파일 (Inno Setup 6, windows\\installer.iss) — 사용자별 설치,
                                                       시작 메뉴, 로그인 시 자동 실행 옵션, 프로그램 추가/제거 항목
Inno Setup 이 필요하다:  winget install --id JRSoftware.InnoSetup -e   (ISCC.exe 를 아래 경로에서 찾는다)

번들 구성(모두 _internal 아래, 코어가 __file__ 기준으로 찾는 자리 그대로):
    frames\\            내장 고양이 스프라이트 (claude_pet.PET_DIR)
    fonts\\             Pretendard-SemiBold.ttf + OFL 라이선스 (claude_pet.bundled_font_path)
    .claude_pet\\       동봉 펫 자산 (시딩은 다음 단계)
    claudepet.ico       트레이·창 아이콘 (macOS 앱 아이콘과 같은 그림)
    fcntl              windows\\compat\\fcntl.py 를 분석 경로에 두어 코어의 `import fcntl` 이 이 shim 으로 묶인다
코어 claude_pet.py 는 --hidden-import 로 PYZ 에 들어간다(런타임에 importlib 로 읽으므로 자동 감지가 안 된다).
서명(코드 서명·SmartScreen)은 미정 — README 의 안내대로 '추가 정보 → 실행'.
"""
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist-win")
WORK = os.path.join(ROOT, "build-win")
ZIP = os.path.join(ROOT, "release", "claude-pet-win.zip")
SETUP = os.path.join(ROOT, "release", "claude-pet-win-setup.exe")
ISCC_CANDIDATES = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Inno Setup 6", "ISCC.exe"),
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Inno Setup 6", "ISCC.exe"),
)
REQUIRED = (
    os.path.join("ClaudePet.exe"),
    os.path.join("_internal", "frames"),
    os.path.join("_internal", "fonts", "Pretendard-SemiBold.ttf"),
    os.path.join("_internal", "fonts", "LICENSE-Pretendard.txt"),
    os.path.join("_internal", ".claude_pet", "pets"),
    os.path.join("_internal", "claudepet.ico"),
)


def app_version():
    src = open(os.path.join(ROOT, "claude_pet.py"), encoding="utf-8").read()
    return re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src).group(1)


def build():
    import PyInstaller.__main__ as pyi
    sep = ";" if sys.platform == "win32" else ":"
    data = [("frames", "frames"), (".claude_pet", ".claude_pet"), ("fonts", "fonts"),
            (os.path.join("windows", "claudepet.ico"), ".")]
    args = ["--noconfirm", "--clean", "--windowed", "--name", "ClaudePet",
            "--icon", os.path.join(ROOT, "windows", "claudepet.ico"),
            "--paths", ROOT, "--paths", os.path.join(ROOT, "windows", "compat"),
            "--hidden-import", "claude_pet",
            "--distpath", DIST, "--workpath", WORK, "--specpath", WORK]
    for src, dst in data:
        args += ["--add-data", f"{os.path.join(ROOT, src)}{sep}{dst}"]
    args.append(os.path.join(ROOT, "windows", "claude_pet_win.py"))
    pyi.run(args)


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
                z.write(full, os.path.join("ClaudePet", os.path.relpath(full, app_dir)))
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
    import subprocess
    subprocess.run([iscc, f"/DMyAppVersion={version}", f"/O{os.path.dirname(SETUP)}", script], check=True)
    if not os.path.isfile(SETUP):
        raise SystemExit("❌ 설치 파일이 만들어지지 않았습니다: " + SETUP)


def main():
    if sys.platform != "win32":
        print("Windows 에서만 빌드합니다 (PyInstaller 는 플랫폼별).", file=sys.stderr)
        return 2
    version = app_version()
    print(f"ClaudePet v{version} — Windows onedir 빌드")
    build()
    app_dir = os.path.join(DIST, "ClaudePet")
    verify(app_dir)
    make_zip(app_dir)
    print(f"✅ {ZIP} ({os.path.getsize(ZIP) // 1024} KB)")
    make_installer(version)
    print(f"✅ {SETUP} ({os.path.getsize(SETUP) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
