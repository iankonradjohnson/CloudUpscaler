# CloudUpscaler TDD Test Plan

**Date:** 2025-11-15
**Approach:** Kent Beck Classicist TDD - Real objects, fakes at boundaries only

---

## Step 0: Architecture Analysis

### Components from CLOUD_UPSCALER_ARCHITECTURE.md

**Domain Layer:**
- `JobStatus` (enum) - no dependencies ✅ DONE
- `UpscaleConfig` (value object) - no dependencies ✅ DONE (validation only)
- `Job` (value object) - has behavior methods
- `StorageLocation` (value object) - minimal logic
- Domain exceptions
- Domain events
- `ICloudComputeProvider` (interface)
- `IStorageProvider` (interface)

**Application Layer:**
- `FileArchiver` - no external dependencies
- `TempFileManager` - wraps Python tempfile
- `StorageManager(IStorageProvider)` - delegates
- `JobManager(ICloudComputeProvider)` - delegates + events
- `JobStatusPoller(JobManager)` - polling logic
- `ResultDownloader(StorageManager, FileArchiver, TempFileManager)` - coordinates
- `EventPublisher` - simple pub/sub
- `UpscalePipeline(all services)` - orchestrates everything

**Infrastructure Layer:**
- `FakeComputeProvider` (ICloudComputeProvider) - for testing
- `FakeStorageProvider` (IStorageProvider) - for testing
- `RunPodServerlessProvider` - real implementation
- `GCSStorageProvider` - real implementation

---

## Dependency Graph

```
Level 0: Interfaces & Domain Objects
├── ICloudComputeProvider (interface)
├── IStorageProvider (interface)
├── JobStatus ✅ DONE
├── UpscaleConfig ✅ DONE
├── Job
├── StorageLocation
├── Domain exceptions
└── Domain events

Level 1: External Boundaries (FAKES)
├── FakeComputeProvider : ICloudComputeProvider
└── FakeStorageProvider : IStorageProvider

Level 2: Leaf Services (no complex dependencies)
├── FileArchiver
├── TempFileManager
└── EventPublisher

Level 3: Mid-Level Services (depend on fakes)
├── StorageManager(IStorageProvider)
└── JobManager(ICloudComputeProvider, EventPublisher)

Level 4: Complex Services
├── JobStatusPoller(JobManager)
└── ResultDownloader(StorageManager, FileArchiver, TempFileManager)

Level 5: Orchestrator
└── UpscalePipeline(FileArchiver, TempFileManager, StorageManager, JobManager, JobStatusPoller, ResultDownloader)
```

---

## What Needs Testing? (Kent Beck Filter)

### ✅ TEST - Has Business Logic/Behavior

1. **Job** (Level 0)
   - `is_terminal()` - knows terminal states
   - `can_be_cancelled()` - cancellation rules
   - `mark_completed()` / `mark_failed()` - immutable updates

2. **FakeComputeProvider** (Level 1)
   - Simulates job lifecycle
   - Returns correct job states
   - Handles job not found

3. **FakeStorageProvider** (Level 1)
   - File upload/download simulation
   - Proper error handling

4. **FileArchiver** (Level 2)
   - Rejects non-directory for zip
   - Rejects non-existent zip for unzip
   - Edge cases matter (empty dirs, permissions)

5. **JobStatusPoller** (Level 4)
   - Polling until terminal state
   - Timeout handling
   - Status callbacks

6. **UpscalePipeline** (Level 5) **← MOST IMPORTANT**
   - End-to-end workflow
   - Error handling at each step
   - Sync vs async modes
   - Cleanup behavior

### ❌ SKIP - Pure Delegation/Data

1. **StorageLocation** - just data + simple parsing
2. **TempFileManager** - thin wrapper around tempfile
3. **StorageManager** - delegates to provider (tested via pipeline)
4. **JobManager** - delegates to provider (tested via pipeline)
5. **ResultDownloader** - coordination (tested via pipeline)
6. **EventPublisher** - trivial pub/sub (tested via JobManager if needed)
7. **Domain exceptions** - just exception classes
8. **Domain events** - just dataclasses

---

## Test Implementation Order

### Phase 1: Foundations (Bottom-Up)

#### 1.1 Complete Domain Objects (Level 0)
**Status:** JobStatus ✅, UpscaleConfig ✅

**TODO:**
- ✅ Domain exceptions (no tests - just create them)
- ✅ Domain events (no tests - just create them)
- ✅ Job value object behavior (test is_terminal, can_be_cancelled, mark_completed/failed)
- ✅ StorageLocation (no tests OR one test for parsing if complex)
- ✅ Interfaces (ICloudComputeProvider, IStorageProvider)

**Estimated tests:** 3-4 for Job behavior

---

#### 1.2 Create Fakes (Level 1) **← START HERE NEXT**

**FakeComputeProvider:**
```python
class FakeComputeProvider(ICloudComputeProvider):
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def submit_job(...) -> Job:
        # Creates job in COMPLETED state (or FAILED if configured)

    def get_job_status(job_id) -> Job:
        # Returns job or raises JobNotFoundException
```

**Tests:**
- Test: submit_job returns completed job
- Test: get_job_status retrieves job
- Test: get_job_status raises JobNotFoundException for unknown job
- Test: can configure fake to simulate failures

**FakeStorageProvider:**
```python
class FakeStorageProvider(IStorageProvider):
    def __init__(self, temp_dir: Path):
        self._temp_dir = temp_dir  # Simulated "cloud"
        self._files: Dict[str, Path] = {}

    def upload_file(...) -> str:
        # Copy to temp_dir, return fake URL

    def download_file(url, local_path) -> Path:
        # Copy from temp_dir
```

**Tests:**
- Test: upload_file stores file and returns URL
- Test: download_file retrieves uploaded file
- Test: download_file raises error for non-existent file

**Estimated tests:** 7 (4 for FakeCompute, 3 for FakeStorage)

---

### Phase 2: Services (Middle Layer)

#### 2.1 FileArchiver (Level 2)

**Tests:**
- Test: rejects non-directory for zip
- Test: zips directory successfully
- Test: rejects non-existent zip for unzip
- Test: unzips archive successfully

**Estimated tests:** 4

---

#### 2.2 JobStatusPoller (Level 4)

**Depends on:** JobManager → FakeComputeProvider

**Tests:**
- Test: polls until job completes
- Test: raises TimeoutError after timeout
- Test: calls status callback on status changes

**Estimated tests:** 3

---

### Phase 3: Pipeline (Top Layer)

#### 3.1 UpscalePipeline (Level 5) **← THE BIG ONE**

**Composition:**
```python
fake_compute = FakeComputeProvider()
fake_storage = FakeStorageProvider(temp_dir)

archiver = FileArchiver()
temp_mgr = TempFileManager()
storage_mgr = StorageManager(fake_storage)  # Real service, fake provider
job_mgr = JobManager(fake_compute, EventPublisher())
poller = JobStatusPoller(job_mgr)
downloader = ResultDownloader(storage_mgr, archiver, temp_mgr)

pipeline = UpscalePipeline(archiver, temp_mgr, storage_mgr, job_mgr, poller, downloader)
```

**Tests:**
1. **Happy path:** End-to-end sync workflow succeeds
2. **Job failure:** Pipeline raises JobNotCompletedException when job fails
3. **Timeout:** Pipeline respects timeout
4. **Async mode:** run_async returns immediately with job_id
5. **Cleanup:** Cleans up remote files when configured
6. **Empty directory:** Handles empty input directory gracefully

**Estimated tests:** 6

---

## Test Summary

| Component | Tests | Priority |
|-----------|-------|----------|
| Job (behavior) | 3-4 | HIGH |
| FakeComputeProvider | 4 | HIGH |
| FakeStorageProvider | 3 | HIGH |
| FileArchiver | 4 | HIGH |
| JobStatusPoller | 3 | MEDIUM |
| UpscalePipeline | 6 | CRITICAL |
| **TOTAL** | **~23-24** | |

**Skipped components:** ~8 (pure delegation/data)

---

## Implementation Plan

### Session 1: Foundations
1. ✅ JobStatus enum
2. ✅ UpscaleConfig (validation only)
3. ⏭️ Domain exceptions (no tests)
4. ⏭️ Domain events (no tests)
5. ⏭️ Interfaces (no tests)
6. ⏭️ Job behavior (~3 tests)

### Session 2: Fakes
7. ⏭️ FakeComputeProvider (~4 tests)
8. ⏭️ FakeStorageProvider (~3 tests)

### Session 3: Services
9. ⏭️ FileArchiver (~4 tests)
10. ⏭️ Create untested services (StorageManager, JobManager, TempFileManager, EventPublisher, ResultDownloader)
11. ⏭️ JobStatusPoller (~3 tests)

### Session 4: Pipeline
12. ⏭️ UpscalePipeline (~6 tests)

---

## Success Criteria

✅ All 23-24 tests passing
✅ End-to-end workflow works (happy path + error cases)
✅ Real objects composed with fakes at boundaries
✅ ~80-90% coverage on tested code
✅ Can swap FakeProvider → RealProvider without changing tests

---

## Next Step

**Proceed with Session 1, Item 3:**
Create domain exceptions (no tests - just classes)

Then continue through the list in order!
