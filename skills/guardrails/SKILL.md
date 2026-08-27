# Skill: guardrails

Apply AI safety checks as a horizontal layer.

## Rules
- Check input before orchestration.
- Check final output before response.
- Keep human-review marker for candidate decisions.
- Require citations for grounded policy responses when configured.
- Do not implement guardrails as an agent tool.
- For policy ingestion, run pre-index file/content/metadata/prompt-injection checks and post-index
  citation/vector/write checks. Route uncertain documents to governed review without indexing and
  corrupt documents to failed; never emit raw document text in observability.
