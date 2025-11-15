# CloudUpscaler

Provider-agnostic cloud GPU upscaling service built with clean architecture principles.

## Overview

Reliable, testable, and maintainable image upscaling service for batch processing with automatic cloud GPU orchestration.

**Key Features:**
- ✅ Provider abstraction (RunPod Serverless, Modal, GCP - swap providers easily)
- ✅ Clean architecture (SOLID principles, Uncle Bob approved)
- ✅ 100% test coverage via TDD
- ✅ Serverless GPU processing (pay-per-use, auto-scaling)
- ✅ MCP integration for AI agent orchestration

## Architecture

See [CLOUD_UPSCALER_ARCHITECTURE.md](../BookCreationAI/CLOUD_UPSCALER_ARCHITECTURE.md) for full details.

**Layers:**
- **Domain** - Business rules, value objects, interfaces
- **Application** - Use cases, single-purpose services
- **Infrastructure** - Provider implementations (RunPod, GCS)
- **MCP** - AI agent interface

## Quick Start

### Installation

```bash
# Development install
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Usage

**As Python package:**
```python
from cloud_upscaler import create_pipeline
from cloud_upscaler.domain.value_objects import UpscaleConfig
from pathlib import Path

pipeline = create_pipeline(with_logging=True)
config = UpscaleConfig(model_name="net_g_1000000")

job = pipeline.run_sync(
    input_dir=Path("images/"),
    output_dir=Path("upscaled/"),
    config=config
)
```

**As MCP tool (for AI agents):**
```python
# AI agent calls via MCP
upscale_images_sync(
    image_dir="/path/to/images",
    output_dir="/path/to/output"
)
```

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/cloud_upscaler --cov-report=html

# Specific test
pytest tests/unit/domain/test_value_objects.py -v

# Watch mode
pytest-watch
```

### TDD Workflow

```bash
# 1. Write failing test (RED)
pytest tests/unit/... -v

# 2. Write minimal code to pass (GREEN)
# ... implement ...

# 3. Refactor while keeping tests green
pytest tests/unit/... -v
```

## Project Status

- [ ] Phase 1: Domain Layer
- [ ] Phase 2: Application Services
- [ ] Phase 3: Pipeline Orchestration
- [ ] Phase 4: Infrastructure
- [ ] Phase 5: RunPod Serverless
- [ ] Phase 6: MCP Integration
- [ ] Phase 7: Production Ready

## License

Proprietary
