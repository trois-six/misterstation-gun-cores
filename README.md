# misterstation-gun-cores

Up-to-date [MiSTer FPGA](https://github.com/MiSTer-devel) cores that draw the
white screen border a [Sinden light gun](https://sindenlightgun.com/) needs,
built automatically from the **official** cores, for
MiSTerStation and anyone else using a Sinden
on MiSTer.

The cores are the official MiSTer-devel cores, unchanged except for the
framework's HDMI scaler (`sys/ascal.vhd`), which shrinks the picture by 28
pixels on each side and draws a 20-pixel white frame around it. The light
gun input of each core is untouched.

## Credits

The border is [MrLightgun](https://github.com/MrLightgun)'s work: his Sinden
forks (NES, SNES, Genesis, MegaDrive, MegaCD, SMS, Atari7800, PSX, Saturn with
terminator2k2) and the
[MiSTerSindenDriver](https://github.com/MrLightgun/MiSTerSindenDriver) that
makes the gun work on MiSTer. Those forks were last updated in 2024-2025 and
fall behind the official cores; this repository re-applies the same change to
the current official sources every day. The scaler is
[ascal](https://github.com/MiSTer-devel/Template_MiSTer/blob/master/sys/ascal.vhd)
by TEMLIB; the cores belong to their authors (see each upstream repository).

## Cores

| Core | Upstream | Branch | Quartus revision | Asset |
|---|---|---|---|---|
| NES | [MiSTer-devel/NES_MiSTer](https://github.com/MiSTer-devel/NES_MiSTer) | master | NES | `NES-Sinden_<date>.rbf` |
| SNES | [MiSTer-devel/SNES_MiSTer](https://github.com/MiSTer-devel/SNES_MiSTer) | master | SNES | `SNES-Sinden_<date>.rbf` |
| Genesis | [MiSTer-devel/Genesis_MiSTer](https://github.com/MiSTer-devel/Genesis_MiSTer) | master | Genesis | `Genesis-Sinden_<date>.rbf` |
| MegaDrive | [MiSTer-devel/MegaDrive_MiSTer](https://github.com/MiSTer-devel/MegaDrive_MiSTer) | main | MegaDrive | `MegaDrive-Sinden_<date>.rbf` |
| MegaCD | [MiSTer-devel/MegaCD_MiSTer](https://github.com/MiSTer-devel/MegaCD_MiSTer) | master | MegaCD | `MegaCD-Sinden_<date>.rbf` |
| SMS | [MiSTer-devel/SMS_MiSTer](https://github.com/MiSTer-devel/SMS_MiSTer) | master | SMS | `SMS-Sinden_<date>.rbf` |
| Atari7800 | [MiSTer-devel/Atari7800_MiSTer](https://github.com/MiSTer-devel/Atari7800_MiSTer) | master | Atari7800 | `Atari7800-Sinden_<date>.rbf` |
| PSX | [MiSTer-devel/PSX_MiSTer](https://github.com/MiSTer-devel/PSX_MiSTer) | main | PSX | `PSX-Sinden_<date>.rbf` |
| PSX (dual SDRAM) | [MiSTer-devel/PSX_MiSTer](https://github.com/MiSTer-devel/PSX_MiSTer) | main | PSX_DualSDRAM | `PSX_DualSDRAM-Sinden_<date>.rbf` |
| Saturn | [MiSTer-devel/Saturn_MiSTer](https://github.com/MiSTer-devel/Saturn_MiSTer) | main | Saturn | `Saturn-Sinden_<date>.rbf` |
| Saturn (dual SDRAM) | [MiSTer-devel/Saturn_MiSTer](https://github.com/MiSTer-devel/Saturn_MiSTer) | main | Saturn_DS | `Saturn_DS-Sinden_<date>.rbf` |
| InputTest | [MiSTer-devel/InputTest_MiSTer](https://github.com/MiSTer-devel/InputTest_MiSTer) | main | InputTest | `InputTest-Sinden_<date>.rbf` |

This is the list of cores MrLightgun's driver ships Sinden builds for. The
list lives in [`cores.json`](cores.json); adding a core is one entry there
(any core built on the MiSTer framework gets the border, but only cores with
light gun support are useful).

### Naming

`<Core>-Sinden_<YYYYMMDD>.rbf`, `<YYYYMMDD>` being the build date (UTC), the
names MrLightgun's driver uses (`NES-Sinden.rbf`) plus MiSTer's date suffix.
MiSTer's menu and MGL `<rbf>` references drop the date (`_LightGun/NES-Sinden`
loads the newest `NES-Sinden_*.rbf`), and since the name continues with `-`,
a reference to the official core (`_Console/NES`) never picks the Sinden
build by mistake.

## Downloads

* Each build is a GitHub release tagged `<Core>-Sinden_<date>-<upstream
  commit>`, with the `.rbf` and its manifest (`<asset>.json`: core, upstream
  repository, branch and commit, build date, Quartus image and revision,
  worst setup slack, build time, sha256, size, download URL, the run that
  built it and the commit of this repository it was built with).
* The release `latest` carries `index.json`, the newest build of every core,
  at a stable URL:
  <https://github.com/trois-six/misterstation-gun-cores/releases/download/latest/index.json>

```json
{
  "format": 1,
  "repository": "https://github.com/trois-six/misterstation-gun-cores",
  "generated_at": "2026-11-21T06:00:00Z",
  "cores": {
    "NES": {
      "core": "NES",
      "asset": "NES-Sinden_20261121.rbf",
      "sha256": "…",
      "upstream_repo": "MiSTer-devel/NES_MiSTer",
      "upstream_commit": "…",
      "download_url": "https://github.com/trois-six/misterstation-gun-cores/releases/download/NES-Sinden_20261121-cf7fe6c/NES-Sinden_20261121.rbf",
      "…": "…"
    }
  }
}
```

## How MiSTerStation uses them

MiSTerStation draws the Sinden border in its own menus when a Sinden gun is
plugged in (Batocera's border settings). For games, the border must come from
the core, which is what these builds are for. The integration this repository
is laid out for: MiSTerStation reads `index.json`, installs the cores the user
enables into a directory of their own (for example `/media/fat/_LightGun/`),
checks the sha256, and launches a light gun game through an MGL whose `<rbf>`
points at the Sinden build (`_LightGun/NES-Sinden`) instead of the official
core. Manual use works the same way: copy the
`.rbf` to the SD card and load it from MiSTer's menu.

The border only appears on the HDMI output (the scaler). Use it with
MrLightgun's [MiSTerSindenDriver](https://github.com/MrLightgun/MiSTerSindenDriver)
and its per-core settings.

## How it works

* [`scripts/sinden_border.py`](scripts/sinden_border.py) applies the border
  to a `sys/ascal.vhd`. It is a transformation anchored on ten stable lines of
  ascal rather than a diff, so it applies to every framework version the
  cores carry (four different `ascal.vhd` versions among the cores today) and
  keeps the file's line endings. Each anchor must match exactly once; if one
  does not (upstream rewrote the scaler), the script changes nothing and fails
  with the anchor's name. [`patches/sinden-border.reference.diff`](patches/sinden-border.reference.diff)
  shows its result on Template_MiSTer, for reading only. `--border`/`--inset`
  change the geometry (defaults 20/28, from `cores.json`).
* [`scripts/detect.py`](scripts/detect.py) decides what to build: for each
  core, `git ls-remote` of the upstream branch against the commit recorded in
  `index.json`; when it moved, a shallow blob-less fetch hashes the source
  tree without `releases/` (MiSTer's release commits only add an `.rbf`
  there and do not trigger a rebuild) and checks that the patch applies to
  the new `sys/ascal.vhd`. Changing the patcher, the build script, the
  Quartus image or a core's entry (the "recipe") rebuilds the cores concerned.
* [`scripts/build-core.sh`](scripts/build-core.sh) checks out the upstream
  commit, patches it, and runs `quartus_sh --flow compile <project> -c
  <revision>` in Docker.
* [`.github/workflows/build.yml`](.github/workflows/build.yml) runs it all:
  * triggers: push to `main` (scripts, `cores.json`, the workflow), daily at
    04:23 UTC, and manually (`force`, `cores` inputs);
  * `detect`: the build matrix, and an issue "Sinden patch no longer applies:
    <core>" for each core the patch does not fit (that core is not built,
    the others are);
  * `image`: archives the Quartus image (Docker Hub
    [`theypsilon/quartus-lite-c5:17.0.2.docker1`](https://hub.docker.com/r/theypsilon/quartus-lite-c5),
    Quartus Prime Lite 17.0.2 for Cyclone V, the version MiSTer cores are
    built with, made for MiSTer CI by theypsilon) in the Actions cache once,
    so builds do not each pull 3 GB from Docker Hub;
  * `build`: one job per core, with disk cleanup and the core's timeout from
    `cores.json` (up to 350 minutes for Saturn); logs and Quartus summaries
    are kept as artifacts; a failure opens (or comments on) an issue "Build
    failed: <core>";
  * `publish`: one release per built core, then `index.json` in `latest`;
    closes the build-failure issue of every core that built.

Run a core locally (Docker and Python 3 needed):

```sh
scripts/build-core.sh NES MiSTer-devel/NES_MiSTer <commit> NES NES \
  theypsilon/quartus-lite-c5:17.0.2.docker1 out
```

## Licence

The cores are free software under their upstream licences (GPL-3.0 for most,
GPL-2.0 for PSX and the MiSTer framework, MIT for Atari7800; see each
upstream repository); a released `.rbf` is under its core's licence. The
corresponding source of a release is the upstream commit recorded in its
manifest plus this repository at the recorded `recipe_commit` (the patch and
the build scripts); both are public.

This repository's scripts and patch are licensed under the GNU General Public
License, version 2 or (at your option) any later version, the MiSTer
framework's licence, which keeps them compatible with both the GPL-2.0 and
the GPL-3.0 cores ([LICENSE](LICENSE)). ascal itself is distributed by TEMLIB
under its own permissive terms (see its header).
