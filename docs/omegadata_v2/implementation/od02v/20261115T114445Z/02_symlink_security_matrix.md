# OD-02V actual symlink-security matrix

OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `feature/od01-source-rights`, unchanged reviewed HEAD `eaedac1bddc35867f9089486beffa3bb38cb11f4`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.


The original assertions were **not modified**, xfailed or removed. Full targeted suites run the same inherited test files on all runtimes. A dedicated Linux proof runs the original three exact IDs plus positive file-symlink smoke: **4 passed, 0 failed, 0 skipped, exit 0**, [raw verbose](logs/linux312-symlink-proof.txt), [command and observed counters](logs/linux312-symlink-proof.json).

| Original scenario | Linux actual link / outside read count | Result |
|---|---|---|
| raw-cache latest pointer escape; `test_r05_cache_escape_never_opens_external_sentinel` | actual symlink **True**, outside reads **0** | PASS, invalid cache returns None before outside bytes opened |
| seed-cache latest pointer escape; `test_r05_cache_escape_never_opens_external_sentinel` | actual symlink **True**, outside reads **0** | PASS, invalid cache returns None before outside bytes opened |
| payload symlink outside raw partition; `test_r06_real_symlink_payload_escape` | actual symlink **True**, outside reads **0** | PASS, invalid cache returns None before outside bytes opened |

For the dedicated proof only, a read-only CPython return-event observer records existing local list/Mock counters and `is_symlink()` after the unmodified assertions. It does not change values, return results, exception handling or file access. Its exact disposable paths are in JSON; no protected/private sentinel data is used.

Additional [new tests](../../../../../tests/unit/test_od02v_portability.py) execute file-symlink positive capability; directory symlink/junction escape for raw and seed; broken pointers, link loops and retargeting before the cache lookup boundary for raw and seed. Linux executes all 17 new cases without skipping. Windows executes directory junction analogues and other new security tests; its seven new file-link cases skip due WinError 1314. Together with the original three that is 10 Windows skips; no skip is counted as a pass. Linux has only two Windows-specific junction skips, covered by actual Windows junction passes.

[Filesystem smoke Windows](logs/win314-filesystem.txt) records actual file-symlink privilege failure, case-insensitive paths, CRLF text output and a successful 320-character file path. [Filesystem smoke Linux](logs/linux312-filesystem.txt) records real file symlink/read-back, case-sensitive paths, LF output and a successful 304-character path. Both parse ISO UTC Z as +00:00. These are measured local capabilities, not all-filesystem guarantees.

Threat-model limit: retargeting is tested before entering the cache API; broken/loop/directory/escape confinement is real. No descriptor-based hostile ancestor-swap race during the filesystem syscall is certified. Existing cache code is not an OS sandbox against a malicious concurrent filesystem owner. This inherited limit stays explicit, production egress disabled and operational cache directories must remain access-controlled. OD-04 architecture is not implemented here.
