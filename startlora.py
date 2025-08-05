#!/usr/bin/env python3
import subprocess
import os
import time
from pathlib import Path
import signal
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server_launcher.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'base_model': '/media/external_drive1/ai/textdata/models/TinyLlama-1.1B-Chat-v1.0',
    'lora_dir': '/home/kdog/pythonprojects/process_transcript/training/datasets/model-out',
    'webui_dir': '/home/kdog/text-generation-webui',
    'listen_port': 5001,
    'timeout': 300,
    'venv_dir': '/home/kdog/text-generation-webui/venv'
}

server_process = None

def validate_paths():
    """Verify all required paths and files exist"""
    required_paths = {
        'Base model': CONFIG['base_model'],
        'LoRA directory': CONFIG['lora_dir'],
        'WebUI directory': CONFIG['webui_dir'],
        'Virtual environment': CONFIG['venv_dir']
    }
    
    missing = []
    for name, path in required_paths.items():
        if not Path(path).exists():
            missing.append(f"{name} path does not exist: {path}")
    
    # Verify LoRA files
    lora_path = Path(CONFIG['lora_dir'])
    required_files = ['adapter_config.json']
    weight_files = ['adapter_model.bin', 'adapter_model.safetensors']
    
    if not any((lora_path / f).exists() for f in weight_files):
        missing.append(f"Missing LoRA weights (need one of: {weight_files})")
    
    for f in required_files:
        if not (lora_path / f).exists():
            missing.append(f"Missing required file: {f}")
    
    if missing:
        raise FileNotFoundError("\n".join(missing))

def start_server():
    """Start the server with the correct LORA path"""
    global server_process
    
    try:
        python_exec = str(Path(CONFIG['venv_dir']) / 'bin' / 'python')
        if not Path(python_exec).exists():
            raise FileNotFoundError(f"Python executable not found: {python_exec}")
        
        os.chdir(CONFIG['webui_dir'])
        logger.info(f"Changed to directory: {CONFIG['webui_dir']}")
        
        # Convert LORA path to absolute and ensure it's a string
        lora_path = str(Path(CONFIG['lora_dir']).absolute())
        
        cmd = [
            python_exec, "server.py",
            "--model", CONFIG['base_model'],
            "--lora", lora_path,
            "--lora-dir", str(Path(CONFIG['lora_dir']).parent.absolute()),
            "--listen",
            "--api",
            "--listen-port", str(CONFIG['listen_port']),
            "--verbose",
            "--nowebui"  # Remove if you want the web interface
        ]
        
        logger.info(f"Starting server with command:\n{' '.join(cmd)}")
        
        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output
        start_time = time.time()
        server_ready = False
        
        while time.time() - start_time < CONFIG['timeout']:
            if server_process.poll() is not None:
                break
                
            for line in server_process.stdout:
                line = line.strip()
                if line:
                    logger.info(line)
                    if "API is running" in line or "Loaded the model" in line:
                        server_ready = True
                        break
            
            for line in server_process.stderr:
                line = line.strip()
                if line:
                    logger.error(line)
            
            if server_ready:
                break
                
            time.sleep(0.1)
        
        if not server_ready:
            raise RuntimeError(f"Server failed to start within {CONFIG['timeout']} seconds")
            
        logger.info("✅ Server started successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        stop_server()
        return False

def stop_server():
    """Stop the server process"""
    global server_process
    if server_process:
        logger.info("🛑 Stopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None
        logger.info("Server stopped.")

def signal_handler(sig, frame):
    """Handle interrupt signal"""
    logger.info("\nReceived interrupt signal")
    stop_server()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🔍 Validating paths...")
    try:
        validate_paths()
        logger.info("✅ All paths validated")
    except Exception as e:
        logger.error(f"❌ Validation failed: {str(e)}")
        sys.exit(1)
    
    if start_server():
        try:
            while server_process and server_process.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            stop_server()
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()