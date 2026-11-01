# Public-release exclusions

This package is a filtered copy. Original local records are unchanged. No file from the original `ITOM/reviews/` or `ITOM/reviews_v1_1/` trees is included. The full per-file exclusion inventory is kept privately alongside the release ZIP as `EXCLUDED_FILES_PRIVATE.json`, rather than republishing private filenames.

## Human-review and administrative material withheld

- Entire original reviewer/inspector/coordinator archives: identities and contact details; original pilot, recalibration and main response forms; reviewer/inspector declarations; individual prior-exposure, relationship, conflict and consent disclosures; correspondence; tracking and intake records; packet-delivery records and archives; freeze/inspection administrative records; and post-lock discussion and adjudication correspondence.
- All blinded review packets, case mappings, coordinator keys and private review keys, including `heldout_v03/analysis_final/PRIVATE_review_key.json`, `heldout_v03/analysis_final/blinded_review/`, `heldout_v03/artifacts/*blinded*`, `followup_v05/review_materials/`, and the corresponding `critical_review_v04/reproduction/` private key and blinded-review directory. Only the published aggregate confusion matrix and resolved distribution are exported.
- Reviewer identities and original individual disclosures are not reconstructed from the manuscript's aggregate descriptions. The manuscript's already approved pseudonyms, methods and limitations remain unchanged.
- Standalone Kubernetes author-approval/launch administration: `A1_APPROVAL.json`, `MAIN_APPROVAL.json`, `results/MAIN_LAUNCH.json`, and transient `results/main.lock`. The scientific protocols, A1 amendment record, cohort documentation, raw provenance fields and original scientific manifests remain, including the author's public attribution in those protocol records.
- Private access checks, account/budget SQLite databases and author-workspace preservation/packaging administration. Published aggregate model-usage estimates remain in the analysis outputs; no private billing/account ledger is released.

- All kubeconfig files and embedded client credentials, including the local kind configuration. No cluster credentials are distributed.

## Nonessential or redundant files omitted

- Git history, virtual environments, downloaded tool caches, Python bytecode, symlinks, operating-system metadata, installation transcripts, console logs, runtime databases and lock files.
- Nested ZIP/tar archives, old manuscript PDFs/TeX/drafts, layout-preview images and superseded paper-only revisions. The current v19 manuscript and vector figure are included explicitly.
- Historical review-building utilities, private readiness notes, old packaging/finalization scripts, and the original workspace-only manifests/checks that describe unpublished administrative deliverables. Original scientific source/protocol manifests are retained and may reference excluded private accounting or approval files; they are historical records, not complete release inventories.
- Development-pilot outcomes and IAM materials outside the scientific cohorts selected here. The `prototype_v02/itom` utility sources required by held-out imports are retained; its live budget ledger is not.

## Integrity and interpretation

The included original experimental source and record files are copied byte-for-byte; no policy identifier, trace, report, or annotation was edited. This release has its own `PUBLIC_MANIFEST.json` for the filtered file set. Its hash check is separate from old workspace-wide provenance manifests. `verify_public.py` checks released data without requiring private ledgers, contacting providers, or changing the original experiment repositories.

The public package does not permit case-by-case re-audit of the withheld human returns. It permits reproduction of aggregate agreement from the published matrix. That is distinct from independently authenticating reviewers or reproducing their judgments.
