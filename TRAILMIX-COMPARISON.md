# Trailmix vs the family host

Read-only comparison, 2026-10-18. **T** = `/Users/mark/Code/Trailmix` (0.15.0, branch `gemini-transcription`, `T backend/`
10.3k lines, `frontend/` 12.5k, `helper/` Swift 3.9k, 230 tests). **F** = `/Users/mark/Code/TrailmixFamily` at
84ea14d (server 2.1k lines, web 2.1k, Swift 0.7k, 58 tests). Every claim names its file.

## 1. Where Trailmix is ahead

**AI providers and model choice** (worth adopting in part)
- T calls Gemini natively with streaming (`T llm_engine.py:320`), a half-price Batch API (`T gemini_batch.py`,
  `T batch_jobs.py`), file upload with patient 429 retries (`T transcribe_gemini.py:44-80`), and an "economy" transcript
  model (`T preflight.py:25`). It prices work (`T pricing.py:12-39`), tallies spend (`T database.py:100`), and ranks
  models 0–100, refreshed daily from a hosted JSON (`T model_ranks.py`, `T docs/model-ranks.json`).
- The pre-flight "choose which AI" sheet is `T preflight.py` + `/api/preflight` and `/api/process` (`T main.py:1257,1269`)
  + `T frontend/src/components/AIChoice.tsx`.
- F has the provider chain, fallback and `provider_down` (`F core/server/ai.py:67,172`), but Gemini goes through the
  OpenAI-compatible shim (`F ai_adapters.py:30`), with no batch, pricing, ranks, streaming or pre-flight. Its Gemini
  default `gemini-2.5-flash` (`F ai.py:49`) is stale: T's comment says it is closed to new accounts (`T settings.py:46`).
- Structured output goes the other way: F has it (`F ai_adapters.py`, `F ai_schema.py`); T has none and parses markdown
  (`T meeting_text.py:155`).
- **Adopt:** fix the Gemini default (S). Add host-level `pricing.py` plus a usage table when Traverse's inbox starts paying
  for AI (M). Defer batch, ranks and the pre-flight sheet until a second module has bulk paid work.

**Jobs and approvals** (nothing to adopt)
- T runs a meeting-row state machine (`T database.py:15-17`) on one thread (`T pipeline.py:49`), with `ready_*` approval
  parks (`T pipeline.py:204,228`) and a RAM gate with "Proceed anyway" (`T pipeline.py:113,124`). It also has five
  hand-written asyncio loops (`T main.py:64-145`).
- F's `approve=True`, `Wait`, `force`, `retry`, lanes and scheduler (`F jobs.py:30`, `F schedule.py`) already cover this.
  The only T-specific idea, never run a heavy model while recording (`T pipeline.py:99`), is a `jobs.Wait` in a port.

**Settings and secret scrubbing**
- T's settings are flat, with secrets matched only by `_api_key` (`T settings.py:83`). It adds **Lockdown**, which blocks
  every cloud call, stat and update check (`T settings.py:167-173`, `T tests/test_lockdown.py`). Its scrubber strips keys,
  names and meeting lines from public problem reports (`T feedback.py:67-151`).
- F is better structured: namespaced keys, choices, and secrets matched on `_api_key/_token/_secret` (`F settings.py:32`).
- **Adopt:** Lockdown as `core.lockdown`, gating `F ai.py:121` (`configured()`, the one choke point) (M). The scrubber's
  patterns are portable (S) once a public report path exists. `known_names()` reads meetings tables (`T feedback.py:75`),
  so it stays in a port.

**Updater, release and Dev/Beta builds** (highest value)
- T's updater has a beta channel (`T helper/.../Updater.swift:61,72`), **Go back** plus skip-version (`:42,226`), refuses to
  update mid-recording (`:239`), and honours Lockdown (`:134`). F's updater is latest-only (`F mac/.../Updater.swift:46`).
- T's CI publishes only a *pre-release*, after a smoke test of a fresh install, an update from the current release and a go
  back (`T .github/workflows/release.yml:71`, `T scripts/smoke-test.sh:1-14`). It auto-promotes after 3 days with no
  `[blocks me]` issue (`T promote-beta.yml`, `T scripts/auto-promote.sh`). F's release is manual-dispatch only, with no
  smoke test and no `--prerelease` (`F .github/workflows/release.yml:35`).
- T's commit eeb208f builds a separate "Trailmix Dev.app" (`T scripts/make-mac-app.sh`) with a Dev/Beta tag from
  `/api/health` (`T main.py:693`).
- T backs up the database once on the first start of each version, keeping 3 (`T database.py:199-230`, `T main.py:153`).
  F's backups are daily plus manual (`F backup.py:27,183`), so a GitHub auto-update migrates with no fresh copy; only
  `F install-app.sh:70` backs up first.
- **Adopt:** a backup-before-migrate on version change (S), the beta/go-back updater (M), and a pre-release-then-promote
  workflow (S–M). The smoke test is Trailmix-specific (`say`, whisper-tiny); generalizing it is M.

**Mac host and recorder**
- T's 3.9k-line app does mic and Core Audio capture, hotkeys, call reminders and a self-test (`T helper/Sources/`). It needs
  macOS 14.2 and mic/audio usage strings (`T scripts/build-app.sh:68,72-73`). F's host has none of these and targets 14.0
  (`F mac/Package.swift`, `F scripts/build-app.sh:73`). The server supervisors are the same code (`T ServerProcess.swift`,
  `F BundledServer.swift`).
- `F ARCHITECTURE.md:337` says the recorder moves "unchanged". It can't, because `mac/` and `build-app.sh` are synced shared
  files (`F scripts/sync-family:22-25`). **Adopt:** nothing. Keep it module-owned.

**Telemetry** (don't adopt yet)
- PostHog, off-switchable, with a first-run notice, rounded values and a "see what's sent" log (`T telemetry.py`,
  `T tests/test_telemetry.py`). F has none. It needs a per-app key and privacy page (`T docs/privacy.html`).

**Tests**
- T's 23 test files include Lockdown, batch, versions and update flows, plus `T scripts/smoke-test.sh` and `SelfTest.swift`.
  F has `F scripts/check-app.py` (supervision) and the style rules in `F scripts/check`, but little feature coverage.

## 2. Where the family host is ahead

- **Backups and restore:** integrity-checked, kept 14/20/5, restore refuses newer databases and undoes itself on failure
  (`F backup.py:27,97,143-178`). T has no restore path (`T database.py:209`).
- **Scheduler and lanes:** `F schedule.py`, `F jobs.py:30` (cloud 4, interactive 2).
- **Module contract, links, search, events:** `F module.py`, `F links.py`, `F search.py`, `F contracts.py`. T search is one
  FTS table for meetings (`T database.py:18`).
- **Migrations:** per-module, counted (`F db.py:111`), against T's ad-hoc `_ADDED_COLUMNS` (`T database.py:131-185`).
- **Ids:** random text ids (`F db.py:52`); T uses integers with a `uid` column (`T database.py:21,149`).
- **Export:** a module `export` hook (`F backup.py:193`). T's per-meeting `meeting.json` and Word/PDF are richer for
  meetings (`T archive.py`, `T exporter.py`).
- **Identity split:** `app.json` and `identity/` (`F config.py`), and `sync-family --check` in CI (`F scripts/check`).
- **Structured output:** `F ai_adapters.py`.

## 3. What a port would take

Sketch per `F ARCHITECTURE.md:332-345`. Chunks:
1. **Compatibility contract (S).** Keep bundle ID `local.trailmix.app` (`T build-app.sh:62`), the `Trailmix-<v>-arm64.dmg`
   + `.sha256` names (`T build-app.sh:84`, same pattern at `F build-app.sh:144`), the name "Trailmix" (data folder) and the
   `trailmix.db` filename (`F config.py` makes `<id>.db`). Port 8765 sits outside the family range (`F ARCHITECTURE.md:162-169`).
2. **Data migration (L, the risky one).** Reshape meetings (keyed by `uid`), tasks, workspaces, history, versions, usage,
   batch jobs and settings into `meetings_*` and `core_settings`, rebuild FTS, and move `audio/<id>/` to `meetings/<uid>/`
   (`T database.py:11-12,131`). It must be idempotent, take a backup first, copy audio rather than move it, and keep the
   old tables so Go back still opens.
3. **Server (L).** Split `T main.py` (1,882 lines, 102 routes), turn pipeline stages into jobs, and map action items to
   `actions.found` and the tasks module without losing ticks (`T archive.py:44`).
4. **Loops and live path (M).** The warm and live-notes loops run every 10–15s (`T main.py:99-131`), but the scheduler ticks
   every 20s (`F schedule.py:22`). Keep the audio WebSocket (`T main.py:795`) and move its id to `uid`.
5. **Web (L).** 12.5k lines onto the `@core` kit, routes `#meeting-12` to `#/meetings/<uid>` (`T App.tsx:382`), and split
   `T Settings.tsx` (2,382 lines).
6. **Mac (M–L).** Bring the recorder in with a family-level change: 14.2, plist keys, optional native features in `sync-family`.
7. **Prerequisites from §1 (M–L).** Beta/go-back updater, pre-release workflow, backup-before-migrate, smoke test.
8. **Ship (M).** Pre-release, tested as an update from the last stable, plus a go-back test.

**Risks**
- *Updates.* The installed Updater accepts a new DMG only with the same bundle ID and a valid signature
  (`T Updater.swift:322-331`), so chunk 1 is mandatory. Ad-hoc signing re-asks for mic permission after every update
  (`T Updater.swift:9`).
- *Shipping.* The synced family `release.yml` publishes straight to everyone (`F release.yml:35`). Using it would drop Trailmix's
  beta gate.
- *Go back.* It relies on additive schema changes (`T Updater.swift:225`). F's `migrate` doesn't check for a database newer than
  the app (`F db.py:111-121`).
- *Independence.* Rule 9 makes `core/`, `mac/` and the build scripts one family copy (`F ARCHITECTURE.md:83`), and `sync-family --check`
  fails on drift. Trailmix's MLX build and 14.2 minimum would have to become family-level options.
- *Work in flight.* The `gemini-transcription` branch (62 commits) would have to ship or freeze first.

## 4. Recommendation: a mix, leaning separate

1. **Keep Trailmix separate** for now. Normalizing its structure *is* the port (chunks 2–5), and it conflicts with Mark's
   "independently developed" wish, because shared code means one copy.
2. **Integrate over the local API** as PLAN chunk 10 says. `GET /api/meetings` (`T main.py:764`) omits `uid`
   (`T database.py:304-311`). Fetch each done meeting with `GET /api/meetings/{id}` (`T main.py:276,774`), which returns `uid`,
   `summary` and `tasks`, and dedupe on `uid`. A one-line addition of `uid` to the list query would remove the N+1 fetch. That is a
   change in T and was not made here. No login is needed unless `TRAILMIX_ACCESS_TOKEN` is set (`T auth.py`).
3. **Adopt into the family, in order:** backup-before-migrate (S), Gemini default (S), beta/go-back updater and pre-release
   workflow (M), Lockdown (M), pricing and usage (M, when chunk 9 spends money). Defer batch, ranks, pre-flight, telemetry and the
   recorder.
4. **Port later**, once items 3's first three are in the family and `gemini-transcription` has shipped. Then do it
   migration-first (chunk 2), and release it as a beta.
