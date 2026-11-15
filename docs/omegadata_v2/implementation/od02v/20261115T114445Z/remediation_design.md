# OD-02V bounded confidentiality remediation

Reviewed baseline eaedac1bddc35867f9089486beffa3bb38cb11f4, before application edits. The executable `confidentiality-negative` run produced seven failed assertions (exit 1): recognized credential-like path fields survive `safe_url`, propagate into typed error context, and legacy cached `used_url` bypasses redaction entirely. All values were synthetic; no actual credential, provider request or exfiltration occurred.

Minimal correction: redact values following explicit credential field segments (`token`, `access_token`, `api_key`, `apikey`, `password`, `secret`, `authorization`, `signature`) and matching `field=value` segments, recognizing percent-encoded field labels. Preserve ordinary URL paths and the existing authority/query/fragment redaction. Apply the same evidence-only sanitizer to the legacy cached artifact's exposed URL. Transport request URLs and archived original bytes remain unchanged. Malformed legacy URLs conservatively display a redacted placeholder.

Review: this addresses a deterministic confidentiality failure under both Windows and Linux; the functions use only stdlib URL parsing. It does not claim to discover secrets in arbitrary unlabeled opaque path values. Real egress remains blocked; callers must not embed such credentials in acquisition URLs. No policy, archive format, signing, release, financial schema, retry or transport authorization changes. Same-model review, not external security approval.

The new tests also exercise real directory/file links, broken/looped pointers and retargeting **before** the cache API boundary. They do not certify descriptor-level protection against a hostile writer swapping ancestors during a syscall; that separately documented filesystem-isolation limitation remains.
