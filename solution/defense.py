"""
Your defense. Implement register(ctx) and a handler per event type.
See ../README.md for the full interface + toolkit reference, and
../RULES.md before you start.
"""
from api import Verdict


def register(ctx):
    ctx.on("data_batch", check_data_batch)
    ctx.on("contract_checkpoint", check_contract_checkpoint)
    ctx.on("lineage_run", check_lineage_run)
    ctx.on("feature_materialization", check_feature_materialization)
    ctx.on("embedding_batch", check_embedding_batch)


def check_data_batch(payload, ctx):
    res = ctx.tools.batch_profile(payload["batch_id"])
    if isinstance(res, dict) and "error" in res:
        return Verdict(alert=False, pillar="checks")

    b = ctx.baseline
    rows = res.get("row_count", 500)
    row_min = b.get("row_count_min", 435.4732)
    row_max = b.get("row_count_max", 561.2948)
    if rows < row_min or rows > row_max:
        return Verdict(alert=True, pillar="checks", reason=f"Row count {rows} outside [{row_min}, {row_max}]")

    null_cust = res.get("null_rate", {}).get("customer_id", 0.0)
    null_max = b.get("null_rate_max", 0.0109)
    if null_cust > null_max:
        return Verdict(alert=True, pillar="checks", reason=f"Null rate {null_cust} > {null_max}")

    mean_amt = res.get("mean_amount", 80.0)
    mean_min = b.get("mean_amount_min", 72.7645)
    mean_max = b.get("mean_amount_max", 90.6053)
    if mean_amt < mean_min or mean_amt > mean_max:
        return Verdict(alert=True, pillar="checks", reason=f"Mean amount {mean_amt} outside [{mean_min}, {mean_max}]")

    stale = res.get("staleness_min", 0.0)
    stale_max = b.get("staleness_min_max", 8.418)
    if stale > stale_max:
        return Verdict(alert=True, pillar="checks", reason=f"Staleness {stale} > {stale_max}")

    return Verdict(alert=False, pillar="checks")


def check_contract_checkpoint(payload, ctx):
    res = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if isinstance(res, dict) and "error" in res:
        return Verdict(alert=False, pillar="contracts")

    violations = res.get("violations", [])
    if violations:
        return Verdict(alert=True, pillar="contracts", reason=f"Contract violations: {violations}")

    freshness_delay = res.get("freshness_delay_min", 0.0)
    freshness_max = ctx.baseline.get("freshness_delay_max_min", 11.1141)
    if freshness_delay > freshness_max:
        return Verdict(alert=True, pillar="contracts", reason=f"Freshness delay {freshness_delay} > {freshness_max}")

    return Verdict(alert=False, pillar="contracts")


def check_lineage_run(payload, ctx):
    res = ctx.tools.lineage_graph_slice(payload["run_id"])
    if isinstance(res, dict) and "error" in res:
        return Verdict(alert=False, pillar="lineage")

    actual_up = res.get("actual_upstream", [])
    if len(actual_up) < 2 or "raw.orders" not in actual_up or "raw.customers" not in actual_up:
        return Verdict(alert=True, pillar="lineage", reason="Missing upstream dependencies")

    if res.get("actual_downstream_count", 1) == 0:
        return Verdict(alert=True, pillar="lineage", reason="Orphaned output with zero downstream")

    duration = res.get("duration_ms", 0.0)
    duration_max = ctx.baseline.get("lineage_duration_ms_max", 5134.9804)
    if duration > duration_max:
        return Verdict(alert=True, pillar="lineage", reason=f"Runtime anomaly: duration {duration} > {duration_max}")

    return Verdict(alert=False, pillar="lineage")


def check_feature_materialization(payload, ctx):
    res = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if isinstance(res, dict) and "error" in res:
        return Verdict(alert=False, pillar="ai_infra")

    shift = res.get("mean_shift_sigma", 0.0)
    # Using 0.50 threshold to avoid FP on borderline clean measurements (~0.414) while catching subtle skew (>=0.970)
    threshold = max(ctx.baseline.get("feature_mean_shift_sigma_max", 0.4095), 0.50)
    if shift > threshold:
        return Verdict(alert=True, pillar="ai_infra", reason=f"Feature mean shift sigma {shift} > {threshold}")

    return Verdict(alert=False, pillar="ai_infra")


def check_embedding_batch(payload, ctx):
    res = ctx.tools.embedding_drift(payload["corpus"], payload["chunk_batch_id"])
    if isinstance(res, dict) and "error" in res:
        return Verdict(alert=False, pillar="ai_infra")

    centroid_shift = res.get("centroid_shift", 0.0)
    centroid_max = ctx.baseline.get("embedding_centroid_shift_max", 0.0435)
    if centroid_shift > centroid_max:
        return Verdict(alert=True, pillar="ai_infra", reason=f"Centroid shift {centroid_shift} > {centroid_max}")

    doc_age = res.get("avg_doc_age_days", 0.0)
    doc_age_max = ctx.baseline.get("corpus_avg_doc_age_days_max", 49.7955)
    if doc_age > doc_age_max:
        return Verdict(alert=True, pillar="ai_infra", reason=f"Avg doc age {doc_age} > {doc_age_max}")

    return Verdict(alert=False, pillar="ai_infra")
