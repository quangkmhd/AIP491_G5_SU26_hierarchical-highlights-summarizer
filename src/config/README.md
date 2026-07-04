# Config Layer

This directory handles configuration settings and environment setup.

## Role
- Contains settings classes, environment variable parsers, and default hyperparameters.
- Defines static values like model names, checkpoint paths, and algorithm thresholds (e.g., the `alpha` value for TextTiling).

## Rules
- **Dependency Limit**: Can only import from the `types` layer.
- MUST NOT import from `repo`, `service`, or `runtime`.
- Keep environment-specific settings separated (e.g., development, testing, production).
