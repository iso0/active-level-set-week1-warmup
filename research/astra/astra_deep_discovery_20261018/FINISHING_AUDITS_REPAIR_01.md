# Technical repair before the finishing observer's first launch

19 October 2026, approximately 04:22 UTC. No finishing scientific check or fit
had started. An attempt to update Astra's own handoff metadata under the shared
coordinator lock failed at `System.IO.File.Replace(source, destination, $null)`:
PowerShell bound the null backup-path argument as an empty path. The original
shared record was not replaced; the lock was released. No active worker failed.

An isolated file probe in this package's runtime directory verified that passing
`[NullString]::Value` instead performs the intended atomic replacement. The same
binding appeared in the unlaunched finishing observer, so it is repaired now.
`history/finishing_v1/source/` preserves all six original frozen files byte for
byte, with the original FROZEN_FINISHING_AUDITS.json unchanged. The repaired
observer and checks read FROZEN_FINISHING_AUDITS_V1_1.json. Only the filesystem
argument and references to the repaired manifest change; the finite example,
checks, budgets, targets and scientific code do not.

This is a preparation failure and filesystem repair, not a failed controlled GP
experiment or a reason to reset the campaign clock. Existing frozen v2, quota
and acquisition-audit source hashes still agree. The original acquisition audit
remains six paid-prefix reconstruction fits, with no additional reservation.
