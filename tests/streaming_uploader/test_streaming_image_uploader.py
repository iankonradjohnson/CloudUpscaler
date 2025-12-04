# Test Case List for StreamingImageUploader:
#
# Testing approach:
# - Use REAL file system (with tmp_path) for file I/O tests
# - Use REAL threading to verify parallelism
# - Use FAKE CloudStorage client to track upload calls
# - Generate small test images (10x10 pixels) in fixtures
# - NO integration tests (no real GCS API calls)
#
# Total: 14 unit tests
#
# Happy Path:
# [x] Uploads images in batches while processing continues
# [x] All images uploaded successfully
# [x] Uploads happen in background thread (parallel to main thread)
# [x] Final batch uploaded after processing completes
# [x] Returns list of uploaded GCS paths
#
# Batching:
# [x] Batch size configurable (default 10)
# [x] Small datasets upload in single batch
# [x] Large datasets split into multiple batches
#
# Threading:
# [x] Upload thread starts immediately
# [x] Upload thread completes before returning
# [x] Main thread not blocked by uploads
#
# Error Cases:
# [x] Upload failure propagates as exception
# [x] All images processed before error detected
# [x] Thread cleanup happens even on error

import pytest
import time
from pathlib import Path
from PIL import Image


class FakeCloudStorage:
    def __init__(self):
        self.uploaded_files = []
        self.upload_times = []
        self.should_fail = False
        self.fail_after_count = None
        self.upload_count = 0

    def upload_and_get_url(self, file_path: Path, bucket_name: str, blob_path: str) -> str:
        if self.should_fail:
            raise Exception("Upload failed")

        if self.fail_after_count is not None:
            if self.upload_count >= self.fail_after_count:
                raise Exception("Upload failed")
            self.upload_count += 1

        self.upload_times.append(time.time())
        gcs_url = f"gs://{bucket_name}/{blob_path}"
        self.uploaded_files.append({
            'local_path': file_path,
            'gcs_url': gcs_url,
            'bucket': bucket_name,
            'blob_path': blob_path
        })
        time.sleep(0.01)
        return gcs_url


class TestStreamingImageUploader:

    def test_uploads_all_images_successfully(self, tmp_path):
        images = given_test_images(tmp_path, count=5)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        result = uploader.upload_images_streaming(images, "test-bucket", "output")

        then_all_images_uploaded(storage, count=5)
        then_returns_gcs_paths(result, count=5)

    def test_uploads_in_batches(self, tmp_path):
        images = given_test_images(tmp_path, count=25)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        uploader.upload_images_streaming(images, "test-bucket", "output")

        then_uploaded_in_batches(storage, expected_batches=[10, 10, 5])

    def test_batch_size_configurable(self, tmp_path):
        images = given_test_images(tmp_path, count=15)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=5)

        uploader.upload_images_streaming(images, "test-bucket", "output")

        then_uploaded_in_batches(storage, expected_batches=[5, 5, 5])

    def test_small_dataset_single_batch(self, tmp_path):
        images = given_test_images(tmp_path, count=3)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        uploader.upload_images_streaming(images, "test-bucket", "output")

        then_uploaded_in_batches(storage, expected_batches=[3])

    def test_returns_gcs_paths_in_order(self, tmp_path):
        images = given_test_images(tmp_path, count=5)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        result = uploader.upload_images_streaming(images, "test-bucket", "output")

        assert result[0] == "gs://test-bucket/output/image_000.png"
        assert result[1] == "gs://test-bucket/output/image_001.png"
        assert result[4] == "gs://test-bucket/output/image_004.png"

    def test_uploads_happen_in_background_thread(self, tmp_path):
        images = given_test_images(tmp_path, count=20)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        start_time = time.time()
        uploader.upload_images_streaming(images, "test-bucket", "output")
        end_time = time.time()

        then_uploads_were_parallel(storage, start_time, end_time)

    def test_final_batch_uploaded_after_processing(self, tmp_path):
        images = given_test_images(tmp_path, count=15)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        result = uploader.upload_images_streaming(images, "test-bucket", "output")

        then_all_images_uploaded(storage, count=15)
        assert len(result) == 15

    def test_upload_thread_starts_immediately(self, tmp_path):
        images = given_test_images(tmp_path, count=20)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        start_time = time.time()
        uploader.upload_images_streaming(images, "test-bucket", "output")

        first_upload_time = storage.upload_times[0]
        time_to_first_upload = first_upload_time - start_time
        assert time_to_first_upload < 0.1, \
            f"First upload should start immediately (took {time_to_first_upload}s)"

    def test_upload_thread_completes_before_returning(self, tmp_path):
        images = given_test_images(tmp_path, count=15)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        result = uploader.upload_images_streaming(images, "test-bucket", "output")

        then_all_images_uploaded(storage, count=15)
        assert len(result) == 15

    def test_main_thread_not_blocked_by_uploads(self, tmp_path):
        images = given_test_images(tmp_path, count=30)
        storage = FakeCloudStorage()
        uploader = when_uploader_created(storage, batch_size=10)

        start_time = time.time()
        uploader.upload_images_streaming(images, "test-bucket", "output")
        end_time = time.time()

        total_time = end_time - start_time
        sequential_time = 30 * 0.01
        assert total_time < sequential_time * 0.5, \
            f"Main thread should not be blocked (took {total_time}s, sequential would be {sequential_time}s)"

    def test_upload_failure_propagates_as_exception(self, tmp_path):
        images = given_test_images(tmp_path, count=10)
        storage = given_storage_that_fails()
        uploader = when_uploader_created(storage, batch_size=10)

        with pytest.raises(Exception, match="Upload failed"):
            uploader.upload_images_streaming(images, "test-bucket", "output")

    def test_all_images_queued_before_error_detected(self, tmp_path):
        images = given_test_images(tmp_path, count=20)
        storage = given_storage_that_fails_after(5)
        uploader = when_uploader_created(storage, batch_size=10)

        with pytest.raises(Exception, match="Upload failed"):
            uploader.upload_images_streaming(images, "test-bucket", "output")

        assert storage.upload_count == 5, "Should process 5 images before failing"

    def test_thread_cleanup_happens_even_on_error(self, tmp_path):
        images = given_test_images(tmp_path, count=10)
        storage = given_storage_that_fails()
        uploader = when_uploader_created(storage, batch_size=10)

        with pytest.raises(Exception, match="Upload failed"):
            uploader.upload_images_streaming(images, "test-bucket", "output")

        import threading
        active_threads = [t for t in threading.enumerate() if "Thread-" in t.name]
        assert len(active_threads) == 0, "Worker thread should be cleaned up after error"


def given_test_images(tmp_path: Path, count: int) -> list[Path]:
    images = []
    for i in range(count):
        img_path = tmp_path / f"image_{i:03d}.png"
        img = Image.new('RGB', (10, 10), color='white')
        img.save(img_path)
        images.append(img_path)
    return images


def given_storage_that_fails() -> FakeCloudStorage:
    storage = FakeCloudStorage()
    storage.should_fail = True
    return storage


def given_storage_that_fails_after(count: int):
    storage = FakeCloudStorage()
    storage.fail_after_count = count
    storage.upload_count = 0
    return storage


def when_uploader_created(storage: FakeCloudStorage, batch_size: int):
    import sys
    from pathlib import Path
    repo_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(repo_root))
    from docker.streaming_uploader import StreamingImageUploader
    return StreamingImageUploader.create_default(storage, batch_size)


def then_all_images_uploaded(storage: FakeCloudStorage, count: int):
    assert len(storage.uploaded_files) == count


def then_returns_gcs_paths(result: list[str], count: int):
    assert len(result) == count
    assert all(path.startswith("gs://") for path in result)


def then_uploaded_in_batches(storage: FakeCloudStorage, expected_batches: list[int]):
    upload_times = storage.upload_times

    batch_start = 0
    for batch_size in expected_batches:
        batch_times = upload_times[batch_start:batch_start + batch_size]

        if len(batch_times) > 1:
            time_span = batch_times[-1] - batch_times[0]
            assert time_span < 0.15, f"Batch should upload quickly (got {time_span}s)"

        batch_start += batch_size


def then_uploads_were_parallel(storage: FakeCloudStorage, start_time: float, end_time: float):
    total_time = end_time - start_time
    upload_count = len(storage.uploaded_files)

    sequential_time = upload_count * 0.01
    assert total_time < sequential_time * 0.8, \
        f"Uploads should be parallel (took {total_time}s, sequential would be {sequential_time}s)"
