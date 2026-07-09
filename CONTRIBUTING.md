# Contributing / 기여 안내

Thanks for helping improve this open education resource on manufacturing AI,
on-prem LLMs, RAG, and agent systems. Contributions of any size are welcome —
and every merged PR credits you as a contributor.

이 저장소는 제조 AI·온프레미스 LLM·RAG·에이전트 교육 자료입니다. 작은 기여도
환영하며, 머지된 모든 PR은 기여자로 기록됩니다.

## Ways to contribute / 기여 방법

- **Fix errors** — typos, broken links, outdated facts, wrong figures.
  Please cite a public source when correcting technical claims.
- **Translate** — improve the EN↔KO pairing of an article, or fix awkward
  phrasing in either language. (기사 영↔한 번역 개선, 어색한 문장 다듬기)
- **Add worked examples** — short, runnable snippets that illustrate a lesson
  (e.g., a chunking comparison, an embedding benchmark on Korean text).
- **Suggest topics** — open an issue describing a question the material
  doesn't answer yet. Real questions from practitioners are the best input.

## Ground rules / 원칙

1. **Public sources only.** All technical claims must be verifiable from
   published papers, talks, or vendor announcements. This project never
   speculates about any company's non-public internals.
2. Keep the existing HTML structure and styling of the page you edit.
3. One topic per pull request — small PRs merge fast.

## Build & check locally

```bash
python build_site.py     # generates dist/
python tools/validate_dist.py
```

Open an issue first if you're unsure whether a change fits — happy to discuss
in English or Korean.
