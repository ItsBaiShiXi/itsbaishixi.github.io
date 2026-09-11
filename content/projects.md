+++
title = 'Projects'
description = "Research and projects by Shengzhe Zhang — robotics, machine learning, distributed systems, and web applications."
subtitle = "What I'm working on. Rough reverse-chronological order."
+++

## Reimplementing AVITM

*CS274B project at UC Irvine, with Chandler Prasetyo.*

A from-scratch PyTorch implementation of
[Autoencoding Variational Inference for Topic Models](https://arxiv.org/abs/1703.01488)
(Srivastava & Sutton, ICLR 2017), testing its central claim: that a VAE-style inference network
can match classical topic-model inference on topic quality while being far cheaper at test time.

Classical inference is the thing to beat. Mean-field variational inference and collapsed Gibbs
sampling both work well, but they re-run optimization from scratch for every new document, and
changing the model means deriving a new inference procedure by hand. An inference *network*
learns the mapping once and then just runs forward.

Reproducing it turned out to be mostly a fight with the Dirichlet prior. A Dirichlet isn't
directly reparameterizable, so the paper's Laplace approximation stands in for it; and the model
readily collapses — topics degenerating into near-identical lists of common words — without batch
normalization, high-momentum training, KL annealing and careful prior-variance calibration. Those
details are the reproduction.

On 20 Newsgroups the result held: ProdLDA under this inference pipeline reached 0.2323 NPMI
coherence in about 16 seconds of training, against two to five minutes for the classical
baselines — a 10–17× speedup at competitive topic quality.

[Read the write-up →](/posts/avitm-topic-modeling/) ·
[Source](https://github.com/ItsBaiShiXi/Pytorch_Implementation_AVITM)

## How Much Policy Does a VLA Need?

*CS295 final report, with Eric.*

How much parameter capacity does a vision-language-action model actually need in its action
policy head? Two stages: first replacing LAPA's 7B LLaMA-2 backbone with smaller Pythia models
behind a frozen interface, then isolating policy capacity directly by freezing FoundryVLA's
vision and language stacks and scaling only the diffusion policy head across 6, 12 and 24
layers (77M / 205M / 410M).

Deeper heads predicted held-out actions better on all three tasks, but none produced reliable
closed-loop control. The gap between those two facts is the interesting part.

[Read the report →](/posts/vla-policy-size/)

## Human-Like Fox v Fox Bots for Melee

*CS274C project at UC Irvine, with Chandler Prasetyo, Ayan Jhunjhunwala, Jaiveer Gahunia and
Sohum Gulla Pulijal.*

Super Smash Bros. Melee's built-in CPUs are scripted and useless as practice, while learned bots
are the opposite problem — they react in under 40 ms against a human threshold near 200 ms, so
they win on reflexes rather than play. Useful training partners have to be constrained to human
reaction windows and learn from human demonstrations.

We asked whether the *quality* of those demonstrations carries through: does reinforcement
learning initialized from professional tournament replays beat the same pipeline initialized from
Platinum+ ranked ladder play? Two identical pipelines on the slippi-ai framework, behavior cloning
then PPO self-play, differing only in the training data.

It didn't. The imitation loss curves were nearly identical, and after RL the two agents went
52%–48% head to head — a coin flip. The likeliest explanation is that 10 hours of RL simply isn't
long enough for a prior to express itself, which is a compute limit rather than a finding about
priors.

[Read the write-up →](/posts/melee-fox-bots/) ·
[Source](https://github.com/ItsBaiShiXi/RF_Melee)

## Distributed System for FPS Game

*CS230 project at UC Irvine, with Chandler Prasetyo and Shu Sekigawa.*

A multiplayer first-person shooter built on the Ursina engine, used as a testbed for the
standard netcode toolkit: a server-authoritative simulation ticking at 20 Hz, client-side
prediction so local input feels instant, rollback-and-replay reconciliation when the server
disagrees, ~100 ms of interpolation delay to smooth out irregular snapshot arrivals, and
server-side hit detection so latency can't be exploited.

The comparison we cared about was transport. WebSocket sends JSON over TCP and guarantees
delivery; the UDP path packs the same state into a fixed-layout binary format with an
application header, carries redundant input history, and acknowledges packets with a 64-bit
arrival mask. We measured both under a Linux `tc` network emulator, sweeping added delay to
400 ms and loss to 10%, with scripted movement so runs were comparable.

Two metrics: positional error, the Euclidean distance between the server-authoritative
position and the position the client would have computed locally, and "loss of smoothness",
the frame-to-frame change in acceleration.

Prediction and reconciliation together kept positional error roughly flat as latency climbed,
while disabling them made error grow linearly with RTT. The most interesting result was a negative one:
**the redundant input history made things slightly worse, not better.** Plain
UDP beat both WebSocket and our redundant variant under prediction, because a lost input can
only be recovered from the very first packet that arrives after the gap — so the redundancy
paid its bandwidth cost without buying back much. Smoothness only became acceptable with all
three mechanisms enabled, and even then sat well short of purely local movement, since linear
interpolation smooths position without preserving acceleration.

[Read the write-up →](/posts/fps-distributed-system/) ·
[Source](https://github.com/shugonta/CS230-FPS-Project)

## Snowfall prediction

*A small side project.*

Predicting daily new snowfall at three Sierra Nevada ski resorts — Mammoth, Heavenly and
Palisades Tahoe — from twenty years of SNOTEL sensor telemetry, about 20,000 daily records
pulled from the USDA NRCS API.

Each station reports twelve raw measurements: snow depth, snow water equivalent, temperature,
precipitation, humidity, wind and soil metrics. Most of the work was turning those into 68
features — lags, rolling windows, momentum terms, and interactions — since the useful signal
is mostly in how yesterday's conditions were changing, not in any single day's reading.

| Model | Test R² | RMSE | MAE |
|---|---:|---:|---:|
| Linear regression | 0.559 | 1.67 in | 0.57 in |
| Random forest (tuned) | 0.687 | 1.41 in | 0.38 in |
| XGBoost (tuned) | **0.704** | **1.37 in** | **0.38 in** |

Feature importances back up the intuition: yesterday's precipitation alone accounts for 16.1%,
and the day-over-day change in precipitation another 8.5%. Accuracy varies a lot by resort —
Mammoth reaches R² = 0.810 and Heavenly 0.751, while Palisades Tahoe sits at 0.573.

[Source](https://github.com/ItsBaiShiXi/Snowfall_Predict)

## LinkUp

*ECS-162 final project at UC Davis, with Ryan Yu, James Fu, Andrew Fojas, Mingzhe Wu and
Weifeng Liu.*

A study-buddy web app. Students list what and how they like to study, get matched with people
whose preferences line up, and create or join study sessions from there. The premise is that
social accountability does more for productivity than another todo list does.

Built with Next.js and React on a Firebase backend — Firestore for data, Firebase Auth for
sign-in — styled with Tailwind, with Cypress covering the main flows end to end.

[Try it →](https://link-up-nine-sigma.vercel.app) ·
[Source](https://github.com/ItsBaiShiXi/LinkUp)
