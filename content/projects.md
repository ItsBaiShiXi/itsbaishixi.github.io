+++
title = 'Projects'
description = "Research and projects by Shengzhe Zhang, in robotics and machine learning."
subtitle = "What I'm working on. Rough reverse-chronological order."
+++

## How Much Policy Does a VLA Need?

*CS295 final report, with Eric and Sean.*

How much parameter capacity does a vision-language-action model actually need in its action
policy head? Two stages: first replacing LAPA's 7B LLaMA-2 backbone with smaller Pythia models
behind a frozen interface, then isolating policy capacity directly by freezing FoundryVLA's
vision and language stacks and scaling only the diffusion policy head across 6, 12 and 24
layers (77M / 205M / 410M).

Deeper heads predicted held-out actions better on all three tasks, but none produced reliable
closed-loop control. The gap between those two facts is the interesting part.

[Read the report →](/posts/vla-policy-size/)

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
