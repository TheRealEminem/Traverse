# Traverse

What's next, and who's on it. A Mac app for planning the work you're responsible for: tasks, projects, a morning
briefing (Muster), and an inbox where AI turns meetings and threads into tasks you approve. It connects to
[Plane](https://plane.so) for your team, and nothing reaches your team until you send it.

**Download:** https://therealeminem.github.io/Traverse/ (Apple silicon, macOS 14 or later). Free and open source (AGPL-3.0).

Traverse is a [Trailmix-family](TRAILMIX.md) app, a sibling of [Trailmix](https://github.com/TheRealEminem/trailmix) and
[The Lodge](https://github.com/TheRealEminem/TheLodge): the same host (server, database, settings, jobs, AI providers, the
web shell and the Mac app) with its own modules (`muster`, `tasks`, `plane`, `inbox`). Read **[ARCHITECTURE.md](ARCHITECTURE.md)**
for how it fits together, **[DESIGN.md](DESIGN.md)** for how it looks, and **[PLAN.md](PLAN.md)** for what's built and what's next.

## Try it from source

Needs Python 3.11+ and Node 18+. For AI, [Ollama](https://ollama.com) with a model, or an API key in Settings.

```bash
scripts/dev
```

Open http://localhost:5173. Run `scripts/check` before committing (tests, types, the web build, style rules and family drift).

## Releasing

Every version goes out as a beta first and becomes the release everyone gets a few days later. Installed apps look
in the repo named by `updateRepo` in `app.json`; the download page is `docs/index.html`, served by GitHub Pages from `main`.

1. Set `VERSION` (say `0.3.0`), commit it to `main` and push.
2. Start the release, either way:
   - **From GitHub, no terminal:** Actions → **Build Mac app** → Run workflow on `main` with **Release it** ticked.
   - **From a terminal:** `git tag v0.3.0 && git push origin v0.3.0`.

   `.github/workflows/release.yml` builds the app on a Mac runner, runs `scripts/smoke-test.sh` (the updater: updating,
   beta updates, going back, skipping, not updating while busy or in Lockdown) and publishes a **pre-release**: the disk
   image, its checksum (the updater checks it) and `Traverse-arm64.dmg`, the fixed-name copy the download page links to.
3. People with **Beta updates** on (Settings → Updates) get it now. `.github/workflows/promote.yml` makes it the release
   everyone gets after 3 days, unless an open issue is labelled `blocks release`. To skip the wait, tick **To everyone**
   in step 2, or run **Promote beta** from the Actions tab with the tag.

An Actions run without **Release it** is a test build: it is kept as a downloadable artifact and publishes nothing.
Day to day, `scripts/install-app.sh` builds and installs on your own Mac (GitHub's Mac runners cost ten times its Linux ones).
Releasing is a person's call; automation shouldn't press the button.

## Licence

[AGPL-3.0](LICENSE), the same as Trailmix and The Lodge.
