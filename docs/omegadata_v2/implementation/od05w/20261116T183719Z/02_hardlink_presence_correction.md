# Versioned physical presence

[Fresh baseline](logs/original-v1-baseline.json), [independent stat reconciliation](logs/original-stat.json), [v2 result/profile](logs/original-v2-post.json), and [actual guarded CLI calls](logs/original-cli-proof.json).

| Fact | v1 | v2 |
|---|---:|---:|
| Manifest candidates | 3626 | 3626 |
| Regular paths observed | 3626 | 3626 |
| Simplified present/size-match totals | 866 | 3626 |
| Hardlinked regular paths | 2760, HARDLINK_REFUSED | 2760, PRESENT_HARDLINK_SIZE_MATCHED |
| Missing paths | 0 | 0 |
| Eligible for content inspection | never granted | 0 |

Seed: 3596 present/matched, 2760 hardlinks, 836 single links. Cache: 30 present/matched, all single links. Each v2 row separates path existence, regular type, filesystem length match, link class, discovery state, rights eligibility and four false content/authenticity/financial verification fields. A hardlink size mismatch is SIZE_MISMATCH with HARDLINKED retained. Manifest identity and original claims remain; payload bytes are not read.

Library v1 remains the default for existing callers; opt-in `version=2` supplies the new report. CLI defaults to v2 and offers `--report-version 1`. Fresh seed CLI exits: v2 `0`, v1 `2`, `--payload-integrity` `2 / POLICY_PENDING`. Exit 0 means stat discovery/length agreement only. Integrity requests never report success without content verification. No RawArchive, source-rights, registry or acquisition semantics changed.

The 2020 legacy-name claim remains ERA_CONFLICT_2020_REFERENCE_PENDING; 2011 lineage is a repository claim; the July 2024 URL is a manifest claim. No historical schema or issuer-origin certification follows from stat agreement.
