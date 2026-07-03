import boto3
import statistics
import os
import sys
import requests
from datetime import datetime, timedelta

CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "eks-pipeline")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")
Z_SCORE_THRESHOLD = float(os.environ.get("Z_SCORE_THRESHOLD", "3.0"))
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "168"))  # 7 days

cw = boto3.client("cloudwatch", region_name=REGION)


def get_metric_datapoints(namespace, metric_name, dimensions, hours=LOOKBACK_HOURS):
    """Pull hourly datapoints for the past LOOKBACK_HOURS."""
    response = cw.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=datetime.utcnow() - timedelta(hours=hours),
        EndTime=datetime.utcnow(),
        Period=3600,
        Statistics=["Average"],
    )
    points = sorted(response["Datapoints"], key=lambda p: p["Timestamp"])
    return [p["Average"] for p in points]


def z_score_latest(values):
    """
    Compute how many standard deviations the most recent
    datapoint is from the rolling baseline (all but the last point).
    Returns 0 if there aren't enough points to compute a meaningful baseline.
    """
    if len(values) < 10:
        print(f"  Not enough datapoints ({len(values)}) — need at least 10 for a reliable baseline, skipping.")
        return 0.0
    baseline = values[:-1]
    latest = values[-1]
    mean = statistics.mean(baseline)
    stdev = statistics.stdev(baseline) or 1e-6   # avoid division by zero on perfectly flat metrics
    return (latest - mean) / stdev


def send_slack_alert(metric_name, z, latest, mean):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        requests.post(
            SLACK_WEBHOOK_URL,
            json={
                "text": (
                    f":rotating_light: *Anomaly Detected* — `{metric_name}`\n"
                    f"Latest value: `{latest:.2f}` is `{z:.1f}` standard deviations "
                    f"from its 7-day rolling baseline (mean: `{mean:.2f}`).\n"
                    f"Cluster: `{CLUSTER_NAME}` | Region: `{REGION}`"
                )
            },
            timeout=10,
        )
    except Exception as e:
        print(f"  WARNING: Slack notification failed (non-blocking): {e}")


def check_metric(label, namespace, metric_name, dimensions):
    print(f"\nChecking: {label}")
    values = get_metric_datapoints(namespace, metric_name, dimensions)

    if not values:
        print(f"  No datapoints returned — metric may not exist yet or cluster is too new.")
        return False

    z = z_score_latest(values)
    latest = values[-1]
    mean = statistics.mean(values[:-1]) if len(values) > 1 else latest

    print(f"  Datapoints: {len(values)} | Latest: {latest:.2f} | Baseline mean: {mean:.2f} | Z-score: {z:.2f}")

    if abs(z) > Z_SCORE_THRESHOLD:
        print(f"  *** ANOMALY: {z:.1f} std devs from baseline (threshold: ±{Z_SCORE_THRESHOLD}) ***")
        send_slack_alert(label, z, latest, mean)
        return True

    print(f"  Normal (within ±{Z_SCORE_THRESHOLD} std devs of baseline).")
    return False


def main():
    print(f"=== Anomaly Detection Run ===")
    print(f"Cluster: {CLUSTER_NAME} | Region: {REGION}")
    print(f"Lookback: {LOOKBACK_HOURS}h | Z-score threshold: ±{Z_SCORE_THRESHOLD}")

    metrics_to_check = [
        (
            "Pod CPU Utilization (backend)",
            "ContainerInsights",
            "pod_cpu_utilization",
            [
                {"Name": "ClusterName", "Value": CLUSTER_NAME},
                {"Name": "Namespace", "Value": "default"},
            ],
        ),
        (
            "Pod Memory Utilization (backend)",
            "ContainerInsights",
            "pod_memory_utilization",
            [
                {"Name": "ClusterName", "Value": CLUSTER_NAME},
                {"Name": "Namespace", "Value": "default"},
            ],
        ),
        (
            "Node CPU Utilization",
            "ContainerInsights",
            "node_cpu_utilization",
            [
                {"Name": "ClusterName", "Value": CLUSTER_NAME},
            ],
        ),
        (
            "Node Memory Utilization",
            "ContainerInsights",
            "node_memory_utilization",
            [
                {"Name": "ClusterName", "Value": CLUSTER_NAME},
            ],
        ),
    ]

    anomalies_found = []
    for label, namespace, metric_name, dimensions in metrics_to_check:
        if check_metric(label, namespace, metric_name, dimensions):
            anomalies_found.append(label)

    print(f"\n=== Summary ===")
    if anomalies_found:
        print(f"ANOMALIES DETECTED: {len(anomalies_found)}")
        for a in anomalies_found:
            print(f"  - {a}")
        sys.exit(0)
    else:
        print("All metrics within normal baseline. No anomalies detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
