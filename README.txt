ITOM v36 consolidated artifact — PUBLIC RELEASE

Canonical manuscript: manuscript/ITOM_AGENT_2027_v36.pdf
Public repository: https://github.com/santoshsibyala/itom-recovery-eval
V36 follows v33 with repetition cuts, restored Introduction citations, and URL copy settings.
V32 through v35 remain frozen. Scientific results and disclosures are unchanged.
Original code uses MIT; original data/documentation uses CC BY 4.0.
See LICENSE_SCOPE.txt for exclusions. No DOI has been assigned.

ONE OFFLINE VERIFICATION COMMAND
From the extracted ITOM_v36_artifact directory:

    python3 -B verify.py

Use Python 3.11–3.13 with the system time-zone database. No pip installation is
required for offline verification. Do not use Python optimization (-O). The
command hashes the complete package, runs preserved base replay and GPT record
verification, and audits Haiku records/journals/metrics using preserved pure
scoring functions. It prints JSON to stdout and progress to stderr, exits zero
on success, and checks that package contents have not changed. It can also be
invoked by absolute path from another working directory. Save output outside
the artifact directory to keep its exact inventory intact.

No API keys, model access, Kubernetes client, Docker, cluster, LaTeX installation
or paid calls are required. The verifier uses a Python audit guard to reject
network operations and non-Python subprocesses. This is a guard against accidental
live execution, not a security boundary for running untrusted modified code.
Offline replay is an internal consistency check, not external replication or a
new experiment. It does not authenticate withheld human-review returns.

LAYOUT
- manuscript/: v36 paper and TeX, frozen v32-v35 fallbacks, figure and revision evidence.
- components/base/: intact v21 release, including its original manifest and
  verifier, initial/follow-up studies, corrected and original RAC cohorts,
  deterministic Kubernetes records, and aggregate human-review results.
- components/gpt_k8s/: intact staged GPT extension, 10 smoke and 50 main runs,
  journals, original verifier and post-measurement cleanup-repair receipt.
- components/haiku_k8s/: intact staged Haiku extension, 10 smoke and 50 main-b
  runs, journals, invalid first launch, lifecycle canary, protocols and analyses.
- verification/: portable additive Haiku verifier and offline guard.
- RESULTS_INDEX.csv: paper-to-artifact navigation, including original table
  numbering differences in historical documents.
- COMPONENTS.json / ARTIFACT_MANIFEST.json: nested provenance and consolidated
  SHA-256 inventory. The manifest excludes itself; the verifier also ignores Git metadata in a checkout.

HISTORICAL CONTENT
The base component retains its old manuscript and README to preserve its manifest.
Those are historical; manuscript/ITOM_AGENT_2027_v36.pdf is the current paper.
The original component READMEs, manifests, approvals and execution code retain
historical paths, dates, account references and authorizations. They do not grant
permission to run new experiments. The top-level offline command uses relative
package paths and never executes historical live launchers.

REPRODUCTION BOUNDARY
Offline verification covers base trace replay; deterministic Kubernetes outcomes;
aggregate human agreement; GPT outcomes, behavior, model/cost journal checks and
cleanup receipt; Haiku smoke/main-b metrics, behaviors, request contracts, model
IDs, usage-charge arithmetic, outcome/behavior summary columns, journal hashes
and the zero-request invalid launch. Ordered-read CSV files and other historical
analysis files are hash-verified; not every derived field is recomputed.
It does not recreate the original live environment, rerun model inference, infer
new human labels, independently authenticate reviewers, or recompute every word
and number in the manuscript. The figures/PDF are hash-verified, not rebuilt.

Live recreation is a separate task. Historical harnesses require pinned tools,
a cluster, configured relative dependencies, external services and separately
supplied credentials; some still contain original absolute paths and execution-
era gates. Do not use them as turnkey launch commands. Never overwrite the
included results. Figure rebuilding may require ReportLab and appropriate fonts;
none are needed to read or verify the supplied PDF.

PUBLICATION REMAINING
Original code/data licenses are selected with third-party/manuscript exclusions.
Public GitHub access is verified. Durable archiving and portal upload remain.
See EXCLUSIONS.txt and LICENSE_STATUS.txt. V36 is the current manuscript; historical manuscript versions remain unchanged.

URL COPY TESTS
All five URLs extract exactly with pdftotext. Preview paste retains a wrapping
newline in references [1] and [2]; repository, [11], and [12] paste exactly.
See manuscript/v36-verification/URL_TEST_REPORT.txt.
