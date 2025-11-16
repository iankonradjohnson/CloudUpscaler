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
            name="upscale_images",
            description=(
                "Upscale PNG images using Real-ESRGAN on cloud GPU. "
                "Takes a directory of PNG files and outputs upscaled versions. "
                "Requires RunPod and Google Cloud Storage credentials in environment variables."
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
    if name != "upscale_images":
        raise ValueError(f"Unknown tool: {name}")

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
