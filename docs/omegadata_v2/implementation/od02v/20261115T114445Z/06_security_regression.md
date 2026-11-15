# OD-02V security/acquisition regression

OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `feature/od01-source-rights`, unchanged reviewed HEAD `eaedac1bddc35867f9089486beffa3bb38cb11f4`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.


All original OD-01/OD-01R/OD-02 tests execute unchanged on each required runtime, alongside 17 new security/portability cases. Test-time fake APPROVED records are in-memory SYNTHETIC_TEST_ONLY fixtures; final real register remains **13 PENDING_REVIEW, zero APPROVED**, unchanged bytes/hash. No actual exchange/provider request, paid call, signer command, production pipeline/probe CLI, warehouse sync, release build or publication was invoked.

| Guarantee | Actual asserted coverage |
|---|---|
| Default pending/unknown/expired/revoked/transport/host and operation scope | All original policy and zero-side-effect tests, mid-fetch/store/bootstrap revocation and cache/seed refusal, entire targeted matrices exit 0 |
| Fake approval does not enable actual egress | HTTPX HTTPTransport callback spy remains uncalled; default urllib/curl refuse BLOCKED_EXTERNAL_EGRESS; unregistered StockReachGraph and legacy diagnostics remain blocked |
| Provider denial terminal across pipeline | 401/403/404/429/451, Retry-After, HTML denial, bootstrap/discovery/profile/candidate/fallback, zero later request assertions; selected 503 finite retry and recovery |
| Redirect/TLS/authority/SSRF | All redirects refused, including allowed-to-allowed; bad scheme/port/userinfo/private/metadata/URL, proxy override and TLS invalid terminal; resolver never called when actual transport disabled |
| Whole-job resource limits | Existing attempt/deadline/backoff/stream/body/header length/ZIP expansion/entry/ratio/rows/config/override negative cases; no trusted partial writes |
| Payload/date/provenance | Legacy/new NSE and BSE synthetic schemas/date/zero-volume/invalid rows, JSON denial/duplicate/malformed forms, exact original SHA, cache vs seed vs mock-unverified distinction, concurrent date contexts |
| Confidentiality | Seven red-before/green-after tests remove recognized URL path credentials and legacy URL query values from exposed artifacts and structured exceptions. Normal request targets and archived bytes remain unchanged |
| Host isolation guard | New V01 plus inherited harness test block DNS/TCP/UDP/subprocess/protected file/SQLite; Linux additionally tests dir_fd protected deletion/open refusal; socketpair allowed only for stdlib internal asyncio mechanics |
| Filesystem confinement | Original three real file symlinks execute on Linux with observed outside-read calls zero; directory links/junctions, broken/loop/retarget raw and seed cases; no privileged skip counted as pass |

- Windows 3.14.3: final targeted guard denials **{"DNS": 2, "PROTECTED_WRITE": 4, "SOCKET": 1, "SUBPROCESS": 2, "UDP": 1}**, [full outcome JSON](logs/win314-reviewed-full.json). These are deliberately refused test attempts, not outbound provider traffic.
- Windows 3.11.15: final targeted guard denials **{"DNS": 2, "PROTECTED_WRITE": 4, "SOCKET": 1, "SUBPROCESS": 2, "UDP": 1}**, [full outcome JSON](logs/win311-reviewed-full.json). These are deliberately refused test attempts, not outbound provider traffic.
- WSL Linux 3.12.3: final targeted guard denials **{"DNS": 2, "PROTECTED_WRITE": 6, "SOCKET": 1, "SUBPROCESS": 2, "UDP": 1}**, [full outcome JSON](logs/linux312-reviewed-full.json). These are deliberately refused test attempts, not outbound provider traffic.


Runner scope: trusted Python test code, not a hostile arbitrary-Python/ctypes sandbox. During pytest imports/execution the audit hook rejects network/process effects and writes beyond its fresh root, including descriptor-relative paths resolved to actual native directories. Signing paths outside sandbox are never read. Native source copies contain no credentials/GnuPG and only exact fixture allowlist archives. Static tools/package consistency checks do not execute application jobs; install network was separately authorized official PyPI only. No blanket loopback/private-network allowance was added.

Remaining limits: no DNS-pinned real transport, authenticated legal approval authority, independent official source-era/financial reconciliation, descriptor-atomic hostile filesystem-race proof, crash/process storage publication, supply-chain advisory/CI clearance or independent physical host certification. Original **D-01 signing custody P0 and D-04 publication/promotion P0 remain OPEN**. D-02/03/06/08/09 financial/storage/provenance findings remain assigned to later approved phases. No strategy/profit/trade claim. Browser/OD-03 and archive/OD-04 implementation were not begun.
