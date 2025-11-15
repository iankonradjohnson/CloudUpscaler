# CloudUpscaler - Requirements

**Purpose:** Upscale book page images using cloud GPU processing (RunPod Serverless with Real-ESRGAN model).

---

## User Stories

### Story 1: Batch Image Upscaling
**As a** book restoration pipeline
**I want to** upscale a directory of low-resolution PNG images using cloud GPU
**So that** I can improve image quality for OCR and archival

**Acceptance Criteria:**
- Given a directory containing 2-1000 PNG images
- When I request upscaling
- Then all images are processed using Real-ESRGAN model
- And upscaled images are returned in output directory
- And original directory structure is preserved

### Story 2: Reliable Processing
**As a** book restoration pipeline
**I want** upscaling to handle failures gracefully
**So that** I don't lose work or money on failed jobs

**Acceptance Criteria:**
- If job fails, I get clear error message
- If job times out, I'm notified
- Partial results are not returned (all or nothing)
- Remote files are cleaned up after processing

### Story 3: Cost Efficiency
**As a** system operator
**I want** to only pay for actual GPU time used
**So that** I minimize cloud compute costs

**Acceptance Criteria:**
- No manual pod management required
- GPU resources auto-scale to zero when idle
- Only billed for actual processing time

### Story 4: Provider Flexibility
**As a** developer
**I want** to switch cloud providers without rewriting business logic
**So that** I can optimize for cost/performance

**Acceptance Criteria:**
- Switching from RunPod to Modal requires changing only provider adapter
- Business logic and tests remain unchanged
- Same interface for all providers

---

## External System Constraints

### RunPod Serverless API

**Endpoints we need:**
```python
# Submit job
POST /run
Request: {
    "input": {
        "input_url": "https://storage.googleapis.com/...",  # Signed URL to download input zip
        "output_bucket": "bucket-name",
        "output_path": "path/to/output",
        "model_name": "net_g_1000000",
        "tile_size": 0,
        "gpu_count": 1
    }
}
Response: {
    "id": "job-abc123",
    "status": "IN_QUEUE"
}

# Check status
GET /status/{job_id}
Response: {
    "id": "job-abc123",
    "status": "COMPLETED",  # or "IN_PROGRESS", "FAILED"
    "output": {
        "output_url": "https://storage.googleapis.com/..."  # Signed URL to download results
    }
}
```

**Job States:** IN_QUEUE → IN_PROGRESS → COMPLETED/FAILED

### Google Cloud Storage

**Operations needed:**
```python
# Upload file, get signed URL
upload_blob(bucket_name, source_file, destination_blob_name) → signed_url

# Download file from signed URL
download_blob_from_url(signed_url, destination_file)

# Delete file
delete_blob(bucket_name, blob_name)
```

### Real-ESRGAN Model

**Model file:** `net_g_1000000.pth` (128MB, custom trained)
**Input:** ZIP file containing PNG images
**Output:** ZIP file containing upscaled PNG images
**Processing:** Multi-GPU support (handler splits work across available GPUs)

---

## Non-Functional Requirements

### Performance
- Cold start: < 5 seconds
- Processing: Similar to current pod-based system
- Timeout: Configurable (default 60 minutes)

### Reliability
- Success rate: 99%+ for valid inputs
- Graceful degradation on failures
- No silent failures

### Testability
- 90%+ test coverage
- Tests run in < 10 seconds
- No real cloud resources needed for unit tests

### Maintainability
- New developer can understand in 5 minutes
- Adding new provider takes < 2 hours
- Business logic independent of infrastructure

---

## Example Usage

### Python Package
```python
# Import
from cloud_upscaler import upscale_images

# Use
result = upscale_images(
    input_dir=Path("book_pages/raw"),
    output_dir=Path("book_pages/upscaled"),
    model_name="net_g_1000000",
    timeout_seconds=3600
)

if result.success:
    print(f"Upscaled {result.images_processed} images")
else:
    print(f"Failed: {result.error}")
```

### MCP Tool
```python
# Claude calls via MCP
upscale_images_sync(
    image_dir="/path/to/images",
    output_dir="/path/to/output"
)
```

---

## Out of Scope (For Now)

- Video upscaling
- Real-time streaming
- Custom model training
- Image format conversion (PNG only)
- Batch job queuing (process one at a time)

---

## Success Metrics

**MVP is successful when:**
1. ✅ Can upscale 100 PNG images end-to-end
2. ✅ Handles job failure gracefully
3. ✅ No manual cleanup required
4. ✅ Costs < $0.50 per 100 images
5. ✅ 90%+ test coverage
6. ✅ Can swap RunPod for FakeProvider in tests

---

**Next:** Start TDD implementation from these requirements!
