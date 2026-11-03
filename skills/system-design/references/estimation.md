# Estimation Cheat Sheet

Use these for back-of-envelope sizing. They are orders of magnitude, not benchmarks: hardware, cloud instance types and networks vary. When a decision depends on a number being right within 2x, measure it.

## Time conversions

| Quantity | Value | Shortcut |
| --- | --- | --- |
| Seconds per day | 86,400 | about 10^5 |
| Seconds per month (30 days) | about 2.6 million | about 2.5 x 10^6 |
| Seconds per year | about 31.5 million | about 3 x 10^7 |
| 1 million requests/day | about 12 per second | dividing per-day counts by 10^5 is quick but underestimates by about 14% |
| 1 billion requests/month | about 385 per second | |

Peak is usually 2-10x average for user-facing traffic, more for spiky events (launches, sales, batch jobs). State the peak factor you assume.

## Latency orders of magnitude

| Operation | Order of magnitude |
| --- | --- |
| CPU cache reference | about a nanosecond |
| Main memory reference | about 100 ns |
| Read 1 MB sequentially from memory | microseconds |
| SSD random read | tens to ~100 microseconds |
| Read 1 MB sequentially from SSD | about a millisecond or less |
| Round trip within a datacenter / availability zone | under a millisecond |
| Round trip between availability zones in one region | about 1-2 ms |
| HDD seek | about 10 ms |
| Round trip across a continent | tens of ms |
| Round trip between continents | 100-200 ms |

Takeaways:

- Memory is roughly 1000x faster than a network round trip; a network round trip is roughly 1000x faster than a human noticing.
- A request that makes 50 sequential calls to a service 1 ms away already spends 50 ms on round trips. Batch or parallelize.
- Cross-region synchronous replication adds a cross-region round trip to every write.

## Availability math

| Target | Downtime per year | Downtime per 30-day month |
| --- | --- | --- |
| 99% | about 3.65 days | about 7.2 hours |
| 99.9% | about 8.8 hours | about 43 minutes |
| 99.95% | about 4.4 hours | about 22 minutes |
| 99.99% | about 53 minutes | about 4.3 minutes |
| 99.999% | about 5.3 minutes | about 26 seconds |

- Serial dependencies multiply: a service that needs three dependencies each at 99.9% has at most about 99.7% availability (0.999^3).
- Redundant components improve it: two independent replicas at 99% each give about 99.99% if failover is instant and failures are independent (they often are not; shared power, config and deploys correlate failures).
- 99.99% and above usually requires automated failover, no single region dependency for critical paths, and deploys that can't take the whole service down.

## Storage math

```
storage = records per day x bytes per record x retention days x replication factor
          (+ indexes, typically 20-100% extra in relational databases)
```

Typical record sizes to start from (replace with real numbers when available):

| Item | Rough size |
| --- | --- |
| UUID / bigint key | 16 / 8 bytes |
| Timestamp | 8 bytes |
| Short row with a few text fields | 200 bytes - 1 KB |
| JSON event with metadata | 1-5 KB |
| Thumbnail image | tens of KB |
| Photo | a few MB |
| Minute of compressed HD video | tens of MB |

Units: 1 KB = 10^3 bytes, 1 MB = 10^6, 1 GB = 10^9, 1 TB = 10^12 (decimal, good enough for estimates).

## Bandwidth math

```
bandwidth (bytes/s) = requests per second x average response size
```

Example: 2,000 req/s x 50 KB = 100 MB/s = about 800 Mbit/s. That is significant egress cost and a reason to use a CDN for static or cacheable content.

## Throughput per node (very rough, verify for your stack)

Treat these as "is this one machine or a hundred?" signals only:

- A stateless web service node: hundreds to thousands of simple requests per second, much lower for heavy work.
- A single relational primary: thousands to tens of thousands of simple indexed writes per second on good hardware; far fewer for heavy transactions.
- An in-memory key-value store node: on the order of 100k simple operations per second.

If the estimate lands within 10x of a single node's capacity, plan the scale-out path now but don't build it yet.

## Sanity checks

- Does the estimate fit on one machine? Then don't distribute it.
- Does the data fit in memory (with room to grow)? Caching the whole working set may be the simplest design.
- Is egress or storage cost the dominant line item? Then data placement matters more than compute choice.
