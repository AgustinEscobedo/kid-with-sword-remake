# The Legend of Zelda: Ocarina of Time, Switch 2 (0400486024DEC000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's patches.py and applies
# those of a module's NSO build ID; CUTS, OBS and FRAME_STEP as described there ("Registered patches"). Patches of Nintendo SDK module builds are in dm/tools/sdk_patches.py
CUTS = {
  # v131072 main: the movie player's video enhancement. Creating a movie player (main+0x3b5f500), the game takes the enhanced player (0x2f0 bytes, main+0x3b62cd0, then the NDVE setup
  # main+0x3b62ea0) when its NDVE manager is ready ([x0+0x460] set and its +0x10 not 0), else the plain one (0x1c0 bytes, main+0x3b619e0). The enhanced player runs an Ampere tensor network
  # (Movie/Ndve/Ndve-Nvn2-vid_seq5.dat: 14 compute dispatches a movie frame, 465 HMMA and 1,005 subgroup shuffles a thread in its largest) that took 47.5 ms of GPU time a frame on an
  # M-series Mac, against a 16.7 ms frame: the movies ran at 20 fps. A workaround for that platform limit (the HMMA chains are open in docs/reference/shaders.md, "Ampere HMMA through
  # simdgroup_matrix"): the branch always takes the plain player, which shows the decoded 1920x1080 picture as it is
  'e0f3ccfaf50065ae4ea01eb5aeb13b1a': [
    (0x3b5f524, '28010034', '09000014', 'movie player: cbz w8 → b main+0x3b5f548 (the plain player, without the NDVE tensor network)'),
  ],
}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md): what, its binding now, the loosest it could have (goal),
# purpose, why; blocked or kept: why the gap stays open (cannot close yet, or left open on purpose); checked: what was checked on game files (else a judgement)
BINDING = [
    {'what': 'movie player: the plain player instead of the NDVE-enhanced one', 'now': 'build', 'goal': 'game', 'purpose': 'frame rate',
     'why': 'a workaround: the tensor network costs 47.5 ms of GPU a movie frame; a function fingerprint could carry it over updates, and once the translator keeps LDSM / MOVM / HMMA chains in matrices the cut can go',
     'blocked': 'one build on hand; the faster tensor path is translator work (docs/reference/shaders.md, Ampere HMMA through simdgroup_matrix, Open)'},
]
