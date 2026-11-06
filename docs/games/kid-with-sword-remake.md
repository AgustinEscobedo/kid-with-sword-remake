# kid with sword remake: Ocarina of Time (Switch 2) as a native iPhone and Mac app

This fork of [nxnative](https://github.com/seedds/nxnative) runs The Legend of Zelda: Ocarina of Time (Switch 2, title ID `0400486024DEC000`) natively on iOS and macOS. This page describes how it was built: where the code came from, what was changed and why, every build step, what was tested, and what is still open. It covers the state as of 2026-11-06.

**Nothing from the game is in this repository.** You need your own dump of the game; the build reads its files from your dump folder and writes the apps on your own Mac.

## The game version: the v1 dump

Everything here was built and tested with the **v1 dump**: the base game (v0) plus update **v131072**. The game profile (`dm/games/0400486024DEC000/game.tsv`) has one build row, `v131072`, and packs that version; other updates are untested.

The dump folder the build was run on looks like this (an unpacked dump, no `prod.keys` needed for a Switch 2 game):

```
kid with sword game/
  base/
    exefs/      the base game's code (main, subsdk0, sdk, main.npdm)
    romfs/      the base game's files
  updates/
    131072/
      exefs/    the v131072 update's code
      romfs/    the v131072 update's files
```

A `.nup` container of the same files works too ([Switch 2 games](../../README.md)).

## What you need

- **A Mac with Apple silicon.** Built and tested on a fanless MacBook Air M5 (10-core GPU) with 16 GB. macOS 26.6 or later and Xcode 27.2, as in the [README](../../README.md).
- **Homebrew tools:** `xcodegen`, `zstd`, the .NET SDK 10 (the shader translator), and Python. The IPA was built with Homebrew's **Python 3.15** (`/opt/homebrew/bin/python3.15`), whose standard library has `compression.zstd`; with Python 3.12 or 3.13 the script also needs `backports.zstd`. The Python running the script needs `lz4`, `capstone` 5.x and `fonttools` (see the header of `scripts/build_ipa_from_nsp.py`).
- **`zbic` 1.0.1.post1** (Nintendo's ZBIC compression of Switch 2 code modules), installed into the user's site of that Python:
  ```sh
  /opt/homebrew/bin/python3.15 -m pip install --user --break-system-packages zbic==1.0.1.post1
  ```
- **`zstandard`**, only for the resolution tool (`scripts/oot_res_overlay.py`), for example in a venv: `python3 -m venv venv && venv/bin/pip install zstandard`.
- **Disk space:** about 80 GB for the build folder (the extracted game, its RomFS image and the compiled shaders), plus 3 GB (split) or 27 GB (bundled) for the IPA.
- **For the iPhone:** an iPhone with iOS 26 or later (tested: iPhone 18 Pro) and a sideloader (tested: LiveContainer; SideStore or AltStore also work for an unsigned IPA).

## Where the code comes from

1. **seedds/nxnative `main`**, the upstream project.
2. **The Ocarina of Time branch** (`game-ocarina-of-time`, 192 commits on top of `main`): the game's profile (#1299), its SDK 22 services, NVN2 task and mesh shaders, Ampere instructions (F2IP, ATOMG.CAS, float atomic adds), the raw global memory pool table, the NDSR / NDVE packs, render conditions (agl's conditional clears), and the bindless pool-table patching that took Kokiri Forest from 46-49 ms to 16-21 ms a frame.
3. **Upstream pull requests merged into it** (3-way merges, conflicts resolved by hand):

   | PR | What it does |
   |---|---|
   | [#1343](https://github.com/seedds/nxnative/pull/1343) | Live shader inputs kept by dead-code removal: fixes the foliage jitter (translator rebuilt, shader chain `dce350aafbe2`) |
   | [#1368](https://github.com/seedds/nxnative/pull/1368) | Mesh pipelines built before their first draw: no missing foliage objects |
   | [#1446](https://github.com/seedds/nxnative/pull/1446) | A null memory pool or buffer gets 0 / NULL from the NVN getters instead of a host crash (Hyrule Field) |
   | [#1447](https://github.com/seedds/nxnative/pull/1447) | GPU-written texture ranges (no terrain holes) and the opt-in texture release |
   | [#1394](https://github.com/seedds/nxnative/pull/1394) | The raw global memory pool table lists only pools the game took a buffer address in |
   | [#1439](https://github.com/seedds/nxnative/pull/1439) | A storage takeover checks the live texture objects in one lookup |
   | [#1455](https://github.com/seedds/nxnative/pull/1455) | Shared textures no live object resolves to are retired when GPU memory runs short (the freeze after the talk with Saria) |
   | [#1393](https://github.com/seedds/nxnative/pull/1393) | Profile key `pool_skip_retired`: a finalized texture's ID gets the dummy instead of its texture made again (out of GPU memory at a scene change) |

   Not merged: [#1427](https://github.com/seedds/nxnative/pull/1427) (needs `main`'s newer write-log code), [#1405](https://github.com/seedds/nxnative/pull/1405) (shared raw-memory lookups), [#1453](https://github.com/seedds/nxnative/pull/1453) (render-target placement heap) and the frame-pacing parts of [#1444](https://github.com/seedds/nxnative/pull/1444).

## What this fork adds

| Change | Files | Why |
|---|---|---|
| Profile key `tex_release` (`off` / `1` / `2`, `DM_GAME_TEX_RELEASE`), level 2 for this game | `dm/games/game.py`, `dm/games/0400486024DEC000/game.tsv`, `dm/gfx/nvn/nvn_mtl.m` (`rel_mode`) | The guest copy of a texture's storage is given back once its GPU copy exists: level 1 for `CPU_NO_ACCESS` pools, level 2 also for CPU-visible pages not written since their upload. Kokiri Forest peak footprint 7.07 → 5.2 GB with the iPhone's guest files. A texture made again over released storage is copied on the GPU from the one released there |
| Released storage inside anonymous pools even with guest memory in files | `dm/host/hle_svc.c` (`dm_guest_range_in_files`), `dm/gfx/nvn/nvn_dirty.c` | On iOS guest memory lives in files; the memory pools moved to anonymous memory could not be released before |
| Game file replacements in the IPA | `dm/ios/tools/build_ipa.sh`, `dm/ios/tools/stage_resources.sh`, `dm/ios/Sources/main.m` | A `romfs_overlay` folder beside the RomFS image goes into the app; `main.m` sets `DM_ROMFS_OVERLAY` to it. Used for the fixed 720p resolution |
| Game file replacements in the Mac app | `dm/mac/pack_app.py` (`--romfs-overlay`), `dm/mac/launcher.c`, `scripts/build_ipa_from_nsp.py` | The Mac app carries `Resources/romfs_overlay` (from `romfs_overlay_mac` beside the RomFS, else `romfs_overlay`); the launcher sets `DM_ROMFS_OVERLAY` |
| Resolution tool | `scripts/oot_res_overlay.py` | Writes the modified resolution table (below) |
| iPhone crash after the opening cutscene fixed | `dm/gfx/nvn/nvn_rec.h` | The iPhone records Metal commands on a separate thread (`DM_NVN_ENC_THREAD`, on by default on iOS); its recorder had no stand-in for `drawMeshThreadgroupsWithIndirectBuffer:…`, the indirect task / mesh draw the game first issues after the opening cutscene, so the app stopped (`FATAL deferred encoding`). The draw is now recorded (`RO_R_MESH_IND`) and replayed |
| iOS SDK build fix | `dm/host/hle_svc.c` | `#include <mach/mach_vm.h>` removed: the iOS SDK rejects it (`vm_remap` comes from `mach/mach.h`) |
| Per-dispatch compute timings | `dm/gfx/nvn/nvn_mtl.m` (`DM_NVN_GPUPROF_CS`) | Diagnostics: GPU time of each compute shader, summed by shader key |

## Game profile settings

`dm/games/0400486024DEC000/game.tsv` holds the game's defaults; the build turns them into `game_profile.h`. The ones that matter for this port:

| Key | Value | What it does |
|---|---|---|
| `op_mode` | `handheld` | Console mode at start, as the iPhone runs it. The launcher's **Console mode** setting (`DM_OPMODE`) changes it |
| `render_cond` | `on` | agl's conditional depth clears (without it Kokiri Forest is a white scene) |
| `gmem_skip` | `on` | Compressible, shader-code and GPU no-access pools stay out of the raw memory pool table |
| `pool_skip_retired` | `on` | #1393 |
| `tex_release` | `2` | This fork; see above |
| `tex_soft` | `on` | Large block-compressed textures without their finest level on the GPU |
| `rt_drop` | `off` | Render-target stand-ins saved memory but made objects pop and sway |
| `rt_alias` | `off` | Render-target heap aliasing: glitches |
| `gpu_timestamps` | `segment` | Dynamic resolution reads the GPU time between the game's timestamp reports |
| `upscaler_chain` | (four shader keys) | `DM_UPSCALER=metalfx` replaces the game's NDSR upscale chain with MetalFX |

## Resolution

The render resolution comes from the game's own files: `Pack/Bootup.Nin_Ounce_NVN2.pack.zs` → `System/GameGraphics/ModelSceneExtensionParam/Default.game__gfx__ModelSceneExtensionParam.bgyml`. Its `ResolutionParam` (a hash-keyed BYML dictionary, node type `0x20`) has one base resolution per mode, with a final image of the same size:

| Mode | Base resolution |
|---|---|
| Handheld | 1920 × 1080 |
| Docked | 2560 × 1440 |

`DynamicResolutionParam` has the dynamic-resolution levels that multiply the base: `ResolutionReduceScale` 0.75, 0.711, 0.667, 0.622, 0.583, 0.533, 0.5, 0.445, 0.372, 0.333, with `LoadThreshold` 95. So the game, unchanged, renders at most 1440 × 810 handheld and 1920 × 1080 docked, and steps down under GPU load.

`scripts/oot_res_overlay.py` writes a copy of that pack with new levels; the RomFS image is not changed, the copy is served over it (`DM_ROMFS_OVERLAY`):

| Build | Command | Handheld | Docked |
|---|---|---|---|
| iPhone (fixed 720p, never lower) | `oot_res_overlay.py RomFS.img overlay_720 0.66667 - flat` | 1280 × 720 | 1707 × 960 |
| Mac app (native base, each mode) | `oot_res_overlay.py RomFS.img overlay_native 1.0 - flat` | 1920 × 1080 | 2560 × 1440 |

`flat` sets every level to the same scale, so the resolution never changes and the game never makes a new set of render targets.

## Building, step by step

The commands below use `G` for the dump folder and `B` for the build folder (`$G/0400486024DEC000_build`, the default), run from the repository's root:

```sh
G=~/Desktop/"kid with sword game"
B="$G/0400486024DEC000_build"
PY=/opt/homebrew/bin/python3.15
```

### 1. Mac development build

```sh
$PY scripts/build_ipa_from_nsp.py "$G" --platform mac --work-dir "$B" --keep-extracted
```

This extracts the game into `$B/extract/v131072` (ExeFS, a 26.2 GB `RomFS.img`), rewrites the code modules, splits out the 42,854 shaders, builds the Mac shader libraries (42,853 translate; one fails, its reason is at the end of `$B/logs/dmsh_build.log`) and the Mac host `$B/tools/dmhost`. The full shader build is the long part of a first run (upstream measured about 40 minutes on an M5 Pro); later runs reuse every stage whose inputs did not change. It prints the command that runs the game on the Mac, in this form:

```sh
cd "$B/run" && DM_ROOT="$B" DM_ROMFS="$B/extract/v131072/RomFS.img" DM_SAVE="$B/run/save" DM_TEMP="$B/run/temp" \
  DM_MSL_DIR="$B/shader/cache" DM_FONT_DIR="$B/font" DM_NVN_SHMAP="$PWD/dm/games/0400486024DEC000/shader_map.tsv" \
  DM_LANG=en-US DM_WINDOW=1 DM_AUDIO=1 DM_PSO_PAIRS="$B/shader/pso_pairs.tsv" "$B/tools/dmhost" "$B/patched_v131072"
```

(Use the exact command the script prints; `DM_NVN_SHMAP` is the profile's `shader_map.tsv` in your checkout.)

### 2. The resolution files

```sh
V="$B/extract/v131072"
venv/bin/python scripts/oot_res_overlay.py "$V/RomFS.img" "$V/romfs_overlay" 0.66667 - flat       # the iPhone's 720p
venv/bin/python scripts/oot_res_overlay.py "$V/RomFS.img" "$V/romfs_overlay_mac" 1.0 - flat      # the Mac app's native resolution
```

`build_ipa.sh` packs `romfs_overlay` into the IPA; the Mac app takes `romfs_overlay_mac` when it exists.

### 3. The iPhone settings file

An environment file baked into the app as `dm/env.txt` (one `KEY=VALUE` per line):

```
# baked into the iPhone app (dm/env.txt): the settings the Mac play tests ran with
DM_UPSCALER=metalfx
```

Saved here as `ios_env.txt` in a work folder.

### 4. The iPhone IPA

Split (recommended: a 2.7 GB IPA, the game files copied to the phone once):

```sh
$PY scripts/build_ipa_from_nsp.py "$G" --work-dir "$B" --env-file ios_env.txt --keep-extracted \
  --romfs separate -o "$G/OcarinaOfTime-split.ipa"
```

Bundled (one 26.9 GB IPA with the game files inside; some sideloaders cannot take a file this large):

```sh
$PY scripts/build_ipa_from_nsp.py "$G" --work-dir "$B" --env-file ios_env.txt --keep-extracted
```

Both are unsigned and ad-hoc signed with the app's entitlements, including `com.apple.developer.kernel.increased-memory-limit`; the sideloader re-signs them. Bundle ID `org.nxnative.0400486024dec000`, minimum iOS 26.0. The iPhone shaders are built once and reused; a repeat build took 2.5 minutes (split) to 8 minutes (bundled), mostly packing.

The IPA has no icon (a dump folder has no control data) and no pipeline archive, so the first start on the phone builds its pipelines (`--gpu g18p` builds one for the A19 / A19 Pro). The frame-rate counter is on; `DM_SHOW_FPS=0` in the app's `Documents/env.txt` turns it off.

### 5. Installing on the iPhone

1. Sideload the IPA.
2. Split IPA only: copy the game image `$B/extract/v131072/RomFS.img` into the app's **Documents** folder as `romfs.img`, once. Either through the Files app or Finder (the app's Documents folder is shared), or over USB with:
   ```sh
   scripts/push_romfs.sh <device UDID> org.nxnative.0400486024dec000 "$B/extract/v131072/RomFS.img"
   ```
   The app carries the image's identity (`romfs.id`) and only uses a complete image of that version, so a copy cut off halfway is never used. Copy it again only when the game version or the extraction changes.
3. Start the game. Its log is `Documents/log.txt`.

### 6. The Mac app with the launcher

```sh
$PY scripts/build_ipa_from_nsp.py "$G" --platform mac-app --work-dir "$B" --env-file ios_env.txt --keep-extracted \
  -o "$G/Ocarina of Time.app"
```

A self-contained, double-clickable app: the game files are APFS clones of the build's (no extra 26 GB on the same volume), the Mac shaders, a pipeline archive made with `metal-tt` for this Mac's GPU, and the native-resolution file. Its settings window opens before the game starts; **Console mode** picks Handheld (1920 × 1080) or Docked (2560 × 1440). On a MacBook Air M5 the native resolutions run well under 60 fps, docked especially: the 720p build already takes about 16 ms of GPU a frame. Saves go to `~/Library/Application Support/nxnative/0400486024DEC000/`, the log to `~/Library/Logs/nxnative/0400486024DEC000.log`.

## Tests and results

All on the v1 dump (v131072). Mac runs were capped by a memory guard (the game killed past a 9 GB footprint); scripted runs press only A, to load the save, and the player does the rest.

| Run | Where | Result |
|---|---|---|
| Unit tests (`dm/gfx/tests`, `GAME=010015100B514000`) | Mac | The merged PRs' tests (t_dirty_discard, t_gmem_marks, t_alias_takeover, t_alias_retire, t_pool_retired, t_cpu_storage) and t_cpu_tex, t_feedback all pass |
| Play test after the merges | MacBook Air M5, Kokiri Forest | Mostly 60 fps outdoors: frame p50 16.6-16.9 ms, GPU about 17 ms; peak footprint 9.45 GB with guest memory in RAM |
| Guest memory in files (`DM_GUEST_FILE=1`, as iOS does it) | Mac | Kokiri Forest peak 7.07 GB |
| `tex_release 2` | Mac, 4-minute play test | Peak 5.53 GB (5.19 GB in a second run), 2.4 GB released, no textures lost, no new errors |
| First iPhone run (bundled IPA, LiveContainer) | iPhone 18 Pro | Boots; title and opening movie mostly at 60 fps (p99 16.67 ms), footprint about 2 GB at the title; then stopped at frame 9911, right after the opening cutscene (`FATAL deferred encoding: DmRecEnc has no stand-in for -drawMeshThreadgroupsWithIndirectBuffer:…`) |
| The crash reproduced on the Mac | Mac, `DM_NVN_ENC_THREAD=1`, the old host | Same `FATAL` line |
| The fix | Mac, `DM_NVN_ENC_THREAD=1 DM_GUEST_FILE=1`, 150 s | No error past the same point |
| Mac play test with the fix | Mac, 73 s until the window was closed | No crash; frame p50 16.5-17.9 ms, a few 90-127 ms loading hitches; peak footprint 7.4 GB |

## Known issues and open work

- **The split IPA with the crash fix is not yet tested on the iPhone.**
- **Frame rate:** mostly 60 fps on the MacBook Air M5, with dips outdoors (GPU 13-19 ms a frame). The game steps its logic once per frame, so a 30 fps cap alone runs it at half speed. A correct 30 fps mode needs the game's own frame-rate controller (in `main`, at `main+0x3b4ef60`: it picks a vsync interval clamped to a config range, sets fps = 60 / interval and calls the framework's `setInterval` at `main+0x346c5c0`, which reaches `nvnWindowSetPresentInterval`) forced to interval 2. Not done; neither is the 30 / 60 setting in the launcher.
- **Two stalls of about 0.9 s** in a Mac play test, on the game's side (the submit time was small). Not investigated.
- **Texture release level 2:** if the game read back a released texture on the CPU, it would read zeros. Not seen in testing.
- **One shader fails to translate** (of 42,854); whether the game uses it is unknown.
- **Memory** can still climb to about 10 GB on some area changes with guest memory in RAM.
- **No app icon**, and no pipeline archive in the IPA.
- **Upstream PRs not merged:** #1427, #1405, #1453 and the frame-pacing parts of #1444.
- **Not checked:** areas past Kokiri Forest and its surroundings on the iPhone; the Mac app's docked mode at length.

## Credits

The upstream nxnative project and its contributors, the authors of the Ocarina of Time branch and the pull requests above, and the projects nxnative is built on ([Acknowledgements](../../README.md#acknowledgements)). This fork is not affiliated with Nintendo.
