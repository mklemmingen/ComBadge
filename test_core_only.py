#!/usr/bin/env python3
"""Test ComBadge core components without importing any GUI modules"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing ComBadge core components (no GUI)...\n")

# Test 1: Config Manager (without GUI imports)
try:
    print("1. Testing configuration...")
    # Direct import to avoid GUI dependencies
    import yaml
    from pathlib import Path
    
    config_path = Path("config/default_config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print(f"✓ Config loaded: {list(config.keys())}")
    else:
        print("✗ Config file not found")
except Exception as e:
    print(f"✗ Config test failed: {e}")

# Test 2: Logging (without GUI)
try:
    print("\n2. Testing logging...")
    import logging
    from pathlib import Path
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "test.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("test")
    logger.info("Test log message")
    print("✓ Logging working")
except Exception as e:
    print(f"✗ Logging test failed: {e}")

# Test 3: Ollama detection
try:
    print("\n3. Testing Ollama detection...")
    import subprocess
    
    # Simple Ollama check
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ Ollama found: {result.stdout.strip()}")
        else:
            print("✗ Ollama not found")
    except FileNotFoundError:
        print("✗ Ollama not installed")
    except Exception as e:
        print(f"✗ Ollama check error: {e}")
        
    # Check if Ollama service is running
    try:
        import requests
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            print(f"✓ Ollama service running: {response.json()}")
        else:
            print("✗ Ollama service not responding")
    except:
        print("✗ Ollama service not running")
        
except Exception as e:
    print(f"✗ Ollama test failed: {e}")

# Test 4: Check knowledge base
try:
    print("\n4. Testing knowledge base...")
    from pathlib import Path
    
    kb_path = Path("knowledge")
    if kb_path.exists():
        template_count = len(list(kb_path.rglob("*.json")))
        prompt_count = len(list(kb_path.rglob("*.txt")))
        yaml_count = len(list(kb_path.rglob("*.yaml")))
        print(f"✓ Knowledge base found: {template_count} templates, {prompt_count} prompts, {yaml_count} configs")
    else:
        print("✗ Knowledge base directory not found")
except Exception as e:
    print(f"✗ Knowledge base test failed: {e}")

# Test 5: Check Python dependencies
try:
    print("\n5. Testing Python dependencies...")
    required_packages = [
        ('requests', 'requests'),
        ('yaml', 'pyyaml'),  # import name vs package name
        ('psutil', 'psutil'),
        ('aiohttp', 'aiohttp'),
        ('pydantic', 'pydantic')
    ]
    
    import importlib
    missing = []
    for import_name, package_name in required_packages:
        try:
            importlib.import_module(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            missing.append(package_name)
            print(f"✗ {package_name} - not installed")
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
except Exception as e:
    print(f"✗ Dependency test failed: {e}")

print("\n" + "="*50)
print("Core component testing completed!")
print("="*50)
print("\nOnce tk is installed with 'sudo pacman -S tk', you can run:")
print("  python main.py")
print("\nThis will launch the full ComBadge application with GUI.")