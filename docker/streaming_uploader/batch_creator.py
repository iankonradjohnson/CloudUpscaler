from pathlib import Path


class BatchCreator:

    def create_batches(self, image_paths: list[Path], batch_size: int) -> list[list[Path]]:
        return [
            image_paths[i:i + batch_size]
            for i in range(0, len(image_paths), batch_size)
        ]
