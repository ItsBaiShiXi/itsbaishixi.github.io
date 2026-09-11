+++
title = 'Human-Like Fox v Fox Bots for Super Smash Bros. Melee'
date = 2026-03-20
draft = false
report = true
style = 'report.css'
course = 'CS274C'
authors = ['Chandler Prasetyo', 'Shengzhe Zhang', 'Ayan Jhunjhunwala', 'Jaiveer Gahunia', 'Sohum Gulla Pulijal']
description = 'Does initializing reinforcement learning from professional-level imitation data produce a stronger Melee agent than initializing from amateur data? Two parallel pipelines, one answer.'
+++

Super Smash Bros. Melee came out in 2001 and never stopped being played competitively. Twenty-odd
years of a fixed ruleset has pushed the skill ceiling far past anything the game shipped with —
the built-in CPUs run on scripted heuristics and are useless as practice for a serious player.

Learned bots could fill that gap, and the need is not evenly distributed. Only 16 of the top-100
ranked players are based outside the US, seven of them Canadian. Everyone else deals with visa
barriers for in-person events and network latency in a game that resolves at 60 frames per
second. A bot with adjustable skill — the way chess engines expose an Elo dial — would let
someone improve without a local scene to practise against.

The catch is that strong Melee bots are already *too* strong, and in an uninteresting way. Modern
hardware reacts in under 40 ms against a human threshold of roughly 200 ms, so bots win on
reflexes rather than on play. Making them useful means constraining them to human reaction
windows and human-like decisions, which is what pushes the problem toward learning from human
demonstrations.

> Does initializing reinforcement learning from professional-level imitation data produce a
> stronger agent than initializing from amateur-level data?

We trained two parallel pipelines to find out — one on professional tournament replays, one on
Platinum-and-above ranked ladder play — and put the resulting agents against each other.

## Setup

**Two datasets.** The professional set is tournament replay data, representing the strongest human
play available. The ranked set comes from the online ladder, which tiers players Bronze through
Grand Master by an Elo-style rating; we restricted it to **Platinum and above** so the comparison
was pro against *good* amateur, not pro against noise.

**One matchup.** Fox versus Fox only. That keeps the state and action distributions tight enough to
learn from a feasible amount of data, at the cost of generality — Melee has 26 characters and far
more matchups than we could cover.

**The problem is partially observable.** We formulate play as a POMDP rather than an MDP, and the
reason is deliberate: we inject input latency so the agent sees a *delayed* sequence of frames
instead of the current one. That is what keeps it human-like, and it means the true game state has
to be inferred from recent context rather than read off directly. Melee rewards exactly that kind
of inference — reading momentum, combo continuation, recovery options, and an opponent's habits
across frames.

- **Observation** — a delayed sequence of game-state features: positions, velocities, action states, frame by frame.
- **State** — the true game state, only partially observed.
- **Action** — controller outputs: movement, defensive options, attacks.
- **Reward** — zero-sum. Positive for dealing damage and taking stocks, negative for conceding them, with stock losses weighted above damage. Zero-sum by construction, so passive play cannot pay.

## Method

We built on [slippi-ai](https://github.com/vladfi1/slippi-ai), Vlad Firoiu's framework, and ran
the same two-stage pipeline on each dataset.

{{< report-figure
  src="/images/melee/trainingslippi.png"
  alt="Diagram of the two-stage training pipeline: Slippi replay data feeds behavior cloning, and the resulting policy initializes PPO reinforcement learning"
  caption="The two-stage pipeline. Replay data trains a behavior-cloning policy, which then initializes PPO self-play."
>}}

**Stage 1 — behavior cloning.** Supervised imitation of human inputs from replays, giving the
agent a policy that already moves and presses buttons like a person before it has played a single
game itself.

**Stage 2 — reinforcement learning.** PPO self-play initialized from that policy, letting the agent
improve through interaction rather than imitation.

The split matters because it isolates the variable we care about. Both pipelines get identical
architecture, identical RL, identical compute. The *only* difference is the skill level of the
demonstrations the policy started from.

## Results

### Imitation learning

Both models learn fast and then plateau — loss drops sharply over the first few thousand update
steps, then flattens into slow refinement.

{{< report-figure
  src="/images/melee/trainloss.png"
  alt="Training imitation loss curves for the professional and Platinum+ behavior cloning models, both dropping sharply then levelling off at a similar value"
  caption="Training imitation loss. Both curves drop sharply early, then level off — fast initial learning followed by slow refinement."
>}}

{{< report-figure
  src="/images/melee/testloss.png"
  alt="Test imitation loss curves for both models, closely tracking the training curves"
  caption="Test imitation loss. The test curves track the training curves closely, so neither model is simply memorizing."
>}}

Two things stand out, and the second was not what we expected.

The train and test curves stay close together throughout, which is the reassuring result — the
models generalize rather than memorize.

The professional and ranked curves also stay close together, and finish at essentially the same
loss. **The professional dataset did not produce lower imitation loss than the Platinum+ dataset.**
Going in, we assumed better demonstrations would at minimum be easier to fit or produce a visibly
better clone. They were not.

What both agents shared was a ceiling. In the emulator they reproduced movement and combo inputs
convincingly, but played passively — no real pressure, no KO conversions. Imitation gets you the
motor skills and not the decisions.

### Reinforcement learning

{{< report-figure
  src="/images/melee/reinforcement.png"
  alt="Mean reward during reinforcement learning for the professional and online-ranked agents over about 1000 update steps, both fluctuating around zero with high variance"
  caption="Mean reward during RL over roughly 1,000 update steps. Both fluctuate around zero with high variance — expected in zero-sum self-play, where one agent's gain is the other's loss."
>}}

After about 10 hours of RL — roughly 80 outer steps — we ran the two agents head to head.

| Metric | Pro | Ranked |
|---|---:|---:|
| Final IL train loss | ~0.9 | ~0.9 |
| Final IL test loss | ~0.9 | ~0.9 |
| RL win rate | 52% | 48% |
| RL outer steps | ~80 | ~80 |

**52% to 48%.** Essentially a coin flip. Combined with the near-identical IL curves, the reading is
that the quality of the behavioral prior had no meaningful effect — on imitation convergence or on
final RL performance. Both initializations landed in the same place after the same training.

Neither reward curve trends upward, which is itself informative: 10 hours is not enough RL to open
a gap. The professional agent does show slightly larger reward swings, consistent with inheriting
a more varied and aggressive style from tournament play — a trace of the prior surviving into RL,
even though it did not translate into wins.

The RL agents were clearly better than their BC starting points, though: more damage dealt, less
damage taken, more active play in emulator evaluation.

## Conclusions

The honest summary is a negative result. Professional and Platinum+ initializations converged to
near-even performance, and the behavioral prior did not measurably matter.

The caveat is real and we would rather state it than bury it: **the most likely explanation is
simply that we did not run RL long enough.** Neither reward curve had started trending upward when
we stopped. A prior that looks irrelevant at 80 outer steps might separate clearly at 800. The
52–48 split is within the range you would expect from noise.

**Compute was the binding constraint.** RL here needs a Dolphin emulator instance per parallel
environment, each on its own CPU core, so the number of instances we could run was capped by
hardware rather than by design. That is the thing to fix first.

Beyond more training: a stronger evaluation setup with many more bot-versus-bot matches, so the
win rate means something; extending past Fox-only to more of the 26-character roster; and
comparing architectures — MLP against pure LSTM against a full Transformer — to see how much of
the behaviour comes from the model rather than the data.

## References

1. V. Firoiu, W. F. Whitney, J. B. Tenenbaum. *Beating the World's Best at Super Smash Bros. with
   Deep Reinforcement Learning.* arXiv:1702.06230, 2017.
2. V. Firoiu. [*slippi-ai*](https://github.com/vladfi1/slippi-ai). GitHub, 2024.
3. Project Slippi. [*Slippi Replay File Specification*](https://github.com/project-slippi/slippi-wiki/blob/master/SPEC.md). GitHub, accessed March 2026.

[Our fork on GitHub](https://github.com/ItsBaiShiXi/RF_Melee)
