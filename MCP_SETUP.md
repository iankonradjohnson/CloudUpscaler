# CloudUpscaler MCP Server Setup

This guide shows how to use CloudUpscaler as an MCP (Model Context Protocol) server with Claude Desktop.

## What is MCP?

MCP allows Claude Desktop to use CloudUpscaler as a tool, enabling you to upscale images directly from conversations with Claude.

## Installation

### 1. Install CloudUpscaler

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
source venv/bin/activate
pip install -e .
```

This installs the `cloud-upscaler-mcp` command.

### 2. Configure Claude Desktop

Edit your Claude Desktop MCP configuration file:

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Add CloudUpscaler MCP server:**

```json
{
  "mcpServers": {
    "cloud-upscaler": {
      "command": "/Users/iankonradjohnson/base/abacus/CloudUpscaler/venv/bin/cloud-upscaler-mcp",
      "env": {
        "RUNPOD_API_KEY": "your_runpod_api_key_here",
        "RUNPOD_ENDPOINT_ID": "your_endpoint_id_here",
        "GCS_BUCKET": "your_gcs_bucket_name",
        "GCS_PROJECT_ID": "your_gcs_project_id",
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/gcs-credentials.json"
      }
    }
  }
}
```

### 3. Environment Variables

**For Cloud Mode (RunPod + GCS):**
- `RUNPOD_API_KEY` - Your RunPod API key
- `RUNPOD_ENDPOINT_ID` - Your deployed RunPod endpoint ID
- `GCS_BUCKET` - Google Cloud Storage bucket name
- `GCS_PROJECT_ID` - (Optional) GCS project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCS service account credentials JSON

**For Local Simulation Mode:**
- No environment variables needed
- Set `use_cloud=false` when calling the tool

### 4. Restart Claude Desktop

After saving the configuration, restart Claude Desktop to load the MCP server.

## Usage

### In Claude Desktop Conversations

Once configured, you can ask Claude to upscale images:

```
Claude, please upscale the PNG images in ~/Pictures/my_images/
and save them to ~/Pictures/upscaled/
```

Claude will use the `upscale_images` tool to process your request.

### Tool Parameters

The MCP server exposes one tool: `upscale_images`

**Parameters:**
- `input_dir` (required): Path to directory with PNG files
- `output_dir` (required): Path to save upscaled images
- `model_name` (optional): Real-ESRGAN model (default: "net_g_1000000")
- `timeout_seconds` (optional): Max wait time (default: 3600)
- `use_cloud` (optional): Use cloud processing or local simulation (default: true)

### Example Tool Call

```python
{
  "input_dir": "/Users/myuser/Pictures/input",
  "output_dir": "/Users/myuser/Pictures/output",
  "model_name": "net_g_1000000",
  "timeout_seconds": 1800,
  "use_cloud": true
}
```

## Testing

### Test the MCP Server Directly

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
source venv/bin/activate

# Test server starts
cloud-upscaler-mcp

# It should wait for MCP protocol messages on stdin
# Press Ctrl+C to exit
```

### Test in Local Mode (No Cloud)

Create a minimal config without credentials:

```json
{
  "mcpServers": {
    "cloud-upscaler": {
      "command": "/Users/iankonradjohnson/base/abacus/CloudUpscaler/venv/bin/cloud-upscaler-mcp"
    }
  }
}
```

Then in Claude Desktop:

```
Please upscale images in ~/test_images to ~/test_output using local mode (use_cloud=false)
```

## Modes

### Cloud Mode (Default)

- Uses RunPod for GPU processing
- Uses GCS for file transfer
- Real Real-ESRGAN upscaling with 4x quality improvement
- Requires credentials

### Local Simulation Mode

- Runs locally without cloud services
- Simulates upscaling (no real processing)
- Useful for testing without credentials
- Set `use_cloud=false`

## Troubleshooting

### "Missing required environment variable"

Make sure all required env vars are set in `claude_desktop_config.json`:
- RUNPOD_API_KEY
- RUNPOD_ENDPOINT_ID
- GCS_BUCKET
- GOOGLE_APPLICATION_CREDENTIALS

### "Input directory does not exist"

Check that the path you provided exists and is accessible.

### "MCP server not found"

- Verify the `command` path in config points to the correct venv
- Try absolute path: `/Users/iankonradjohnson/base/abacus/CloudUpscaler/venv/bin/cloud-upscaler-mcp`
- Ensure `pip install -e .` was run

### "Job timed out"

Increase the `timeout_seconds` parameter for large batches:

```
Please upscale these images with a 30-minute timeout (timeout_seconds=1800)
```

## Architecture

```
┌──────────────────────────────────────────┐
│  Claude Desktop                           │
│                                          │
│  User: "Upscale my images"              │
└────────────────┬─────────────────────────┘
                 │ MCP Protocol
                 ▼
┌──────────────────────────────────────────┐
│  CloudUpscaler MCP Server                 │
│  (cloud-upscaler-mcp)                    │
│                                          │
│  - Receives tool call                    │
│  - Validates parameters                  │
│  - Calls upscale_images()                │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│  Cloud Processing                         │
│                                          │
│  1. Upload to GCS                        │
│  2. Submit job to RunPod                 │
│  3. RunPod runs Real-ESRGAN              │
│  4. Download results from GCS            │
└──────────────────────────────────────────┘
```

## Next Steps

1. **Deploy Handler to RunPod** - See `docker/DEPLOYMENT.md`
2. **Get RunPod Credentials** - Sign up at runpod.io
3. **Setup GCS** - Create bucket and service account
4. **Configure Claude Desktop** - Add MCP server config
5. **Test** - Ask Claude to upscale some images!

## Example Claude Desktop Config (Complete)

```json
{
  "mcpServers": {
    "cloud-upscaler": {
      "command": "/Users/iankonradjohnson/base/abacus/CloudUpscaler/venv/bin/cloud-upscaler-mcp",
      "env": {
        "RUNPOD_API_KEY": "XXXXXXXXXXXXXXXXXXXXXX",
        "RUNPOD_ENDPOINT_ID": "abc123def456",
        "GCS_BUCKET": "my-upscaler-bucket",
        "GCS_PROJECT_ID": "my-gcp-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "/Users/myuser/.gcp/upscaler-credentials.json",
        "UPSCALER_MODE": "cloud"
      }
    }
  }
}
```

## Logs

MCP server logs are written to:
- macOS/Linux: Check Claude Desktop logs or stderr
- Look for "Starting CloudUpscaler MCP server" message

Enable debug logging:
```json
{
  "mcpServers": {
    "cloud-upscaler": {
      "command": "/Users/iankonradjohnson/base/abacus/CloudUpscaler/venv/bin/cloud-upscaler-mcp",
      "env": {
        "LOG_LEVEL": "DEBUG",
        ...
      }
    }
  }
}
```
