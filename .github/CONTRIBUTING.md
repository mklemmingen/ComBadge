# Contributing to ComBadge

Thank you for your interest in contributing to ComBadge! This document provides guidelines and information for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contributing Process](#contributing-process)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation Guidelines](#documentation-guidelines)
8. [Issue Guidelines](#issue-guidelines)
9. [Pull Request Guidelines](#pull-request-guidelines)
10. [Community](#community)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful, inclusive, and constructive in all interactions.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic understanding of fleet management concepts
- Familiarity with natural language processing (helpful but not required)

### Areas for Contribution

- **Core NLP Engine**: Improve intent classification and entity extraction
- **Fleet Management**: Enhance vehicle and maintenance management features  
- **API Integration**: Add support for new fleet management APIs
- **User Interface**: Improve user experience and workflow
- **Email Processing**: Enhance email-based request handling
- **Documentation**: Improve user and developer documentation
- **Testing**: Add test coverage and improve test quality
- **Performance**: Optimize processing speed and resource usage

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/Combadge.git
cd combadge

# Add upstream remote
git remote add upstream https://github.com/mklemmingen/Combadge.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Verify Setup

```bash
# Run tests to verify setup
make test-fast

# Check code quality
make lint
make type-check
```

## Contributing Process

### 1. Choose or Create an Issue

- Browse [existing issues](https://github.com/mklemmingen/Combadge/issues)
- Look for issues labeled `good first issue` or `help wanted`
- For new features, create an issue first to discuss the approach

### 2. Create a Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### 3. Make Changes

- Follow our [coding standards](#coding-standards)
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 4. Test Your Changes

```bash
# Run the full test suite
make test-all

# Run specific test categories
make test-unit          # Unit tests
make test-integration   # Integration tests
make test-performance   # Performance tests

# Check code quality
make lint
make type-check
make security-scan
```

### 5. Submit Pull Request

- Push your branch to your fork
- Create a pull request against the main branch
- Fill out the PR template completely
- Respond to review feedback promptly

## Coding Standards

### Python Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for code formatting and linting:

```bash
# Format code
ruff format src/ tests/

# Check for issues
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/
```

### Code Conventions

- **Line Length**: Maximum 88 characters
- **Imports**: Use absolute imports, group by standard/third-party/local
- **Type Hints**: All public functions must have type hints
- **Docstrings**: All classes and public functions must have docstrings
- **Variable Names**: Use descriptive names, avoid abbreviations

### Example Function

```python
async def process_vehicle_request(
    request_text: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> ProcessingResult:
    """
    Process a vehicle-related natural language request.
    
    Args:
        request_text: The user's natural language request
        user_id: Unique identifier for the requesting user
        context: Optional conversation context from previous interactions
        
    Returns:
        ProcessingResult containing analysis and generated API calls
        
    Raises:
        ValidationError: If the request cannot be validated
        APIError: If external API calls fail
    """
    # Implementation here
    pass
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Component interaction tests  
├── performance/    # Performance and load tests
└── fixtures/       # Test data and utilities
```

### Writing Tests

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions
- **Performance Tests**: Test performance characteristics
- **Coverage**: Aim for >90% code coverage

### Test Example

```python
import pytest
from unittest.mock import Mock, AsyncMock
from combadge.intelligence.nlp_processor import NLPProcessor

class TestNLPProcessor:
    @pytest.fixture
    def processor(self):
        llm_client = AsyncMock()
        return NLPProcessor(llm_client)
        
    @pytest.mark.asyncio
    async def test_vehicle_reservation_processing(self, processor):
        # Test implementation
        pass
        
    @pytest.mark.parametrize("request_text,expected_intent", [
        ("Reserve vehicle F-123", "vehicle_reservation"),
        ("Schedule maintenance", "maintenance_scheduling"),
    ])
    async def test_intent_classification(self, processor, request_text, expected_intent):
        # Test implementation
        pass
```

## Documentation Guidelines

### Types of Documentation

- **User Documentation**: For end users of ComBadge
- **Administrator Documentation**: For system administrators
- **Developer Documentation**: For contributors and integrators
- **API Documentation**: For API consumers

### Documentation Standards

- **Format**: Use Markdown for most documentation
- **Structure**: Use clear headings and table of contents
- **Examples**: Include practical examples and code snippets
- **Screenshots**: Add screenshots for UI-related documentation
- **Links**: Use relative links for internal documentation

### Docstring Format

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.
    
    More detailed explanation if needed. This can span multiple
    paragraphs and include implementation details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is invalid
        TypeError: When param2 is wrong type
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True
    """
    return True
```

## Issue Guidelines

### Before Creating an Issue

1. Search existing issues to avoid duplicates
2. Check the documentation for existing solutions
3. Verify you're using the latest version

### Issue Types

- **Bug Report**: Use the bug report template
- **Feature Request**: Use the feature request template  
- **Documentation**: Use the documentation template
- **Question**: Use discussions for questions

### Good Issue Characteristics

- **Clear Title**: Descriptive and specific
- **Detailed Description**: Include steps to reproduce for bugs
- **Environment Info**: OS, Python version, ComBadge version
- **Expected vs Actual**: What you expected vs what happened
- **Logs/Screenshots**: Include relevant error logs or screenshots

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally (`make test-all`)
- [ ] Code follows style guidelines (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Documentation is updated
- [ ] Self-review completed

### PR Requirements

- **Descriptive Title**: Clear description of changes
- **Complete Template**: Fill out all relevant sections
- **Focused Changes**: One feature/fix per PR
- **Test Coverage**: Include tests for new functionality
- **Documentation**: Update docs for user-facing changes

### Review Process

1. **Automated Checks**: CI/CD pipeline must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Reviewers may test functionality manually
4. **Documentation Review**: Ensure docs are accurate and complete
5. **Security Review**: For security-sensitive changes

### After Review

- **Address Feedback**: Respond to all review comments
- **Update Code**: Make requested changes promptly
- **Rebase if Needed**: Keep commit history clean
- **Final Approval**: Wait for approval before merging

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code review and collaboration

### Getting Help

- Check the [documentation](https://github.com/mklemmingen/Combadge/docs)
- Search existing issues and discussions
- Create a new discussion for questions
- Join our community discussions

### Recognition

We appreciate all contributions! Contributors will be:

- Listed in the CONTRIBUTORS.md file
- Mentioned in release notes for significant contributions
- Invited to join the maintainers team for sustained contributions

## Development Resources

### Useful Commands

```bash
# Development workflow
make install-dev       # Set up development environment
make test-watch        # Run tests on file changes
make docs-serve        # Serve documentation locally
make clean             # Clean build artifacts

# Code quality
make lint              # Run linting checks
make format            # Format code
make type-check        # Run type checking
make security-scan     # Run security analysis

# Testing
make test-fast         # Run fast unit tests
make test-all          # Run all tests
make test-coverage     # Generate coverage report
make test-performance  # Run performance tests
```

### Project Structure

```
combadge/
├── src/combadge/          # Main source code
├── tests/                 # Test suite
├── docs/                  # Documentation
├── config/                # Configuration files
├── scripts/               # Utility scripts
├── .github/               # GitHub templates and workflows
└── requirements*.txt      # Dependency files
```

## Questions?

If you have questions about contributing:

1. Check the [FAQ](https://github.com/mklemmingen/Combadge/docs/faq.md)
2. Search [existing discussions](https://github.com/mklemmingen/Combadge/discussions)
3. Create a new discussion
4. Contact the maintainers

Thank you for contributing to ComBadge! 🚗✨