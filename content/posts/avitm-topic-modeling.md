+++
title = 'Variational Autoencoders in Topic Modeling'
date = 2026-06-11
draft = false
report = true
style = 'report.css'
course = 'CS274B'
authors = ['Shengzhe Zhang', 'Chandler Prasetyo']
description = 'Reimplementing AVITM in PyTorch and checking its central claim: that a learned inference network can match classical topic-model inference while being far cheaper at test time.'
+++

Topic models sort a pile of documents into themes nobody labelled in advance, which is why they
end up underneath literature reviews, content curation and customer-feedback analysis. Latent
Dirichlet Allocation is still the standard: every document is a mixture of topics, every topic a
distribution over words.

The awkward part is not the model, it is the inference. Recovering the latent topic distribution
θ that produced a document is its own optimization problem, and classical approaches — mean-field
variational inference, collapsed Gibbs sampling — solve it well but pay for it twice. They re-run
from scratch for every new document, and changing the model at all means deriving a new inference
procedure by hand.

> If an inference network can be *learned* once and then simply run forward, what do you give up
> in topic quality to get that?

Srivastava & Sutton's [AVITM](https://arxiv.org/abs/1703.01488) (ICLR 2017) answers by putting a
variational autoencoder where the inference procedure used to be. We reimplemented it in PyTorch
and checked whether the claim survives contact with someone else's code.

## What makes AVITM work

Two contributions do the heavy lifting, and both exist to defeat a specific failure.

**A Laplace approximation to the Dirichlet prior.** The reparameterization trick — the thing that
lets gradients flow through a sampling step — needs a distribution you can express as a
deterministic function of noise. A Dirichlet is not that. So the prior is approximated by a
Gaussian in softmax space, which *is* reparameterizable, and the whole network becomes trainable
end to end.

**Batch normalization and high-momentum training.** Without them the model collapses: topics
degenerate into near-identical lists of common words. This is a known pathology of the Dirichlet
prior, and it is not a subtle effect — you can read it straight off the topic lists.

The paper also introduces **ProdLDA**, which replaces LDA's mixture of topics with a product of
experts. It exists mainly to make a point: swapping the model required no new inference
derivation, which is the entire argument for learning the inference network.

{{< report-figure
  src="/images/avitm/LDAandAVITM.png"
  alt="Side-by-side comparison: on the left the LDA plate diagram with its document, topic and word variables; on the right an overview of AVITM as an encoder-decoder network"
  caption="Left: the LDA plate diagram. Right: AVITM, where the inference procedure is replaced by a trained encoder."
>}}

## What we built

Four models, all on 20 Newsgroups with a vocabulary of 2,000 words and topic counts
K ∈ {50, 200}, sharing the same training data and evaluation code. The two AVITM variants share
an encoder and training loop and differ only in the decoder.

**DMFVI** — scikit-learn's `LatentDirichletAllocation` with `learning_offset = 50` and
`learning_decay = 0.7`, the standard online-LDA settings. The paper trained until it matched
perplexities from prior work without naming hyperparameters; we capped iterations at 200 for time
and compute, since this baseline was not the thing under test.

**Collapsed Gibbs sampling** — a transformation layer over the bag-of-words input, then a training
loop that integrates out θ and φ so the MCMC sampler runs only over word-topic assignments z. We
capped it at 20 iterations, which was enough on a corpus this size.

**AVITM on LDA** and **AVITM on ProdLDA** — the encoder maps a bag-of-words document to a Gaussian
over topics; the reparameterization trick draws `z = μ + σ·ε` with ε from a standard normal, so
the sampling step stays differentiable; a softmax turns z into the topic vector θ; the decoder
reconstructs the bag of words from it. The loss combines reconstruction error against the original
document with the KL divergence between the encoder's output and the prior — the latter handled by
the Laplace approximation, which is what makes the two comparable at all.

We measured two things: **perplexity** for predictive quality, and **NPMI** for topic coherence —
whether the words in a topic actually belong together.

## Experiments

The order mattered more than we expected. We ran it in four stages: prepare and inspect the data
(80/20 split), establish both classical baselines, train the AVITM variants, then compare.

Building the baselines first was what made the rest interpretable. Our Gibbs coherence came out
slightly *better* than the paper's, which initially looked like a mistake. The likely explanation
is preprocessing: the paper used a modified 20 Newsgroups with an unspecified cleaning step, so
our bag-of-words probably carried less noise. Same story for the DMFVI coherence. Knowing that up
front meant we could read later differences as real rather than as artifacts of our pipeline.

{{< report-figure
  src="/images/avitm/result50.png"
  alt="Bar charts comparing perplexity and NPMI coherence between our reimplementation and the original paper's reported results, at 50 topics, across DMFVI, Gibbs, AVITM-LDA and AVITM-ProdLDA"
  caption="Perplexity and coherence, ours against the original paper, at K = 50 topics."
>}}

{{< report-figure
  src="/images/avitm/result200.png"
  alt="The same perplexity and NPMI coherence comparison at 200 topics"
  caption="The same comparison at K = 200 topics."
>}}

The qualitative output is more revealing than either metric. Sampling topics from each model:

**AVITM on ProdLDA**

```text
Topic 47: stage, rocket, station, spacecraft, dept, development, vehicle, flight, satellite
Topic 48: scheme, produce, experts, nsa, agencies, messages, details, random, cryptography
Topic 14: militia, bear, amendment, providing, firearm, license, cities, organized, dangerous
```

**AVITM on LDA**

```text
Topic  1: like, just, don, use, know, does, good, new, time, think
Topic  2: just, like, don, know, time, think, good, new, use, does
Topic  4: like, just, don, know, use, new, good, time, think, does
```

**Collapsed Gibbs**

```text
Topic  7: team, league, hockey, players, win, teams, nhl, detroit, season, division
Topic 12: key, chip, keys, bit, des, number, clipper, used, algorithm, chips
Topic 21: armenian, armenians, turkish, people, turkey, greek, killed, armenia, turks, said
```

Those three AVITM-on-LDA topics are the same topic wearing different hats — the component
collapse the paper warns about, reproduced faithfully and unintentionally. The words are the
corpus's most common tokens in slightly different orders, which is what a collapsed model outputs
when it has stopped distinguishing anything. More learning-rate tuning and momentum adjustment on
the Adam optimizer would likely have pulled it apart. ProdLDA, on the same encoder, produced
topics that are recognizably about spaceflight, cryptography policy and gun law.

## Conclusions

The central claim reproduces: under this inference pipeline ProdLDA beat AVITM-LDA on both
coherence and perplexity at K = 50, consistent with the original paper.

But the honest reading of our numbers is more qualified than "the neural method wins". On a corpus
this small, the classical methods — Gibbs especially — remain strong on the raw metrics, and AVITM
on LDA came out slightly worse on average, with real headroom left in tuning. What does not show
up in a coherence score is the cost: even on a small corpus Gibbs was visibly slowing down, and
classical inference has to pay that cost again for every new document. The implementation reaches
0.2323 NPMI in roughly 16 seconds of training against two to five minutes for the baselines — a
10–17× speedup at competitive quality.

So the result is not that learned inference produces better topics. It is that it produces
comparable topics while being amortized and adaptable — you train the encoder once, and switching
from LDA to ProdLDA cost us a decoder change instead of a derivation.

Where we would take it next: larger corpora, where the scalability argument should actually start
to bite; more LDA baselines; and a richer evaluation of topic-word distributions, possibly with an
LLM in the loop, since NPMI is a thin proxy for whether a topic means anything to a reader.

## References

1. D. M. Blei, A. Y. Ng, M. I. Jordan. *Latent Dirichlet Allocation.* Journal of Machine Learning
   Research, 3:993–1022, 2003.
2. Y. Miao, L. Yu, P. Blunsom. *Neural Variational Inference for Text Processing.* ICML, 2016.
3. D. P. Kingma, M. Welling. *Auto-Encoding Variational Bayes.* ICLR, 2014.
4. A. Srivastava, C. Sutton. *Autoencoding Variational Inference For Topic Models.* ICLR, 2017.
5. M. D. Hoffman, D. M. Blei, F. Bach. *Online Learning for Latent Dirichlet Allocation.* NeurIPS
   vol. 23, 2010.

[Source on GitHub](https://github.com/ItsBaiShiXi/Pytorch_Implementation_AVITM)
