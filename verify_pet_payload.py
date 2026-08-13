#!/usr/bin/env python3
"""동봉 펫 자산(.claude_pet)이 산출물 안에 온전히 들어갔는지 검사한다.

    python3 verify_pet_payload.py <payload-root> [--source <repo .claude_pet>]

<payload-root> 는 검사할 `.claude_pet` 디렉터리다 — 앱 번들 안의
`Contents/Resources/.claude_pet` 이거나, 설치 전에 옆에 만들어 둔 스테이징 트리.

왜 필요한가: `setup.py` 는 자산을 '선언'하고 `build_app.sh` 는 '복사'할 뿐,
그것이 실제로 들어갔는지는 아무도 확인하지 않았다. 빠진 채로 서명·공증·배포되면
사용자에게는 그냥 '펫이 안 생긴다'로 보이고, 앱은 아무 말도 하지 않는다
(`_dbg` 는 CLAUDE_PET_DEBUG=1 없이는 한 줄도 남기지 않는다).

기대 목록은 `claude_pet.py` 의 BUNDLED_PET_README / BUNDLED_PET_IDS /
BUNDLED_PET_FILES 에서 뽑는다. 숫자를 박아 두지 않는 이유는, 펫이 하나 늘어난
날 16개짜리 검사가 조용히 '19개 중 16개만' 확인하게 되기 때문이다.
(이 저장소에는 build_app.sh 에 박아 둔 값이 실제로 어긋난 적이 있어서
 test_manual_bundle_versions_are_not_hard_coded 가 남아 있다.)

읽는 것은 소스와 산출물뿐이고 출력에는 저장소 경로만 나온다 — 빌드 도구이므로
사용자 데이터는 건드리지 않는다.
"""

import argparse
import ast
import hashlib
import json
import os
import stat as _s
import sys


REPO = os.path.dirname(os.path.abspath(__file__))
APP_SOURCE = os.path.join(REPO, "claude_pet.py")
DEFAULT_SOURCE = os.path.join(REPO, ".claude_pet")
SPRITE_VERSION = 2          # PET_LAYOUTS 에 정의된 유일한 규약 버전
_UNRESOLVED = object()      # AST 로 값을 확정하지 못한 표시


def _constants(path=APP_SOURCE):
    """claude_pet.py 를 '실행하지 않고' 상수 세 개만 읽는다.

    import 하면 모듈 최상위 코드(https 오프너 설치 등)가 함께 돈다. 빌드 게이트가
    앱의 부작용에 기대게 만들 이유가 없으므로 AST 로 읽는다.
    """
    want = {"BUNDLED_PET_README", "BUNDLED_PET_IDS", "BUNDLED_PET_FILES"}
    known, found = {}, {}
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    def value_of(node):
        """리터럴이거나, 앞서 정의된 이름으로만 이루어진 값이면 그 값.

        BUNDLED_PET_FILES 는 ("pet.json", BUNDLED_PET_SHEET, "preview.png") 처럼
        다른 상수를 참조하므로 literal_eval 만으로는 읽히지 않는다.
        """
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError):
            pass
        if isinstance(node, ast.Name) and node.id in known:
            return known[node.id]
        if isinstance(node, (ast.Tuple, ast.List)):
            out = []
            for el in node.elts:
                v = value_of(el)
                if v is _UNRESOLVED:
                    return _UNRESOLVED
                out.append(v)
            return tuple(out)
        return _UNRESOLVED

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            v = value_of(node.value)
            if v is _UNRESOLVED:
                continue
            known[target.id] = v
            if target.id in want:
                found[target.id] = tuple(v) if isinstance(v, (tuple, list)) else v
    missing = want - set(found)
    if missing:
        raise SystemExit(f"❌ claude_pet.py 에서 상수를 못 읽음: {sorted(missing)}")
    return found


def expected_members(consts):
    """기대하는 상대 경로 전체. (README 4개 + 펫당 파일들)"""
    rels = list(consts["BUNDLED_PET_README"])
    for pet in consts["BUNDLED_PET_IDS"]:
        for name in consts["BUNDLED_PET_FILES"]:
            rels.append(f"pets/{pet}/{name}")
    return rels


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _actual_entries(root):
    """트리 안의 모든 항목. (상대경로, 링크인지, 폴더인지) — 링크는 안 따라간다.

    폴더도 세는 이유: 파일만 훑으면 '비어 있는' 폴더가 통째로 안 보인다.
    그러면 "정확히 이 목록"이라는 약속이 실은 "파일 목록만 정확히"가 된다.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in list(dirnames):
            p = os.path.join(dirpath, name)
            is_link = os.path.islink(p)
            out.append((os.path.relpath(p, root), is_link, True))
            if is_link:
                dirnames.remove(name)      # 링크 너머로 들어가지 않는다
        for name in filenames:
            p = os.path.join(dirpath, name)
            out.append((os.path.relpath(p, root), os.path.islink(p), False))
    return out


def verify(root, source, consts=None):
    """문제 목록을 돌려준다. 빈 리스트면 통과."""
    consts = consts or _constants()
    sheet = consts["BUNDLED_PET_FILES"][1] if len(consts["BUNDLED_PET_FILES"]) > 1 else None
    problems = []
    if not os.path.lexists(root):
        return [f"payload tree is missing entirely: {root}"]
    # 루트(와 기대 하위 폴더)는 '진짜 폴더'여야 한다. 링크면 os.walk 가 링크
    # 너머를 훑고 "깨끗함"이라고 보고한다 — 잎은 전부 맞는데 검사한 트리가
    # 우리 것이 아닌 상태다. 잎을 고르는 주체를 확인하지 않으면 잎 검사는 무의미하다.
    if os.path.islink(root) or not _s.S_ISDIR(os.lstat(root).st_mode):
        return [f"payload root is not a real directory (symlink?): {root}"]

    rels = expected_members(consts)
    expected_dirs = ["pets"] + [f"pets/{pet}" for pet in consts["BUNDLED_PET_IDS"]]
    for rel in expected_dirs:
        p = os.path.join(root, rel)
        if not os.path.lexists(p):
            problems.append(f"{rel}: expected directory is missing")
        elif os.path.islink(p) or not _s.S_ISDIR(os.lstat(p).st_mode):
            problems.append(f"{rel}: is not a real directory (symlink?)")
    for rel in rels:
        dst = os.path.join(root, rel)
        src = os.path.join(source, rel)
        if os.path.islink(dst):
            problems.append(f"{rel}: is a symlink (must be a regular file)")
            continue
        if not os.path.isfile(dst):
            problems.append(f"{rel}: missing from the payload")
            continue
        if not os.path.isfile(src):
            problems.append(f"{rel}: no such file in the repo source ({source})")
            continue
        if _sha256(dst) != _sha256(src):
            problems.append(f"{rel}: contents differ from the repo source")

    # 링크는 어디에 있든(기대 목록 밖이어도) 문제다 — 설치 복사가 그대로 보존한다
    actual = _actual_entries(root)
    allowed = set(rels) | set(expected_dirs)
    for rel, is_link, _is_dir in actual:
        if is_link and rel not in rels:
            problems.append(f"{rel}: unexpected symlink inside the payload")
    for rel in sorted({rel for rel, _, _ in actual} - allowed):
        problems.append(f"{rel}: unexpected extra entry in the payload")

    # 메타데이터 — 게시된 뒤에는 폴더 단위로 건너뛰므로 고쳐지지 않는다
    for pet in consts["BUNDLED_PET_IDS"]:
        meta_path = os.path.join(root, "pets", pet, "pet.json")
        if not os.path.isfile(meta_path) or os.path.islink(meta_path):
            continue                      # 위에서 이미 보고됨
        try:
            with open(meta_path, "rb") as f:
                meta = json.load(f)
        except Exception as e:
            problems.append(f"pets/{pet}/pet.json: unreadable ({type(e).__name__})")
            continue
        if not isinstance(meta, dict):
            problems.append(f"pets/{pet}/pet.json: not a JSON object")
            continue
        # 런타임 시더(_bad_pet_metadata)가 거절하는 조건은 게이트도 잡아야 한다.
        # 안 그러면 우리 게이트가 통과시킨 릴리즈를 우리 설치기가 거절한다.
        # 소스와 산출물이 '똑같이' 틀린 경우는 해시 비교로는 절대 보이지 않는다.
        if str(meta.get("id") or pet) != pet:
            problems.append(
                f"pets/{pet}/pet.json: id is {meta.get('id')!r}, expected {pet!r} "
                "(the installer refuses a pet whose id disagrees with its folder)")
        if sheet and (meta.get("spritesheetPath") or sheet) != sheet:
            problems.append(
                f"pets/{pet}/pet.json: spritesheetPath is "
                f"{meta.get('spritesheetPath')!r}, expected {sheet!r}")
        ver = meta.get("spriteVersionNumber")
        if ver != SPRITE_VERSION:
            problems.append(
                f"pets/{pet}/pet.json: spriteVersionNumber is {ver!r}, "
                f"expected {SPRITE_VERSION}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", help="the .claude_pet directory to check")
    ap.add_argument("--source", default=DEFAULT_SOURCE,
                    help="repo .claude_pet to compare against")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    problems = verify(args.root, args.source)
    if problems:
        print(f"❌ 동봉 펫 자산 검사 실패: {args.root}", file=sys.stderr)
        for p in problems:
            print(f"   · {p}", file=sys.stderr)
        print("   (.DS_Store 같은 잡파일이면 지우고 다시 빌드하세요)", file=sys.stderr)
        return 1
    if not args.quiet:
        n = len(expected_members(_constants()))
        print(f"✅ 동봉 펫 자산 {n}개 확인: {args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
