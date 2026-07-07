# top-journal-tracker

Codex skill for tracking recent frontier papers from top journals with the `/topjournal` trigger. It collects public metadata from PubMed, Crossref, and optional RSS feeds, then generates Chinese Markdown digests and CSV tables.

## Install

Copy this folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R top-journal-tracker ~/.codex/skills/top-journal-tracker
```

Restart or refresh Codex so the skill list reloads.

## Usage

```text
/topjournal
```

Default behavior:

- Tracks the last 7 days.
- Uses the default biomedical/life-science top-journal list.
- Produces a Chinese Markdown digest and CSV table.
- Keeps full journal coverage and separately ranks Top picks.

Examples:

```text
/topjournal Nature Medicine 最近14天 只看肿瘤免疫
/topjournal weekly
/topjournal deep Nature Biotechnology gene editing
```

## Customize

Edit `config/journals.yaml` to change:

- default journals
- default time window
- topic include/exclude terms
- Top pick limit
- optional RSS feeds

## Run Script Directly

```bash
cd ~/.codex/skills/top-journal-tracker
python3 scripts/journal_frontier_tracker.py --days 7 --output reports
```

The script uses only Python standard library modules.

## Notes

- The skill does not bypass paywalls.
- Default summaries are based on public metadata and abstracts.
- For current completeness checks, ask Codex to verify with web or academic search sources.
