from flask import Flask, jsonify
import psutil
import subprocess
import json
import requests

app = Flask(__name__)

def get_cpu_info():
    """Get CPU information"""
    return {
        'usage_percent': psutil.cpu_percent(interval=1),
        'cores': psutil.cpu_count(logical=False),
        'threads': psutil.cpu_count(logical=True),
        'frequency_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
        'per_core_usage': psutil.cpu_percent(interval=1, percpu=True)
    }

def get_memory_info():
    """Get RAM information"""
    mem = psutil.virtual_memory()
    return {
        'total_gb': round(mem.total / (1024**3), 2),
        'used_gb': round(mem.used / (1024**3), 2),
        'available_gb': round(mem.available / (1024**3), 2),
        'percent': mem.percent
    }

def get_disk_info():
    """Get disk information"""
    disk = psutil.disk_usage('/')
    return {
        'total_gb': round(disk.total / (1024**3), 2),
        'used_gb': round(disk.used / (1024**3), 2),
        'free_gb': round(disk.free / (1024**3), 2),
        'percent': disk.percent
    }

def get_amd_gpu_info():
    """Get AMD GPU information via rocm-smi"""
    try:
        result = subprocess.run(
            ['rocm-smi', '--showuse', '--showmeminfo', 'vram', '--json'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                formatted = []
                for card_name, card_data in data.items():
                    vram_total = int(card_data.get('VRAM Total Memory (B)', 0))
                    vram_used = int(card_data.get('VRAM Total Used Memory (B)', 0))
                    
                    gpu_info = {
                        'name': card_name,
                        'usage_percent': int(card_data.get('GPU use (%)', 0)),
                        'vram_total_gb': round(vram_total / (1024**3), 2),
                        'vram_used_gb': round(vram_used / (1024**3), 2),
                        'vram_free_gb': round((vram_total - vram_used) / (1024**3), 2),
                        'vram_used_percent': round((vram_used / vram_total) * 100, 2) if vram_total > 0 else 0
                    }
                    formatted.append(gpu_info)
                
                return {
                    'type': 'AMD ROCm',
                    'gpus': formatted
                }
            except Exception as e:
                return {
                    'type': 'AMD ROCm',
                    'error': f'Parse error: {str(e)}',
                    'raw': data
                }
    except Exception as e:
        return {'error': str(e), 'type': 'AMD ROCm'}

def get_nvidia_gpu_info():
    """Get NVIDIA GPU information via nvidia-smi"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            gpus = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = [p.strip() for p in line.split(',')]
                    gpus.append({
                        'index': int(parts[0]),
                        'name': parts[1],
                        'temperature': int(parts[2]) if parts[2] != '[N/A]' else None,
                        'gpu_utilization': int(parts[3]) if parts[3] != '[N/A]' else None,
                        'memory_utilization': int(parts[4]) if parts[4] != '[N/A]' else None,
                        'memory_total_mb': int(parts[5]) if parts[5] != '[N/A]' else None,
                        'memory_used_mb': int(parts[6]) if parts[6] != '[N/A]' else None,
                        'memory_free_mb': int(parts[7]) if parts[7] != '[N/A]' else None,
                    })
            return {'gpus': gpus, 'type': 'NVIDIA'}
        
        return {'error': 'nvidia-smi failed', 'type': 'NVIDIA'}
    except FileNotFoundError:
        return None
    except Exception as e:
        return {'error': str(e), 'type': 'NVIDIA'}

def get_gpu_info():
    """Auto-detect GPU type"""
    nvidia_info = get_nvidia_gpu_info()
    if nvidia_info:
        return nvidia_info
    
    return get_amd_gpu_info()

def get_ollama_info(ollama_host='http://localhost:11434'):
    """Get running Ollama models information"""
    try:
        response = requests.get(f'{ollama_host}/api/ps', timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get('models', []):
                models.append({
                    'name': model.get('name'),
                    'size_gb': round(model.get('size', 0) / (1024**3), 2),
                    'vram_gb': round(model.get('size_vram', 0) / (1024**3), 2),
                    'processor': model.get('processor', 'Unknown'),
                    'expires_at': model.get('expires_at')
                })
            return {
                'running_models': len(models),
                'models': models
            }
        return {'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'error': str(e)}

def get_network_info():
    """Get network information"""
    net = psutil.net_io_counters()
    return {
        'bytes_sent_gb': round(net.bytes_sent / (1024**3), 2),
        'bytes_recv_gb': round(net.bytes_recv / (1024**3), 2),
        'packets_sent': net.packets_sent,
        'packets_recv': net.packets_recv
    }

@app.route('/stats')
def get_all_stats():
    """Get all statistics"""
    return jsonify({
        'timestamp': psutil.boot_time(),
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'disk': get_disk_info(),
        'gpu': get_gpu_info(),
        'network': get_network_info(),
        'ollama': get_ollama_info()
    })

@app.route('/stats/cpu')
def cpu_stats():
    """CPU statistics only"""
    return jsonify(get_cpu_info())

@app.route('/stats/memory')
def memory_stats():
    """RAM statistics only"""
    return jsonify(get_memory_info())

@app.route('/stats/disk')
def disk_stats():
    """Disk statistics only"""
    return jsonify(get_disk_info())

@app.route('/stats/gpu')
def gpu_stats():
    """GPU statistics only"""
    return jsonify(get_gpu_info())

@app.route('/stats/network')
def network_stats():
    """Network statistics only"""
    return jsonify(get_network_info())

@app.route('/stats/ollama')
def ollama_stats():
    """Ollama statistics only"""
    return jsonify(get_ollama_info())

@app.route('/stats/summary')
def summary_stats():
    """Brief summary"""
    cpu = get_cpu_info()
    mem = get_memory_info()
    gpu = get_amd_gpu_info()
    ollama = get_ollama_info()
    
    summary = {
        'cpu_usage': f"{cpu['usage_percent']}%",
        'ram_usage': f"{mem['used_gb']} GB / {mem['total_gb']} GB ({mem['percent']}%)",
        'disk_usage': f"{get_disk_info()['percent']}%"
    }
    
    if 'gpus' in gpu:
        for i, card in enumerate(gpu['gpus']):
            summary[f'gpu_{i}_usage'] = f"{card['usage_percent']}%"
            summary[f'gpu_{i}_vram'] = f"{card['vram_used_gb']} GB / {card['vram_total_gb']} GB ({card['vram_used_percent']}%)"
    
    if 'models' in ollama:
        summary['ollama_models'] = ollama['running_models']
    
    return jsonify(summary)

@app.route('/')
def index():
    """Home page with documentation"""
    return jsonify({
        'service': 'System Monitor API',
        'endpoints': {
            '/stats': 'All statistics',
            '/stats/cpu': 'CPU information',
            '/stats/memory': 'RAM information',
            '/stats/disk': 'Disk information',
            '/stats/gpu': 'GPU information',
            '/stats/network': 'Network information',
            '/stats/ollama': 'Ollama models',
            '/stats/summary': 'Brief summary'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)