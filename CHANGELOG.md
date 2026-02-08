# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-07

### Changed
- **ALGORITHM_VERSION bumped to 1.1.0** — drift detection now uses structural features only
- Excluded content features (`content:*` tokens from reasoning text) from trace feature extraction for drift detection. Alignment Cards contain only structural declarations, so content tokens from reasoning diluted cosine similarity without adding alignment signal, causing false positive drift alerts on well-aligned traces. Content features remain available for text-to-text similarity via `compute_similarity()`.
- Fixed TypeScript SDK `detectDrift` to generate one alert per drift event (`==` threshold) instead of one per trace after threshold (`>=`), matching Python SDK behavior.

### Updated
- SPEC.md Section 8 — clarified that drift detection uses structural features only
- CALIBRATION.md Section 3.5 — documented rationale for excluding content features

## [0.1.0] - TBD

Initial release.

### Added
- Alignment Card schema and implementation
- AP-Trace audit log format
- Value Coherence Handshake protocol
- A2A integration extension
- MCP integration extension
- Example implementations
