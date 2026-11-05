# Main execution diagnostics

{
  "planned": 200,
  "attempted": 200,
  "complete": 200,
  "valid_fixture": 200,
  "missing": 0,
  "interrupted": 0,
  "fixture_failures": 0,
  "harness_error_runs": 0,
  "unsupported_reports": 90,
  "unassessable_attempted_reports": 0
}

Unknown counts include missing scheduled cells; unassessable_attempted_reports excludes missing cells. Smoke data are not pooled.

| Policy | Condition | Attempted | Complete | Valid | Missing | Interrupted | Fixture failures | Harness-error runs | Unsupported reports | Unassessable attempted reports |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| snapshot | clean | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| snapshot | disjoint | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| snapshot | same_field | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| snapshot | dep_race | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| snapshot | dep_race_late | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| field_comp | clean | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| field_comp | disjoint | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| field_comp | same_field | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| field_comp | dep_race | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| field_comp | dep_race_late | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| object_cas | clean | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| object_cas | disjoint | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| object_cas | same_field | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| object_cas | dep_race | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| object_cas | dep_race_late | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| ownership | clean | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| ownership | disjoint | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| ownership | same_field | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| ownership | dep_race | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| ownership | dep_race_late | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
