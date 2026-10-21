# TODO

Design details are in Specs.md. Every step says what to run or write; check it off when the "done when" holds.

## Decide

- [ ] Order: solver before or after the enrichers and the compiler
- [ ] Missing data (staff/TBA instructors, few ratings, no grade data): neutral score with a prior, or a small penalty
  - Size of it in 202701: GSU 1,252 of 9,882 sections have no instructor (13%), KSU 1,349 of 7,159 (19%).
- [ ] First category catalog: which 10–15 categories, each with its normalization rule
  - Instructor-style draft below (Extraction eval, step 1). Schedule-shape draft: `gaps`, `early_start`, `late_end`, `days_on_campus`, `campus_switches`, `credit_total` (rules in Specs.md).
- [ ] Defaults: only tie-breakers, or also a weak professor-quality term

## Store

Tables already exist (`db/tables.py`); nothing here needs a migration.

- [ ] 1. Write `src/registerhelper/db/store.py`: `store_sections(session, school, term, sections) -> int`
  - Delete every `SectionRow` for `(school, term)` with one `delete(...).where(...)`, then insert the new rows. Meetings and `section_instructors` go with them through `ON DELETE CASCADE` (SQLite foreign keys are on in `session.py`).
  - Instructors: load the school's `InstructorRow`s into a dict by `external_id` (Banner `bannerId`), create the missing ones, update changed names. Never delete instructors: match rows will point at them.
  - Sets → sorted lists (`tags`, `attribute_codes`, meeting `days`), `modality` → `.value`, so the same snapshot always writes the same rows.
- [ ] 2. Rule for every later table: point at sections by `(school, term, section_id)`, never `sections.id` (it changes on every re-load). Add it as one line under Storage in Specs.md.
- [ ] 3. Add `rh store <school> -t <term>` to `cli.py`: `load_raw` → `normalize_sections` → `_summary` → `store_sections` inside `get_session()`. Offline.
- [ ] 4. Run `uv run rh store gsu -t 202701` and `uv run rh store ksu -t 202701`.
- [ ] 5. Check: `sqlite3 data/registerhelper.db "select school, count(*) from sections group by school"` → gsu 9882, ksu 7159. `select school, count(*) from instructors group by school` → gsu 2220, ksu 1986.
- [ ] 6. Run step 4 again: same counts, no duplicates (re-load works). `uv run alembic check` → no changes.

## Comments for the eval set (RMP)

Samples first, like Banner. Only fetch what the eval needs: about 30 professors, not the whole school.

- [ ] 1. Find GSU's RMP school id: open GSU on ratemyprofessors.com, the id is in the URL (`/school/<id>`). Put it in `gsu.yaml` as `rmp_school_id` (README already lists it as `# later`).
- [ ] 2. Capture samples: open one GSU professor page with DevTools → Network → filter `graphql`. Save two responses to `samples/rmp/gsu/` (teacher search, ratings list), and the request bodies next to them.
- [ ] 3. Write `src/registerhelper/enrichers/rmp.py`, same split as the adapters: `fetch_*` (httpx, polite delay, raw JSON untouched) and `parse_*` (private pydantic models, offline). Develop the parser against the samples.
- [ ] 4. Fetch ratings for about 30 professors from about 10 departments (mix of high and low ratings, at least 20 ratings each). Save raw to `data/raw/rmp/gsu/` with `fetched_at`.
  - Done when: about 600+ comments on disk, parse runs offline with 0 errors.

## Extraction eval

Goal: pick the comment extraction model with numbers, not guesses. Eval data goes in `data/eval/` (gitignored, like the snapshots); code in `evals/extraction/`.

- [ ] 1. Write the category draft in `src/registerhelper/catalog.py`: one pydantic `Category` per line (`id`, `description`, `low` pole, `high` pole). Start from RMP's tags, then edit:
  - `difficulty`: easy / hard ("Tough grader")
  - `homework_load`: light / heavy ("Lots of homework")
  - `reading_load`: light / heavy ("Get ready to read", "So many papers")
  - `exam_weight`: few exams / test heavy ("Test heavy", "Graded by few things", "Beware of pop quizzes")
  - `grading_clarity`: unclear / clear ("Clear grading criteria")
  - `feedback`: unhelpful / helpful ("Gives good feedback")
  - `lecture_quality`: boring / engaging ("Amazing lectures", "Inspirational", "Hilarious")
  - `participation`: doesn't matter / matters ("Participation matters")
  - `attendance`: optional / required ("Skip class? You won't pass.")
  - `group_projects`: none / many ("Group projects")
  - `caring`: indifferent / caring ("Caring", "Respected")
  - `availability`: hard to reach / accessible ("Accessible outside class")
  - `extra_credit`: none / offered ("Extra credit")
- [ ] 2. Pick 200 comments from step 4 above into `data/eval/comments.jsonl` (`id`, `text`):
  - about 15 per department, half from low-rated professors
  - about 30 with negation or sarcasm (grep for `not`, `n't`, `lol`, `/s`)
  - about 20 that mention no category at all
  - Split: first 50 = `dev` (tune thresholds), other 150 = `test` (score only, never tune on it). Store the split in each line.
- [ ] 3. Write `evals/extraction/label.py`: shows one comment, you type `homework_load:high attendance:low` (empty = none), appends to `data/eval/gold.jsonl`, resumes where you stopped. Gold labels are category + pole only, no evidence.
- [ ] 4. Label the 50 `dev` comments by hand, with no model help. Then pre-label the 150 `test` comments with `claude-opus-5-5` and correct each one by hand.
- [ ] 5. A few days later, re-label 20 random comments without looking. If you disagree with yourself on more than about 15% of labels, the category descriptions are too vague: fix them in `catalog.py`, then fix the labels.
- [ ] 6. Write `evals/extraction/score.py <preds.jsonl>`, scores on `test`:
  - per category: mention precision / recall / F1 (category found, pole ignored)
  - pole accuracy on correctly found mentions
  - macro F1 over all (category, pole) labels: the one number to compare
  - the same on the negation/sarcasm subset
  - evidence: share of quotes that really are substrings of the comment
  - seconds per comment
- [ ] 7. Write `evals/extraction/run.py <candidate>`: one `predict(text, categories) -> list[Label]` per candidate, writes `data/eval/preds/<candidate>.jsonl`, resumes if interrupted.
  - Classifiers (rerankers, GLiClass) run per sentence; the evidence is the sentence that triggered the label.
  - Each pole becomes a statement for classifiers: `homework_load:high` → "The professor assigns a lot of homework."
- [ ] 8. Eval dependencies in their own group, CPU-only torch (no usable GPU here):
  - `uv add --group eval anthropic transformers torch gliclass gliner2`
  - `pyproject.toml`: `[[tool.uv.index]] name = "pytorch-cpu"`, `url = "https://download.pytorch.org/whl/cpu"`, `explicit = true`, and `[tool.uv.sources] torch = { index = "pytorch-cpu" }`
- [ ] 9. Run the candidates, cheapest first. Each is `uv run python evals/extraction/run.py <name>` then `score.py`:
  - [ ] `claude-opus-5-5`: structured output (JSON schema of the labels, with an evidence quote each). Needs `ANTHROPIC_API_KEY`. The ceiling.
  - [ ] `claude-haiku-5-5`: same prompt. Is the cheap hosted model close to the ceiling?
  - [ ] `knowledgator/gliclass-base-v3.0`, then `knowledgator/gliclass-large-v3.0`: `ZeroShotClassificationPipeline(..., classification_type="multi-label")`, labels = pole statements. Tune the threshold on `dev`.
  - [ ] `fastino/gliner2-large-v1`: multi-label classification with the pole statements as labels, following the model card example.
  - [ ] `Qwen/Qwen3-Reranker-0.6B`: score each (pole statement, sentence) pair with the yes/no prompt from the model card; tune the threshold on `dev`. Expect minutes on CPU.
  - [ ] `Qwen/Qwen3-Reranker-4B`: same, only if 0.6B is promising. Expect a couple of hours on CPU: run it overnight.
  - [ ] `qwen3:4b`, then `qwen3:8b` through Ollama: `ollama serve`, `ollama pull qwen3:8b`, `POST /api/chat` with `format` = the JSON schema, `think: false`, `temperature: 0`. Expect tens of seconds per comment on CPU: overnight for 150 comments.
  - [ ] `Qwen/Qwen3-Reranker-8B` on a rented GPU with 24 GB+ (RTX 4090, L4, A10: ~16 GB of weights in bf16, so a 16 GB T4 is too small). Copy `run.py`, `catalog.py` and `data/eval/comments.jsonl` to the box, run it, download `preds/`, score locally. The same box can run `qwen3:8b` and the 4B reranker in minutes instead of overnight.
- [ ] 10. Fill a results table in `evals/extraction/RESULTS.md`: candidate, macro F1, negation subset F1, evidence rate, seconds per comment.
  - Decision rule: the best local candidate wins if its macro F1 is within 0.05 of `claude-opus-5-5`. Otherwise the hosted model labels, and the next section trains a local one.

## Fine-tune

- [ ] 1. Pre-label about 2,000 more comments (not the eval ones) with the best hosted model. Spot-check 100 by hand.
- [ ] 2. Train a pair classifier: input (sentence, category description), output none / low / high. Base: `microsoft/deberta-v3-base` or `answerdotai/ModernBERT-base`, with the `transformers` Trainer. On this laptop that's hours per run; a free Kaggle or Colab T4 (16 GB is enough for a base model) makes it minutes.
- [ ] 3. Score it on the same 150 `test` comments with `score.py`, and add the row to `RESULTS.md`.
  - SetFitABSA extracts aspect *terms* (noun spans), not fixed categories, so it doesn't fit this task directly.

## Compiler eval set

Constraint types don't exist yet: write the expected output in plain words now, convert it when they do.

- [ ] 1. `evals/compiler/phrases.yaml`, about 60 entries (`text`, `expected`), 10 of each:
  - times ("nothing before 10", "done by 3 on Tuesdays")
  - days ("Fridays off", "only MWF")
  - gaps and compactness ("no more than an hour between classes")
  - campus and modality ("only Downtown", "online if it's a gen ed")
  - instructors ("avoid Smith for MATH 1111")
  - unexpressible ("a chill professor", "near a good food spot"): expected = reported or rerank
- [ ] 2. Write about 5 phrases that combine several of these at once ("MWF only, nothing before 10 unless it's online, and keep it to 15 credits").

## `llm/` layer

After the extraction eval picks a winner.

- [ ] 1. `src/registerhelper/llm/task.py`: `Task[I, O]` with pydantic `I` and `O`, `prompt_version`, `model`.
- [ ] 2. A provider protocol with `anthropic.py` and `ollama.py`, chosen by config.
- [ ] 3. Table `llm_results`: `task`, `prompt_version`, `model`, `input_hash`, `output` (JSON), `created_at`, unique on the first four. `uv run alembic revision --autogenerate -m "llm_results"`, read it, `uv run alembic upgrade head`.
- [ ] 4. `run(task, input)` returns the stored result when one exists, otherwise calls the provider, validates, stores.

## Solver

- [ ] Constraint types (the compiler's target)
- [ ] Feasibility: time conflicts, credits, mini-mester dates, sections with no times
- [ ] GSU labs tied by corequisites
- [ ] Deterministic solves: fixed seed, deterministic search, tie-break on CRN

## Adapters

- [ ] KSU campuses with no tags: KSU Center, Off Campus, City Springs, FinTech Academy (also GSU)
- [ ] GSU: 5 sections with UNKNOWN modality (no method ×4, method `10` ×1)
- [ ] KSU attributes: only available through a per-section request; only if a feature needs them

## Cleanup

- [ ] Explicit `Any` in `load_raw`, `get_platform`, `session.py`
- [ ] Fetch retries
- [ ] Tags are free-form strings
- [ ] basedpyright warnings

## Potential features

- [ ] Lexicographic priorities (Specs.md, Categories and scoring)
