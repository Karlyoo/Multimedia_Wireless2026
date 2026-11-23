# Repository Instructions

Apply the BMW Lab global instructions supplied to the agent. This file records repository scope and conventions, not session activity.

## Scope

This is the Multimedia Wireless Networks coursework repository. README.md indexes the submissions. A1–A3 contain earlier coursework; A4 contains ns-3 channel reproduction experiments and their presentation.

## Conventions

- Preserve earlier coursework and external ns-3 installations.
- Keep original-paper settings distinct from simulator assumptions and exploratory settings.
- Report actual seeds, run IDs, counts, source revisions and reference provenance.
- Compare matching run subsets; correlation-curve RMSE is not positioning error.
- Preserve exact CSV bytes and recorded hashes; .gitattributes disables CSV line-ending conversion.
- Do not claim exact Figure 6/7 measurement replication or an identified oscillation mechanism without evidence.
- Never commit or push without the user's authorization; never create branches or worktrees without being asked.

## Recall and Handoff

Read CONTEXT.md, MEMORY.md and TODO.md together with this file. The detailed live handoff is docs/HANDOFF_PROMPT.md. Preserve MEMORY.md entries and append new activity instead of rewriting history.
