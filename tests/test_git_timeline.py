from __future__ import annotations

from datetime import datetime
import subprocess
from unittest import TestCase

from mizuchi.git import GitClient
from mizuchi.git.timeline import FIELD_SEP, parse_commit_detail, parse_timeline


class GitTimelineTests(TestCase):
    def test_parse_timeline_counts_changed_files_and_selected_touch(self) -> None:
        raw = "\n".join(
            [
                FIELD_SEP.join(["a" * 40, "aaaaaaa", "2026-04-29T01:02:03+09:00", "Ada", "First"]),
                "1\t2\tsrc/app.py",
                "-\t-\tassets/logo.png",
                FIELD_SEP.join(["b" * 40, "bbbbbbb", "2026-04-28T01:02:03+09:00", "Ben", "Second"]),
                "3\t4\tdocs/readme.md",
            ]
        )

        commits = parse_timeline(raw, selected_file="src/app.py")

        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0].commit_hash, "a" * 40)
        self.assertEqual(commits[0].changed_files_count, 2)
        self.assertTrue(commits[0].selected_file_touched)
        self.assertFalse(commits[1].selected_file_touched)

    def test_parse_commit_detail_extracts_body_and_changed_files(self) -> None:
        raw = "\n".join(
            [
                FIELD_SEP.join(
                    [
                        "c" * 40,
                        "ccccccc",
                        "2026-04-29T01:02:03+00:00",
                        "Cy",
                        "Subject",
                        "Body line one",
                    ]
                ),
                "Body line two",
                "",
                "src/app.py",
                "tests/test_app.py",
            ]
        )

        detail = parse_commit_detail(raw)

        self.assertEqual(detail.date, datetime.fromisoformat("2026-04-29T01:02:03+00:00"))
        self.assertEqual(detail.body, "Body line one\nBody line two")
        self.assertEqual(detail.changed_files, ("src/app.py", "tests/test_app.py"))
        self.assertEqual(detail.changed_files_count, 2)

    def test_get_timeline_adds_validated_path_filter_to_log(self) -> None:
        from mizuchi.git.timeline import LOG_FORMAT, get_timeline

        calls = []
        raw = "\n".join(
            [
                FIELD_SEP.join(["a" * 40, "aaaaaaa", "2026-04-29T01:02:03+00:00", "Ada", "Touch app"]),
                "1\t2\tsrc/app.py",
            ]
        )

        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, raw, "")

        commits = get_timeline(GitClient("/repo", runner=runner), selected_file="src/app.py")

        self.assertEqual(len(commits), 1)
        self.assertTrue(commits[0].selected_file_touched)
        self.assertEqual(
            calls[0],
            [
                "git",
                "-C",
                "/repo",
                "log",
                "-n50",
                "--date=iso-strict",
                f"--pretty=format:{LOG_FORMAT}",
                "--numstat",
                "--",
                "src/app.py",
            ],
        )
