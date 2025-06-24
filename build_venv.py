#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import shutil
import re

# Configuration
TGWUI_DIR = "/home/kdog/text-generation-webui"
VENV_DIR = os.path.join(TGWUI_DIR, "venv")
LOG_FILE = os.path.join(TGWUI_DIR, "launch.log")
PYTHON_310 = "/usr/bin/python3.10"

def log(msg):
    print(msg)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

def run(cmd, cwd=None, allow_fail=False):
    """Improved run command that handles venv paths correctly"""
    if cmd[0].endswith('python') or cmd[0].endswith('pip'):
        cmd[0] = os.path.join(VENV_DIR, 'bin', os.path.basename(cmd[0]))
    
    log(f"Running: {' '.join(cmd)}")
    env = os.environ.copy()
    env['PATH'] = f"{os.path.join(VENV_DIR, 'bin')}:{env.get('PATH', '')}"
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=not allow_fail,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        log(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        log(f"Command failed with code {e.returncode}: {' '.join(cmd)}")
        log(e.stdout)
        if not allow_fail:
            raise

def check_environment():
    """Verify critical environment paths and settings"""
    log("Checking environment...")
    
    # Verify Python version
    result = run([PYTHON_310, "--version"], allow_fail=True)
    if result.returncode != 0:
        raise RuntimeError(f"Python 3.10 not found at {PYTHON_310}")
    
    # Verify CUDA
    result = run(["nvcc", "--version"], allow_fail=True)
    if result.returncode == 0:
        log(f"CUDA detected: {result.stdout.splitlines()[0]}")
        version_match = re.search(r'release (\d+\.\d+)', result.stdout)
        if version_match:
            version_str = version_match.group(1)
            return version_str.split('.')  # Return as list ['11', '5']
    log("CUDA version could not be determined, continuing with CPU")

def install_core_dependencies(venv_python, cuda_version):
    """Install essential dependencies first"""
    log("Installing core dependencies...")
    
    # Base dependencies - matches bash script
    run([venv_python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    
    # Install PyTorch and other core packages - matches bash script
    core_packages = [
        "torch",
        "markdown",
        "pyyaml",
        "rich",
        "pillow",
        "psutil"
    ]
    run([venv_python, "-m", "pip", "install"] + core_packages)

def install_requirements(venv_python):
    """Install all requirements from full requirements.txt"""
    log("Installing requirements...")
    
    reqs_file = os.path.join(TGWUI_DIR, "requirements", "full", "requirements.txt")
    if os.path.exists(reqs_file):
        run([venv_python, "-m", "pip", "install", "-r", reqs_file])
    else:
        raise RuntimeError("requirements/full/requirements.txt not found!")

def install_llama_cpp(venv_python):
    """Install llama_cpp_binaries exactly like bash script"""
    log("Installing llama_cpp_binaries...")
    run([venv_python, "-m", "pip", "install", 
        "https://github.com/oobabooga/llama-cpp-binaries/releases/download/v0.20.0/llama_cpp_binaries-0.20.0+cu124-py3-none-linux_x86_64.whl"])

def setup_environment():
    """Set up environment variables"""
    log("Setting up environment variables...")
    
    os.environ["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["CUDA_HOME"] = "/usr/local/cuda"
    os.environ["PATH"] = f"/usr/local/cuda/bin:{os.environ.get('PATH', '')}"
    os.environ["PATH"] = f"{os.path.join(VENV_DIR, 'bin')}:{os.environ['PATH']}"

def start_server(venv_python):
    """Start the text generation webui server"""
    log("Starting server...")
    
    server_cmd = [
        venv_python,
        "server.py",
        "--listen",
        "--api"
    ]
    
    with open(LOG_FILE, 'a') as log_file:
        process = subprocess.Popen(
            server_cmd,
            cwd=TGWUI_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=os.environ,
            preexec_fn=os.setsid
        )
    
    log(f"Server started with PID: {process.pid}")
    time.sleep(10)
    
    # Verify server is running
    try:
        os.kill(process.pid, 0)
        log("✅ Server is running")
        log("Web UI: http://localhost:7860")
        return True
    except OSError:
        log("❌ Server failed to start")
        with open(LOG_FILE) as f:
            log("Last 20 lines of log:")
            for line in f.readlines()[-20:]:
                log(line.strip())
        return False

def main():
    # Initialize log
    with open(LOG_FILE, 'w') as f:
        f.write("=== Installation Log ===\n")
    
    log("Starting installation process...")
    try:
        cuda_version = check_environment()
        
        # Clean previous installation
        log("Cleaning previous installation...")
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        run(["pkill", "-f", "python3 server.py"], allow_fail=True)
        
        # Create fresh virtual environment
        log("Creating virtual environment...")
        run([PYTHON_310, "-m", "venv", VENV_DIR])
        venv_python = os.path.join(VENV_DIR, "bin", "python")
        
        # Installation steps - matches bash script order
        install_core_dependencies(venv_python, cuda_version)
        install_requirements(venv_python)
        install_llama_cpp(venv_python)  # Changed to match bash script
        setup_environment()
        
        # Verify installation
        log("Verifying installation...")
        run([venv_python, "-m", "pip", "check"], allow_fail=True)
        
        # Start server
        if not start_server(venv_python):
            sys.exit(1)
    except Exception as e:
        log(f"❌ Installation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()