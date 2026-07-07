---
name: top-journal-tracker
description: Track, monitor, and summarize recent papers from top journals. Use when the user types /topjournal, asks for top-journal frontier tracking, weekly journal digests, Nature/Science/Cell/NEJM/Lancet/JAMA paper monitoring, biomedical frontier article summaries, recent issue or online-first tracking, Markdown/CSV journal reports, or customized top-journal paper filters by journal, topic, date window, or summary depth.
---

# Top Journal Tracker

## Overview

Use this skill to generate Chinese frontier digests for recent top-journal papers. Prefer the bundled script for repeatable metadata collection, then use Codex judgment to summarize, rank, and contextualize the results.

Default behavior for `/topjournal`:

- Track the last 7 days.
- Use the default life-science and medical top-journal set in `config/journals.yaml`.
- Collect all matching recent articles into CSV.
- Produce a Chinese Markdown digest with Top picks and journal-grouped full coverage.
- Summarize from title, abstract, DOI, journal, publication date, and source metadata unless the user explicitly asks for full-text analysis.

## Workflow

1. Parse the user's `/topjournal` request.
   - `weekly`: use the default 7-day window and avoid already-seen articles.
   - Journal names after `/topjournal`: restrict to those journals.
   - Time phrases such as `最近14天`, `last 30 days`, or `本月`: pass the matching day window.
   - Topic phrases such as `肿瘤免疫`, `gene editing`, or `AI medicine`: pass them as keywords and emphasize them during ranking.
   - `deep`: keep collection broad, but expand the Markdown card for the most relevant papers.

2. Run the script from the skill directory:

   ```bash
   python3 scripts/journal_frontier_tracker.py --days 7 --output reports
   ```

   Useful variants:

   ```bash
   python3 scripts/journal_frontier_tracker.py --days 14 --journals "Nature Medicine,Cell" --keywords "tumor immunology"
   python3 scripts/journal_frontier_tracker.py --days 7 --weekly
   python3 scripts/journal_frontier_tracker.py --days 30 --include-seen
   ```

3. Read the generated Markdown and CSV under `reports/`.

4. Improve the report when needed:
   - Always turn user-facing Top picks and requested paper cards into Chinese analytical summaries; treat the script's Markdown as a metadata draft.
   - Add concise Chinese interpretation, field context, and likely follow-up value.
   - Mark uncertainty when only metadata is available.
   - If the user asks for current completeness or article verification, browse or use academic search tools and cite sources.
   - Do not imply full-text reading unless a full text, abstract, or accessible PDF was actually reviewed.

5. If the user asks to customize defaults, update `config/journals.yaml` or explain the exact edit. Keep `/topjournal` as the main trigger.

## Output Standard

Markdown reports should contain:

- `本期概览`: date window, source count, included article count, source limitations.
- `Top picks`: ranked papers with why they matter.
- `按期刊分组`: all collected articles, including non-Top-pick papers.
- Per-paper card: title, journal/date, DOI or URL, one-sentence conclusion, method, key finding, novelty, limitation, follow-up value.
- `检索说明`: APIs/sources used and any failures.

CSV rows should preserve machine-readable metadata for later filtering:

`date`, `journal`, `title`, `doi`, `url`, `article_type`, `abstract`, `source`, `relevance_score`, `novelty_score`, `top_pick`, `reason`

## Source And Ranking Rules

Read `references/source-and-ranking.md` when changing source priority, ranking criteria, or reporting caveats.

Default source priority:

1. PubMed for biomedical journals and abstracts.
2. Crossref for DOI metadata and non-PubMed coverage.
3. RSS or journal pages when configured or when the user asks for online-first completeness.
4. Web search only when the user asks for the latest verification or when API coverage looks incomplete.

Default ranking:

- Keep full journal coverage in CSV.
- Select Top picks by novelty, topic relevance, method strength, and translational/scientific importance.
- Do not rank only by journal prestige.
