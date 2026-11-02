# Portable review archive

ASTRA_LOCAL_CORRECTION_REVIEW.zip contains all selected stable study artifacts. FILE_MANIFEST.json lists each member SHA-256 and is also embedded. ZIP_RECEIPT.json is a companion generated after all member hashes are verified; it cannot contain its own archive hash from inside the archive. Mutable STATE/NEXT_ACTION/EVENTS, the final post-seal completion receipt, environment and Git internals are outside the ZIP. Actual shutdown evidence, complete attempt ledger, sources, predictions and frozen protocols are inside.

Do not rerun the closed queue. No installed environment or scheduled task is recreated by extraction.
