# Runtime Layer

This directory is the entry point of the application execution.

## Role
- Orchestrates and bootstraps the application.
- Houses executable scripts, Command Line Interfaces (CLIs), background workers, or API route handlers (e.g. FastAPI app).
- Handles user argument parsing and presents the outputs.

## Rules
- **Dependency Limit**: Can import from any layer (`service`, `repo`, `config`, `types`) to bootstrap the workflow.
- Avoid placing core algorithm or ML logic directly in this layer; delegate all heavy lifting to the `service` layer.

## Core Modules to Implement
- `cli.py`: CLI application taking transcript files, executing segmentation and recap tasks, and formatting output for stdout/files.
