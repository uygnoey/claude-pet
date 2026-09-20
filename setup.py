"""py2app 빌드 설정 — 자체포함(Python 내장) ClaudePet.app 생성.

    python setup.py py2app     # dist/ClaudePet.app (standalone)

버전은 claude_pet.py 의 APP_VERSION 하나만 수정하면 됨 (여기서 자동 추출).
"""
import re
from setuptools import setup

APP_VERSION = re.search(r'APP_VERSION\s*=\s*"([^"]+)"',
                        open("claude_pet.py", encoding="utf-8").read()).group(1)

setup(
    app=["claude_pet.py"],
    options={
        "py2app": {
            "iconfile": "release/icon.icns",
            # frames: 내장 고양이 스프라이트 / .claude_pet: 동봉 펫 자산 트리
            # (앱이 시작할 때 ~/.claude_pet 에 없는 것만 채워 넣는다)
            # fonts: 요약 필 글꼴 Pretendard(OFL) — ATSApplicationFontsPath 가 앱 시작 때 등록한다
            # logos: 제공자 마크(Claude/OpenAI SVG) — 요약 필이 제공자 블록 앞에 그린다.
            #   빠지면 소스 실행은 멀쩡하고 번들에서만 마크가 사라진다(fonts 가 겪은 실패).
            "resources": ["frames", ".claude_pet", "fonts", "logos"],
            "plist": {
                "CFBundleName": "ClaudePet",
                "CFBundleDisplayName": "Claude Pet",
                "CFBundleIdentifier": "me.yeongyu.claudepet",
                "CFBundleVersion": APP_VERSION,
                "CFBundleShortVersionString": APP_VERSION,
                "LSUIElement": True,
                "NSHighResolutionCapable": True,
                "ATSApplicationFontsPath": "fonts",
            },
            # certifi: HTTPS 인증서 검증용 CA 번들(특히 CA 없는 python.org 빌드 대비)
            "packages": ["objc", "certifi"],
            # ServiceManagement: 우클릭 '로그인 시 자동 실행'(SMAppService). 빠지면
            # 번들에서는 항목이 영영 비활성이고 소스 실행만 되는 상태가 된다.
            "includes": ["Foundation", "AppKit", "Quartz", "ServiceManagement"],
            # 사용 안 하는 대형 모듈 제외해 용량 축소
            "excludes": ["test", "tkinter", "lib2to3", "pydoc_data",
                         "idlelib", "distutils", "setuptools", "pip"],
        }
    },
    setup_requires=["py2app"],
)
