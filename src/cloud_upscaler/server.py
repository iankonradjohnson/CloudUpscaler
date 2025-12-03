#!/usr/bin/env python3
"""
CloudUpscaler MCP Server

Provides image upscaling capabilities via Model Context Protocol.
"""

import os
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from cloud_upscaler import upscale_images, UpscaleResult
from cloud_upscaler.providers.runpod import RunPodComputeProvider
from cloud_upscaler.providers.gcs import GoogleCloudStorageProvider

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("cloud-upscaler")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="start_upscale_job",
            description=(
                "Start an async upscaling job on RunPod cloud GPU and return immediately with job ID. "
                "Use check_upscale_status to monitor progress. Job runs in background while you continue other work."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "Path to directory containing images to upscale (PNG, JPG, JPEG)",
                    },
                    "book_dir": {
                        "type": "string",
                        "description": "Path to book directory where job_id.txt will be saved",
                    },
                    "gcs_output_path": {
                        "type": "string",
                        "description": "Unique GCS path for this job (e.g. 'upscaled/book_1/output.zip')",
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Real-ESRGAN model to use (default: net_g_1000000)",
                        "default": "net_g_1000000",
                    },
                    "tile_size": {
                        "type": "integer",
                        "description": "Tile size for processing (0=auto, default: 0)",
                        "default": 0,
                    },
                    "tile_pad": {
                        "type": "integer",
                        "description": "Tile padding for processing (default: 10)",
                        "default": 10,
                    },
                    "scale": {
                        "type": "integer",
                        "description": "Upscaling factor (default: 4)",
                        "default": 4,
                    },
                },
                "required": ["input_dir", "book_dir", "gcs_output_path"],
            },
        ),
        Tool(
            name="check_upscale_status",
            description=(
                "Check status of a running upscaling job and download results if complete. "
                "Reads job ID from book_dir/job_id.txt file."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "book_dir": {
                        "type": "string",
                        "description": "Path to book directory containing job_id.txt",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Path to directory where upscaled images will be saved (if job complete)",
                    },
                },
                "required": ["book_dir", "output_dir"],
            },
        ),
        Tool(
            name="upscale_images",
            description=(
                "DEPRECATED: Use start_upscale_job + check_upscale_status instead. "
                "This synchronous tool blocks for entire upscaling duration (30-60 min)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "Path to directory containing PNG images to upscale (must contain at least 2 PNG files)",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Path to directory where upscaled images will be saved",
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Real-ESRGAN model to use (default: net_g_1000000)",
                        "default": "net_g_1000000",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum time to wait for upscaling job (default: 3600)",
                        "default": 3600,
                    },
                    "use_cloud": {
                        "type": "boolean",
                        "description": "Use cloud processing (RunPod + GCS) or local simulation (default: true)",
                        "default": True,
                    },
                },
                "required": ["input_dir", "output_dir"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if name == "start_upscale_job":
        return await start_upscale_job(arguments)
    elif name == "check_upscale_status":
        return await check_upscale_status(arguments)
    elif name == "upscale_images":
        return await upscale_images_sync(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")



async def start_upscale_job(arguments: Any) -> list[TextContent]:
    """Start an async upscaling job and return job ID."""
    import itertools
    import zipfile
    import tempfile

    try:
        # Extract arguments
        input_dir = Path(arguments["input_dir"])
        book_dir = Path(arguments["book_dir"])
        gcs_output_path = arguments["gcs_output_path"]
        model_name = arguments.get("model_name", "net_g_1000000")
        tile_size = arguments.get("tile_size", 0)
        tile_pad = arguments.get("tile_pad", 10)
        scale = arguments.get("scale", 4)

        # Validate directories
        if not input_dir.exists():
            return [TextContent(type="text", text=f"Error: Input directory does not exist: {input_dir}")]

        book_dir.mkdir(parents=True, exist_ok=True)

        # Get credentials from environment
        runpod_api_key = os.environ["RUNPOD_API_KEY"]
        runpod_endpoint_id = os.environ["RUNPOD_ENDPOINT_ID"]
        gcs_bucket = os.environ["GCS_BUCKET"]
        gcs_project_id = os.environ.get("GCS_PROJECT_ID")

        logger.info(f"Starting upscaling job for {input_dir}")
        logger.info(f"GCS output: gs://{gcs_bucket}/{gcs_output_path}")

        # Collect all image files
        image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
        image_files = list(itertools.chain.from_iterable(
            input_dir.glob(pattern) for pattern in image_patterns
        ))

        if not image_files:
            return [TextContent(type="text", text="Error: No image files found (PNG, JPG, JPEG)")]

        logger.info(f"Found {len(image_files)} images to upscale")

        # Create temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            zip_path = Path(tmp_zip.name)

        with zipfile.ZipFile(zip_path, 'w') as zf:
            for image_file in image_files:
                zf.write(image_file, image_file.name)

        # Initialize providers
        storage_provider = GoogleCloudStorageProvider(
            bucket_name=gcs_bucket,
            project_id=gcs_project_id
        )

        compute_provider = RunPodComputeProvider(
            api_key=runpod_api_key,
            endpoint_id=runpod_endpoint_id,
            output_bucket=gcs_bucket,
            output_path=gcs_output_path
        )

        # Upload zip to GCS
        remote_url = storage_provider.upload(str(zip_path), "input.zip")
        logger.info(f"Uploaded input images to {remote_url}")

        # Submit job to RunPod
        realesrgan_params = {
            'tile_size': tile_size,
            'tile_pad': tile_pad,
            'scale': scale,
            'face_enhance': False,
            'fp32': False,
            'gpu_id': '0'
        }

        job_id = compute_provider.submit_job(remote_url, model_name, realesrgan_params)

        # Clean up zip file
        zip_path.unlink()

        # Save job ID to file
        job_id_file = book_dir / "upscaling_job_id.txt"
        job_id_file.write_text(job_id)

        logger.info(f"Job submitted: {job_id}")
        logger.info(f"Job ID saved to: {job_id_file}")

        return [TextContent(
            type="text",
            text=f"✓ Upscaling job started!\n\n"
                 f"Job ID: {job_id}\n"
                 f"Input images: {len(image_files)}\n"
                 f"GCS output: gs://{gcs_bucket}/{gcs_output_path}\n"
                 f"Job ID saved to: {job_id_file}\n\n"
                 f"Use check_upscale_status to monitor progress."
        )]

    except KeyError as e:
        return [TextContent(
            type="text",
            text=f"Error: Missing environment variable: {e}\n\n"
                 f"Required: RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, GCS_BUCKET"
        )]
    except Exception as e:
        logger.error(f"Error starting upscale job: {e}", exc_info=True)
        return [TextContent(type="text", text=f"✗ Error: {str(e)}")]


async def check_upscale_status(arguments: Any) -> list[TextContent]:
    """Check status of running upscaling job and download if complete."""
    import zipfile
    import tempfile

    try:
        # Extract arguments
        book_dir = Path(arguments["book_dir"])
        output_dir = Path(arguments["output_dir"])

        # Read job ID from file
        job_id_file = book_dir / "upscaling_job_id.txt"
        if not job_id_file.exists():
            return [TextContent(
                type="text",
                text=f"Error: Job ID file not found: {job_id_file}\n"
                     f"Run start_upscale_job first."
            )]

        job_id = job_id_file.read_text().strip()
        logger.info(f"Checking status for job: {job_id}")

        # Get credentials
        runpod_api_key = os.environ["RUNPOD_API_KEY"]
        runpod_endpoint_id = os.environ["RUNPOD_ENDPOINT_ID"]
        gcs_bucket = os.environ["GCS_BUCKET"]
        gcs_project_id = os.environ.get("GCS_PROJECT_ID")

        # Initialize providers
        storage_provider = GoogleCloudStorageProvider(
            bucket_name=gcs_bucket,
            project_id=gcs_project_id
        )

        compute_provider = RunPodComputeProvider(
            api_key=runpod_api_key,
            endpoint_id=runpod_endpoint_id,
            output_bucket=gcs_bucket,
            output_path="dummy"  # Not used for status check
        )

        # Check job status
        status = compute_provider.get_job_status(job_id)
        logger.info(f"Job {job_id}: {status}")

        if status == "IN_QUEUE":
            return [TextContent(
                type="text",
                text=f"⏳ Job is queued (waiting for GPU)\n\nJob ID: {job_id}"
            )]
        elif status == "IN_PROGRESS":
            return [TextContent(
                type="text",
                text=f"⚙️ Job is running (upscaling in progress)\n\nJob ID: {job_id}"
            )]
        elif status == "FAILED":
            return [TextContent(
                type="text",
                text=f"✗ Job FAILED\n\nJob ID: {job_id}\n"
                     f"Check RunPod dashboard for error details."
            )]
        elif status == "COMPLETED":
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Download results
            logger.info("Job completed! Downloading results...")
            output_url = compute_provider.get_job_output_url(job_id)

            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                result_zip_path = Path(tmp.name)

            storage_provider.download(output_url, str(result_zip_path))

            # Extract to output directory
            logger.info(f"Extracting upscaled images to {output_dir}")
            with zipfile.ZipFile(result_zip_path, 'r') as zf:
                zf.extractall(output_dir)

            # Clean up
            result_zip_path.unlink()

            # Count output files
            output_files = list(output_dir.glob("*.jpg")) + list(output_dir.glob("*.png"))

            return [TextContent(
                type="text",
                text=f"✅ Job COMPLETED!\n\n"
                     f"Job ID: {job_id}\n"
                     f"Upscaled images: {len(output_files)}\n"
                     f"Output directory: {output_dir}\n\n"
                     f"Ready for next stage!"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Unknown status: {status}\n\nJob ID: {job_id}"
            )]

    except KeyError as e:
        return [TextContent(
            type="text",
            text=f"Error: Missing environment variable: {e}"
        )]
    except Exception as e:
        logger.error(f"Error checking status: {e}", exc_info=True)
        return [TextContent(type="text", text=f"✗ Error: {str(e)}")]


async def upscale_images_sync(arguments: Any) -> list[TextContent]:
    """DEPRECATED: Synchronous upscaling (blocks for entire duration)."""
    # Extract arguments
    input_dir = Path(arguments["input_dir"])
    output_dir = Path(arguments["output_dir"])
    model_name = arguments.get("model_name", "net_g_1000000")
    timeout_seconds = arguments.get("timeout_seconds", 3600)
    use_cloud = arguments.get("use_cloud", True)

    # Validate input directory
    if not input_dir.exists():
        return [
            TextContent(
                type="text",
                text=f"Error: Input directory does not exist: {input_dir}",
            )
        ]

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Upscaling images from {input_dir} to {output_dir}")
    logger.info(f"Model: {model_name}, Timeout: {timeout_seconds}s, Cloud: {use_cloud}")

    # Initialize providers if cloud mode
    storage_provider = None
    compute_provider = None

    if use_cloud:
        try:
            # Get credentials from environment
            runpod_api_key = os.environ["RUNPOD_API_KEY"]
            runpod_endpoint_id = os.environ["RUNPOD_ENDPOINT_ID"]
            gcs_bucket = os.environ["GCS_BUCKET"]
            gcs_project_id = os.environ.get("GCS_PROJECT_ID")

            # Initialize providers
            storage_provider = GoogleCloudStorageProvider(
                bucket_name=gcs_bucket,
                project_id=gcs_project_id
            )

            compute_provider = RunPodComputeProvider(
                api_key=runpod_api_key,
                endpoint_id=runpod_endpoint_id,
                output_bucket=gcs_bucket,
                output_path="upscaled/output.zip"
            )

            logger.info(f"Cloud mode: RunPod endpoint {runpod_endpoint_id}, GCS bucket {gcs_bucket}")

        except KeyError as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Missing required environment variable: {e}\n\n"
                         f"Required for cloud mode:\n"
                         f"  - RUNPOD_API_KEY\n"
                         f"  - RUNPOD_ENDPOINT_ID\n"
                         f"  - GCS_BUCKET\n"
                         f"  - GCS_PROJECT_ID (optional)\n\n"
                         f"Or set use_cloud=false for local simulation mode.",
                )
            ]
    else:
        logger.info("Local mode: Simulating upscaling (no real processing)")

    # Run upscaling
    try:
        result: UpscaleResult = upscale_images(
            input_dir=input_dir,
            output_dir=output_dir,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            storage_provider=storage_provider,
            compute_provider=compute_provider,
        )

        if result.success:
            mode = "cloud GPU" if use_cloud else "local simulation"
            output_files = list(output_dir.glob("*.png"))

            response = (
                f"✓ Successfully upscaled {result.images_processed} images using {mode}!\n\n"
                f"Input:  {input_dir}\n"
                f"Output: {output_dir}\n"
                f"Model:  {model_name}\n\n"
                f"Output files:\n"
            )

            for f in output_files:
                response += f"  - {f.name}\n"

            return [TextContent(type="text", text=response)]
        else:
            return [
                TextContent(
                    type="text",
                    text=f"✗ Upscaling failed: {result.error}",
                )
            ]

    except Exception as e:
        logger.error(f"Upscaling error: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=f"✗ Upscaling error: {str(e)}",
            )
        ]


async def main():
    """Run the MCP server."""
    logger.info("Starting CloudUpscaler MCP server")

    # Check for required environment variables in cloud mode
    cloud_mode = os.environ.get("UPSCALER_MODE", "cloud") == "cloud"
    if cloud_mode:
        required_vars = ["RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID", "GCS_BUCKET"]
        missing = [v for v in required_vars if v not in os.environ]
        if missing:
            logger.warning(f"Missing environment variables for cloud mode: {missing}")
            logger.warning("Server will only work in local simulation mode")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
