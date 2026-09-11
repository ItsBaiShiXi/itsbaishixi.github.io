+++
title = 'Distributed System for FPS Game'
date = 2025-12-12
draft = false
report = true
style = 'report.css'
course = 'CS230'
authors = ['Shengzhe Zhang', 'Chandler Prasetyo', 'Shu Sekigawa']
description = 'Client-side prediction, interpolation and server reconciliation in a multiplayer FPS, and what happens to accuracy and smoothness when the network gets worse.'
+++

Real-time multiplayer games have to keep clients in agreement over a network that offers no
guarantees. Latency delays input, jitter makes motion stutter, and packet loss puts players in
places they never went. The usual answers are well known — an authoritative server, client-side
prediction, interpolation — but knowing the techniques is not the same as knowing what each one
buys you, or what it costs.

We built a multiplayer first-person shooter on the [Ursina](https://www.ursinaengine.org/)
engine to measure exactly that. Alongside the synchronization work, we compared two transports:
**WebSocket**, which rides on TCP and guarantees ordered delivery, and **UDP**, which is faster
and lossier and needs its own machinery to cope.

> When every mechanism costs something, which ones actually earn their keep as the network
> degrades?

We answer it with two numbers: how far the player ends up from where they should be, and how
jerky the motion looks getting there.

## Approach

### Server authority and snapshots

The prototype is server-authoritative on a fixed **20 Hz** tick. Clients send *inputs*, never
state. Each tick the server applies the inputs it has received, advances the simulation, and
produces a snapshot of the authoritative world — entity positions, velocities, bullets,
obstacles — which it sends to every connected client.

Sending inputs rather than state is what makes the rest possible. The server stays the single
source of truth, runs deterministically, and can validate everything; clients are left to worry
only about presenting it smoothly.

### Prediction and reconciliation

Waiting for a round trip before the player sees their own movement feels terrible, so the client
predicts. When an input is generated it is applied locally *immediately*, and also sent to the
server tagged with a sequence number.

When the authoritative snapshot arrives, the client compares it against what it predicted. If
they disagree, it rolls its state back to the server's version and replays every input the
server had not yet acknowledged. This rollback-and-replay keeps the client eventually consistent
with the server without ever making the player wait for the network. Corrections are
occasionally visible, and that visibility turns out to matter for smoothness later.

### Interpolation

Snapshots do not arrive on a tidy schedule. Rather than rendering the newest one the moment it
lands, the client deliberately renders **about 100 ms in the past**, interpolating between the
two snapshots that bracket the render time.

This buys a buffer: late snapshots have a window to arrive before they are needed, so entities
glide instead of teleporting. The cost is a fixed, controlled visual delay — trading a little
latency for a lot of stability.

### Server-side hit detection

All hit resolution happens on the server. Clients may play a muzzle flash optimistically, but
they do not decide whether anything was hit. The server checks bullet trajectories against the
authoritative state at the right tick and applies damage itself, so a client cannot manufacture
hits or exploit its own latency.

## Protocols

Both transports carry the same three message types — connection, input, and snapshot.

Over **WebSocket**, the client opens an HTTP connection on port 8000, the server answers
`101 Switching Protocols`, and everything afterwards is JSON over a reliable ordered channel.
The connection-completion message also hands the client a UDP endpoint, so the session can
switch transports — with WebSocket remaining as a fallback on networks where UDP is blocked by
NAT or defeated by a small MTU.

Over **UDP** there is no channel and no delivery guarantee, so the payloads are hand-packed
binary. Every message opens with a common header giving version, message type, and payload
length.

{{< report-figure
  src="/images/fps/UDP_Input_diagram.png"
  alt="Byte-level layout of the UDP input payload: a common header, player ID, input count, then a sequence of fixed-width input structures containing sequence number, timestamp, movement vector, look direction and flags"
  caption="UDP input payload structure. Each input carries a sequence number, an f64 client timestamp, movement and look vectors as f32 triples, and a flags byte — all fixed-width and big-endian, so the server can parse without ambiguity."
>}}

Input messages can carry **several past inputs**, not just the current one, so that a single
packet arriving after a gap can restore the history the server missed. Because UDP has no
built-in acknowledgement, the client confirms delivery with an ACK carrying the last sequence
number received plus a 64-bit **arrival mask** — a sliding window where each bit marks whether
one earlier packet arrived. If sequence 10 is current and 8 and 9 are missing, the mask reads
`...111001`.

Snapshots are larger and need care. With a 1500-byte MTU only 1472 bytes fit in a packet, and a
snapshot holds every player and every bullet, so it is fragmented at the application layer.

{{< report-figure
  src="/images/fps/UDP_Snapshot_diagram.png"
  alt="Byte-level layout of the UDP snapshot payload: tick number, server timestamp, player and bullet counts, the recipient's own 38-byte state, then variable numbers of other-player and bullet states"
  caption="UDP snapshot payload structure. The recipient's own 38-byte state is mandatory and always travels in the first packet; other players and bullets are optional and may be split across packets."
>}}

Two details make fragmentation survivable. A client's **own** state is mandatory and always
rides in the first packet — and is sent redundantly — so self-position stays accurate even when
other data is lost. And every entity has a timeout, so a player whose state is missing from a
snapshot holds position briefly instead of flickering out of existence.

## Evaluation

### Setup

We needed repeatable network conditions, so we emulated them rather than hunting for bad
networks. Client and server run on the same physical Windows host to keep everything outside the
emulator negligible — end-to-end delay without emulation averages **0.3 ms**. The server runs in
a Docker container on Ubuntu under WSL, where the Linux kernel's packet scheduler is available,
and `tc` applies ingress and egress delay and loss on the container's interface.

{{< report-figure
  src="/images/fps/Evaluation_setup.png"
  alt="Diagram of the experiment setup: a game client on the Windows host, mirrored networking into WSL, the kernel packet scheduler, and the game server in a Docker container with tc controlling delay and loss"
  caption="Experiment setup. Mirrored networking forwards loopback traffic into the WSL guest, iptables routes it to the container's virtual interface, and tc shapes ingress and egress delay and loss rate."
>}}

To keep runs comparable, players were driven by a script rather than a human: pattern (a) moves
in a straight line for 10 seconds, pattern (b) traces a square by cycling W→D→S→A at one-second
intervals. The client renders at a vsync-locked 144 Hz, well above both the server tick and the
input rate, and every metric is sampled per rendered frame — so rendering hitches show up in the
results too, which is the honest way to measure something a player actually sees.

### Accuracy

Accuracy is the Euclidean distance between the position the server reports and the position the
client would have computed locally from the same inputs:

```text
Error = sqrt( (x_actual - x_ideal)² + (y_actual - y_ideal)² + (z_actual - z_ideal)² )
```

Server-side collision was disabled for these runs so players always move exactly as their inputs
dictate, isolating the synchronization behaviour from the physics.

{{< report-figure
  src="/images/fps/position_error_avg_feature_vs_delay.png"
  alt="Line chart of average position error against network delay from 0 to 400 ms, comparing four configurations; the two using prediction stay flat and low while the other two rise linearly"
  caption="Average position error against network delay. The two configurations that predict stay flat as latency climbs; those without prediction, or with prediction but no reconciliation, degrade linearly."
>}}

This is the clearest result in the project. **Prediction is what keeps error flat as latency
rises**; without it, error grows linearly with RTT, because the player is simply waiting for
snapshots that arrive later and later.

There is a counterintuitive wrinkle: some configurations *without* self-position interpolation
scored slightly better here. That is a measurement artifact with a real cause — interpolating
your own position introduces up to one input tick of delay, since the client eases toward the
target across several frames rather than snapping to it. Against a metric defined as "distance
from the instantaneous ideal", easing looks like error. It also looks considerably better in
motion, which is what the smoothness section measures.

{{< report-figure
  src="/images/fps/position_errors_plot_200_0.png"
  alt="Position error plotted against frame number at 200 ms RTT, showing a sawtooth for the no-prediction case that resets each time a snapshot arrives"
  caption="Position error over time at 200 ms RTT. Without prediction the error climbs between snapshots and drops each time one lands — the sawtooth is the player being repeatedly dragged back into place."
>}}

Watching it frame by frame shows the mechanism: error ramps up between snapshots and collapses
when one arrives, over and over. Once input stops, everything converges — the error is a
property of motion, not of position.

{{< report-figure
  src="/images/fps/position_error_avg_feature_vs_loss.png"
  alt="Average position error against packet loss rate from 0 to 10 percent; all configurations fluctuate between roughly 0.3 and 1 with no clear trend"
  caption="Average position error against packet loss. Error fluctuates between roughly 0.3 and 1 with no correlation to loss rate — the aggregate hides what is actually happening."
>}}

Against packet loss the averages say almost nothing: everything sits between 0.3 and 1 with no
trend. The time series explains why the average is the wrong summary.

{{< report-figure
  src="/images/fps/position_errors_plot_0_10_feature.png"
  alt="Position error over frame number at 10 percent packet loss; the configuration without prediction diverges steadily and never recovers, while the three using prediction stay bounded"
  caption="Position error over time at 10% packet loss. Without prediction, lost inputs accumulate into a drift that never recovers — the player is simply slower than they should be."
>}}

Without prediction, each lost input is movement that never happens, so the player falls
progressively behind and the error never comes back — it is still wrong after the movement ends.
With prediction, loss stays bounded.

### Protocols

{{< report-figure
  src="/images/fps/position_error_avg_protocol_vs_delay.png"
  alt="Average position error against delay for WebSocket, redundant UDP and plain UDP, with and without prediction; without prediction all three rise together, with prediction all stay low"
  caption="Average position error against delay, by protocol. Without prediction the protocols are indistinguishable and all degrade; with prediction they all stay low. The transport matters far less than the client-side mechanisms."
>}}

{{< report-figure
  src="/images/fps/position_error_avg_protocol_vs_loss.png"
  alt="Average position error against packet loss for the three protocols; plain UDP with prediction performs best, and redundant UDP is slightly worse than plain UDP"
  caption="Average position error against packet loss, by protocol. Plain UDP with prediction generally beat WebSocket — and also beat our own redundant-input variant."
>}}

Here is the result we least expected. **The redundant input history made things slightly
worse.** Plain UDP outperformed both WebSocket and the variant carrying two inputs per packet.

The cause is a design flaw rather than a measurement error. Any input whose sequence number is
older than the last tick the server already processed gets discarded, even if it is sitting in
the queue — so only the *first* packet to arrive after a loss can contribute recovered history.
Everything after that is redundant in the useless sense. The mechanism pays its bandwidth cost
on every packet and collects on almost none of them.

### Smoothness

Accuracy says where the player ended up; it says nothing about whether getting there looked
right. For that we take acceleration per frame and measure how much it changes frame to frame:

```text
Accel_t          = ((P_t - P_t-Δt)/Δt - (P_t-Δt - P_t-2Δt)/Δt) / Δt
Loss of Smoothness = | Accel_t - Accel_t-Δt |
```

Purely local movement — no network at all — scores around **20**. That is the target.

{{< report-figure
  src="/images/fps/actual_smoothness_avg_feature_vs_delay.png"
  alt="Average loss of smoothness against network delay for four configurations; the full stack stays low and flat while the others are several times worse"
  caption="Loss of smoothness against delay. Only the full combination — prediction, reconciliation and interpolation — stays low, and it stays low regardless of latency."
>}}

Only the complete stack produces smooth motion, and it does so at every latency we tested. The
ordering in between is instructive: **prediction alone is worse than no prediction at all.**
Without prediction the position updates once per snapshot, so there is one acceleration jump per
tick. With prediction but no interpolation there are two update sources — the input tick and the
arriving snapshot — and reconciliation snaps the position instantly when they disagree. More
correctness, more visible discontinuities.

{{< report-figure
  src="/images/fps/actual_smoothness_avg_feature_vs_loss.png"
  alt="Average loss of smoothness against packet loss for four configurations, showing the same ordering as the delay chart across all loss rates"
  caption="Loss of smoothness against packet loss. The same ordering holds at every loss rate: smooth motion requires prediction and correction together."
>}}

{{< report-figure
  src="/images/fps/actual_smoothness_avg_protocol_vs_delay.png"
  alt="Average loss of smoothness against delay for the three protocols, showing negligible differences between them"
  caption="Loss of smoothness against delay, by protocol. Transport choice is essentially irrelevant to smoothness."
>}}

{{< report-figure
  src="/images/fps/actual_smoothness_avg_protocol_vs_loss.png"
  alt="Average loss of smoothness against packet loss for the three protocols, again showing negligible differences"
  caption="Loss of smoothness against packet loss, by protocol. Again, only the presence or absence of prediction and interpolation moves the needle."
>}}

Protocol choice barely registers. Smoothness is decided entirely by the client-side mechanisms.

And even at its best, the full stack stays well short of the local baseline. Our interpolation is
linear: it smooths *position* without any attempt to keep *acceleration* continuous, and the
metric is a second derivative. Fixing that means a higher-order scheme — spline interpolation, or
explicit predictive smoothing.

## What we took away

Three things, in rough order of how much they surprised us.

**Prediction is the load-bearing mechanism.** It is what decouples perceived responsiveness from
RTT, and it holds error flat across every latency and loss rate we tested. Nothing else in the
stack comes close in impact.

**Half a solution can be worse than none.** Prediction without interpolation measurably degrades
smoothness relative to no prediction at all, because it adds a second source of position updates
and lets reconciliation snap the player around. These mechanisms are a set, not a menu.

**Our redundancy scheme did not work.** It was a reasonable idea implemented in a way that could
only ever help on the first packet after a loss, and the data shows it — slightly worse than
plain UDP, for strictly more bandwidth. The fix is to let the server accept recovered inputs
further back than the last processed tick, which is a change to the queueing rule rather than to
the packet format.

The broader point is that responsiveness, accuracy and smoothness genuinely trade against each
other, and the right balance depends on the network you are actually on. That argues for adaptive
synchronization — varying the interpolation delay or the tick rate with measured conditions —
rather than the fixed constants we used throughout.

Left for future work: higher-order interpolation, better input recovery under heavy loss,
scalability in server architecture and player count, and fault tolerance on both ends.

[Source on GitHub](https://github.com/shugonta/CS230-FPS-Project)
