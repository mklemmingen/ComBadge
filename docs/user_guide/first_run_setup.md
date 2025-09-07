# ComBadge First Run Setup Guide

This guide explains the automatic setup process that runs when you first launch ComBadge.

## Overview

ComBadge includes an intelligent setup wizard that automatically:
- Detects if Ollama is installed
- Downloads and installs Ollama if needed
- Configures the Ollama service
- Downloads the required AI model (~8GB)
- Verifies everything is working correctly

## First Launch Experience

### 1. Starting ComBadge

When you run ComBadge for the first time:

**Windows Installer:**
```
Double-click ComBadge.exe from Start Menu or Desktop
```

**From Source:**
```bash
python main.py
```

### 2. Setup Wizard

The setup wizard will appear automatically if:
- Ollama is not installed
- The AI model is not downloaded
- This is your first time running ComBadge

![Setup Wizard Overview]
- Welcome screen explaining the setup process
- Progress tracking for each component
- Estimated download times based on your connection

### 3. Automatic Installation Steps

#### Step 1: Ollama Installation (if needed)
- **Download Size**: ~150MB
- **Duration**: 1-2 minutes
- **What happens**: 
  - Downloads Ollama installer from official source
  - Runs silent installation
  - No user interaction required

#### Step 2: Service Configuration
- **Duration**: < 30 seconds
- **What happens**:
  - Starts Ollama background service
  - Verifies API connectivity
  - Configures local endpoints

#### Step 3: AI Model Download
- **Download Size**: ~8GB (qwen2.5:14b model)
- **Duration**: 10-60 minutes (depends on internet speed)
- **What happens**:
  - Downloads AI model in chunks
  - Shows real-time progress
  - Can be paused/resumed

### 4. Setup Complete

Once setup is complete:
- Main ComBadge window appears
- AI is ready for processing
- No further setup needed

## Network Requirements

### Bandwidth Estimates

| Internet Speed | Total Setup Time |
|----------------|------------------|
| 100 Mbps | ~15 minutes |
| 50 Mbps | ~30 minutes |
| 25 Mbps | ~60 minutes |
| 10 Mbps | ~2.5 hours |

### Firewall Considerations

ComBadge may need firewall exceptions for:
- Downloading Ollama installer (HTTPS)
- Downloading AI models (HTTPS)
- Local Ollama API (localhost:11434)

## Troubleshooting

### Setup Wizard Doesn't Appear

If the wizard doesn't appear but ComBadge isn't working:

1. **Manual Ollama Check:**
   ```bash
   ollama --version
   ```

2. **Manual Model Check:**
   ```bash
   ollama list
   ```

3. **Reset Setup State:**
   Delete `~/.combadge/setup_state.json` and restart ComBadge

### Download Interrupted

The setup wizard automatically resumes interrupted downloads:
- Progress is saved
- Partial downloads are retained
- Simply restart ComBadge to continue

### Installation Fails

Common issues and solutions:

**"Administrator privileges required"**
- Right-click ComBadge.exe → "Run as Administrator"

**"Insufficient disk space"**
- Ensure 10GB+ free space
- Check both system drive and user profile drive

**"Network error downloading"**
- Check internet connection
- Verify firewall/proxy settings
- Try manual download from https://ollama.ai

### Slow Download Speed

To improve download speed:
1. Close bandwidth-intensive applications
2. Use wired connection if possible
3. Download during off-peak hours
4. Consider manual model download:
   ```bash
   ollama pull qwen2.5:14b
   ```

## Manual Setup (Advanced)

If automatic setup fails, you can install manually:

### 1. Install Ollama
```bash
# Windows
winget install ollama

# or download from
https://ollama.ai/download
```

### 2. Start Ollama Service
```bash
ollama serve
```

### 3. Download Model
```bash
ollama pull qwen2.5:14b
```

### 4. Verify Installation
```bash
# Check service
curl http://localhost:11434/api/version

# Check model
ollama list
```

## Privacy and Security

During setup:
- **No personal data is collected**
- **Downloads use HTTPS encryption**
- **All processing remains local**
- **No telemetry or analytics**

The setup wizard only:
- Downloads official Ollama binaries
- Downloads open-source AI models
- Saves setup state locally

## Offline Installation

For air-gapped environments:

1. **Pre-download on internet-connected machine:**
   - Ollama installer
   - Model file using `ollama pull`

2. **Transfer files to target machine**

3. **Install manually:**
   - Run Ollama installer
   - Import model with `ollama import`

4. **Run ComBadge**

## Frequently Asked Questions

**Q: Can I cancel the setup?**
A: Yes, click Cancel anytime. Progress is saved and will resume next launch.

**Q: Is the setup one-time only?**
A: Yes, once complete, ComBadge starts directly in future.

**Q: Can I use a different model?**
A: Yes, configure in Settings after setup completes.

**Q: Where is Ollama installed?**
A: Default locations:
- Windows: `%LOCALAPPDATA%\Programs\Ollama`
- macOS: `/Applications/Ollama.app`
- Linux: `/usr/local/bin/ollama`

**Q: How much total disk space is needed?**
A: Approximately:
- ComBadge: 250MB
- Ollama: 200MB
- AI Model: 8GB
- **Total: ~8.5GB**

## Next Steps

After successful setup:
1. Read the [Getting Started Guide](getting_started.md)
2. Try your first natural language request
3. Configure API endpoints in Settings
4. Explore the [User Manual](user_manual.md)

## Support

If you encounter issues during setup:
1. Check the troubleshooting section above
2. Review logs in `logs/setup.log`
3. Report issues at https://github.com/mklemmingen/Combadge/issues