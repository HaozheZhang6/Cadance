# Skills Storyline Notes

## Core Message
Start with a **general Agent workflow**, then convert repeated reliable steps into **Skills**.

## Why this matters
- Improves maintainability and reproducibility.
- Makes failure handling explicit.
- Separates routing logic (Agent) from execution logic (Skills).

## Manual Skill Section
A dedicated manual section for hard cases was added and is important:
- Targets only failing or ambiguous samples.
- Uses curated prompts and constrained regeneration.
- Improves hard-case recovery.
- Reduces total API spend by avoiding global expensive retries.

## Suggested Paper Claim
"The Agent-to-Skills decomposition, with a selective manual Skill tier, improved hard-case success while reducing API cost in production-scale data generation."

## Evidence to add
- Hard-case before/after counts.
- Average API calls per accepted sample before/after.
- Cost per 1,000 accepted samples before/after.
