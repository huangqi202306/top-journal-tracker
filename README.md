# top-journal-tracker

`top-journal-tracker` is a Codex skill for tracking recent frontier papers from top journals. It is designed for biomedical and life-science literature monitoring, with a `/topjournal` trigger, public metadata collection, Chinese Markdown digests, and CSV exports.

It collects public metadata from PubMed, Crossref, and optional RSS feeds. It does not bypass paywalls and does not require API keys.

## What It Does

- Tracks recent articles from top journals such as Nature Medicine, Nature, Science, Cell, NEJM, The Lancet, and JAMA.
- Supports focused requests such as `Nature Medicine AI 最近30天`.
- Generates a Chinese Markdown digest with Top picks and journal-grouped coverage.
- Generates a CSV table for filtering, ranking, and long-term tracking.
- Uses public article metadata and abstracts by default.
- Includes a configurable journal/topic list in `config/journals.yaml`.

## Install

### Option 1: Install With Git

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/huangqi202306/top-journal-tracker.git ~/.codex/skills/top-journal-tracker
```

Restart or refresh Codex so it reloads the skill metadata.

### Option 2: Install With Codex Skill Installer

If your Codex installation includes the system skill installer, run:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo huangqi202306/top-journal-tracker \
  --path . \
  --name top-journal-tracker
```

Restart or refresh Codex after installation.

## Verify Installation

```bash
ls ~/.codex/skills/top-journal-tracker
head ~/.codex/skills/top-journal-tracker/SKILL.md
```

You should see `SKILL.md`, `config/`, `scripts/`, `references/`, and `agents/`.

## Usage

In Codex, type:

```text
/topjournal
```

Examples:

```text
/topjournal Nature Medicine AI 最近30天
/topjournal Nature Medicine 最近14天 只看肿瘤免疫
/topjournal weekly
/topjournal deep Nature Biotechnology gene editing
```

You can also explicitly mention the skill:

```text
$top-journal-tracker Nature Medicine AI 最近30天
```

Default behavior:

- Tracks the last 7 days.
- Uses the default biomedical/life-science top-journal list.
- Produces a Chinese Markdown digest and CSV table.
- Keeps full journal coverage in CSV and separately ranks Top picks.
- Treats script output as a metadata draft; Codex should add analytical summaries before user-facing delivery.

## Run The Script Directly

```bash
cd ~/.codex/skills/top-journal-tracker
python3 scripts/journal_frontier_tracker.py --days 7 --output reports
```

Focused examples:

```bash
python3 scripts/journal_frontier_tracker.py \
  --days 30 \
  --journals "Nature Medicine" \
  --keywords "AI medicine,artificial intelligence,machine learning,large language model" \
  --output reports
```

```bash
python3 scripts/journal_frontier_tracker.py \
  --days 14 \
  --journals "Nature Medicine,Cell" \
  --keywords "tumor immunology" \
  --output reports
```

The script uses only Python standard library modules.

## Output

The script writes:

```text
reports/YYYY-MM-DD-journal-frontier-digest.md
reports/YYYY-MM-DD-journal-frontier-digest.csv
```

CSV fields include:

```text
date, journal, title, doi, url, article_type, abstract, source,
relevance_score, novelty_score, top_pick, reason
```

## Customize

Edit:

```text
config/journals.yaml
```

You can change:

- default journals
- default time window
- topic include/exclude terms
- Top pick limit
- optional RSS feeds

## Update

```bash
cd ~/.codex/skills/top-journal-tracker
git pull
```

Restart or refresh Codex after updating.

## Troubleshooting

- If Codex does not trigger the skill, restart Codex and try `/topjournal` again.
- If Crossref returns `429 Too Many Requests`, rerun later or rely on PubMed/Nature pages for verification.
- If the report includes loosely related articles, ask Codex to produce a curated version using stricter topic filtering.
- If you need latest completeness, ask Codex to verify with journal pages or web search and cite sources.

## Notes

- The skill does not bypass paywalls.
- Default summaries are based on public metadata and abstracts.
- For clinical or high-stakes interpretation, verify the article page and read the full paper where available.
