#!/usr/bin/env python3
"""Extract setup slack from a TimeQuest summary (<revision>.sta.summary).

usage: setup_slack.py STA_SUMMARY

The summary lists, for every corner and clock, blocks like
    Type  : Slow 1100mV 85C Model Setup 'pll_hdmi|...|divclk'
    Slack : -0.156
    TNS   : -1.234
Prints JSON: {"worst_setup_slack_ns": <min over corners and clocks>,
"setup_slack_ns": {clock: <min over corners>}, "hdmi_setup_slack_ns": <min
over the pll_hdmi clocks>}. Emits a GitHub warning when the HDMI clock, the
only clock domain the Sinden patch adds logic to, misses timing.
"""

import json
import re
import sys

TYPE = re.compile(r"^Type\s*:\s*.*\bSetup\s+'(?P<clock>.+)'\s*$")
SLACK = re.compile(r"^Slack\s*:\s*(?P<v>-?[0-9.]+)")


def main():
    per_clock, clock = {}, None
    try:
        with open(sys.argv[1], errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"::warning::no timing summary: {e}", file=sys.stderr)
        lines = []
    for line in lines:
        line = line.strip()
        m = TYPE.match(line)
        if m:
            clock = m.group("clock")
            continue
        s = SLACK.match(line)
        if s and clock is not None:
            v = float(s.group("v"))
            per_clock[clock] = min(per_clock.get(clock, v), v)
            clock = None
        elif line.startswith("Type"):
            clock = None
    hdmi = [v for c, v in per_clock.items() if "pll_hdmi" in c]
    out = {
        "worst_setup_slack_ns": min(per_clock.values()) if per_clock else None,
        "setup_slack_ns": dict(sorted(per_clock.items(), key=lambda kv: kv[1])),
        "hdmi_setup_slack_ns": min(hdmi) if hdmi else None,
    }
    if hdmi and min(hdmi) < 0:
        print(f"::warning::HDMI clock setup slack {min(hdmi)} ns: the scaler (and the Sinden patch) misses timing",
              file=sys.stderr)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
