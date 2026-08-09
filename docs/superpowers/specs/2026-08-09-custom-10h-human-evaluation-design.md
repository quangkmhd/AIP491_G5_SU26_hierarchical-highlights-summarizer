# Custom 10h Human Evaluation HTML Design

## Goal

Provide one offline HTML file for manually reviewing and scoring all 246 topics from `custom-10h-full-v2`, without exposing prior automated scores or requiring a server.

## Data and Privacy

The generator reads `topic_outputs.jsonl` only. It embeds the topic transcript, BARTpho title, and every ViT5 source chunk/summary into the generated HTML. It never reads credential files, prior score files, or network resources. Embedded JSON is escaped so transcript text cannot terminate the script element.

## Review Workflow

The page has a searchable/filterable topic navigator, progress statistics, previous/next controls, and a main review area. Each topic shows the complete transcript, title, and source-summary pairs. The reviewer assigns 0–5 scores to every chunk for faithfulness, coverage, and conciseness; to the title for representativeness, specificity, and faithfulness; and to the whole topic for coverage, consistency, and usefulness. Four issue flags, per-chunk notes, an overall note, completion state, and review-needed state are retained.

The total is recomputed in the browser using the same 60/15/25 rubric as the AI evaluator. Chunk dimensions use utterance-count weighting. Issue flags are diagnostic and do not directly change the numerical score.

## Persistence and Portability

Every edit is saved to `localStorage` under a run-specific versioned key. The page supports exporting all ratings as JSON, importing a prior export after schema/run validation, and clearing saved ratings only after explicit confirmation. No data is transmitted over the network.

## Output

The reusable Python generator lives under the Custom_10h evaluator package. A small script invokes it. The generated artifact is stored beside the v2 run as `human_evaluation.html` and is ignored like the other evaluation results.

## Verification

Python tests verify topic loading, AI-judgment exclusion, safe embedding, required offline controls, and generation from a fixture. Browser scoring and persistence logic are exposed as pure JavaScript functions and smoke-tested in an available headless browser when the environment provides one.
