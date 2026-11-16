# OD-05W identity and preservation

Branch `feature/od01-source-rights`, reviewed/current HEAD `c8e7ff974e6c4a471a002d4807f268dc5d0044b1`. No commit, push, merge, release or later phase. Entry commands and exact diffs are in [entry](logs/entry.json); the phase prompt, pre-existing environments and untracked signing paths were preserved.

Allowed patch: [presence library](../../../../../src/omegadata/parsers/local_archive_presence.py), [presence CLI](../../../../../scripts/audit_local_archive_presence.py), new [safe copy contract](../../../../../scripts/od05w_safe_harness.py), new [W tests](../../../../../tests/unit/test_od05w_engineering.py), and an explicit immutable-observation/native-canary harness contract in [existing presence tests](../../../../../tests/unit/test_od05v_local_presence.py). All other application, source-policy, financial expectation, routing, database and signing/release code is unchanged.

[Preservation](preservation.json): 364 current-run code/evidence identities, 202 previous sealed evidence files, 3,626 fresh before/after archive stat records, and 11210 historical-to-current data/artifact/database metadata comparisons. No unexpected hash/stat change. Historical-to-current is ARCH compared with RUN, not a new pre-run snapshot. Raw payload/key bytes were never hashed for this check. Size/mtime/inode/link preservation is not byte-integrity certification.

Installed runtime identities and packages are in each `*-r3-accepted-environment` log. Windows 3.14.3, Windows 3.11.15 and WSL/native Ubuntu 3.12.3 share one physical host. No independent hardware claim.
