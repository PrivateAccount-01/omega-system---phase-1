"""X01-X18: offline OS-security canaries; zero financial observations.

Native probes require the real restricted worker before making any syscall.
Never run this file through an unrestricted historical controller.
"""

import hashlib
import importlib
import json
import os
import threading
from pathlib import Path

import pytest


def api():
    return importlib.import_module("od05x_isolated_runner")


def manifest(root):
    source = root / "source"
    source.mkdir()
    (source / "ok.py").write_text("# NON_MARKET_CANARY\n")
    raw = (source / "ok.py").read_bytes()
    return source, {
        "schema_version": "od05x.inputs/v1",
        "file_count": 1,
        "files": [{"path": "ok.py", "class": "CODE", "bytes": len(raw),
                   "sha256": hashlib.sha256(raw).hexdigest()}],
    }


def test_x01_missing_sandbox_fail_closed(tmp_path):
    h = api()
    source, spec = manifest(tmp_path)
    with pytest.raises(ValueError, match="ISOLATION"):
        h.stage(source, tmp_path / "dest", spec, capability=None)
    assert not (tmp_path / "dest").exists()


def test_x02_incorrect_capability_refused(tmp_path):
    h = api()
    source, spec = manifest(tmp_path)
    with pytest.raises(ValueError, match="ISOLATION"):
        h.stage(source, tmp_path / "dest", spec, capability={"verified": True})
    assert not (tmp_path / "dest").exists()


@pytest.mark.parametrize("probe", ["read", "write", "exec", "tcp", "dns"])
def test_x03_x06_native_os_denial(probe):
    h = api()
    h.assert_boundary()
    result = h.native_probe(probe)
    assert result["denied"] is True
    assert result["native_return"] == -1 and result["errno"] > 0
    assert result["python_hook"] is False


def test_x07_single_staging_entrypoint():
    h = api()
    source = Path(h.__file__).read_text()
    assert "copy_sources(" not in source and "shutil.copy" not in source
    assert "control.py" not in source
    assert h.STAGING_ENTRYPOINT == "stage"


@pytest.mark.parametrize("change", ["hash", "class", "count", "traversal", "unknown"])
def test_x08_manifest_refusal(tmp_path, change):
    h = api()
    source, spec = manifest(tmp_path)
    if change == "hash":
        spec["files"][0]["sha256"] = "0" * 64
    elif change == "class":
        spec["files"][0]["class"] = "UNREVIEWED"
    elif change == "count":
        spec["file_count"] = 2
    elif change == "traversal":
        spec["files"][0]["path"] = "../ok.py"
    else:
        spec["files"].append(dict(spec["files"][0], path="unknown.py"))
        spec["file_count"] = 2
    with pytest.raises((ValueError, OSError)):
        h.stage(source, tmp_path / "dest", spec, capability=h.assert_boundary())


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "destination"])
def test_x09_link_escape_refused(tmp_path, kind):
    h = api()
    source, spec = manifest(tmp_path)
    dest = tmp_path / "dest"
    if kind == "hardlink":
        os.link(source / "ok.py", source / "second.py")
    elif kind == "symlink":
        (source / "ok.py").rename(source / "real.py")
        (source / "ok.py").symlink_to(source / "real.py")
    else:
        (tmp_path / "redirect").symlink_to(source, target_is_directory=True)
        dest = tmp_path / "redirect" / "dest"
    with pytest.raises((ValueError, OSError)):
        h.stage(source, dest, spec, capability=h.assert_boundary())


@pytest.mark.parametrize("when", ["before_open", "after_read"])
def test_x10_mutation_refused(tmp_path, when):
    h = api()
    source, spec = manifest(tmp_path)

    def mutate():
        (source / "ok.py").write_text("# NON_MARKET_CANARY_CHANGED\n")

    with pytest.raises(ValueError, match="CHANGED"):
        h.stage(source, tmp_path / "dest", spec, capability=h.assert_boundary(),
                hooks={when: mutate})


def test_x11_no_output_overwrite(tmp_path):
    h = api()
    source, spec = manifest(tmp_path)
    dest = tmp_path / "dest"
    receipt = h.stage(source, dest, spec, capability=h.assert_boundary())
    assert receipt["file_count"] == 1
    assert receipt["payload_files_copied"] == 0
    with pytest.raises(ValueError, match="FRESH"):
        h.stage(source, dest, spec, capability=h.assert_boundary())
    assert (dest / "ok.py").read_bytes() == (source / "ok.py").read_bytes()


def test_x12_identity_diagnostic(tmp_path):
    h = api()
    repo, pins, meta = h.small_canary(tmp_path)
    events = []
    observation = h.CanaryObservation(repo, "seed", pins, events)
    observation.get()
    meta.write_bytes(meta.read_bytes() + b" ")
    with pytest.raises(Exception, match="INPUT_CHANGED"):
        observation.get()
    event = events[-1]
    assert event["reason"] == "INPUT_CHANGED" and event["changes"]
    assert event["generation"] and event["thread"] and event["process"]
    assert str(tmp_path) not in json.dumps(event)
    assert set(event["changes"][0]["before"]) == {
        "dev", "ino", "mode", "size", "mtime_ns", "nlink"
    }


def test_x13_concurrent_invalidation(tmp_path):
    h = api()
    repo, pins, meta = h.small_canary(tmp_path)
    events = []
    observation = h.CanaryObservation(repo, "seed", pins, events)
    observation.get()
    start = threading.Event()
    done = threading.Event()

    def mutation():
        start.wait()
        meta.write_bytes(meta.read_bytes() + b" ")
        done.set()

    thread = threading.Thread(target=mutation)
    thread.start()
    start.set()
    assert done.wait(10)
    with pytest.raises(Exception, match="INPUT_CHANGED"):
        observation.get()
    thread.join()
    assert observation.scan_count == 1 and events[-1]["changes"]


def test_x14_native_not_original():
    h = api()
    assert h.corpus_status("NON_MARKET_CANARY")["financial_rows"] == 0
    assert h.corpus_status("LOCAL_META")["financial_rows"] == 0
    with pytest.raises(ValueError):
        h.corpus_status("AUTHENTIC_MARKET_DATA")


def test_x15_unknown_nodes_not_arbitrary_A():
    h = api()
    with pytest.raises(ValueError, match="UNCLASSIFIED"):
        h.classify(["new"], {"known": "A"})
    assert h.classify(["known"], {"known": "A"}) == {"known": "A"}


def test_x16_B_C_preserved():
    h = api()
    report = h.verdicts(software=False, containment=False)
    assert report["B"] == "BLOCKED_INPUT" and report["C"] == "NOT_RUN_BLOCKED_REAL_DATA"
    assert h.diagnostic_status(1) == "FAIL"


def test_x17_preservation_fail_closed(tmp_path):
    h = api()
    source, spec = manifest(tmp_path)
    assert h.verify_pins(source, spec) == 1
    (source / "ok.py").write_text("# changed NON_MARKET_CANARY\n")
    with pytest.raises(ValueError, match="CHANGED"):
        h.verify_pins(source, spec)


def test_x18_separate_gatekeeper_axes():
    report = api().verdicts(software=True, containment=False)
    assert report["software"] == "PASS" and report["containment"] == "BLOCKED"
    assert report["financial"] == "BLOCKED_REAL_DATA"
    assert report["safe_engineering"] == "BLOCKED"


def test_x15_collected_inventory_and_source_pins():
    h = api()
    report = h.reconcile_reviewed_inputs(Path("/work/repo"))
    assert report["old_nodes"] == 775
    assert report["old_classes"] == {"A": 767, "B": 4, "C": 4}
    assert report["all_reviewed_test_hashes_match"] is True
    assert report["new_test_class"] == "EXPLICIT_REVIEWED_A"


def test_x16_original_B_C_identities_preserved():
    report = api().reconcile_reviewed_inputs(Path("/work/repo"))
    assert report["B_exact_unchanged"] == 4 and report["C_exact_blocked"] == 4
    assert report["C_executed"] == 0


def test_x17_fresh_original_stat_reconciliation():
    report = api().reconcile_reviewed_inputs(Path("/work/repo"))
    assert report["fresh_stat_counts"] == {
        "seed": 3596, "cache": 30, "present": 3626,
        "size_matched": 3626, "hardlinked": 2760, "single_link": 866, "missing": 0,
    }
    assert report["all_candidate_identities_accounted"] == 3626
    assert report["original_byte_integrity"] == "NOT_MEASURED"
