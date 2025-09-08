# ComBadge - Natural Language to API Converter

<img src="https://github.com/mklemmingen/ComBadge/blob/e25f0a39ae53464b13468861891140e33060cfef/NLP2API_Architecture.drawio.png?raw=true" alt="NLP2API Architecture">

ComBadge transforms natural language requests into API calls. Simply type or paste your request, review the AI's 
understanding, and approve the generated API call.

For example:

**"Reserve vehicle F-123 for tomorrow 2-4pm"** → **Structured API Request** → **Executed with Approval**

Disclaimer: 

The displayed framework is the bare NLP 2 API solution without any configuration to existing systems. 
No actual api documentation was used in documentating and planning this repo. 
It was created outside of work-time and is inspired by the need of real-world systems to have fully-private non-cloud 
solutions for intent detection and json population for process optimization and automation. 

As such, you are free to fork and use this repo in the state in which it is here while crediting is required. 
The system will not receive bug fixes or changes that could correlate to real world enterprise patterns. 

The GUI features configuration to API-Endpoints and Templates, but it is advised to fork, change the hardcoded templates, 
as well as prompts etc, so to better fit your needs.

## Quick Start

### Prerequisites
- Python 3.9+ (for running from source)
- 8GB+ RAM
- 10GB+ free disk space

### Install & Run

#### Option 1: Windows Installer (Recommended)
```bash
# Download and run the installer
ComBadge_Setup.exe

# First launch will automatically:
# - Install Ollama if needed (~150MB)
# - Download AI model (~8GB)
# - Configure everything for you
```

#### Option 2: From Source
```bash
# 1. Clone and install
git clone https://github.com/mklemmingen/Combadge.git
cd combadge
pip install -r requirements/base.txt

# 2. Launch ComBadge
python main.py
# Setup wizard will handle Ollama installation automatically
```

### First Request
1. **Type**: `"Schedule maintenance for vehicle F-123 next Friday"`
2. **Review**: Check AI understanding and generated JSON
3. **Configure**: Update API endpoint in Settings
4. **Approve**: Execute the request

## Configuration

**Essential Setup:**
- **API Endpoint**: `Settings → API → Base URL`
- **Authentication**: Configure your API credentials  
- **Templates**: Customize for your system's JSON format

See **[Configuration Guide](docs/admin_guide/configuration.md)** for detailed setup.

## Key Features

- **One-Click Setup**: Automatic Ollama installation and model download
- **Local Processing**: All AI runs locally via Ollama
- **Human Oversight**: Review every request before execution
- **Transparent AI**: See exactly how requests are interpreted
- **Audit Trail**: Complete logging of all operations
- **Secure**: No data leaves your machine

## Architecture

ComBadge follows a modular 3-tier design:

- **UI Layer**: CustomTkinter-based modern desktop interface
- **Business Logic Layer**: Core processing, LLM integration, and API generation
- **Data Persistence Layer**: SQLite for audit logs and configuration storage

```mermaid
graph TB
    subgraph "User Input Layer"
        A[Single Text Input Interface<br/>CustomTkinter Text Area<br/>Email Content or Natural Language Commands<br/>Placeholder: "Paste email or enter your command..."]
    end
    
    subgraph "Local LLM Management Layer"
        B[Ollama Server Manager<br/>llm_manager.py]
        B1[Qwen 2.5-14B Model Loading<br/>4-bit Quantization (Q4_K_M)<br/>Automatic Server Lifecycle]
        B2[Health Monitoring<br/>/api/tags endpoint checking<br/>Model Cache Management]
    end
    
    subgraph "Natural Language Processing Engine"
        C[Reasoning Engine<br/>reasoning_engine.py<br/>Chain of Thought Processing]
        
        subgraph "Chain of Thought Streaming"
            C1[Real-time Stream Processing<br/>50ms Update Intervals<br/>Queue-based UI Updates]
            C2[Reasoning Visualization<br/>Semantic Highlighting<br/>Step-by-step Analysis Display]
        end
        
        subgraph "Core NLP Components"
            D[Intent Classifier<br/>intent_classifier.py<br/>VEHICLE_OPERATION, MAINTENANCE_REQUEST<br/>RESERVATION_BOOKING, PARKING_ASSIGNMENT]
            E[Entity Extractor<br/>entity_extractor.py<br/>Vehicle IDs, VINs, Dates, Locations<br/>Confidence Scoring 0-1.0]
            F[Input Processor<br/>email_parser.py + command_processor.py<br/>Email Header Detection + Content Cleaning]
        end
    end
    
    subgraph "Fleet Management Intelligence"
        G[Template Management System<br/>template_manager.py]
        G1[Template Selection<br/>template_selector.py<br/>Intent-based Template Matching]
        G2[JSON Generation<br/>json_generator.py<br/>Entity Population + Validation]
        G3[Knowledge Base Integration<br/>knowledge/ directory<br/>API Docs, Business Rules, Prompts]
    end
    
    subgraph "Human-in-the-Loop Approval"
        H[Approval Workflow Interface<br/>approval_workflow.py<br/>CustomTkinter Components]
        H1[Request Preview<br/>Human-readable Summary<br/>Technical JSON Display<br/>Confidence Indicators]
        H2[User Actions<br/>Approve | Edit & Approve<br/>Regenerate | Reject]
        H3[Inline Editing<br/>JSON Editor with Validation<br/>Syntax Highlighting]
    end
    
    subgraph "API Execution Layer"
        I[HTTP Client Manager<br/>client.py + authentication.py]
        I1[Authentication Management<br/>Cookie/Token Storage<br/>Windows Credential Manager]
        I2[Request Execution<br/>Retry Logic + Error Handling<br/>TLS 1.3 + Certificate Validation]
        I3[Response Processing<br/>Status Code Handling<br/>Success/Error Reporting]
    end
    
    subgraph "Data Persistence & Audit"
        J[SQLite Database<br/>connection_manager.py]
        J1[Audit Logging<br/>audit_logger.py<br/>All User Actions + API Calls<br/>Tamper-evident Storage]
        J2[Configuration Storage<br/>config_repository.py<br/>User Preferences + Settings]
        J3[Performance Metrics<br/>Processing Time, Success Rate<br/>Memory Usage Tracking]
    end
    
    subgraph "Output & Results"
        K[API Response Display<br/>Success/Error Status<br/>Response Details]
        L[Audit Trail Export<br/>CSV/JSON Format<br/>Compliance Reporting]
        M[Session Management<br/>Request History<br/>User Preferences Persistence]
    end
    
    A --> B
    B --> B1
    B1 --> B2
    B2 --> C
    C --> C1
    C --> C2
    C --> D
    C --> E
    C --> F
    D --> G
    E --> G
    F --> G
    G --> G1
    G1 --> G2
    G2 --> G3
    G3 --> H
    H --> H1
    H1 --> H2
    H2 --> H3
    H3 --> I
    I --> I1
    I1 --> I2
    I2 --> I3
    I3 --> J
    J --> J1
    J1 --> J2
    J2 --> J3
    J3 --> K
    J3 --> L
    J3 --> M
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style G fill:#e8f5e8
    style H fill:#ffecb3
    style I fill:#fce4ec
    style J fill:#f0f8ff
    style K fill:#e8f5e8
    style L fill:#e8f5e8
    style M fill:#e8f5e8
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements/base.txt
   ```
3. Ensure Ollama is installed and running with the Qwen 2.5-14B model
4. Run the application:
   ```bash
   python main.py
   ```

## Configuration

Configuration is managed through YAML files in the `config/` directory. The default configuration can be customized to match your fleet management API specifications.

## Building and Deployment

For building executable distributions and enterprise deployment:

- **[Build System Documentation](docs/developer_guide/build_system.md)** - Complete build process
- **[Deployment Guide](docs/developer_guide/deployment_guide.md)** - Enterprise deployment strategies
- **[Quick Build Reference](scripts/BUILD.md)** - Essential build commands

### Quick Build

```bash
# Build Windows executable
python scripts/build/build_executable.py --clean

# Create installer
python scripts/build/package_installer.py --type installer
```

## Development

This project uses:
- Python 3.9+
- CustomTkinter for UI
- Ollama for local LLM processing
- SQLite for data persistence
- PyYAML for configuration management

For development setup, see [Developer Guide](docs/developer_guide/getting_started.md).

## License

[License information to be added]
