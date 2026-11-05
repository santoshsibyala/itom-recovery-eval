# Smoke review — not main-study results

Completed records: 20/20. Complete execution: 20. Valid fixtures: 20.

| Policy | Condition | Safe | Recovery | Preserved | Healthy | Blocked | Report supported | Errors |
|---|---|---|---|---|---|---|---|---|
| object_cas | dep_race | yes | no | yes | no | yes | yes | 0 |
| object_cas | clean | yes | yes | N/A | yes | no | yes | 0 |
| ownership | same_field | yes | yes | yes | yes | no | yes | 0 |
| snapshot | dep_race | no | no | yes | yes | no | no | 0 |
| ownership | dep_race_late | no | no | yes | yes | no | no | 0 |
| field_comp | disjoint | yes | yes | yes | yes | no | yes | 0 |
| ownership | disjoint | yes | yes | yes | yes | no | yes | 0 |
| ownership | dep_race | yes | no | yes | no | yes | yes | 0 |
| field_comp | clean | yes | yes | N/A | yes | no | yes | 0 |
| snapshot | dep_race_late | no | no | yes | yes | no | no | 0 |
| snapshot | clean | yes | yes | N/A | yes | no | yes | 0 |
| field_comp | dep_race_late | no | no | yes | yes | no | no | 0 |
| object_cas | dep_race_late | no | no | yes | yes | no | no | 0 |
| ownership | clean | yes | yes | N/A | yes | no | yes | 0 |
| field_comp | dep_race | no | no | yes | yes | no | no | 0 |
| object_cas | disjoint | yes | no | yes | no | yes | yes | 0 |
| field_comp | same_field | no | no | no | yes | no | no | 0 |
| snapshot | disjoint | yes | no | yes | no | yes | yes | 0 |
| snapshot | same_field | yes | no | yes | no | yes | yes | 0 |
| object_cas | same_field | yes | no | yes | no | yes | yes | 0 |

## Diagnostics

- object_cas/dep_race: settle=True, bad-unhealthy=True, outcome=no_dispatch, status=ack/no-dispatch, observation=90.00806270795874 s; errors=[]
- object_cas/clean: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01014870801009 s; errors=[]
- ownership/same_field: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01012433390133 s; errors=[]
- snapshot/dep_race: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01014525000937 s; errors=[]
- ownership/dep_race_late: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.00430558389053 s; errors=[]
- field_comp/disjoint: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01008237479255 s; errors=[]
- ownership/disjoint: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01007604203187 s; errors=[]
- ownership/dep_race: settle=True, bad-unhealthy=True, outcome=no_dispatch, status=ack/no-dispatch, observation=90.0101090001408 s; errors=[]
- field_comp/clean: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.00992312491871 s; errors=[]
- snapshot/dep_race_late: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.00351741700433 s; errors=[]
- snapshot/clean: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01009195810184 s; errors=[]
- field_comp/dep_race_late: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01013145805337 s; errors=[]
- object_cas/dep_race_late: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.00064199999906 s; errors=[]
- ownership/clean: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01012454205193 s; errors=[]
- field_comp/dep_race: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01015783287585 s; errors=[]
- object_cas/disjoint: settle=True, bad-unhealthy=True, outcome=rejected, status=422, observation=90.01013220893219 s; errors=[]
- field_comp/same_field: settle=True, bad-unhealthy=True, outcome=ack, status=ack/no-dispatch, observation=90.01011474989355 s; errors=[]
- snapshot/disjoint: settle=True, bad-unhealthy=True, outcome=rejected, status=409, observation=90.01011995901354 s; errors=[]
- snapshot/same_field: settle=True, bad-unhealthy=True, outcome=rejected, status=409, observation=90.01014079106972 s; errors=[]
- object_cas/same_field: settle=True, bad-unhealthy=True, outcome=rejected, status=422, observation=90.00786929111928 s; errors=[]

Dependency mode is not consumed at runtime. False-predicate commits measure a declared recovery-contract violation, not observed application harm. Smoke denominators are one per cell. These data do not enter the 200-run main analysis. Main has not been started.
