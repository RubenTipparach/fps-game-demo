---
name: owner-survey
description: Put every question for the owner into the survey Claude Doc they fill in, never into chat, and fold their answers back into the OpenSpec changes. Use whenever a plan, a mockup, a level or a change has a question for the owner, whenever you would otherwise ask anything in a reply, and whenever the owner says they answered ("I filled in the survey", "answered the doc").
metadata:
  author: Undercity (Claude Code), ported from Pale-Blue-Dot's owner-survey skill
  version: "1.0"
---

# Ask the owner with a survey, never in chat

The owner, 2026-09-27: "always ask questions inside of survey artifacts". This
is Pale-Blue-Dot's rule, taken one step further: there, one quick question could
still go in chat; here every question goes in the survey. A question in chat gets
lost in a long thread. In the survey it sits beside its options and a
recommendation, with a place to answer.

The current survey is https://claude.ai/artifact/Bp34gDXJnZW3EP1uHVLM6J
(CLAUDE.md section 10). Keep editing it rather than starting another.

## When

- A change's proposal or design gains a question only the owner can decide.
- A mockup, a map or a gate is ready and needs the owner's choice.
- You are about to ask the owner anything in a reply. Put it in the survey
  instead, and give the link.

## The survey doc

It is a Claude Doc, made and edited through the Claude Docs connector. Load the
`docs` skill, or call the connector's `guide`, before the first docs call.
Follow the connector's own instructions: read from your last revision, and
write one section per call.

If the session has no Claude Docs connector, say so in one line. Then publish the
same tables as an artifact page with an answer field per question. Load
`artifact-capabilities` first, so the answers are saved where you can read them
back. Move them into the Claude Doc the next time the connector is available.

- **One survey, kept current.** Add new questions to it rather than starting a
  new doc each round.
- **One section per area**, each with a one-line lead and one table:

  | # | Question | Options | My recommendation | Your answer |
  | --- | --- | --- | --- | --- |

  - **`#` is a stable id:** a letter for the area and a number. The areas so
    far are A missions, B systems, C art and levels, and D mockups. Commits and
    changes quote answers by it.
  - **A question gives the fact it turns on,** with its number and unit: "A
    tier 2 lock is a 2.0 s hold with a lockpick".
  - **Options** are short and separated by " / ".
  - **My recommendation** is one option, with the reason in a clause.
  - **Your answer** is left blank for the owner.
  - **A question about something the owner should see** links it: the design
    page section, the map or the mockup.
- **How to answer comes first.** It says how a blank answer is read. The
  current survey proposes that a blank accepts the recommendation, and asks the
  owner to say otherwise.
- **Already decided comes last:** date, decision and where it went, newest
  first. A question moves there once answered and is never asked again.
- **Plain words, from the owner's side:** what they will see or do, not the code.

## Reading the answers back

1. Read the doc from the revision you last saw (the connector's `read` with
   `sinceRev`), not the whole doc.
2. For each answered row, quote the owner's words into the change it shapes:
   the proposal's Why, or the design's decisions.
   - Update the tasks it moves.
   - Update the design page if the change is presented there.
   - Run `openspec validate --all`.
3. Move the row to Already decided, naming where it went.
4. If an answer is unclear, reply in the doc's comment thread for that row. Don't
   guess.
5. Record a blank read as a yes as "(recommendation accepted)", so nobody
   mistakes it for the owner's own words.

## Do not

- Ask a question in chat, or ask the same question in chat and in the survey.
- Put a question in the survey that the code or a measurement can answer.
  Answer it yourself and record the finding.
- Start implementation on an unanswered question that changes behaviour.
  Planning can go on, with the recommendation marked provisional.
