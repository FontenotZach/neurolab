# Neurolab (name to change)

**Deterministic Research Data Engine**

- **Author:** Zach Fontenot  
- **Status:** Early Development (v0.1)  
- **License:** Apache 2.0

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Vision & Motivation](#2-vision--motivation)
3. [Design Philosophy](#3-design-philosophy)
4. [Project Scope](#4-project-scope)
5. [System Architecture](#5-system-architecture)
6. [Core Components](#6-core-components)
7. [Data Model](#7-data-model)
8. [Deterministic Data Principles](#8-deterministic-data-principles)
9. [Reproducibility Model](#9-reproducibility-model)
10. [CLI Interface](#10-cli-interface)
11. [Development Environment](#11-development-environment)
12. [Project Structure](#12-project-structure)
13. [Testing Strategy](#13-testing-strategy)
14. [Plugin & Extension System](#14-plugin--extension-system)
15. [Roadmap](#15-roadmap)
16. [Lifecycle Diagrams](#16-lifecycle-diagrams)
17. [Development Principles & Contributing](#17-development-principles--contributing)
18. [Current Status](#18-current-status)

---

## 1. Project Overview

Neurolab is a **deterministic data processing engine** designed for scientific research workflows. The system provides infrastructure for:

- **Structured dataset ingestion**
- **Dataset discovery and artifact tracking**
- **Deterministic dataset representation**
- **Reproducible analysis pipelines**
- **Automated dataset comparison**
- **AI-assisted insight discovery** (future)

The value chain:

```
raw datasets → artifacts → manifests → analysis pipelines → insights
```

The goal is to provide **research infrastructure**, not a single-purpose analysis application. By focusing on deterministic identity and manifest-based versioning first, Neurolab creates a stable foundation that any downstream analysis (statistical, ML, or AI) can rely on without sacrificing reproducibility.

---

## 2. Vision & Motivation

### Vision

Modern research workflows often suffer from:

- Fragmented scripts  
- Inconsistent dataset handling  
- Poor reproducibility  
- Undocumented preprocessing  
- Difficulty identifying patterns in large datasets  

Neurolab addresses these by providing a deterministic research data engine that lets researchers:

- Ingest complex datasets  
- Standardize dataset structure  
- Automatically track dataset changes  
- Run consistent analytical pipelines  
- Surface high-value insights from large data spaces  

The aim is to **reduce the friction between raw data and scientific insight**.

### Motivation

Labs often accumulate hundreds or thousands of small scripts to process datasets. Common problems:

- Tightly coupled pipelines  
- Undocumented transformations  
- Inconsistent analysis results  
- Inability to reproduce prior experiments  
- Manual data inspection  

Neurolab replaces fragile research scripts with a structured engine that provides:

- **Deterministic dataset identity**  
- **Automated dataset discovery**  
- **Standardized metadata tracking**  
- **Reproducible pipelines**  
- **Modular extension points**  

The goal is not to replace scientific reasoning, but to build **infrastructure that supports it**.

---

## 3. Design Philosophy

### Determinism

Given identical inputs, the system must produce identical outputs. This enables:

- Reproducible science  
- Reliable debugging  
- Dataset identity verification  
- Stable research pipelines  

Enforced through **content hashing**, **stable artifact ordering**, and **immutable manifests**.

### Reproducibility

A dataset processed through Neurolab should always be reconstructable. Researchers should be able to say: *“This analysis was performed using manifest X.”* Anyone with the same source data can regenerate that manifest and reproduce results.

### Modularity

Neurolab is built from loosely coupled modules: collectors, adapters, processing pipelines, storage backends, analysis modules. Each component has a clear responsibility and interface; modules should be replaceable without affecting others.

### Transparency

Every result must be traceable back to raw data, transformations applied, pipeline configuration, and dataset manifest—avoiding “black box” research workflows.

### Simplicity Over Cleverness

The project favors **clear code**, **explicit logic**, and **understandable architecture** over complex abstractions. Future researchers should be able to understand the system quickly.

---

## 4. Project Scope

Neurolab focuses on building a **deterministic data engine**. For clarity:

- **Neurolab is not** a ML project.  
- **Neurolab is not** the analysis pipeline itself.  
- **Neurolab is** infrastructure supporting those workflows.  

Domain-agnostic design allows the same engine to support many scientific domains; analysis and AI layers are built on top of deterministic manifests.

---

## 5. System Architecture

Layered architecture:

```
User
  │
  ▼
CLI Interface
  │
  ▼
Orchestrator
  │
  ▼
Collectors
  │
  ▼
Models
  │
  ▼
Manifest Store
  │
  ▼
Future Processing / Analysis Layers
```

Each layer has a distinct responsibility.

---

## 6. Core Components

### CLI Layer

- **Role:** Primary user interface.  
- **Responsibilities:** Command routing, input validation, formatted output.  
- **Stack:** Typer, Rich.  
- **Example:** `neurolab collect data/`

### Orchestrator

- **Role:** Coordinates ingestion workflows.  
- **Example operation:** `collect_source(DataSourceSpec)` — select collector, coordinate artifact discovery, assemble manifests.

### Collectors

- **Role:** Discover artifacts in data sources.  
- **Current:** `FilesystemCollector` (directory traversal, metadata extraction, hashing, artifact creation).  
- **Properties:** Deterministic, stateless, modular.  
- **Future options:** SQLiteCollector, PostgresCollector, S3Collector, APICollector.

### Models

- **Role:** Data contracts used across all layers.  
- **Key types:** `DataSourceSpec`, `Artifact`, `Manifest`.

### Manifest Store

- **Role:** Persist manifests.  
- **Current:** `FileManifestStore` at `~/.neurolab/data/manifests/`.  
- **Future:** SQLite, PostgreSQL, cloud storage.

---

## 7. Data Model

### DataSourceSpec

Describes where data originates, e.g.:

```python
DataSourceSpec(
    uri="data/",
    recursive=True,
    include_globs=["**/*.csv"]
)
```

### Artifact

Represents an atomic data unit. Fields include: `artifact_id`, `relative_path`, `size_bytes`, `mtime`, `content_hash`, `media_type`. Artifacts are the smallest units Neurolab tracks.

### Manifest

Represents dataset state at collection time: `manifest_id`, `source`, `created_at`, `artifacts`, `warnings`. Manifests must be **immutable**, **deterministic**, **serializable**, and **comparable**.

---

## 8. Deterministic Data Principles

- **Content hashing:** Each artifact stores `SHA256(file_contents)` for reliable change detection, reproducible comparison, and caching.  
- **Stable ordering:** Artifacts are ordered deterministically to avoid nondeterministic manifests.  
- **Immutable manifests:** Manifests are snapshots; they cannot be modified after creation.

---

## 9. Reproducibility Model

Researchers can share:

- Dataset manifest  
- Pipeline configuration  
- Analysis scripts  

So that others can reproduce results. Deterministic manifests are the anchor for this workflow.

---

## 10. CLI Interface

| Command | Description |
|--------|-------------|
| `neurolab collect <path>` | Collect dataset from path |
| `neurolab history` | Show manifest history |
| `neurolab show <manifest_id>` | Inspect a manifest |
| `neurolab diff <manifest1> <manifest2>` | Compare two manifests |
| `neurolab delete <manifest_id>` | Delete a manifest |
| `neurolab clear` | Clear history |

---

## 11. Development Environment

- **Python:** 3.11+  
- **CLI / UX:** Typer, Rich  
- **Testing:** pytest  
- **Linting / formatting:** Ruff  
- **Package management:** uv  
- **Hooks:** pre-commit  

**Primary platforms:** Windows 11, WSL (Ubuntu), VS Code.

| Task | Command |
|------|--------|
| Install dependencies | `uv sync` |
| Run all tests | `pytest` |
| Run by layer | `pytest -m data_interface`, `pytest -m storage` |
| Run unit only | `pytest -m unit` |
| Lint | `ruff check .` |
| Format | `ruff format .` |

---

## 12. Project Structure

Current layout (src layout to avoid import issues):

```
neurolab/
├── src/neurolab/
│   ├── data_interface/   # collectors, hashing, models, orchestrator
│   ├── storage/          # manifest_store
│   └── interfaces/       # cli.py
├── tests/                # organized by layer, then unit vs integration
│   ├── data_interface/   # unit/ and integration/ for this layer
│   ├── storage/          # unit/ (manifest store)
│   ├── interfaces/       # placeholder for CLI tests
│   └── conftest.py
├── docs/
├── pyproject.toml
└── README.md
```

Models live in `data_interface/models.py`; the CLI is in `interfaces/cli.py`.

---

## 13. Testing Strategy

- **Framework:** pytest.  
- **Layout:** Tests are organized by **layer** (mirroring `src/neurolab/`): `tests/data_interface/`, `tests/storage/`, `tests/interfaces/`. Within each layer, `unit/` and `integration/` subdirs separate fast isolated tests from tests that use the filesystem or external data.  
- **Markers:** Use `-m` to run tests by layer or by type:
  - **By layer:** `pytest -m data_interface`, `pytest -m storage`, `pytest -m interfaces`
  - **By type:** `pytest -m unit`, `pytest -m integration`
  - **All:** `pytest` or `pytest tests/`
- **Unit tests:** Individual modules (models, hashing, collectors, manifest store).  
- **Integration tests:** Orchestrator + collector pipelines, manifest_id stability (e.g. against `test_data/`).  

Tests should be **deterministic**, **isolated**, and **fast**. Filesystem tests use temporary directories (`tmp_path`).

---

## 14. Plugin & Extension System

Planned extension interface: `analyze(dataset) -> result_object`. Plugins may compute custom metrics, perform domain-specific analysis, add derived features, or generate reports. They should **not** modify core system behavior; they operate on deterministic datasets produced by the engine.

---

## 15. Roadmap

### Data Processing & Analysis (after ingestion is stable)

- Statistical summaries, correlation analysis, regression, anomaly detection, feature extraction — all on structured datasets derived from manifests.

### AI Insight Layer (future)

- Pattern discovery, anomaly detection, hypothesis suggestion, experiment comparison, trend detection. AI operates only on deterministic datasets to preserve reproducibility.

### Planned major features

| Area | Plans |
|------|--------|
| **Adapter system** | Parsers for CSV, JSON, Parquet, SQL tables |
| **Database manifest storage** | SQLite, PostgreSQL backends |
| **Dataset versioning** | Full dataset lineage tracking |
| **Analysis framework** | Automated statistical workflows |
| **AI insight engine** | Automated discovery of meaningful patterns |

### Long-term vision

Neurolab may evolve into: research data versioning, deterministic pipeline framework, automated analysis infrastructure, and AI-assisted research platform—all while staying **small enough to understand** and **powerful enough to matter**.

---

## 16. Lifecycle Diagrams

### Manifest Lifecycle

```
Dataset → Artifact Discovery → Manifest Generation → Manifest Storage
    → Manifest Comparison → Downstream Analysis
```

Manifests are the dataset versioning layer.

### Artifact Lifecycle

```
Data Source → Collector → Artifact Creation → Hash Computation → Manifest Assembly
```

Artifacts are the atomic data units.

---

## 17. Development Principles & Contributing

### Development principles

- Deterministic behavior  
- Modular architecture  
- Explicit interfaces  
- Strict testing  
- Readable code, minimal hidden logic  

Automation: linting, formatting, and testing before commit (e.g. via pre-commit).

### Contributing philosophy

Neurolab is intended to become an open-source research infrastructure project. Goals: transparency, reproducible science, community collaboration, long-term maintainability. Contributions should prioritize **clarity**, **determinism**, and **modularity**.

---

## 18. Current Status

**Implemented:**

- CLI interface  
- Filesystem collector  
- Artifact discovery  
- Content hashing  
- Manifest generation  
- Manifest storage  
- Dataset diff engine  
- Testing framework  

**In progress:**

- Adapter layer  
- Improved diff logic  
- Expanded collectors  

---

*Guiding principle: Neurolab aims to be **small enough to understand**, **powerful enough to matter**—prioritizing reproducibility, determinism, extensibility, and scientific usefulness.*
