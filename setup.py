"""py2app 빌드 설정 — 자체포함(Python 내장) ClaudePet.app 생성.

    python setup.py py2app     # dist/ClaudePet.app (standalone)
"""
from setuptools import setup

setup(
    app=["claude_pet.py"],
    options={
        "py2app": {
            "iconfile": "release/icon.icns",
            "resources": ["frames"],
            "plist": {
                "CFBundleName": "ClaudePet",
                "CFBundleDisplayName": "Claude Pet",
                "CFBundleIdentifier": "me.yeongyu.claudepet",
                "CFBundleVersion": "1.0",
                "CFBundleShortVersionString": "1.0",
                "LSUIElement": True,
                "NSHighResolutionCapable": True,
            },
            "packages": ["objc"],
            "includes": ["Foundation", "AppKit", "Quartz"],
            # 사용 안 하는 대형 모듈 제외해 용량 축소
            "excludes": ["test", "tkinter", "lib2to3", "pydoc_data",
                         "idlelib", "distutils", "setuptools", "pip"],
        }
    },
    setup_requires=["py2app"],
)
