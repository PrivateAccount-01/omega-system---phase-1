from __future__ import annotations

from prometheus_client import Counter, Histogram


DOWNLOAD_COUNTER = Counter(
    "omegadata_download_total",
    "Count of source downloads",
    ["source", "status"],
)

DOWNLOAD_LATENCY = Histogram(
    "omegadata_download_latency_seconds",
    "Download latency by source",
    ["source"],
)

DISCONTINUITY_COUNTER = Counter(
    "omegadata_discontinuity_total",
    "Detected discontinuities",
    ["category"],
)

VALIDATION_COUNTER = Counter(
    "omegadata_validation_total",
    "Cross-source validation outcomes",
    ["result"],
)

FAILOVER_COUNTER = Counter(
    "omegadata_download_failover_total",
    "Count of download fallbacks to secondary official URLs",
    ["source"],
)

API_REQUEST_COUNTER = Counter(
    "omegadata_api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)

API_REQUEST_LATENCY = Histogram(
    "omegadata_api_request_latency_seconds",
    "API latency by route",
    ["method", "path"],
)

ALERT_COUNTER = Counter(
    "omegadata_alerts_total",
    "Count of alerts routed",
    ["severity", "channel", "status"],
)
