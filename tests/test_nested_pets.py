"""Gates for nested pet folders and UTF-8 text I/O (staged v0.24).

Owner: Verifier (verifier-v024). ``discover_pets`` is exercised through a plain
``import claude_pet`` against a pet tree built under ``tempfile``; ``USER_PETS_DIR``
and ``PET_DIR`` are pointed at that tree for the test's duration and restored by
``addCleanup``. The real ``~/.claude_pet`` is never read or written.

User decision pinned (2026-09-12): "중첩 폴더도 인식하게 고쳐" — a zip unpacked one level
too deep (``pets/<name>/<name>/pet.json``, with a ``__MACOSX`` beside it) is a pet;
the entry keeps the outer name as its id and the inner folder as its dir. Two levels
are not searched, and among several candidates only the one named like the parent is
taken. The encoding gates pin the Windows finding of the same day: with the platform
default (cp949) the pets README came out 0 bytes, so every text-mode open names UTF-8
and an empty README is rewritten.

Rivals each fixture separates are listed on the test. Red/green evidence:
docs-design/summary-unify-verification-20260912.md.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

import claude_pet


def write_pet(folder, display=None, pet_id=None):
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"id": pet_id or folder.name, "displayName": display or folder.name,
            "spriteVersionNumber": 2, "spritesheetPath": "spritesheet.webp"}
    (folder / "pet.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return folder


class PetTreeCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.pets = self.root / "pets"
        self.pets.mkdir()
        for name in ("USER_PETS_DIR", "PET_DIR"):
            original = getattr(claude_pet, name)
            self.addCleanup(setattr, claude_pet, name, original)
        claude_pet.USER_PETS_DIR = str(self.pets)
        claude_pet.PET_DIR = str(self.root / "no-builtin-here")   # no default entry

    def found(self):
        pets = claude_pet.discover_pets()
        self.assertNotIn("default", [p["id"] for p in pets])
        return {p["id"]: (p["name"], os.path.relpath(p["dir"], self.root)) for p in pets}, \
               [p["id"] for p in pets]


class NestedPetDiscoveryTests(PetTreeCase):
    def test_flat_pet_folder_still_works(self):
        write_pet(self.pets / "a", "Alpha")
        self.assertEqual(self.found(), ({"a": ("Alpha", "pets/a")}, ["a"]))

    def test_zip_unpacked_one_level_deep_keeps_outer_id_and_inner_dir(self):
        """Rivals: not descending at all (the old contract); id taken from the inner
        folder or from pet.json; dir left at the outer folder; __MACOSX taken as the
        pet folder."""
        write_pet(self.pets / "k" / "k", "Kitty", pet_id="kitty")
        junk = self.pets / "k" / "__MACOSX"
        junk.mkdir()
        (junk / "pet.json").write_text("{}", encoding="utf-8")
        (junk / "._pet.json").write_bytes(b"\x00")
        self.assertEqual(self.found(), ({"k": ("Kitty", "pets/k/k")}, ["k"]))

    def test_a_single_inner_pet_wins_even_when_junk_looks_like_a_pet(self):
        """Rival: counting __MACOSX as a candidate — then two candidates, neither named
        'j', and the pet is refused."""
        write_pet(self.pets / "j" / "__MACOSX")
        write_pet(self.pets / "j" / "inner", "Inner")
        self.assertEqual(self.found(), ({"j": ("Inner", "pets/j/inner")}, ["j"]))

    def test_two_inner_pets_named_unlike_the_parent_are_refused(self):
        """Rivals: taking the first or the last candidate; taking any."""
        write_pet(self.pets / "two" / "a")
        write_pet(self.pets / "two" / "b")
        self.assertEqual(self.found(), ({}, []))

    def test_among_several_the_inner_folder_named_like_the_parent_wins(self):
        """Sorted order is a < pick < z, so first-sorted and last-sorted rivals each
        pick a different folder from the correct one."""
        write_pet(self.pets / "pick" / "a")
        write_pet(self.pets / "pick" / "pick", "Picked")
        write_pet(self.pets / "pick" / "z")
        self.assertEqual(self.found(), ({"pick": ("Picked", "pets/pick/pick")}, ["pick"]))

    def test_two_levels_deep_is_not_recognised(self):
        """Rival: a recursive search."""
        write_pet(self.pets / "deep" / "x" / "deep")
        self.assertEqual(self.found(), ({}, []))

    def test_junk_and_dot_folders_are_skipped_at_both_levels(self):
        """Rivals: __MACOSX listed as a pet at the top level (the old contract did);
        a nested dot-folder taken as the single candidate."""
        write_pet(self.pets / "__MACOSX")
        write_pet(self.pets / ".hidden")
        write_pet(self.pets / "dot" / ".hidden")
        self.assertEqual(self.found(), ({}, []))
        self.assertEqual(claude_pet._PET_JUNK_DIRS, ("__MACOSX",))

    def test_a_symlinked_inner_folder_is_not_followed(self):
        """Rival: os.path.isdir alone, which follows the link."""
        real = write_pet(self.pets / "a", "Alpha")
        (self.pets / "sym").mkdir()
        os.symlink(str(real), str(self.pets / "sym" / "link"))
        self.assertEqual(self.found(), ({"a": ("Alpha", "pets/a")}, ["a"]))

    def test_ordering_is_by_outer_name(self):
        """Rival: ordering by the resolved inner dir or by display name."""
        write_pet(self.pets / "k" / "k", "Zed")
        write_pet(self.pets / "a", "Yankee")
        write_pet(self.pets / "j" / "inner", "Xray")
        write_pet(self.pets / "pick" / "pick", "Alpha")
        write_pet(self.pets / "pick" / "a")
        entries, order = self.found()
        self.assertEqual(order, ["a", "j", "k", "pick"])
        self.assertEqual(entries["k"], ("Zed", "pets/k/k"))
        self.assertEqual(entries["j"], ("Xray", "pets/j/inner"))
        self.assertEqual(entries["pick"], ("Alpha", "pets/pick/pick"))

    def test_nested_pet_dir_helper_contract(self):
        """The helper alone: None for a missing/unreadable folder, never a string for
        two levels, the inner path otherwise."""
        self.assertIsNone(claude_pet._nested_pet_dir(str(self.pets / "absent")))
        write_pet(self.pets / "k" / "k")
        self.assertEqual(claude_pet._nested_pet_dir(str(self.pets / "k")), str(self.pets / "k" / "k"))
        write_pet(self.pets / "deep" / "x" / "deep")
        self.assertIsNone(claude_pet._nested_pet_dir(str(self.pets / "deep")))


class TextEncodingTests(PetTreeCase):
    def test_a_zero_byte_readme_is_rewritten_and_a_real_one_is_kept(self):
        """Rivals: 'exists → return' (the old contract, which left the 0-byte file the
        Windows run produced); rewriting every time (a user's edited README lost)."""
        readme = self.pets / "README.txt"
        readme.write_bytes(b"")
        claude_pet._write_pets_readme(str(self.pets))
        self.assertGreater(readme.stat().st_size, 0)
        self.assertEqual(readme.read_text(encoding="utf-8"), claude_pet._PETS_README)
        readme.write_text("user's own notes\n", encoding="utf-8")
        claude_pet._write_pets_readme(str(self.pets))
        self.assertEqual(readme.read_text(encoding="utf-8"), "user's own notes\n")

    def test_a_fresh_readme_is_utf8_and_mentions_the_nested_layout(self):
        """Rival: the platform default encoding, which is not UTF-8 on Windows (cp949)
        and is US-ASCII under a C locale — the red run uses the latter."""
        readme = self.pets / "README.txt"
        claude_pet._write_pets_readme(str(self.pets))
        raw = readme.read_bytes()
        self.assertEqual(raw.decode("utf-8"), claude_pet._PETS_README)
        self.assertIn("펫".encode("utf-8"), raw)
        self.assertIn("pets/dog/dog/pet.json", claude_pet._PETS_README)

    def test_pet_json_with_korean_and_emoji_display_name_reads_back(self):
        """Rival: the platform default encoding on read (cp949 / US-ASCII), which
        returns None here and the folder name instead of the display name."""
        name = "고양이 🐱"
        write_pet(self.pets / "cat", name)
        self.assertEqual(claude_pet._read_pet_json(str(self.pets / "cat"))["displayName"], name)
        entries, _order = self.found()
        self.assertEqual(entries["cat"], (name, "pets/cat"))

    def test_every_text_mode_open_names_utf8(self):
        """AST scan of the module under test. Binary modes are exempt; os.open is not
        open(). The count floor keeps the scan from passing vacuously."""
        source = Path(claude_pet.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        text_calls, missing = [], []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_open = isinstance(func, ast.Name) and func.id == "open"
            is_fdopen = (isinstance(func, ast.Attribute) and func.attr == "fdopen"
                         and isinstance(func.value, ast.Name) and func.value.id == "os")
            if not (is_open or is_fdopen):
                continue
            mode = "r"
            if len(node.args) > 1:
                mode = node.args[1].value if isinstance(node.args[1], ast.Constant) else "?"
            for kw in node.keywords:
                if kw.arg == "mode":
                    mode = kw.value.value if isinstance(kw.value, ast.Constant) else "?"
            if isinstance(mode, str) and "b" in mode:
                continue
            text_calls.append(node.lineno)
            encodings = [kw.value.value for kw in node.keywords
                         if kw.arg == "encoding" and isinstance(kw.value, ast.Constant)]
            if encodings != ["utf-8"]:
                missing.append(node.lineno)
        self.assertGreaterEqual(len(text_calls), 8, f"scan found too few text-mode opens: {text_calls}")
        self.assertEqual(missing, [], f"text-mode open()/os.fdopen() without encoding='utf-8' at lines {missing}")

    def test_run_gui_seeds_the_pets_readme_at_startup_not_only_from_the_menu(self):
        """Read as AST; run_gui is never called. The 0-byte README the Windows run left
        is repaired only if something writes it *before* the user reaches the
        '펫 추가…' menu item, so run_gui's own top level must create USER_PETS_DIR and
        call _write_pets_readme on it.

        Rivals: the call only inside open_user_pets_dir (the pre-change contract);
        the call on a different directory; makedirs skipped so the write fails on a
        fresh profile; the menu action losing its own call."""
        tree = ast.parse(Path(claude_pet.__file__).read_text(encoding="utf-8"))
        run_gui = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_gui")
        nested = {n.name: n for n in run_gui.body if isinstance(n, ast.FunctionDef)}
        top_level = [s for s in run_gui.body
                     if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]

        def calls(nodes):
            out = []
            for stmt in nodes:
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Call):
                        out.append(ast.unparse(node))
            return out

        startup = calls(top_level)
        self.assertIn("_write_pets_readme(USER_PETS_DIR)", startup,
                      "run_gui's top level no longer seeds the pets README at startup")
        self.assertIn("os.makedirs(USER_PETS_DIR, exist_ok=True)", startup)
        self.assertIn("open_user_pets_dir", nested)
        self.assertIn("_write_pets_readme(USER_PETS_DIR)", calls([nested["open_user_pets_dir"]]),
                      "the '펫 추가…' menu action must still seed the README too")
        for stmt in top_level:
            if any(isinstance(n, ast.Call) and ast.unparse(n) == "_write_pets_readme(USER_PETS_DIR)"
                   for n in ast.walk(stmt)):
                self.assertIsInstance(stmt, ast.Try,
                                      "a failed README write must not stop the app from starting")


if __name__ == "__main__":
    unittest.main()
