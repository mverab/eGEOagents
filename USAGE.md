# GEO harness (rank-delta)

## Files
- `geo_eval.py`: evaluation + lightweight prompt meta-optimization
- `llm_client.py`: OpenAI-compatible HTTP client (stdlib only)
- `prompts/`: prompt templates

## Environment
- `OPENAI_API_KEY`: required
- `OPENAI_BASE_URL`: optional (defaults to `https://api.openai.com/v1`)
- `RANKER_MODEL`: optional (default `gpt-4o`)
- `REWRITER_MODEL`: optional (default `gpt-4o`)
- `META_MODEL`: optional (default `gpt-4o`)

## Dataset format (JSONL)
One JSON object per line:

- `query_id` (string)
- `query` (string)
- `candidates` (array of 10 objects)
  - `id` (string)
  - `title` (string)
  - `description` (string)
- `target_id` (optional string). If missing, the script picks a random candidate.

## Evaluate

```bash
python3 geo_eval.py evaluate --dataset /absolute/path/to/dataset.jsonl
```

## Optimize (prompt meta-optimization)

```bash
python3 geo_eval.py optimize --train /absolute/path/to/train.jsonl --val /absolute/path/to/val.jsonl --iters 5
```

This overwrites `prompts/rewriter_user.txt` with the best-on-validation prompt.
