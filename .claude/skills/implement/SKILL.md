---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

Run the /tdd skill and follow its instructions, including its approval pauses.
Implement the remaining requirements using the project's normal process.

## 3. Run Feedback Loops

Run the full test suite, linter, formatter checks, and any other checks required by
the project. Fix any issues and rerun the relevant checks until they pass.

## 4. Manual Verification

Answer: "How do I verify this phase or feature manually in the browser?"
Stop and wait for me to confirm that manual verification passed before marking
the phase complete or continuing to the finish steps.

## 5. Finish the Phase

Mark the phase complete and update PROMPTS.md using the format specified in that file.
Commit the completed phase and push the commit to GitHub.