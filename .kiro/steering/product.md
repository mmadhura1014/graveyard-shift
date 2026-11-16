# Product: Graveyard Shift

Kiroween 2026 entry, category: **Costume Contest** (haunting, polished, spooky UI). Solo build.

## What it is
A read-only scanner that finds "zombie" AWS resources (orphaned, idle, forgotten) and shows them as a haunted graveyard. Each resource is a tombstone with a cause of death, age, and monthly haunting cost. An "Exorcism" view generates a cleanup plan (CLI commands + Terraform removal hints). The tool NEVER deletes anything itself.

## Target user
SRE / DevOps / platform engineers and small-team owners who suspect their AWS account is full of forgotten resources.

## Judging criteria (each 20%) - every decision should serve one of these
1. Potential impact: real money and security risk found in real accounts.
2. Technological implementation with Kiro: specs, steering, hooks, MCP all visibly used in /.kiro.
3. Design: polished, complete, coherent, not a prototype.
4. Innovation: ghost-story framing for FinOps/security hygiene, "cause of death" explanations, safe-by-design exorcism plans.
5. Presentation: a 3-minute end-to-end demo works from seed data on any machine.

## Non-goals
No auto-deletion. No multi-account orchestration. No LLM dependency. No user accounts or login.

## Honesty rules
Cost figures are estimates from a bundled price table and must be labelled "estimated". Never present invented numbers as measured results. The demo dataset must be labelled as sample data.
