+++
title = 'How Much Policy Does a VLA Actually Need?'
date = 2026-06-07T13:16:01-07:00
draft = false
+++
![Structure of Qwen](/images/VLA.png)

Vision-Language-Action (VLA) models are increasingly capable but computationally heavy, raising a critical question for edge deployment: **how much parameter capacity is actually necessary in the action policy head?** Initial attempts to test this by swapping in smaller, text-only policies revealed a core architectural challenge—backbone capacity and visual grounding become fundamentally entangled, making it impossible to isolate the true effect of policy size.

To achieve clean variable isolation, we pivoted to a modular architecture using **Foundry-VLA-1.7B**. By freezing the vision and language backbones, we trained Diffusion Policy Heads of three distinct sizes (77M, 205M, and 410M parameters) from scratch. In this post, we explore the architectural lessons learned from our early experiments and present comprehensive physical rollout evaluations to determine the optimal trade-off between model size, latency, and physical task success.

---

## Motivation: The VLA Bottleneck

VLA models are getting smart, but they are also getting heavy. In practical robotics, deploying massive models onboard leads to high latency, which translates directly to sluggish physical control. 

From a practical standpoint, a smaller policy head reduces latency and onboard compute, making rollouts faster. We set out to discover if the action head actually benefits from being massive, or if we could optimize it without losing capability.

## Attempt 1: The Entanglement Problem
![From LLaMA-2 to Pythia](/images/LAPA.png)
We initially set out to test this using the **OpenVLA** architecture—specifically LAPA (Latent Action Pretraining from Videos). Our idea was to swap out the massive policy for smaller, text-only Pythia models (160M, 410M, 1B) to see how size affected performance. 

However, our 160M model had a validation accuracy of just **12.6%** on the SIMPLER evaluation. We realized the issue wasn’t just the parameter count. 

> In the original OpenVLA architecture, the LLaMA-2 backbone acts as both the reasoning engine and the visual interpreter. Because LLaMA-2 was fine-tuned on billions of image-text and video-text pairs, it already intrinsically knows how to map visual tokens to real-world concepts.

Pythia, however, is a text-only model. When we swapped LLaMA-2 for Pythia, we didn’t just shrink the network’s size—**we made the model blind.** Pythia had no prior knowledge of how to interpret an image or a frame, meaning it had to learn complex visual observation tokens entirely from scratch during our task training, which is highly unrealistic.

## Enter Foundry-VLA: Isolating the Action Head

To get a clean read on policy capacity, we moved to **Foundry VLA 1.7B**. 

We kept the ViT encoder and the LLM transformer entirely frozen. The only part we tuned was the **Diffusion Policy Head**, which we trained from scratch. We tested three diffusion head sizes:
* **77M** parameters
* **205M** parameters
* **410M** parameters

## Initial Signals: Validation Loss

Before hitting the robots, the validation loss across our tasks (*PickAndPlaceBox*, *PutOrangeOnSaucer*, *PushBox*) showed a clear, consistent trend. Moving from a 77M head to a 410M head resulted in a validation loss decrease of roughly **6.5% to 10%** depending on the task.

Validation loss is a helpful proxy, but it doesn’t always map to true physical task success. To truly answer our question, we needed to see these heads control the robot.