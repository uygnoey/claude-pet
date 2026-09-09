#!/usr/bin/env python3
"""릴리즈 산출물(zip/dmg) 게이트 — 올라갈 파일 자체를 업로드 직전에 검사한다.

업데이터가 '설치 직전'에 하는 preflight 와 같은 검사를 '업로드 직전'에 한다.
두 경계는 목적이 다르다. 업데이터는 나쁜 산출물로부터 **사용자**를 지키고,
이쪽은 나쁜 산출물을 **우리가 내보내는 것**을 막는다. 그래서 둘 다 있어야 한다.

**다시 구현하지 않고 그대로 부른다.** 같은 검사를 두 번 적으면 두 벌은 반드시
갈라지고, 갈라진 순간 어느 쪽이 맞는지 아무도 모른다 — 게이트가 통과시킨 것을
사용자의 업데이터가 거부하는 것이 정확히 그 모양이다. 그래서 여기서는
claude_pet 의 `_zip_members_are_safe` 와 `validate_update_app` 을 직접 부른다.
그 결과로 이 게이트의 진단은 `[update]` 접두사로 찍힌다 — 어색해 보여도 그대로
둔다. 그게 '같은 코드가 돌았다'는 증거다.

이 재사용에는 한계가 하나 있고, 숨기지 않고 적어 둔다: 여기서 도는 것은
**이 체크아웃의** preflight 이고, 사용자 기기에서 도는 것은 **그들이 설치한
버전의** preflight 다. 검사 코드 자체를 바꾸는 릴리즈에서는 둘이 다르다.
그때 게이트가 보증하는 것은 '새 규칙에 맞다'이지 '옛 클라이언트가 받아들인다'가
아니다.

verify_pet_payload.py 와의 분업:
  · verify_pet_payload.py — 동봉 펫 자산이 **저장소 소스와 바이트까지 같은지**.
    업데이터는 원본이 없어 할 수 없는 검사고, 그래서 게이트에만 있다.
  · 이 파일 — 아카이브 안전성 + 번들 신원/버전/아키텍처/서명/공증/티켓.

사용법:
  verify_release_artifact.py scan <artifact.zip|artifact.dmg>
  verify_release_artifact.py app <app_path> --expect-version 0.21 --arches arm64,x86_64
  verify_release_artifact.py assets <올릴 파일…>
"""
import argparse
import hashlib
import os
import stat
import sys


# 이 체크아웃의 소스. 산출물 안에 든 claude_pet.py 가 '이것'이어야 한다.
CHECKOUT_CODE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "claude_pet.py")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_app():
    """claude_pet 를 import 한다. import 부작용은 HTTPS opener 설치뿐이다."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import claude_pet
    return claude_pet


def scan(artifact):
    """바이트가 디스크에 닿기 **전에** 아카이브를 본다.

    풀고 나서 훑는 것으로는 대체할 수 없다. 밖으로 나가는 멤버는 우리가 훑을
    폴더 바깥에 이미 쓰인 뒤이고, 우리는 안쪽만 훑으므로 영영 안 보인다 —
    풀린 트리가 깨끗한 것은 '탈출이 없었다'는 증거가 아니라 탈출의 '결과'다.
    업데이터의 zip 검사를 ditto 앞으로 옮긴 것과 같은 이유다.
    """
    if not os.path.exists(artifact):
        print(f"[gate] rejected: no such artifact: {artifact}")
        return False
    if os.path.islink(artifact):
        print("[gate] rejected: the artifact path is a symlink")
        return False
    if not os.path.isfile(artifact):
        print("[gate] rejected: the artifact is not a regular file")
        return False
    low = artifact.lower()
    if low.endswith(".zip"):
        cp = _load_app()
        return bool(cp._zip_members_are_safe(artifact))
    if low.endswith(".dmg"):
        # dmg 는 '푸는' 물건이 아니라 읽기전용으로 **마운트**하는 물건이라,
        # 이 단계에서 디스크에 쓰이는 바이트가 없다. 그래서 zip 과 같은
        # 사전 스캔이 필요 없다 — 없는 게 아니라 해당하지 않는다. 볼륨 안의
        # 링크는 마운트 뒤 트리 봉쇄 검사(validate_update_app)가 잡는다.
        # 이 비대칭을 '둘 다 스캔한다'고 뭉뚱그리면 다음 사람이 dmg 에도
        # 사전 스캔이 도는 줄 안다.
        print("[gate] dmg: mounted read-only, nothing is written — "
              "containment is checked after mount")
        return True
    print(f"[gate] rejected: unknown artifact type: {artifact}")
    return False


def check_app(app_path, expect_version, arches):
    """번들 신원·버전·아키텍처·서명·공증·티켓 — 업데이터와 **같은 함수**로.

    그 앞에 이 게이트에만 있는 검사가 하나 붙는다: 번들 안의 claude_pet.py 가
    **이 체크아웃의 바이트와 같은지**. 업데이터는 원본이 없어 할 수 없고,
    서명·공증은 '누가 만들었나'만 말할 뿐 '무엇이 들었나'는 말하지 않는다 —
    옛 코드가 든 번들을 새로 서명해도 전부 통과한다. 실제로 그 상태였다:
    소스는 cde92f45… 인데 빌드된 번들은 전부 334e3748… 을 싣고 있었고,
    낡은 재서명본이 게이트를 그대로 지나갔다.
    """
    if not os.path.isdir(app_path) or os.path.islink(app_path):
        print("[gate] rejected: the app is not a real directory")
        return False
    leaf = os.path.join(app_path, "Contents", "Resources", "claude_pet.py")
    # islink 를 먼저 본다 — isfile 은 링크를 따라가므로, 순서를 바꾸면
    # '가리키는 곳이 정상이면 통과'가 되어 링크가 검사를 빠져나간다.
    if os.path.islink(leaf) or not os.path.isfile(leaf):
        print("[gate] rejected: Contents/Resources/claude_pet.py is missing "
              "or is not a regular file")
        return False
    try:
        got, want = _sha256(leaf), _sha256(CHECKOUT_CODE)
    except OSError as exc:
        print(f"[gate] rejected: could not hash the bundled code ({exc})")
        return False
    if got != want:
        print("[gate] rejected: the bundled claude_pet.py is not this "
              f"checkout's ({got[:12]}… != {want[:12]}…)")
        return False
    cp = _load_app()
    ok = cp.validate_update_app(app_path, expect_version,
                                expect_arches=tuple(arches))
    if not ok:
        print(f"[gate] rejected by the updater's own preflight: {app_path}")
    return bool(ok)


def check_assets(paths):
    """올릴 파일 '전부'가 있는지, 그리고 그 이름이 업데이터의 표와 맞는지.

    이름은 여기 박아 두지 않고 claude_pet 의 UPDATE_ASSET_NAMES 에서 가져온다.
    release.sh 와 업데이터가 각자 이름을 들고 있었고 둘이 같은지 보는 곳이
    없었다 — 한쪽만 바꾸면 check_github_update 가 'failed' 를 돌려주는데,
    그 값은 쿨다운을 태우지 않으므로 설치된 모든 사본이 조용히 영원히 재시도한다.
    사용자에게는 아무 증상도 안 보이고, 우리 쪽에도 아무 신호가 안 온다.
    """
    cp = _load_app()
    expected_zips = sorted({str(name).strip().lower()
                            for group in cp.UPDATE_ASSET_NAMES.values()
                            for name in group})
    # dmg 는 수동 설치용이라 업데이터의 표에 없다. 이름만 zip 과 짝을 맞춘다.
    expected_dmgs = sorted(name[:-len(".zip")] + ".dmg"
                           for name in expected_zips)
    expected = expected_zips + expected_dmgs

    missing = [p for p in paths
               if os.path.islink(p) or not os.path.isfile(p)]
    if missing:
        print("[gate] rejected: these upload targets are missing or are not "
              f"regular files: {', '.join(missing)}")
        return False
    names = sorted(os.path.basename(p).lower() for p in paths)
    if names != sorted(expected):
        print("[gate] rejected: the upload set does not match what the "
              "updater looks for")
        print(f"   expected (case-insensitive): {', '.join(sorted(expected))}")
        print(f"   got:                         {', '.join(names)}")
        return False
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="pre-extraction archive safety scan")
    s.add_argument("artifact")
    a = sub.add_parser("app", help="bundle identity/signature checks")
    a.add_argument("app_path")
    a.add_argument("--expect-version", required=True)
    a.add_argument("--arches", default="")
    n = sub.add_parser("assets", help="upload set vs the updater's asset table")
    n.add_argument("paths", nargs="+")
    ns = ap.parse_args(argv)
    if ns.cmd == "scan":
        return 0 if scan(ns.artifact) else 1
    if ns.cmd == "assets":
        return 0 if check_assets(ns.paths) else 1
    arches = [x for x in ns.arches.replace(",", " ").split() if x]
    if not arches:
        # 기본값을 '이 기기'로 두지 않는다. 릴리즈 게이트에서 기준을 빌드
        # 머신에 물으면, arm64 머신에서 만든 universal 산출물이 x86_64
        # 슬라이스를 잃어도 통과한다 — 정확히 Intel 사용자만 겪는 사고다.
        print("[gate] rejected: --arches is required (what the artifact "
              "claims to support, not what this machine happens to be)")
        return 1
    return 0 if check_app(ns.app_path, ns.expect_version, arches) else 1


if __name__ == "__main__":
    sys.exit(main())
