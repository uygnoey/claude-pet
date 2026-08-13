import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import claude_pet


UTC = timezone.utc
BASE = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def usage_record(
    *,
    timestamp,
    message_id="msg-1",
    request_id="req-1",
    model="claude-opus-5",
    input_tokens=0,
    output_tokens=0,
    cache_creation_input_tokens=0,
    cache_read_input_tokens=0,
    cache_creation=None,
    is_sidechain=False,
):
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
    }
    if cache_creation is not None:
        usage["cache_creation"] = cache_creation
    return {
        "type": "assistant",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "requestId": request_id,
        "isSidechain": is_sidechain,
        "message": {
            "id": message_id,
            "model": model,
            "role": "assistant",
            "usage": usage,
        },
    }


class ParseUsageEntriesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_log_dirs = claude_pet.LOG_DIRS
        claude_pet.LOG_DIRS = [self.temp_dir.name]
        self.addCleanup(setattr, claude_pet, "LOG_DIRS", self.original_log_dirs)

    def write_log(self, records, relative_path="session.jsonl"):
        path = Path(self.temp_dir.name, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record) + "\n")
        os.utime(path, None)
        return path

    def test_streaming_duplicates_keep_the_final_usage_snapshot(self):
        records = [
            usage_record(timestamp=BASE, output_tokens=3),
            usage_record(timestamp=BASE + timedelta(seconds=1), output_tokens=40),
            usage_record(timestamp=BASE + timedelta(seconds=2), output_tokens=250),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        timestamp, weighted, model, noncache = entries[0]
        self.assertEqual(timestamp, BASE + timedelta(seconds=2))
        self.assertEqual(weighted, 1_250)
        self.assertEqual(noncache, 1_250)
        self.assertEqual(model, "claude-opus-5")

    def test_record_before_since_does_not_hide_a_later_snapshot(self):
        records = [
            usage_record(timestamp=BASE - timedelta(seconds=1), output_tokens=3),
            usage_record(timestamp=BASE + timedelta(seconds=1), output_tokens=100),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], BASE + timedelta(seconds=1))
        self.assertEqual(entries[0][1], 500)

    def test_equal_timestamp_duplicates_keep_the_largest_complete_snapshot(self):
        records = [
            usage_record(timestamp=BASE, output_tokens=200),
            usage_record(timestamp=BASE, output_tokens=5),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1], 1_000)

    def test_equal_weight_duplicates_keep_the_later_timestamp(self):
        records = [
            usage_record(timestamp=BASE, output_tokens=20),
            usage_record(timestamp=BASE + timedelta(seconds=1), output_tokens=20),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], BASE + timedelta(seconds=1))
        self.assertEqual(entries[0][1], 100)

    def test_streaming_duplicates_keep_an_interior_maximum(self):
        records = [
            usage_record(timestamp=BASE, output_tokens=5),
            usage_record(timestamp=BASE + timedelta(seconds=1), output_tokens=200),
            usage_record(timestamp=BASE + timedelta(seconds=2), output_tokens=50),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], BASE + timedelta(seconds=1))
        self.assertEqual(entries[0][1], 1_000)

    def test_distinct_request_ids_are_counted_separately(self):
        records = [
            usage_record(timestamp=BASE, request_id="req-1", output_tokens=10),
            usage_record(
                timestamp=BASE + timedelta(seconds=1),
                request_id="req-2",
                output_tokens=20,
            ),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 2)
        self.assertEqual(sum(entry[1] for entry in entries), 150)

    def test_records_without_dedup_keys_are_counted_independently(self):
        records = [
            usage_record(
                timestamp=BASE,
                message_id=None,
                request_id=None,
                output_tokens=10,
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=1),
                message_id=None,
                request_id=None,
                output_tokens=20,
            ),
        ]
        self.write_log(records)

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 2)
        self.assertEqual(sum(entry[1] for entry in entries), 150)

    def test_malformed_usage_numbers_skip_only_the_bad_rows(self):
        malformed = [
            usage_record(
                timestamp=BASE,
                request_id="valid-after-bad-rows",
                output_tokens="not-a-number",
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=1),
                request_id="bad-cache",
                cache_creation_input_tokens=10,
                cache_creation={"ephemeral_1h_input_tokens": "broken"},
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                request_id="non-finite",
                input_tokens=float("inf"),
            ),
            [],
            {
                "timestamp": BASE.isoformat(),
                "message": "not-an-object",
            },
            {
                "timestamp": BASE.isoformat(),
                "message": {"id": "bad-usage", "usage": [1, 2, 3]},
            },
            {
                "timestamp": 12345,
                "message": {"id": "bad-timestamp", "usage": {"input_tokens": 1}},
            },
            {
                "timestamp": BASE.replace(tzinfo=None).isoformat(),
                "message": {"id": "naive-timestamp", "usage": {"input_tokens": 1}},
            },
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                request_id="bad-model",
                model=12345,
                input_tokens=1,
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                request_id="negative-token-count",
                input_tokens=-100,
                output_tokens=100,
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                request_id="weighted-overflow",
                output_tokens=1e308,
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                request_id="huge-json-integer",
                output_tokens=10**1000,
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                request_id="bad-cache-shape",
                cache_creation_input_tokens=1,
                cache_creation=[{"unexpected": "list"}],
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                message_id=[],
                request_id="unhashable-message-id",
                output_tokens=1,
            ),
            usage_record(
                timestamp=BASE + timedelta(seconds=2),
                message_id="unhashable-request-id",
                request_id={"bad": "shape"},
                output_tokens=1,
            ),
        ]
        valid = usage_record(
            timestamp=BASE + timedelta(seconds=3),
            request_id="valid-after-bad-rows",
            output_tokens=20,
        )
        self.write_log([*malformed, valid])

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], BASE + timedelta(seconds=3))
        self.assertEqual(entries[0][1], 100)

    def test_nested_sidechain_agent_usage_is_included(self):
        record = usage_record(
            timestamp=BASE,
            output_tokens=20,
            is_sidechain=True,
        )
        self.write_log(
            [record],
            "session-id/subagents/agent-a-parser.jsonl",
        )

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1], 100)

    def test_cache_creation_uses_ttl_specific_weights(self):
        record = usage_record(
            timestamp=BASE,
            input_tokens=10,
            output_tokens=2,
            cache_creation_input_tokens=300,
            cache_read_input_tokens=50,
            cache_creation={
                "ephemeral_5m_input_tokens": 100,
                "ephemeral_1h_input_tokens": 200,
            },
        )
        self.write_log([record])

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        # input 10 + output 2*5 + 5m cache 100*1.25
        # + 1h cache 200*2 + cache read 50*0.1
        self.assertEqual(entries[0][1], 550)
        self.assertEqual(entries[0][3], 545)

    def test_legacy_cache_creation_without_breakdown_uses_5m_fallback(self):
        record = usage_record(
            timestamp=BASE,
            cache_creation_input_tokens=80,
        )
        self.write_log([record])

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1], 100)
        self.assertEqual(entries[0][3], 100)

    def test_unclassified_cache_creation_remainder_uses_5m_fallback(self):
        record = usage_record(
            timestamp=BASE,
            cache_creation_input_tokens=300,
            cache_creation={
                "ephemeral_5m_input_tokens": 100,
                "ephemeral_1h_input_tokens": 100,
            },
        )
        self.write_log([record])

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        # 5m 100*1.25 + 1h 100*2 + unclassified remainder 100*1.25
        self.assertEqual(entries[0][1], 450)
        self.assertEqual(entries[0][3], 450)

    def test_nested_cache_breakdown_above_flat_total_is_clamped(self):
        record = usage_record(
            timestamp=BASE,
            cache_creation_input_tokens=100,
            cache_creation={
                "ephemeral_5m_input_tokens": 100,
                "ephemeral_1h_input_tokens": 100,
            },
        )
        self.write_log([record])

        entries = claude_pet.parse_usage_entries(BASE - timedelta(minutes=1))

        self.assertEqual(len(entries), 1)
        # Nested values are authoritative; an inconsistent smaller flat field must not
        # create a negative remainder that subtracts already-accounted cache tokens.
        self.assertEqual(entries[0][1], 325)
        self.assertEqual(entries[0][3], 325)


class ComputeUsageTests(unittest.TestCase):
    def test_rolling_week_has_no_single_reset_timestamp(self):
        original_parser = claude_pet.parse_usage_entries
        original_window = claude_pet._weekly_window_start
        claude_pet.parse_usage_entries = lambda since: [
            (BASE, 100.0, "claude-opus-5", 100.0),
        ]
        claude_pet._weekly_window_start = lambda: None
        self.addCleanup(setattr, claude_pet, "parse_usage_entries", original_parser)
        self.addCleanup(setattr, claude_pet, "_weekly_window_start", original_window)

        stats = claude_pet.compute_usage()

        self.assertIsNone(stats["weekly"]["reset"])
        self.assertIsNone(stats["opus"]["reset"])


if __name__ == "__main__":
    unittest.main()
