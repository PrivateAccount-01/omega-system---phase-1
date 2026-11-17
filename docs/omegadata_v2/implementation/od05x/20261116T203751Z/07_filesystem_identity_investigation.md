# Filesystem identity investigation

The historical Windows event remains **INPUT_CHANGED_ROOT_CAUSE_UNKNOWN**. Its differing fields were never captured. Current Windows serialized/stress tests are NOT_RUN because the required approved OS boundary is absent. Later Linux success cannot explain that historical failure.

The additive canary-only wrapper captures dev, inode, mode, size, mtime_ns, link count, directory identity, generation, process, thread and invocation. Original paths and contents are not instrumented. [Fresh native diagnostics](logs/profile-1f2fb8b1099a-identity-diagnostics.json) record 100 serial accesses, 8 threaded readers, one underlying scan, and deterministic mutation refusal. The changed metadata size/mtime are explicit. These demonstrate known-mutation invalidation only; they do not identify the cause of the old Windows event. No check or cache invalidation was disabled.
