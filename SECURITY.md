# Security policy

## Scope of v0

CD-AVC v0 is a trusted-input local developer tool. Task graphs, repositories,
test commands and local model endpoints must be trusted by the person running
the tool.

The supervisor runs declared test commands as the current user. It is not a
security sandbox and must not be used to execute untrusted task graphs,
repositories or model-generated commands.

The supervisor does run candidates in a temporary workspace and copies back only
verified implementation files, but this is filesystem hygiene, not process
isolation. Commands still have the invoking user's permissions, environment and
network access.

## Reporting

Do not include credentials, model files or private source in an issue. Report
security problems privately to the repository owner before public disclosure.
