# Source And Ranking Reference

## Source Policy

Use public, stable metadata sources first. Do not bypass paywalls or use restricted full text.

- PubMed: best default for biomedical journals; often includes abstracts, publication types, and MeSH-like metadata.
- Crossref: useful DOI and publication metadata fallback; abstracts are inconsistent.
- RSS and journal pages: useful for online-first completeness, but publisher formats vary. Use only configured RSS feeds or explicit user requests unless API coverage is clearly insufficient.
- Web search: use for verification, recency-sensitive claims, or when the user asks for links and source attribution.

When sources disagree, prefer DOI-level identity and the publisher page for the final title/date. Keep duplicates collapsed by DOI first, then normalized title.

## Article Inclusion

Default `/topjournal` is full journal coverage for the selected date window. Include all research articles, reviews, perspectives, editorials, and correspondence in CSV unless the user asks to restrict article types. In Markdown, distinguish article types and avoid overstating editorials or news items as primary research.

## Top Pick Ranking

Assign Top picks by balancing:

- Novelty: new question, new mechanism, new platform, unusually strong dataset, or field-changing synthesis.
- Relevance: match to user keywords or configured topics.
- Evidence strength: human cohort, randomized trial, causal perturbation, multi-omic validation, prospective validation, or robust benchmarking.
- Follow-up value: likely to influence experiments, clinical translation, methods, policy, or grant/manuscript framing.

Prefer 5-10 Top picks for weekly reports. If there are fewer than 5 strong papers, say so instead of padding.

## Reporting Caveats

Use wording such as "based on available abstract/metadata" when no full text was read. If only title metadata exists, keep the summary short and mark the evidence as limited.
