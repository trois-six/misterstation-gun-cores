#!/usr/bin/env python3
"""Add the Sinden light gun border to a MiSTer framework scaler (sys/ascal.vhd).

Port of MrLightgun's Sinden patch (https://github.com/MrLightgun) as a
transformation anchored on stable lines of ascal.vhd, so it applies to every
version of the MiSTer framework (Template_MiSTer sys/) the target cores carry,
whatever their line endings. Every anchor must match exactly once: if one does
not, the file is left untouched and the script exits with status 1, naming the
anchor, so a build never ships an unpatched core.

What the patch does (same geometry and colour as MrLightgun's forks):
  * the scaled picture is inset by BORDER_H2/BORDER_V2 (28) pixels on each side
    (o_hmin/o_hmax/o_vmin/o_vmax);
  * the BORDER_H/BORDER_V (20) pixels of the output just around the picture
    (o_bzl, delayed with the rest of the output pipeline) are drawn white
    (x"FF"), the remaining 8 pixels keep the normal border colour.
Only the HDMI scaler output changes; inputs, the core and the analog/direct
video paths are untouched.

Usage: sinden_border.py [--check] [--border N] [--inset N] ascal.vhd...
  --check   verify that the patch applies, write nothing
"""

import argparse
import re
import sys

MARKER = "Sinden light gun border"


class PatchError(Exception):
    pass


def build_steps(border, inset):
    """Return (name, regex, replacement-function) for every edit, in order."""

    def generics(m):
        i = m.group("indent")
        return (
            f"{i}-- {MARKER} (MrLightgun): white frame of BORDER_H/V pixels\n"
            f"{i}-- around the picture, which is inset by BORDER_H2/V2 pixels\n"
            f"{i}BORDER_H     : natural := {border};\n"
            f"{i}BORDER_V     : natural := {border};\n"
            f"{i}BORDER_H2    : natural := {inset};\n"
            f"{i}BORDER_V2    : natural := {inset};\n" + m.group(0)
        )

    def window(m):
        dim, side = m.group("dim"), m.group("side")
        op = "+" if side == "min" else "-"
        return f"{m.group('lhs')}{dim}{side} {op} BORDER_{dim.upper()}2;"

    def zone(m):
        i = m.group("indent")
        return (
            f"{i}-- {MARKER}: output pixel inside the white frame\n"
            f"{i}o_bzl(0)<=to_std_logic(o_hcpt>=o_hmin-BORDER_H AND o_hcpt<=o_hmax+BORDER_H AND\n"
            f"{i}                       o_vcpt>=o_vmin-BORDER_V AND o_vcpt<=o_vmax+BORDER_V);\n"
            + m.group(0)
        )

    def colour(m):
        i, body = m.group("indent"), m.group("body")
        body = "".join("\t" + line for line in body.splitlines(keepends=True))
        return (
            f"{m.group('head')}"
            f"{i}\tIF o_bzl(11)='1' THEN -- {MARKER}\n"
            f"{i}\t\to_r<=x\"FF\";\n"
            f"{i}\t\to_g<=x\"FF\";\n"
            f"{i}\t\to_b<=x\"FF\";\n"
            f"{i}\tELSE\n"
            f"{body}"
            f"{i}\tEND IF;\n"
            f"{i}END IF;"
        )

    return [
        ("generic N_BURST",
         r"^(?P<indent>[ \t]*)N_BURST[ \t]*:[ \t]*natural\b[^\n]*\n", generics),
        ("signal o_hsv,o_vsv,o_dev,o_pev,o_end",
         r"\bSIGNAL o_hsv,o_vsv,o_dev,o_pev,o_end[ \t]*:",
         lambda m: "SIGNAL o_hsv,o_vsv,o_dev,o_pev,o_bzl,o_end :"),
        ("o_hmin<=hmin", r"(?P<lhs>\bo_(?P<dim>h)(?P<side>min)[ \t]*<=[ \t]*)h(min);", window),
        ("o_hmax<=hmax", r"(?P<lhs>\bo_(?P<dim>h)(?P<side>max)[ \t]*<=[ \t]*)h(max);", window),
        ("o_vmin<=vmin", r"(?P<lhs>\bo_(?P<dim>v)(?P<side>min)[ \t]*<=[ \t]*)v(min);", window),
        ("o_vmax<=vmax", r"(?P<lhs>\bo_(?P<dim>v)(?P<side>max)[ \t]*<=[ \t]*)v(max);", window),
        ("o_vss<=... (pipeline stage 0)",
         r"^(?P<indent>[ \t]*)o_vss[ \t]*<=[ \t]*to_std_logic\(o_vcpt_pre2[^\n]*\n", zone),
        ("o_pev(1 TO 11)<=o_pev(0 TO 10)",
         r"^(?P<indent>[ \t]*)o_pev\(1 TO 11\)[ \t]*<=[ \t]*o_pev\(0 TO 10\);[^\n]*\n",
         lambda m: m.group(0) + f"{m.group('indent')}o_bzl(1 TO 11)<=o_bzl(0 TO 10);\n"),
        ("o_pev(2)<='0'",
         r"^(?P<indent>[ \t]*)o_pev\(2\)[ \t]*<=[ \t]*'0';[^\n]*\n",
         lambda m: m.group(0) + f"{m.group('indent')}o_bzl(2)<='0';\n"),
        ("IF o_pev(11)='0' (border colour)",
         r"(?P<head>^(?P<indent>[ \t]*)IF o_pev\(11\)[ \t]*=[ \t]*'0'[ \t]*THEN[^\n]*\n)"
         r"(?P<body>(?:[ \t]*o_[rgb][ \t]*<=[ \t]*o_border\([^\n]*\n){3})"
         r"(?P=indent)END IF;",
         colour),
    ]


def patch_text(text, border=20, inset=28):
    if "BORDER_H2" in text or "o_bzl" in text:
        raise PatchError("already patched (BORDER_H2/o_bzl present)")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")
    for name, pattern, repl in build_steps(border, inset):
        rx = re.compile(pattern, re.MULTILINE)
        n = len(rx.findall(text))
        if n != 1:
            raise PatchError(f"anchor '{name}' matched {n} times, expected 1")
        text = rx.sub(repl, text, count=1)
    return text.replace("\n", "\r\n") if crlf else text


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify only, write nothing")
    ap.add_argument("--border", type=int, default=20, help="white frame width (BORDER_H/V)")
    ap.add_argument("--inset", type=int, default=28, help="picture inset (BORDER_H2/V2)")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    if not 0 < args.border <= args.inset:
        ap.error("need 0 < --border <= --inset")
    status = 0
    for path in args.files:
        with open(path, newline="") as f:
            src = f.read()
        try:
            out = patch_text(src, args.border, args.inset)
        except PatchError as e:
            print(f"::error file={path}::Sinden border patch does not apply: {e}", file=sys.stderr)
            status = 1
            continue
        if not args.check:
            with open(path, "w", newline="") as f:
                f.write(out)
        print(f"{path}: Sinden border patch {'applies' if args.check else 'applied'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
