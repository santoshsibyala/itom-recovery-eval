# Native transport mapping — candidate, not executed

| Component | 1.0 OpenAI | 1.1 Anthropic |
|---|---|---|
| Model | gpt-4.1-mini-2025-04-14 | claude-haiku-4-5-20251001, no aliases |
| Endpoint | Responses | Messages, API version 2023-06-01 |
| System prompt | instructions | system; identical text bytes |
| Initial task | user input with canonical JSON task | user message containing identical canonical JSON task (new namespace/run ID only) |
| Required tool | tool_choice=required, parallel_tool_calls=false | tool_choice={type:any, disable_parallel_tool_use:true} |
| Thinking/temperature | no added reasoning mode; temperature 0 | thinking={type:disabled}, temperature 0 |
| Output cap | max_output_tokens=900 | max_tokens=900 |
| Tool definition | type:function, name, description, parameters, strict:true | name, description, input_schema, strict:true; omit OpenAI-only type:function |
| Argument schema | canonical schemas.json | identical JSON Schema values; required fields, nullability and additionalProperties unchanged |
| Tool call | function_call call_id/name/arguments JSON string | assistant tool_use id/name/input object |
| Tool result | function_call_output string | following user tool_result block with matching tool_use_id and identical canonical JSON content; no added prose or is_error flag |
| Conversation | accumulated Responses input items | full assistant content blocks then user tool_result; preserve required native order, no compaction |
| Result extraction | parse arguments string | input is already an object; unchanged validator and report projection |
| Usage | input_tokens incl cached, output_tokens | uncached input + cache_read_input_tokens + cache_creation_input_tokens; output separately; no cache-control directives |
| Preflight input counter | o200k_base serialized-request estimate +512 | native count_tokens estimate +512; numerical limits unchanged |
| Retention switch | store=false | do not send unsupported store; no equivalent retention promise |

Only five tools: read_deployment {}, read_configmap {}, read_health {}, recover {restore_image:boolean, restore_replicas:boolean}, finish {status, claims:{image:string|null,replicas:integer|null}, evidence_ids, reason}. Names, descriptions, arguments, projections and behavior are exactly those bound from 1.0. No new instructions, few-shot examples, reminders or tool prompts. Preserve tool ordering. No schema relaxation or automatic SDK conversion of nullable/required fields. If strict mode or any exact schema is rejected, stop, retain diagnostics, and request a new reviewed change rather than silently adapting it.

Provider response IDs/stop reasons/text are evidence, not scoring inputs. No server-side tools. Required tool choice should produce exactly one tool_use, but local checks still reject multiple calls before dispatch. A prose-only response is no_report. Map valid tool errors, invalid reports, unknown mutations and interruption to the unchanged outcome categories.

Availability is not yet checked against the account. After approval, a non-generative Models API lookup must match the exact ID. The first scheduled smoke request checks the full generation interface; if rejected, retain that smoke failure and stop. No alternate endpoint/model or unscheduled generation probe is permitted.
