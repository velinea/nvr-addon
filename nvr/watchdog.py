import json
import os
import sys
import time
import urllib.error
import urllib.request
from time import perf_counter

GO2RTC_HTTP = "http://127.0.0.1:1984"
PROBE_TIMEOUT = 3.0
FAILURES_BEFORE_RESTART = 3
CHECK_INTERVAL = 10.0
RESTART_COOLDOWN = 120.0

t0 = perf_counter()


def log(msg):
    print(f"{perf_counter()-t0:8.3f} {msg}", file=sys.stderr, flush=True)


def configured_streams():
    channels = os.environ.get("CHANNELS", "0,1,2,3")
    streams = os.environ.get("STREAMS", "main,sub")
    names = []
    for ch in channels.split(","):
        ch = ch.strip()
        if not ch:
            continue
        for st in streams.split(","):
            st = st.strip()
            if st:
                names.append(f"cam{ch}_{st}")
    return names


def probe(name):
    url = f"{GO2RTC_HTTP}/api/frame.jpeg?src={name}"
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def restart_go2rtc(reason):
    url = f"{GO2RTC_HTTP}/api/restart"
    request = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read()
        log(f"WARN watchdog: restarted go2rtc ({reason}): {body!r}")
        return True
    except Exception as error:
        log(f"ERR watchdog: restart request failed: {error}")
        return False


def main():
    names = configured_streams()
    log(
        f"watchdog: monitoring {len(names)} streams: "
        + ", ".join(names)
    )

    failures = {name: 0 for name in names}
    seen_healthy = False
    next_restart_allowed = 0.0

    while True:
        trigger = None
        for name in names:
            if probe(name):
                failures[name] = 0
                seen_healthy = True
            else:
                failures[name] += 1
                if (
                    failures[name] >= FAILURES_BEFORE_RESTART
                    and failures[name] % FAILURES_BEFORE_RESTART == 0
                ):
                    if trigger is None:
                        trigger = name

        if (
            trigger is not None
            and seen_healthy
            and time.monotonic() >= next_restart_allowed
        ):
            next_restart_allowed = (
                time.monotonic() + RESTART_COOLDOWN
            )
            for name in names:
                failures[name] = 0
            restart_go2rtc(
                f"{trigger} no frames for "
                f"{FAILURES_BEFORE_RESTART} consecutive checks"
            )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()