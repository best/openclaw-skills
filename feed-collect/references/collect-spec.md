# collect-spec

## Data Flow

`feedctl collect` performs:

1. Prepare feed repository and clean generated artifacts only.
2. Validate `data/candidates.json` and migrate/validate `data/seen.json`.
3. Fetch unread Miniflux entries with pagination.
4. Fetch supplemental HN and GitHub Trending items best-effort.
5. Normalize URLs and dedupe against `seen.entries` and current candidates.
6. Append new candidates to `data/candidates.json`.
7. Update `data/seen.json` for newly appended candidates and prune entries older than 30 days.
8. Commit/push only `data/candidates.json` and `data/seen.json` when requested.
9. Mark processed Miniflux entries as read only after local writes and requested git operations succeed.
10. Print structured JSON summary.

## Candidate Schema

```json
{
  "title": "Article title",
  "url": "https://example.com/article",
  "source": "OpenAI News",
  "sourceType": "openai-blog",
  "category": "AI Labs",
  "pubDatetime": "2026-03-24T10:00:00Z",
  "snippet": "Plain text summary or excerpt",
  "collectedAt": "2026-03-24T09:30:00+08:00"
}
```

## Source Type Mapping

- Anthropic → `anthropic-blog`
- OpenAI → `openai-blog`
- DeepMind → `deepmind-blog`
- Meta AI → `meta-ai-blog`
- Google AI / Google Research → `google-ai-blog`
- Microsoft → `microsoft-research`
- TechCrunch → `techcrunch`
- The Verge → `the-verge`
- Wired → `wired`
- Ars Technica → `ars-technica`
- VentureBeat → `venturebeat`
- MIT Technology Review → `mit-tech-review`
- arXiv → `arxiv`
- 36kr / 36氪 → `36kr`
- AIbase / AI日报 → `aibase`
- 虎嗅 → `huxiu`
- 少数派 → `sspai`
- Hugging Face → `huggingface-blog`
- PyTorch → `pytorch-blog`
- GitHub Blog → `github-blog`
- Simon Willison → `simon-willison`
- Lilian Weng / Lil'Log → `lilian-weng`
- Hacker News → `hacker-news`
- GitHub Trending → `github-trending`
- Other → `other`

## URL Normalization

- Remove fragment identifiers.
- Drop tracking params beginning with `utm_` plus common `fbclid`, `gclid`, `mc_cid`, `mc_eid`.
- Normalize arXiv PDF/export URLs to `https://arxiv.org/abs/<id>`.
- Strip arXiv version suffixes like `v2` for dedupe.

## Failure Rules

- Never fabricate candidates when a source is empty.
- Never replace Miniflux failures with web search.
- Supplemental HN/GitHub failures are warnings, not fatal.
- Commit only `data/candidates.json` and `data/seen.json`.
