# MrLightgun's Sinden forks compared

Checked on 2026-11-21 against the upstream MiSTer-devel repositories. Every
fork is the upstream core plus one commit, "Update ascal.vhd" (2024-07-05),
except the Saturn fork, which carries the same change through
terminator2k2's merges (2025-02 to 2025-04).

| Fork | Upstream | Fork base | Ahead / behind upstream | Files changed |
|---|---|---|---|---|
| MrLightgun/NES_MiSTer | MiSTer-devel/NES_MiSTer `master` | 2e1dca4 (2024-06-30) | 1 / 75 | `sys/ascal.vhd` |
| MrLightgun/SNES_MiSTer | MiSTer-devel/SNES_MiSTer `master` | ff8e6b6 (2024-04-08) | 1 / 119 | `sys/ascal.vhd` |
| MrLightgun/Genesis_MiSTer | MiSTer-devel/Genesis_MiSTer `master` | adc0c42 (2023-02-24) | 1 / 0 | `sys/ascal.vhd` |
| MrLightgun/MegaDrive_MiSTer | MiSTer-devel/MegaDrive_MiSTer `main` | badbf74 (2024-06-25) | 1 / 23 | `sys/ascal.vhd` |
| MrLightgun/MegaCD_MiSTer | MiSTer-devel/MegaCD_MiSTer `master` | d1fb714 (2024-04-08) | 1 / 8 | `sys/ascal.vhd` |
| MrLightgun/SMS_MiSTer | MiSTer-devel/SMS_MiSTer `master` | 89630ef (2024-04-18) | 1 / 77 | `sys/ascal.vhd` |
| MrLightgun/Atari7800_MiSTer | MiSTer-devel/Atari7800_MiSTer `master` | 282bce4 (2024-04-23) | 1 / 32 | `sys/ascal.vhd` |
| MrLightgun/PSX_MiSTer | MiSTer-devel/PSX_MiSTer `main` | 702439b (2024-06-05) | 1 / 101 | `sys/ascal.vhd` |
| MrLightgun/Saturn_MiSTer_Sinden | MiSTer-devel/Saturn_MiSTer `main` | 5c260b5 (2025-03-27) | 7 (merges) / 160 | `sys/ascal.vhd` |
| InputTest | MiSTer-devel/InputTest_MiSTer `main` | no public fork (the MiSTerSindenDriver README links a missing MrLightgun/InputTest_MiSTer and ships a prebuilt `InputTest-Sinden.rbf`) | | |

Genesis is "0 behind" because upstream Genesis has not changed since
2023-02-24; MrLightgun's Genesis fork is current.

## The change

Every fork changes `sys/ascal.vhd` (the framework's HDMI scaler) and nothing
else: no core RTL, no input or light gun code, no `CONF_STR`, no `.qsf`.
Most forks also converted the file to CRLF line endings, which is why GitHub
shows the whole file as changed; ignoring line endings, the change is:

1. four generics: `BORDER_H`/`BORDER_V` = 20, `BORDER_H2`/`BORDER_V2` = 28;
2. the output picture window is inset by the `*2` values:
   `o_hmin <= hmin + BORDER_H2`, `o_hmax <= hmax - BORDER_H2`, same for `v`;
3. a new pipeline signal `o_bzl` (declared with `o_hsv`, `o_pev`...):
   stage 0 is `o_hcpt/o_vcpt` inside the window grown by `BORDER_H/V`,
   shifted like the other stages and cleared when `o_run='0'`;
4. where ascal draws the border colour (`IF o_pev(11)='0'`), pixels with
   `o_bzl(11)='1'` are white (`x"FF"` on R, G and B).

The result on screen: the picture is shrunk by 28 pixels on each side, a
20-pixel white frame surrounds it, and the outer 8 pixels keep the normal
(black) border.

## Differences between forks

After removing comments and whitespace, the patched files of NES, SNES,
Genesis, MegaDrive, MegaCD, SMS, Atari7800 and PSX are token-for-token what
`scripts/sinden_border.py` produces from each fork's base. MegaCD differs
only by trailing whitespace. Saturn differs in one point of form:

* `o_vmin <= vmin + BORDER_H2` / `o_vmax <= vmax - BORDER_H2` (the horizontal
  generic for the vertical inset). Both generics are 28, so the result is
  identical; the patch here uses `BORDER_V2` as the other forks do.
* Its border-colour block nests the `IF o_bzl(11)` differently (indentation
  only), with the same logic.

No fork differs in thickness (20/28), colour (white), core-specific code or
input handling, so this repository keeps the same geometry for every core.
