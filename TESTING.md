# CloudUpscaler Testing Guide

This guide covers all testing scenarios for CloudUpscaler.

## Quick Start - Test CLI

The simplest way to test the system is using the CLI:

### 1. Local Mode (No Cloud Required)

Test the library in simulation mode without any cloud services:

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
source venv/bin/activate

# Create test images
python -c "
from pathlib import Path
from PIL import Image

test_input = Path('test_images_input')
test_input.mkdir(exist_ok=True)

for i, color in enumerate(['red', 'green', 'blue']):
    img = Image.new('RGB', (200, 200), color=color)
    img.save(test_input / f'test_{color}.png')
"

# Run CLI in local mode
python test_cli.py test_images_input/ test_images_output/

# Check output
ls -lh test_images_output/
```

### 2. Cloud Mode (Requires Credentials)

Test with real RunPod and GCS:

```bash
# Set environment variables
export RUNPOD_API_KEY=your_runpod_api_key
export RUNPOD_ENDPOINT_ID=your_endpoint_id
export GCS_BUCKET=your_gcs_bucket_name
export GCS_PROJECT_ID=your_gcs_project_id  # optional

# Run CLI in cloud mode
python test_cli.py test_images_input/ test_images_output/ --cloud --timeout 600
```

## Unit Tests

Run all unit tests with coverage:

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
source venv/bin/activate

# Run all tests (34 tests)
pytest tests/ -v

# Run specific test files
pytest tests/test_handler.py -v          # Handler tests (8 tests)
pytest tests/test_upscaler.py -v         # Client tests (24 tests)
pytest tests/test_gcs_provider.py -v     # GCS provider tests (2 tests)
pytest tests/test_runpod_provider.py -v  # RunPod provider tests (3 tests)
pytest tests/test_mcp_tool.py -v         # MCP tool tests (1 test)

# Run with coverage report
pytest tests/ -v --cov=src/cloud_upscaler --cov-report=term-missing
```

## Testing the Handler (Server-Side)

### 1. Test Handler with Dependency Injection

Test the handler class directly with real objects:

```python
import sys
from pathlib import Path

# Add docker directory to path
sys.path.insert(0, str(Path.cwd() / 'docker'))

from handler import Handler
from image_downloader import ImageDownloader
from zip_extractor import ZipExtractor
from image_upscaler import ImageUpscaler
from zip_creator import ZipCreator
from cloud_storage import CloudStorage

# Create handler with real dependencies
handler = Handler(
    downloader=ImageDownloader(),
    extractor=ZipExtractor(),
    upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
    creator=ZipCreator(),
    storage=CloudStorage()
)

# Test with mock job
job = {
    'input': {
        'input_url': 'https://storage.googleapis.com/bucket/input.zip',
        'output_bucket': 'test-bucket',
        'output_path': 'test/output.zip'
    }
}

# This will fail without real URLs/credentials, but tests DI setup
result = handler.handle(job)
print(result)
```

### 2. Test Handler Docker Build

Build and verify the Docker image:

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler/docker

# Build Docker image
./build.sh

# Verify image exists
docker images | grep cloud-upscaler

# Run handler locally (requires credentials)
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials.json \
  -v /path/to/credentials.json:/credentials.json \
  cloud-upscaler:latest
```

## Test Architecture

### Client-Server Flow

```
┌─────────────────────────────────────────────────────┐
│ CLIENT (src/cloud_upscaler/)                        │
│                                                     │
│  1. upscale_images()                               │
│     ├── Create ZIP of input images                 │
│     ├── Upload to GCS (GoogleCloudStorageProvider) │
│     ├── Submit job to RunPod (RunPodComputeProvider)│
│     ├── Poll for job completion                    │
│     └── Download results from GCS                  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│ SERVER (docker/handler.py - RunPod)                 │
│                                                     │
│  Handler (with DI):                                │
│     ├── ImageDownloader: Download input ZIP        │
│     ├── ZipExtractor: Extract PNG files            │
│     ├── ImageUpscaler: Run Real-ESRGAN             │
│     ├── ZipCreator: Create output ZIP              │
│     └── CloudStorage: Upload to GCS                │
└─────────────────────────────────────────────────────┘
```

### Test Coverage

- **34 total tests** with **100% coverage**
  - 8 handler integration tests (validation, download, upscale, output)
  - 24 client integration tests (local mode, cloud mode, error handling)
  - 2 GCS provider unit tests
  - 3 RunPod provider unit tests
  - 1 MCP tool unit test

### Dependency Injection Benefits

All components use constructor injection for testability:

```python
# Handler (docker/handler.py)
handler = Handler(
    downloader=ImageDownloader(),    # Real object
    extractor=ZipExtractor(),        # Real object
    upscaler=ImageUpscaler(...),     # Real object
    creator=ZipCreator(),            # Real object
    storage=CloudStorage()           # Real object
)

# Tests use real objects, only mock external services:
- Mock HTTP requests (requests.get)
- Mock GCS API (google.cloud.storage.Client)
- Mock Real-ESRGAN library (basicsr, realesrgan)
```

## End-to-End Testing

### Prerequisites

1. **RunPod Account**
   - API key
   - Deployed endpoint with CloudUpscaler handler

2. **Google Cloud Storage**
   - GCS bucket
   - Service account with read/write permissions

3. **Local Setup**
   - Virtual environment activated
   - Test images prepared

### E2E Test Steps

```bash
# 1. Prepare environment
export RUNPOD_API_KEY=your_key
export RUNPOD_ENDPOINT_ID=your_endpoint
export GCS_BUCKET=your_bucket
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# 2. Create test images
python test_cli.py test_images_input/ test_images_output/ --cloud

# 3. Verify results
ls -lh test_images_output/
```

## Troubleshooting

### Tests Failing

```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -e ".[dev]"

# Clear pytest cache
rm -rf .pytest_cache
pytest --cache-clear tests/
```

### Handler Import Errors

```bash
# Add docker directory to Python path
export PYTHONPATH="${PYTHONPATH}:/Users/iankonradjohnson/base/abacus/CloudUpscaler/docker"
```

### Cloud Mode Timeouts

```bash
# Increase timeout
python test_cli.py input/ output/ --cloud --timeout 1800  # 30 minutes
```

## CI/CD Testing

Run the full test suite as CI/CD would:

```bash
#!/bin/bash
set -e

cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
source venv/bin/activate

# Run all tests with coverage
pytest tests/ -v --cov=src/cloud_upscaler --cov-report=term-missing --cov-fail-under=100

# Type checking (optional)
# mypy src/cloud_upscaler

# Linting (optional)
# ruff check src/ tests/

echo "✓ All tests passed!"
```
