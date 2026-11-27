# Evidence Loop pilot packet (DRAFT — not approved)

**Status:** draft for owner review, 2026-11-26. Nothing in this file is authorized yet.
No one has been contacted, no session has been scheduled and no budget has been spent.
Roadmap: `openspec/changes/validate-evidence-loop-roadmap` (task 2.1, Phase 2, Gate V).

**What approval means.** Approving this packet authorizes sending the recruitment message
below to people the owner picks, running the two sessions as scripted, and spending up to the
budget in section 6. It does not authorize a feature, a release, a public case study or a
paid service. Approval must name this file and its commit.

Items marked `[FILL: …]` need the owner's input before the packet is complete.

## 1. What the pilot is for

**Question:** will a technical team use E-GEO a second time, without being reminded, to make
a decision about their content?

It is a discovery cohort of three projects, not a statistical test. The outcome can be
"proceed", "fix onboarding only", "more discovery" or "stop". Stars, clones and a pleasant
first session do not count as evidence of repeat use.

## 2. Who to recruit

- 3 people, each with a different project, who can edit that project's site content.
- Mix if possible: one docs-heavy open-source project, one SaaS marketing site, one content site.
- Not collaborators on this repository, and not people who have used E-GEO before.
- Source of candidates: `[FILL: e.g. people who ran the public URL audit and left a contact, issue authors, personal network]`.

## 3. Recruitment message (send as written, from the owner)

> Subject: 45 minutes to test an open-source tool on your own site?
>
> Hi `[name]`,
>
> I maintain E-GEO, an open-source tool that tracks whether AI search (Google's AI Overview
> for now) cites a site, and proposes one content change at a time. I'm looking for three
> people to try it on their own project while I watch, so I can see where it fails.
>
> What it takes: one 45-minute call, and a 20-minute follow-up about three weeks later. You
> run it on your machine; I never get access to your site, your keys or your analytics.
>
> What you get: the setup done with you, and whatever the tool finds about your site.
> There's no payment and nothing to buy. It may well find nothing useful; that's a result
> I need to hear too.
>
> I'll take notes (no recording unless you say yes). Nothing with your name or your
> project's name is published. You can stop at any point and ask me to delete my notes.
>
> Interested? `[FILL: how to reply / scheduling link]`

## 4. Consent (read aloud at the start of session 1; note the answer)

1. I will take written notes about what you do and say. **Recording:** yes / no.
2. Notes are kept `[FILL: where — must be outside this public repository]` and deleted on
   request, or after `[FILL: retention, e.g. 90 days after Gate V]`.
3. Findings are written up without your name, your project's name, your domain or your
   queries. Anything quoted is paraphrased unless you approve the exact words.
4. Your content, API keys and analytics stay on your machine. I will not ask you to share a
   screen that shows a key.
5. Any API calls made during the sessions are paid by `[FILL: owner / participant]`, up to
   the budget in section 6.
6. You can stop now or later, with no explanation.

## 5. Sessions

### Session 1 — first use (45 minutes)

The participant drives. The observer speaks only when asked, or after 3 minutes stuck on the
same step; every intervention is written down.

| Step | Task given to the participant | What "done" looks like |
|---|---|---|
| 1 | "Install it from PyPI and check it works." | `egeo --version` and `egeo loop doctor` succeed |
| 2 | "Describe your project: 3 to 5 queries you want to be cited for, and the pages that should win them." | a `project.yaml` that `egeo loop doctor` accepts |
| 3 | "Collect a first set of observations." | `egeo loop collect serp` and `page` wrote records; `ai_overview` if they have a key |
| 4 | "Ask it what to do next." | `egeo loop decide` printed one action |
| 5 | "Is that action something you'd act on? Why or why not?" | their answer, in their words |
| 6 | Optional, if time: "Try it on one page." | `egeo optimize <page>`; note the fidelity status and whether they would publish the result |

Before leaving: agree on the date of session 2, and say plainly that nothing is expected in
between. Do not send reminders.

### Session 2 — did they come back (20 minutes, about 3 weeks later)

1. "Have you run it since we spoke?" If yes: what, when, why. If no: what got in the way.
2. Look together at their `LOG.md` and `data/outcomes/ledger.jsonl` (they read; nothing is copied).
3. "Did anything it showed change something you did or decided?" Ask for the concrete case.
4. "What would have to be true for you to keep using it?"
5. "What would you have paid attention to that it didn't show you?"

A participant who does not show up, or did not run it again, is a result. Record it as such.

## 6. Budget `[FILL: owner must set the numbers]`

Quantities are per participant, for both sessions. Prices are not filled in because they
depend on the provider plan; the owner sets the cap.

| Item | Quantity | Unit price | Cap |
|---|---|---|---|
| SERP collector (Brave or other engine) | up to 5 queries × 3 passes = 15 calls | `[FILL]` | `[FILL]` |
| AI Overview collector (about 3 credits per call) | up to 5 queries × 3 passes = 15 calls | `[FILL]` | `[FILL]` |
| `egeo optimize` on one page (2 ranker calls, 1 or 2 rewriter calls) | up to 3 pages = at most 12 model calls | `[FILL]` | `[FILL]` |
| **Total for 3 participants** | | | `[FILL: hard cap]` |

If the cap is reached, the session continues with fixture or mock runs and that is noted.

## 7. Observation worksheet (one copy per participant, kept outside the repo)

```
Participant code: P1 / P2 / P3          Project type: docs / SaaS / content / other
Session 1 date:                         Recording: yes / no

Time to each step (minutes from start; "—" if not reached)
  1 install + doctor: ____   2 project.yaml valid: ____   3 first collect: ____
  4 first decide: ____       5 judged the action: ____    6 optimize (optional): ____

Observer interventions (step, what was said):
  -

Errors and confusion (step, exact message or what they expected instead):
  -

First action `decide` proposed (kind only):
Would they act on it?   yes / no / unsure      Their reason:

If step 6 ran: fidelity status ______   Would publish as is?  yes / after edits / no

Useful output, in their words:
Not useful or misleading, in their words:

Session 2 date:                         Showed up: yes / no
Ran it between sessions?  yes / no      How many times: ____  (from LOG.md, if they show it)
A decision it influenced (concrete case, or "none"):
What blocked repeat use (or "nothing"):
What they needed that was missing:
```

## 8. What comes out of it

`validation-findings.md` (roadmap task 2.5), anonymized, with for each participant: time to
first useful result, interventions needed, failure points, whether session 2 happened,
whether they ran it in between, and one decision it influenced or "none". Negative results
and no-shows stay in.

Proposed reading aid for Gate V (from the roadmap design, not a proof of market fit): a
release recommendation needs at least two independently observed useful workflows and a
recurring unmet need. Fewer than that points to onboarding fixes, more discovery or stopping.
The owner makes that call.

## 9. Not covered by this packet

- The public case-study article (roadmap task 2.4) and any public post.
- Any change to the product in response to what a participant says during the pilot.
- Telemetry. Nothing is collected automatically; everything comes from the two sessions.
