# System Monitor API Documentation

A Flask-based REST API for monitoring system resources including CPU, RAM, disk, GPU, network, and Ollama models.

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Response Examples](#response-examples)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites
- Python 3.7+
- pip package manager
- For AMD GPU: ROCm installed with `rocm-smi` command available
- For NVIDIA GPU: CUDA drivers with `nvidia-smi` command available
- Ollama server running (optional)

### Install Dependencies
```bash
pip install flask psutil requests
```

## Quick Start

1. Save the script as `monitor.py`

2. Run the server:
```bash
python3 monitor.py
```

3. Access the API:
```bash
curl http://localhost:5000/stats/summary
```

4. For remote access (replace with your server IP):
```bash
curl http://192.168.110.158:5000/stats/summary
```

## API Endpoints

### Root Endpoint
**GET /** - API documentation and available endpoints
```bash
curl http://localhost:5000/
```

### Complete Statistics
**GET /stats** - Returns all system statistics in one response
```bash
curl http://localhost:5000/stats
```

Returns: CPU, Memory, Disk, GPU, Network, and Ollama information

### Individual Components

#### CPU Statistics
**GET /stats/cpu** - CPU usage and core information
```bash
curl http://localhost:5000/stats/cpu
```

**Response fields:**
- `usage_percent` - Overall CPU usage percentage
- `cores` - Number of physical cores
- `threads` - Number of logical threads
- `frequency_mhz` - Current CPU frequency in MHz
- `per_core_usage` - Usage percentage for each core

#### Memory Statistics
**GET /stats/memory** - RAM usage information
```bash
curl http://localhost:5000/stats/memory
```

**Response fields:**
- `total_gb` - Total RAM in GB
- `used_gb` - Used RAM in GB
- `available_gb` - Available RAM in GB
- `percent` - Usage percentage

#### Disk Statistics
**GET /stats/disk** - Disk usage information
```bash
curl http://localhost:5000/stats/disk
```

**Response fields:**
- `total_gb` - Total disk space in GB
- `used_gb` - Used disk space in GB
- `free_gb` - Free disk space in GB
- `percent` - Usage percentage

#### GPU Statistics
**GET /stats/gpu** - GPU usage and VRAM information
```bash
curl http://localhost:5000/stats/gpu
```

**AMD GPU Response fields:**
- `type` - GPU type (AMD ROCm)
- `gpus` - Array of GPU information:
  - `name` - GPU card name (e.g., "card0")
  - `usage_percent` - GPU utilization percentage
  - `vram_total_gb` - Total VRAM in GB
  - `vram_used_gb` - Used VRAM in GB
  - `vram_free_gb` - Free VRAM in GB
  - `vram_used_percent` - VRAM usage percentage

**NVIDIA GPU Response fields:**
- `type` - GPU type (NVIDIA)
- `gpus` - Array of GPU information:
  - `index` - GPU index
  - `name` - GPU model name
  - `temperature` - GPU temperature in Celsius
  - `gpu_utilization` - GPU usage percentage
  - `memory_utilization` - Memory usage percentage
  - `memory_total_mb` - Total memory in MB
  - `memory_used_mb` - Used memory in MB
  - `memory_free_mb` - Free memory in MB

#### Network Statistics
**GET /stats/network** - Network traffic information
```bash
curl http://localhost:5000/stats/network
```

**Response fields:**
- `bytes_sent_gb` - Total bytes sent in GB
- `bytes_recv_gb` - Total bytes received in GB
- `packets_sent` - Total packets sent
- `packets_recv` - Total packets received

#### Ollama Statistics
**GET /stats/ollama** - Running Ollama models information
```bash
curl http://localhost:5000/stats/ollama
```

**Response fields:**
- `running_models` - Number of currently running models
- `models` - Array of model information:
  - `name` - Model name
  - `size_gb` - Model size in GB
  - `vram_gb` - VRAM used by model in GB
  - `processor` - Processor type (CPU/GPU percentage)
  - `expires_at` - When model will be unloaded

#### Summary Statistics
**GET /stats/summary** - Brief overview of key metrics
```bash
curl http://localhost:5000/stats/summary
```

Returns a condensed view with:
- CPU usage percentage
- RAM usage (used/total and percentage)
- Disk usage percentage
- GPU usage and VRAM for each GPU
- Number of running Ollama models

## Response Examples

### Summary Response
```json
{
  "cpu_usage": "15.2%",
  "ram_usage": "1.65 GB / 31.32 GB (5.3%)",
  "disk_usage": "45.8%",
  "gpu_0_usage": "0%",
  "gpu_0_vram": "0.06 GB / 15.92 GB (0.35%)",
  "ollama_models": 1
}
```

### GPU Response (AMD)
```json
{
  "type": "AMD ROCm",
  "gpus": [
    {
      "name": "card0",
      "usage_percent": 0,
      "vram_total_gb": 15.92,
      "vram_used_gb": 0.06,
      "vram_free_gb": 15.86,
      "vram_used_percent": 0.35
    }
  ]
}
```

### CPU Response
```json
{
  "usage_percent": 15.2,
  "cores": 8,
  "threads": 16,
  "frequency_mhz": 3600.0,
  "per_core_usage": [12.5, 18.3, 14.7, 16.1, 13.9, 15.8, 17.2, 14.3]
}
```

### Ollama Response
```json
{
  "running_models": 1,
  "models": [
    {
      "name": "glm-4.7:fixed",
      "size_gb": 13.77,
      "vram_gb": 13.77,
      "processor": "100% GPU",
      "expires_at": "2026-02-03T18:12:25.883098758Z"
    }
  ]
}
```

## Requirements

### Python Packages
```txt
flask>=2.0.0
psutil>=5.8.0
requests>=2.26.0
```

### System Requirements

**For AMD GPU monitoring:**
- ROCm drivers installed
- `rocm-smi` command available in PATH

**For NVIDIA GPU monitoring:**
- NVIDIA drivers installed
- `nvidia-smi` command available in PATH

**For Ollama monitoring:**
- Ollama server running on localhost:11434 (default)
- Or modify `ollama_host` parameter in `get_ollama_info()` function

## Configuration

### Change Port
Modify the last line in `monitor.py`:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Change port here
```

### Change Ollama Host
If your Ollama server is on a different host/port, modify the function call:
```python
def get_ollama_info(ollama_host='http://192.168.110.158:11434'):
```

### Run as System Service

Create `/etc/systemd/system/monitor.service`:
```ini
[Unit]
Description=System Monitor API
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/script
ExecStart=/usr/bin/python3 /path/to/monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable monitor.service
sudo systemctl start monitor.service
```

### Production Deployment

For production, use a WSGI server like Gunicorn:
```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 monitor:app
```

## Troubleshooting

### GPU Not Detected

**AMD GPU:**
```bash
# Check if rocm-smi is installed
which rocm-smi

# Test rocm-smi manually
rocm-smi --showuse --showmeminfo vram --json
```

**NVIDIA GPU:**
```bash
# Check if nvidia-smi is installed
which nvidia-smi

# Test nvidia-smi manually
nvidia-smi
```

### Ollama Connection Failed

Check if Ollama is running:
```bash
curl http://localhost:11434/api/ps
```

If Ollama is on a different host, update the script.

### Permission Denied

If you get permission errors when accessing GPU commands, add your user to the appropriate group:

**AMD:**
```bash
sudo usermod -a -G video $USER
sudo usermod -a -G render $USER
```

**NVIDIA:**
```bash
sudo usermod -a -G video $USER
```

Then log out and log back in.

### Port Already in Use

Change the port in the script or kill the process using port 5000:
```bash
sudo lsof -i :5000
sudo kill -9 <PID>
```

## Usage Tips

### Continuous Monitoring

Use `watch` to monitor in terminal:
```bash
watch -n 1 'curl -s http://localhost:5000/stats/summary | jq'
```

### Save to Log File

Log statistics every 5 seconds:
```bash
while true; do 
  curl -s http://localhost:5000/stats/summary >> monitor.log
  echo "" >> monitor.log
  sleep 5
done
```

### Integration with Other Tools

**Prometheus:**
Extend the script to expose metrics in Prometheus format.

**Grafana:**
Use the JSON responses to create custom dashboards.

**Monitoring Scripts:**
Parse JSON responses in bash/python scripts for alerting.

## API Rate Limiting

Currently, there are no rate limits. For production use, consider adding rate limiting:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

## Security Considerations

1. **Firewall:** Restrict access to trusted IPs
2. **Authentication:** Add API key authentication for production
3. **HTTPS:** Use reverse proxy (nginx) with SSL certificate
4. **Debug Mode:** Disable debug mode in production (`debug=False`)

## License

This script is provided as-is for monitoring purposes.

## Support

For issues or questions:
- Check system logs: `journalctl -u monitor.service`
- Verify dependencies are installed
- Test individual commands (rocm-smi, nvidia-smi) manually