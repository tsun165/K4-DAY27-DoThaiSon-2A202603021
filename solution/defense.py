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
    # TODO: full checks in next commit
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
    # TODO: feature check in next commit
    return Verdict(alert=False, pillar="ai_infra")


def check_embedding_batch(payload, ctx):
    # TODO: embedding check in next commit
    return Verdict(alert=False, pillar="ai_infra")
