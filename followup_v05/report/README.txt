ITOM v05 follow-up artifact

Execution sources are frozen by manifest_main.json. Do not edit root-level Python
files after main-cohort requests. Initial calibration protocol and sources remain
in manifest.json and protocol_initial_sources. The amended evidence rule and
calibration transport gate were frozen before the main cohort; main prompts,
models, schedule, execution engine and services were not tuned to main results.

Study unit: 288 model service episodes, not individual workload requests.
Two HTTP applications, eight conditions, three process-reset repetitions, three
models, two runtime arms. The atomic arm has stronger database-level capabilities;
this is a system comparison, not a model reasoning comparison. No trained model
or new transaction primitive is introduced. All writers cooperate through SQLite.

Controls: 576 offline cases across four author-designed follow-up configurations and six
policies. 144 real-service controls across two applications and field, ownership-
only, and full atomic policies. Three provider calibration episodes are excluded.
Read-only operator delays are 0/4/8 ms; the interference boundary is controlled
before the second write attempt. These are not natural arrival distributions.

The stronger reporting score requires truthful state/history outcomes plus
post-write all-resource snapshots, complete version-matched histories, current
common epochs, and audits linking committed operation IDs to the required final
evidence. Extra known citations are allowed. Operational scoring additionally
requires measured health. This is an automated evaluation endpoint, not a formal
certificate, human entailment judgment, or persistent availability guarantee.

The original v02/v03/v04 sources and results are retained. The original cumulative
ledger at ../prototype_v02/live_state/budget.sqlite3 necessarily appends authorized
v05 calls. budget_before.sqlite3 preserves its pre-v05 state. Never reset the
ledger or discard old uncertain-charge reservations. Paid code stops new work at
$12.50 total locally estimated bound, while the original ledger enforces $15.

Local verification (Python 3.11+):
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_followup.Core
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_followup.Service
The latter starts loopback-only processes; neither invokes model APIs.
  PYTHONDONTWRITEBYTECODE=1 python3 analyze.py --output NEW_OUTPUT_DIRECTORY
This verifies traces and the continuing ledger; requires the retained sibling
v02/v03 journals. No model calls are made. study.py calibration/models are PAID.
Do not rerun or rename recorded IDs. Interrupted attempts remain preserved.

No external publication or repository upload is authorized by this local package.
Author approval, independent review and venue-specific formatting remain separate.

Structural-novelty clarification: the frozen scenario names denote new concrete
configurations, not four independent novel graph families. Codec reuses the
schema-compatibility inequality shape; capacity reservation reuses an aggregate
bound; quorum and cache are both three-variable bound chains. The new physical
data paths and evidence/enforcement comparison are the empirical extension.
Do not count renamed/isomorphic predicates as independent structural novelty.

Final additional cohorts: native_protocol describes 72 typed-field episodes;
function_protocol describes 36 native-provider-function episodes. Each has three
separate calibration episodes. Neither replaces the main cohort. Use
  PYTHONDONTWRITEBYTECODE=1 python3 report/reproduce.py
for offline checking of all archived traces and cumulative accounting. This does
not repeat provider calls or claim external replication. The functions protocol
uses documented provider tool APIs; links are pinned in its manifest. The paper
and submission assessment explain its post-hoc and small-subset limitations.

RAC order correction: the initial adapter omitted explicit dependency edges and
retains all 224 traces. The separately frozen rac_ordered_protocol.json supplies
the declared recovery ordering to unchanged upstream ActionRecord.depends_on,
with the same handlers and runtime arms. Another 192 offline and 32 service cases
are preserved separately. This is a post-hoc adapter correction, not a confirmatory
superiority comparison. The paper uses the corrected cohort and discloses the
initial mismatch and its zero service progress.
