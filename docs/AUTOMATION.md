# Automation setup

This repo is the GitHub profile for [sosadtsia](https://github.com/sosadtsia). `README.md` is the profile page. Two GitHub Actions workflows keep it current. Neither workflow is started from a shell script in the repo.

## Profile cards

`.github/workflows/update-profile.yaml` replaces the old live stats widgets. Those widgets loaded images from third-party hosts. This workflow writes PNGs into `assets/` and points `README.md` at those files.

| File | Card |
| --- | --- |
| `assets/stats.png` | Public stars, forks, repos, followers, commits in the last year |
| `assets/languages.png` | Top languages by bytes, forks excluded |
| `assets/streak.png` | Current streak, longest streak, contributions in the last year |
| `assets/pin-<repo>.png` | One card per featured repo |

### Schedule

- Daily at 06:15 UTC (`15 6 * * *`).
- Manual run from the Actions tab, or:

```fish
gh workflow run "Update profile cards" --repo sosadtsia/sosadtsia
```

The job uses `ubuntu-latest`, Python 3.15, and `contents: write`. Actions are pinned:

- `actions/checkout` `11d5960a326750d5838078e36cf38b85af677262` (v4.4.0)
- `actions/setup-python` `a26af69be951a213d495a4c3e4e4022e16d87065` (v5.6.0)

Steps: install `requirements.txt` (Pillow), run `python -m unittest discover -s tests -v`, then `python -m profile`. If `README.md` or `assets/` changed, the job commits as `github-actions[bot]` with message `chore(profile): refresh static cards` and pushes to the branch it checked out. A run with the same numbers does not create a commit. A push from `GITHUB_TOKEN` does not start this workflow again.

`GITHUB_LOGIN` is `sosadtsia`. `FEATURED_REPOS` is `awake,github-manager-cli`. The token is `github.token`. Counts are public. Language totals skip forks.

### What the renderer edits

`python -m profile` reads the GitHub API, draws the PNGs, and replaces only the marked blocks in `README.md`:

```markdown
<!-- profile:projects -->
<!-- /profile:projects -->

<!-- profile:stats -->
<!-- /profile:stats -->
```

Image URLs include `?v=` plus the first 12 hex characters of the PNG sha256. The query changes when the image changes, so GitHub's image cache picks up the new file. Pin cards whose repo left `FEATURED_REPOS` are deleted.

Leave the marker comments in place. Text outside the markers is left as it is. Skill icons, social icons, and the Buy Me a Coffee button are still remote images and are not part of this job.

### Run it locally

Use Python 3.15. `gh` must already be logged in, or set `GH_TOKEN`.

```fish
cd /Users/svosadtsia/z_team/projects/sosadtsia
python3.15 -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m profile
```

Optional environment variables:

| Variable | Default |
| --- | --- |
| `GITHUB_LOGIN` | `sosadtsia` |
| `FEATURED_REPOS` | `awake,github-manager-cli` |
| `GH_TOKEN` or `GITHUB_TOKEN` | `gh auth token` when unset |
| `PROFILE_ASSETS_DIR` | `assets` |
| `PROFILE_README` | `README.md` |

Repo names in `FEATURED_REPOS` must match `[A-Za-z0-9._-]+`.

## Renovate

`.github/workflows/call-ci-renovate.yaml` calls the reusable workflow `sosadtsia/workflow-templates/.github/workflows/ci-renovate.yaml` on `main`. Config is `.github/renovate.json5`, which extends `github>sosadtsia/renovate-config`.

Schedule is 04:30 and 06:30 UTC (`30 4,6 * * *`): one run opens update pull requests, the later run follows up. `workflow_dispatch` accepts `logLevel` (default `info`) and `overrideSchedule` (`true` clears Renovate's schedule for that run).

Repository secrets required by the reusable workflow:

- `RENOVATE_APP_ID`
- `RENOVATE_PRIVATE_KEY`

The job permissions are `contents: write`, `issues: write`, and `pull-requests: write`.
