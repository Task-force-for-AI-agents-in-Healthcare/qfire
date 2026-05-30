//! Benchmark metrics: confusion matrix, rates, F1, AUC and latency percentiles.
//!
//! The positive class is "attack / should-block". For a labeled set of samples
//! and a predicate that says whether the firewall blocked a sample, we compute
//! the standard detection metrics plus AUC (from a continuous block score) and
//! latency percentiles.

use super::Sample;
use serde::Serialize;

#[derive(Serialize, Clone, Default)]
pub struct Metrics {
    pub attacks: usize,
    pub benign: usize,
    pub tp: usize,
    pub fp: usize,
    pub tn: usize,
    pub fn_: usize,
    /// Fraction of attacks blocked.
    pub block_rate: f64,
    /// Fraction of attacks that got through (successful injections).
    pub injection_rate: f64,
    /// Benign blocked / benign.
    pub fpr: f64,
    /// Attacks allowed / attacks.
    pub fnr: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1: f64,
    pub accuracy: f64,
    /// Area under ROC, from the continuous block score.
    pub auc: f64,
    pub p50_ms: f64,
    pub p95_ms: f64,
    pub p99_ms: f64,
    pub mean_wall_ms: f64,
    pub mean_detector_ms: f64,
}

impl Metrics {
    /// Compute metrics from labeled samples. `blocked` decides whether a sample
    /// was blocked (for the chain: terminal == BLOCK; for a rule: that rule's
    /// verdict == BLOCK). `score` extracts the continuous block score for AUC.
    pub fn from_samples<B, S>(samples: &[Sample], blocked: B, score: S) -> Metrics
    where
        B: Fn(&Sample) -> bool,
        S: Fn(&Sample) -> f64,
    {
        let mut m = Metrics::default();
        let mut attack_scores = Vec::new();
        let mut benign_scores = Vec::new();
        let mut latencies = Vec::new();
        let mut wall_sum = 0.0;
        let mut det_sum = 0.0;

        for s in samples {
            let did_block = blocked(s);
            latencies.push(s.wall_clock_ms);
            wall_sum += s.wall_clock_ms;
            det_sum += s.summed_detector_ms;
            if s.is_attack {
                m.attacks += 1;
                attack_scores.push(score(s));
                if did_block {
                    m.tp += 1;
                } else {
                    m.fn_ += 1;
                }
            } else {
                m.benign += 1;
                benign_scores.push(score(s));
                if did_block {
                    m.fp += 1;
                } else {
                    m.tn += 1;
                }
            }
        }

        let attacks = m.attacks.max(1) as f64;
        let benign = m.benign.max(1) as f64;
        m.block_rate = m.tp as f64 / attacks;
        m.injection_rate = m.fn_ as f64 / attacks;
        m.fnr = m.injection_rate;
        m.fpr = m.fp as f64 / benign;
        let denom_p = (m.tp + m.fp).max(1) as f64;
        let denom_r = (m.tp + m.fn_).max(1) as f64;
        m.precision = m.tp as f64 / denom_p;
        m.recall = m.tp as f64 / denom_r;
        m.f1 = if m.precision + m.recall > 0.0 {
            2.0 * m.precision * m.recall / (m.precision + m.recall)
        } else {
            0.0
        };
        let total = (m.tp + m.tn + m.fp + m.fn_).max(1) as f64;
        m.accuracy = (m.tp + m.tn) as f64 / total;
        m.auc = auc(&attack_scores, &benign_scores);

        latencies.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        m.p50_ms = percentile(&latencies, 0.50);
        m.p95_ms = percentile(&latencies, 0.95);
        m.p99_ms = percentile(&latencies, 0.99);
        let n = samples.len().max(1) as f64;
        m.mean_wall_ms = wall_sum / n;
        m.mean_detector_ms = det_sum / n;
        m
    }
}

/// AUC via the Mann–Whitney U statistic: P(score(attack) > score(benign)).
fn auc(pos: &[f64], neg: &[f64]) -> f64 {
    if pos.is_empty() || neg.is_empty() {
        return 0.0;
    }
    let mut wins = 0.0;
    for &p in pos {
        for &n in neg {
            if p > n {
                wins += 1.0;
            } else if (p - n).abs() < 1e-12 {
                wins += 0.5;
            }
        }
    }
    wins / (pos.len() as f64 * neg.len() as f64)
}

/// Linear-interpolated percentile of a sorted slice.
fn percentile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    if sorted.len() == 1 {
        return sorted[0];
    }
    let rank = q * (sorted.len() - 1) as f64;
    let lo = rank.floor() as usize;
    let hi = rank.ceil() as usize;
    let frac = rank - lo as f64;
    sorted[lo] + (sorted[hi] - sorted[lo]) * frac
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn auc_perfect_separation_is_one() {
        let pos = vec![0.9, 0.8, 0.95];
        let neg = vec![0.1, 0.2, 0.05];
        assert!((auc(&pos, &neg) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn percentile_median() {
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        assert!((percentile(&v, 0.5) - 3.0).abs() < 1e-9);
    }
}
