#!/usr/bin/env python3
"""Extract setup slack from a Quartus flow log (quartus_sta tables).

usage: setup_slack.py QUARTUS_LOG

Prints JSON: {"worst_setup_slack_ns": <min over corners and clocks>,
"setup_slack_ns": {clock: <min over corners>}, "hdmi_setup_slack_ns": <min
over the pll_hdmi clocks>}. Emits a GitHub warning when the HDMI clock, the
only clock domain the Sinden patch adds logic to, misses timing.
"""

import json
import re
import sys

HEAD = re.compile(r"Worst-case setup slack is (-?[0-9.]+)")
ROW = re.compile(r"Info \(332119\):\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(\S.*?)\s*$")


def main():
    per_clock, worst, in_table = {}, None, False
    with open(sys.argv[1], errors="replace") as f:
        for line in f:
            m = HEAD.search(line)
            if m:
                v = float(m.group(1))
                worst = v if worst is None else min(worst, v)
                in_table = True
                continue
            if in_table:
                if "Info (332119)" not in line:
                    in_table = False
                    continue
                r = ROW.search(line)
                if r:
                    clk, v = r.group(3), float(r.group(1))
                    per_clock[clk] = min(per_clock.get(clk, v), v)
    hdmi = [v for c, v in per_clock.items() if "pll_hdmi" in c]
    out = {
        "worst_setup_slack_ns": worst,
        "setup_slack_ns": dict(sorted(per_clock.items(), key=lambda kv: kv[1])),
        "hdmi_setup_slack_ns": min(hdmi) if hdmi else None,
    }
    if hdmi and min(hdmi) < 0:
        print(f"::warning::HDMI clock setup slack {min(hdmi)} ns: the scaler (and the Sinden patch) misses timing",
              file=sys.stderr)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
