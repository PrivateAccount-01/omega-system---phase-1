"""WIN01-WIN20 safe contract tests; native Windows proof is separately blocked.

These tests may run only in the accepted isolated Linux worker until an approved
Windows VM/worker exists. Harmless canaries contain no financial observations.
"""
import copy
import hashlib
import importlib
from pathlib import Path

import pytest


def api():
    return importlib.import_module("od05xr1_windows_backend")


def spec():
    raw = b"# NON_MARKET_CANARY\n"
    return {"schema_version": "od05x.inputs/v1", "file_count": 1,
            "files": [{"path": "scripts/ok.py", "class": "CODE", "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}]}


def test_win01_no_backend_before_input_read(tmp_path):
    with pytest.raises(ValueError, match="OS_ISOLATION_CAPABILITY_BLOCKED"):
        api().launch_windows(tmp_path / "not-read.json", "0" * 64,
                             tmp_path / "not-created", configuration=None)
    assert not (tmp_path / "not-created").exists()


def test_win02_false_VM_report_refused(tmp_path):
    with pytest.raises(ValueError, match="UNVERIFIED_WINDOWS_BOUNDARY"):
        api().launch_windows(tmp_path / "not-read.json", "0" * 64,
                             tmp_path / "not-created", configuration={
                                 "verified": True, "backend": "WindowsSandbox",
                                 "native_probes_passed": True})
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("group", ["WIN03", "WIN04", "WIN05", "WIN06", "WIN15", "WIN18", "WIN20"])
def test_windows_native_execution_requires_approved_VM(group):
    # No native attack is issued on the unrestricted host to obtain a red result.
    pytest.skip(group + ": OS_CAPABILITY_BLOCKED; approved Windows VM/worker absent")


@pytest.mark.parametrize("change", ["unknown", "class", "count", "duplicate"])
def test_win07_exact_source_contract(change):
    manifest = spec()
    approved = copy.deepcopy(manifest)
    if change == "unknown":
        manifest["files"][0]["path"] = "scripts/unreviewed.py"
    elif change == "class":
        manifest["files"][0]["class"] = "DOCUMENTATION"
    elif change == "count":
        manifest["file_count"] = 0
    else:
        manifest["files"].append(copy.deepcopy(manifest["files"][0]))
        manifest["file_count"] = 2
    with pytest.raises(ValueError):
        api().validate_reviewed_manifest(manifest, approved)


def test_win08_changed_hash_refused():
    manifest = spec()
    approved = copy.deepcopy(manifest)
    manifest["files"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="REVIEWED_MANIFEST_MISMATCH"):
        api().validate_reviewed_manifest(manifest, approved)


@pytest.mark.parametrize("change", ["reparse", "hardlink", "volume", "directory"])
def test_win09_win10_native_identity_contract(change):
    before = api().FileIdentity(10, 20, 21, 0x80, 1, False)
    fields = {"volume": 10, "file_id": 20, "size": 21, "attributes": 0x80,
              "links": 1, "directory": False}
    fields.update({"reparse": {"attributes": 0x480}, "hardlink": {"links": 2},
                   "volume": {"volume": 11}, "directory": {"directory": True}}[change])
    with pytest.raises(ValueError, match="WINDOWS_SOURCE_UNSAFE"):
        api().validate_file_identity(api().FileIdentity(**fields), before, expected_volume=10)


@pytest.mark.parametrize("name", ["C:ok.py", "C:/ok.py", "//host/share/ok.py", "../ok.py",
                                  "scripts/x.py:ads", "scripts/CON.py", "scripts/NUL.py",
                                  "scripts/COM1.py", "scripts/LPT9.py", "scripts/ok.py.",
                                  "scripts/ok.py ", "scripts/x./ok.py", "scripts/ok\\x.py"])
def test_win11_windows_path_hazards(name):
    with pytest.raises(ValueError, match="WINDOWS_PATH_UNSAFE"):
        api().windows_relative(name)


def test_win11_case_alias():
    manifest = spec()
    approved = copy.deepcopy(manifest)
    manifest["files"][0]["path"] = "Scripts/ok.py"
    with pytest.raises(ValueError, match="REVIEWED_MANIFEST_MISMATCH"):
        api().validate_reviewed_manifest(manifest, approved)


@pytest.mark.parametrize("when", ["before_open", "after_open"])
def test_win12_win13_identity_change_refused(when):
    before = api().FileIdentity(10, 20, 21, 0x80, 1, False)
    changed = api().FileIdentity(10, 21, 21, 0x80, 1, False)
    with pytest.raises(ValueError, match="WINDOWS_INPUT_CHANGED"):
        api().validate_file_identity(changed, before, expected_volume=10)
    # A pure identity comparison does not certify an actual Windows handle race.
    assert when in {"before_open", "after_open"}


def test_win14_fresh_destination(tmp_path):
    dest = tmp_path / "existing"
    dest.mkdir()
    with pytest.raises(ValueError, match="FRESH_DESTINATION_REQUIRED"):
        api().validate_destination(dest)
    assert list(dest.iterdir()) == []


def test_win16_reviewed_runtime_inventory():
    h = api()
    reviewed = {"one": "A", "two": "B", "three": "C"}
    assert h.reconcile_nodes(["three", "one", "two"], reviewed) == reviewed
    with pytest.raises(ValueError, match="UNCLASSIFIED"):
        h.reconcile_nodes([*reviewed, "unreviewed"], reviewed)


def test_win17_linux_source_contract_retained():
    h = importlib.import_module("od05x_isolated_runner")
    assert h.STAGING_ENTRYPOINT == "stage"
    assert len(h.entries(spec())) == 1
    assert Path(h.__file__).name == "od05x_isolated_runner.py"


def test_win19_financial_and_incident_gates():
    report = api().gatekeeper(linux=True, windows314=False, windows311=False,
                             windows_containment=False)
    assert report["G1"] == "PASS"
    assert report["G2"] == report["G3"] == "BLOCKED"
    assert report["G4"] == "BLOCKED_REAL_DATA"
    assert report["incident"] == "PENDING_HUMAN_OWNER_REVIEW"
    assert report["verified_market_rows"] == 0
    assert report["safe_engineering"] == "BLOCKED"


def test_win07_positive_exact_manifest():
    assert api().validate_reviewed_manifest(spec(), spec()) == spec()["files"]


def test_win10_positive_identity_contract():
    original = api().FileIdentity(10, 20, 21, 0x80, 1, False)
    assert api().validate_file_identity(original, original, expected_volume=10) is None
