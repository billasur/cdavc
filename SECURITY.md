# Security policy

## Trust boundary

CD-AVC is a trusted-input local developer tool. Task graphs, repositories,
test commands and local model endpoints must be trusted by the person running
the tool.

The supervisor runs declared test commands as the current user. It is not a
security sandbox and must not be used to execute untrusted task graphs,
repositories or model-generated commands.

The supervisor does run candidates in a temporary workspace and copies back only
verified implementation files, but this is filesystem hygiene, not process
isolation. Commands still have the invoking user's permissions, environment and
network access.

The shared verifier uses frozen snapshots, fresh candidate/check workspaces and
content digests to catch observable evaluator or candidate mutation. These are
correctness/integrity checks, not an isolation boundary against hostile Python
or subprocesses. A process with the user's permissions can reach other paths,
alter the harness or mutate and restore files within one invocation. Use an
independent OS/container boundary before executing hostile code.

Content-addressed receipts are not signed vendor attestations. Export source
labels and external usage are self-reported; missing telemetry cannot justify
matched-budget or zero-cost claims. Private/hidden directories and known caches
are excluded from ordinary snapshots, but test commands still inherit the
user's environment. Explicitly published context must not include secrets.

`.cdavc/artifacts/`, execution logs, patches and test output can contain private
source or diagnostics. Keep runtime artifacts private and inspect/redact any
report before publishing it. The checked-in adversarial fixtures and external
example contain only synthetic source and explicitly synthetic usage data.

## Reporting

Do not include credentials, model files or private source in an issue. Report
security problems privately to the repository owner before public disclosure.
