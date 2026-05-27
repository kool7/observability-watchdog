"""Synthetic log generator with configurable error spike simulation."""

import argparse
import random
import sys
import time
from datetime import datetime, timezone

import httpx
from faker import Faker

fake = Faker()

SERVICES = ["api-gateway", "auth-service", "payment-service"]

INFO_MESSAGES = [
    "Request processed successfully",
    "Cache hit for key {key}",
    "User {user} authenticated",
    "Health check passed",
    "Connection pool size: {n}",
    "Scheduled job completed in {ms}ms",
    "Config reloaded",
    "Session created for user {user}",
]

WARN_MESSAGES = [
    "Response time elevated: {ms}ms",
    "Retrying connection attempt {n}",
    "Cache miss for key {key}",
    "Deprecated endpoint called by {user}",
    "Rate limit threshold at 80% for {service}",
    "Memory usage at {pct}%",
]

ERROR_MESSAGES = [
    "Database connection timeout after {ms}ms",
    "Unhandled exception in payment processor: NullPointerException",
    "Failed to charge card for user {user}: gateway error",
    "Circuit breaker OPEN for downstream {service}",
    "Transaction rollback: deadlock detected",
    "Authentication token expired for user {user}",
    "Payment gateway returned 503 after {n} retries",
    "Out of memory error in worker thread {n}",
]


def _render(template: str) -> str:
    return template.format(
        key=fake.md5()[:8],
        user=fake.user_name(),
        n=random.randint(1, 10),
        ms=random.randint(50, 5000),
        service=random.choice(SERVICES),
        pct=random.randint(70, 95),
    )


def _make_entry(service: str, level: str, message: str) -> dict:
    return {
        "service_name": service,
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _send(api_url: str, payload: dict | list) -> bool:
    try:
        resp = httpx.post(f"{api_url}/logs/ingest", json=payload, timeout=5)
        return resp.status_code == 201
    except httpx.RequestError as exc:
        print(f"  [warn] send failed: {exc}", file=sys.stderr)
        return False


def _baseline_log(api_url: str, services: list[str]) -> None:
    service = random.choice(services)
    roll = random.random()
    if roll < 0.70:
        level, pool = "INFO", INFO_MESSAGES
    elif roll < 0.90:
        level, pool = "WARN", WARN_MESSAGES
    else:
        level, pool = "ERROR", ERROR_MESSAGES
    _send(api_url, _make_entry(service, level, _render(random.choice(pool))))


def run(
    api_url: str,
    services: list[str],
    duration: int,
    spike: bool,
    spike_service: str,
    spike_errors: int,
) -> None:
    api_url = api_url.rstrip("/")
    print(f"Sending baseline logs for {duration}s to {api_url} ...")
    print(f"Services: {', '.join(services)}")

    sent = 0
    spike_done = False
    spike_at = max(duration // 2, 1)

    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed >= duration:
            break

        _baseline_log(api_url, services)
        sent += 1

        if spike and not spike_done and elapsed >= spike_at:
            print(
                f"\n  >>> Injecting error spike ({spike_errors} errors on {spike_service}) <<<"  # noqa: E501
            )
            # Send as a single batch request to avoid hitting the rate limiter
            batch = [
                _make_entry(
                    spike_service, "ERROR", _render(random.choice(ERROR_MESSAGES))
                )  # noqa: E501
                for _ in range(spike_errors)
            ]
            if _send(api_url, batch):
                sent += spike_errors
            else:
                print(
                    "  [warn] Spike batch failed — anomaly may not trigger",
                    file=sys.stderr,
                )  # noqa: E501
            spike_done = True
            print("  >>> Spike complete. Resuming baseline ...\n")

        if sent % 20 == 0:
            print(f"  [{elapsed:.0f}s] {sent} logs sent")

        time.sleep(1)

    elapsed_total = time.monotonic() - start
    print(f"\nDone. {sent} logs sent in {elapsed_total:.1f}s.")

    # Report anomaly count
    try:
        resp = httpx.get(f"{api_url}/anomalies", params={"limit": 5}, timeout=5)
        if resp.status_code == 200:
            anomalies = resp.json()
            print(f"Anomalies detected: {len(anomalies)}")
            for a in anomalies:
                svc = a.get("service_name", "?")
                sev = a.get("severity", "?")
                z = a.get("z_score", 0.0)
                errs = a.get("error_count", "?")
                print(f"  [{sev}] {svc} — z={z:.2f}, errors={errs}")
        else:
            print(f"Could not fetch anomalies (HTTP {resp.status_code})")
    except httpx.RequestError as exc:
        print(f"Could not fetch anomalies: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic logs for Observability Watchdog"
    )
    parser.add_argument(
        "--api-url", default="http://localhost:8000", help="Base API URL"
    )
    parser.add_argument(
        "--services", nargs="+", default=SERVICES, help="Service names to simulate"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Baseline duration in seconds (min 2 when spike enabled)",
    )
    parser.add_argument(
        "--no-spike",
        dest="spike",
        action="store_false",
        help="Disable error spike (spike is on by default)",
    )
    parser.set_defaults(spike=True)
    parser.add_argument(
        "--spike-service", default="payment-service", help="Service to spike"
    )
    parser.add_argument(
        "--spike-errors", type=int, default=30, help="Error count during spike"
    )
    args = parser.parse_args()

    if args.spike and args.duration < 2:
        parser.error("--duration must be at least 2 when spike is enabled")
    if args.spike and args.spike_service not in args.services:
        parser.error(
            f"--spike-service '{args.spike_service}' not in --services {args.services}"
        )

    run(
        api_url=args.api_url,
        services=args.services,
        duration=args.duration,
        spike=args.spike,
        spike_service=args.spike_service,
        spike_errors=args.spike_errors,
    )


if __name__ == "__main__":
    main()
