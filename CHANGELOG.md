# Changelog

All notable changes to Eagle Eval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Comprehensive `docs/` folder with world-class, focused tutorials:
  - Getting Started (agent-first path)
  - North Star + Resolution Policy (the highest-leverage concept)
  - Platform-specific guides for Grok Build, Claude Code, and Codex
  - Detailed Multi-Agent & Sequential Workflows with full concrete example for orchestrators + async workers
- Major DX improvements for coding-agent driven workflows (the intended primary usage mode).
- Significantly better error messages and post-`init` guidance.

### Changed
- `init --minimal` now generates much smarter, agent-friendly starter configs with excellent inline guidance.
- `doctor` now gently promotes custom scorers at the right moment in the journey.
- Improved several key error messages with actionable next steps and doc links.
- Bumped to 0.2.0 as a meaningful DX and documentation release.

### Changed
- Default output is now strongly goal-oriented rather than generic metric-first.
- `run` command now supports `--target` for running specific flows in complex agents.

### Fixed
- Various improvements to language consistency, slot coverage, and next-action matching logic in goal evaluators.

---

## [0.1.0] - 2025-05

Initial private release of Eagle Eval.

### Core Features
- Generate realistic multilingual test conversations using Gemini (default), OpenAI, or Claude.
- Quality gate with automated checks + LLM review (`naturalness`, `topic_coverage`, `difficulty_match`, `language_quality`).
- Run real agent code via a minimal `run_conversation(messages, language, prompt_versions=None)` contract.
- Local and Langfuse result destinations.
- Deterministic + model-based evaluators.
- Prompt version comparison (`compare`).
- Support for custom domain scorers.

### Documentation & Integration
- `init --minimal` for coding-agent-driven setup.
- AGENTS.md + CLAUDE.md + skill templates for Codex and Claude Code.
- Full SDK-neutral examples (Google ADK, OpenAI Agents SDK, Claude Code SDK, Anthropic, rule-based).

---

[Unreleased]: https://github.com/YOUR_ORG/eagle-eval/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YOUR_ORG/eagle-eval/releases/tag/v0.1.0