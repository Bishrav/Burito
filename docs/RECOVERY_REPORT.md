# Repository recovery

All 39 affected files were decoded from their current Git blobs. The common envelope contains a 96-byte prefix after reversing a two-bit shift. The first affected commit was `05b2a3f`. The process that applied the transformation is unknown. No source reconstruction or package upgrades were required for decoding.

| Path | Original blob | Latest readable historical change |
| --- | --- | --- |
| `README.md` | `845bf19547d28ccdcc43a861f7bd5098e47ccd6a` | `3ecc185` |
| `burito/__main__.py` | `109ac2a258e3c9dafc47e9a8333d5453e6d71fc5` | `7d8e0f6` |
| `burito/access.py` | `943a1c51ce1f290ab73f032025a90b8120e4f0e7` | `7d8e0f6` |
| `burito/chat.py` | `c9aaeee8a7a6b0b1f7d965ae7fc8dbd239a51267` | `c6ec1a5` |
| `burito/runtime_lock.py` | `da05e72f09ad91a7c85a4789632b94343c683b85` | `c6ec1a5` |
| `burito/web.py` | `1c6f408f6862ea9a63a10f9b2a761cafe2163821` | `c6ec1a5` |
| `burito/windows.py` | `44082ff2fffa82aac5ed694004ba10821465b5ac` | `7d8e0f6` |
| `docs/FIRST_CHAT.md` | `b649746c837c684c8fa000932d012187d25e42a0` | `d7d1dd7` |
| `docs/NEW_LINUX_MIGRATION.md` | `5550b7fcae57ff61709c1cf353761695343c576d` | No earlier readable file |
| `docs/PC_ACCESS.md` | `b2fc5cad125203ae12c9b9e9b69307b511bdd351` | `7d8e0f6` |
| `docs/ROADMAP.md` | `bd79787e021ae249da41556a81c3011993294ae7` | `7d8e0f6` |
| `docs/STATUS.md` | `fd39c2a3a414a0807c2ab589dbabf6dc839a8a73` | `7d8e0f6` |
| `runtime/agent/instructions.md` | `7c1cd473af66ba28d58faf0c603f19e74a557a59` | `7d8e0f6` |
| `runtime/agent/instructions/lesson.ts` | `e653bbff9313f3cd930f141f00d54e459db433b3` | `7d8e0f6` |
| `runtime/agent/tools/browser_activate_tab.ts` | `049aa14aa09feb74bc6ccb8728a2ea419e132bcf` | No earlier readable file |
| `runtime/agent/tools/browser_copy_text.ts` | `7bfb59551d3046feb99b95ee12a136a3a9feb5b2` | No earlier readable file |
| `runtime/agent/tools/browser_find_tabs.ts` | `a9ed32ce2de3cce4697c58ab840e57765a6691e8` | No earlier readable file |
| `runtime/agent/tools/browser_navigate.ts` | `31305848b2a895821dcec40b0f6565980af34274` | No earlier readable file |
| `runtime/agent/tools/browser_page_action.ts` | `0c719a66bc9b67dbfdc1ffdd683ef485dc1c84dc` | No earlier readable file |
| `runtime/agent/tools/browser_read_page.ts` | `2c830cc496693bfe4fb5b81e811082e53fda4fa0` | No earlier readable file |
| `runtime/agent/tools/browser_search.ts` | `ed5da08f88545a9da6227a378a845d5658c837f3` | No earlier readable file |
| `runtime/agent/tools/browser_tabs.ts` | `086c56abae4b8709de7265d2e9a4ec7df51990b7` | No earlier readable file |
| `runtime/agent/tools/clipboard_write_text.ts` | `9713c1c074c3cd1ba60531825b2a8e1fa3296105` | No earlier readable file |
| `runtime/agent/tools/desktop_insert_text.ts` | `f53fd9f0612d726e7897f285e853af2b997bc3b3` | No earlier readable file |
| `runtime/agent/tools/inspect_window.ts` | `609c963560f4663c2069674068b18dad80382545` | `7d8e0f6` |
| `runtime/agent/tools/read_screen.ts` | `0ff15ac13b3be69e1a48a6ee868e728de1cee07b` | `7d8e0f6` |
| `runtime/browser-extension/manifest.json` | `890d17c2280dcf98a1b016a9c82d60d58c3c4bbd` | No earlier readable file |
| `runtime/browser-extension/offscreen.html` | `f7bf545fc52bd11b9511368378e422707b41c567` | No earlier readable file |
| `runtime/browser-extension/offscreen.js` | `6a35e7bf4b5dd49bdf521f6e02711330c3f28b80` | No earlier readable file |
| `runtime/browser-extension/popup.html` | `355da857989966b0bac19cbe4caef65f5108ab79` | No earlier readable file |
| `runtime/browser-extension/popup.js` | `5bac6a2ae6082dc40e5be007034886fd218d6231` | No earlier readable file |
| `runtime/browser-extension/service-worker.js` | `fa3f398cf9c5190f09aea4569b9b9003cece82a4` | No earlier readable file |
| `runtime/lib/host-access.mjs` | `0a183429f71eb9509f08cd9201500a71da8c7889` | `7d8e0f6` |
| `runtime/package-lock.json` | `986f5d3a3e76629a77e5e9f2b0c5552d0586bdc0` | `9a53881` |
| `runtime/package.json` | `8888b590075052a6b60fb7d26de7091bef1af1ee` | `9a53881` |
| `scripts/brave-tab-host.py` | `3d7812be97c522423fc452836a4eb87adfb1747d` | No earlier readable file |
| `scripts/install-brave-tab-host.sh` | `41433a4b459422ecc446d795dbbf6d5ce5e20bd9` | No earlier readable file |
| `scripts/probe_brave_accessibility.py` | `6363141ffced629bc169cb86b9f69e5432e06a8c` | No earlier readable file |
| `scripts/start-chat.sh` | `3d91bf30b39238a579f6ba8223cb3a5f111f4439` | No earlier readable file |

## Verification

- The integrity gate rejected all 39 affected paths on original main and
  passed on the recovery tree. It checks UTF-8, NUL bytes, and Python,
  JavaScript, TypeScript, shell and JSON syntax.
- Python 3.11.18 and 3.14.9 each passed all 56 tests with host tools available.
  The restricted Python 3.14 run skipped the systemd analyzer test.
- The recovered lockfile installed 25 packages. Eve 1.0.2 discovery reported
  zero errors and all six Node tests passed. The prior tests incorrectly
  expected dynamic tools at startup and an approval function on the wrapper.
  The revised tests check zero startup tools, the runtime flag and the
  required approval decision.
- A real Eve session with synthetic SQLite data returned `ready` through local
  Ollama. A separate local session requested approval for a nonexistent
  synthetic application's launch. After denial it completed with zero host
  access audit records. Earlier prompts exposed incomplete streams and a
  model-generated malformed hash. These are reliability observations.
- The GitHub workflow now gates the Python and npm jobs on source integrity
  and runs both Python versions independently. The new workflow awaits a run
  on the recovery branch after publication approval.
- `git diff --check` passed. A pattern scan of source found no common private
  key, GitHub token, AWS key or API key signatures.

## Remaining verification

The recovery worktree used temporary synthetic databases. The external brain
drive was absent. The regular migration launcher expects the verified mount
and alias `burito-local:8b`; the smoke tests used the existing alias
`burito-local`. The launcher's mountpoint check does not validate the disk UUID.
Verify the drive identity before using the private database. The previous main
worktree and user updater were preserved. The updater was inactive at audit.

Live native messaging, screen operations and KWin or Hyprland tool behavior
were outside the recovery smoke tests. The Brave installer writes an allowlist
for the supplied extension ID, while the manifest requests broad optional
HTTP and HTTPS coverage. The development runtime reported that its workflow
queue route lacks delivery authentication. Keep the dev servers on loopback.
Review browser permissions, host and origin checks, and runtime authentication
before enabling wider access. See [security boundaries](SECURITY.md).
