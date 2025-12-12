# Contributing to ASN 856 + SSCC Label Generator

Thank you for your interest in contributing to the ASN 856 + SSCC Label Generator project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions
- Respect differing viewpoints

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Other unprofessional conduct

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic understanding of EDI and supply chain concepts (helpful but not required)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/PROJECT-3-ASN-856-GENERATOR-DEMO.git
   cd PROJECT-3-ASN-856-GENERATOR-DEMO
   ```

3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/PROJECT-3-ASN-856-GENERATOR-DEMO.git
   ```

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
# Run tests
pytest tests/ -v

# Run CLI
python main.py --help

# Validate sample order
python main.py validate examples/sample_orders/order_001.json
```

### 4. Install Development Tools

```bash
pip install black mypy ruff pytest-cov
```

## How to Contribute

### Types of Contributions

We welcome:

1. **Bug Fixes** - Fix issues in existing functionality
2. **New Features** - Add new capabilities
3. **Documentation** - Improve or add documentation
4. **Tests** - Add or improve test coverage
5. **Performance** - Optimize existing code
6. **Code Quality** - Refactoring and cleanup

### Reporting Bugs

**Before submitting a bug report:**
- Check existing issues to avoid duplicates
- Verify the bug in the latest version
- Collect relevant information (OS, Python version, error messages)

**Bug Report Template:**
```markdown
**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. ...

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.0]
- Version: [e.g., 1.0.0]

**Additional Context:**
Any other relevant information
```

### Suggesting Enhancements

**Enhancement Request Template:**
```markdown
**Feature Description:**
Clear description of the proposed feature

**Use Case:**
Why is this feature needed?

**Proposed Solution:**
How would you implement it?

**Alternatives Considered:**
Other approaches you've thought about

**Additional Context:**
Any other relevant information
```

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

**Line Length:**
- Maximum 100 characters (not 79)
- Break long lines logically

**Imports:**
```python
# Standard library
import json
from datetime import datetime

# Third-party
from pydantic import BaseModel
import click

# Local
from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
```

**Type Hints:**
Always use type hints for function signatures:
```python
def process_order(order: OrderInput, config: CartonizationConfig) -> ShipmentPackage:
    """Process an order and return shipment package."""
    ...
```

**Docstrings:**
Use Google-style docstrings:
```python
def calculate_check_digit(digits: str) -> str:
    """
    Calculate GS1 mod-10 check digit.

    Args:
        digits: String of digits to calculate check digit for

    Returns:
        Single digit check digit as string

    Raises:
        ValueError: If digits contain non-numeric characters

    Example:
        >>> calculate_check_digit("00614141123456789")
        "8"
    """
    ...
```

### Code Formatting

**Use Black:**
```bash
black src/ tests/ main.py
```

**Use Ruff for Linting:**
```bash
ruff check src/ tests/ main.py
```

**Use mypy for Type Checking:**
```bash
mypy src/ main.py
```

### Naming Conventions

**Variables and Functions:**
- Use `snake_case`
- Be descriptive: `calculate_total_weight()` not `calc_wt()`

**Classes:**
- Use `PascalCase`
- Nouns: `CartonizationEngine`, `SSCCGenerator`

**Constants:**
- Use `UPPER_SNAKE_CASE`
- Define at module level: `MAX_CARTON_WEIGHT = 50.0`

**Private Methods:**
- Prefix with underscore: `_calculate_check_digit()`

## Testing Guidelines

### Writing Tests

**Test File Organization:**
```python
"""Tests for cartonization engine."""
import pytest
from src.cartonization.engine import CartonizationEngine

class TestCartonizationEngine:
    """Test suite for CartonizationEngine."""

    def test_simple_order_single_carton(self):
        """Test that small order fits in single carton."""
        # Arrange
        order = create_test_order(items=10)
        engine = CartonizationEngine()

        # Act
        result = engine.cartonize_order(order)

        # Assert
        assert len(result.shipment.cartons) == 1
        assert result.shipment.cartons[0].items[0].quantity == 10
```

**Test Coverage Requirements:**
- Aim for 80%+ code coverage
- Test happy paths AND error cases
- Test edge cases and boundary conditions

**Running Tests:**
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_cartonization.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test
pytest tests/test_cartonization.py::TestCartonizationEngine::test_simple_order_single_carton -v
```

### Test Categories

**Unit Tests:**
- Test individual functions/methods
- Mock external dependencies
- Fast execution (<1ms per test)

**Integration Tests:**
- Test module interactions
- Use real dependencies
- Moderate execution (<100ms per test)

**End-to-End Tests:**
- Test complete workflows
- Use sample data files
- Slower execution (<1s per test)

## Documentation

### Documentation Requirements

**Code Documentation:**
- All public functions must have docstrings
- Complex logic should have inline comments
- Type hints required for all function signatures

**User Documentation:**
- Update relevant .md files for feature changes
- Add examples for new features
- Keep QUICKSTART.md up to date

**API Documentation:**
- Document all CLI commands
- Include usage examples
- Document all options and arguments

### Documentation Style

**Markdown Files:**
- Use proper heading hierarchy (# → ## → ###)
- Include code examples with syntax highlighting
- Add tables for structured information
- Use emojis sparingly (✅, ❌, ⚠️ for status)

**Code Comments:**
```python
# Good: Explain WHY
# Calculate check digit using GS1 mod-10 to ensure barcode validity
check_digit = calculate_check_digit(sscc)

# Bad: Explain WHAT (code already shows this)
# Call calculate_check_digit function
check_digit = calculate_check_digit(sscc)
```

## Pull Request Process

### Before Submitting

1. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes:**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Test your changes:**
   ```bash
   pytest tests/ -v
   black src/ tests/ main.py --check
   mypy src/ main.py
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Add feature: concise description"
   ```

   **Commit Message Format:**
   ```
   <type>: <subject>

   <body>

   <footer>
   ```

   **Types:**
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation only
   - `style`: Code style changes (formatting)
   - `refactor`: Code refactoring
   - `test`: Adding/updating tests
   - `chore`: Maintenance tasks

   **Example:**
   ```
   feat: Add batch processing mode to CLI

   - Add --batch flag to process command
   - Support multiple input files
   - Add progress reporting for batch operations

   Closes #42
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Submitting Pull Request

1. Go to GitHub and create a Pull Request
2. Fill out the PR template:
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Code refactoring
   - [ ] Performance improvement

   ## Testing
   - [ ] All existing tests pass
   - [ ] Added new tests for changes
   - [ ] Manually tested changes

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No breaking changes (or documented)
   - [ ] Commit messages follow convention
   ```

3. Wait for review and address feedback

### Review Process

**What Reviewers Look For:**
- Code quality and style compliance
- Test coverage and quality
- Documentation completeness
- No breaking changes (or properly documented)
- Performance considerations

**Response Time:**
- Initial review within 3-5 business days
- Follow-up reviews within 1-2 business days

## Project Structure

### Key Directories

```
src/
├── models/          # Data models (Pydantic)
├── sscc/            # SSCC generation
├── cartonization/   # Cartonization logic
├── asn_builder/     # EDI 856 generation
└── label_generator/ # Label rendering

tests/               # Test suite
examples/            # Sample data and demos
docs/                # Documentation
```

### Adding New Modules

**When adding a new module:**
1. Create directory under `src/`
2. Add `__init__.py` with public API exports
3. Create corresponding test file in `tests/`
4. Update documentation in `docs/`
5. Add examples in `examples/` if applicable

**Module Template:**
```python
"""
Module description.

This module provides functionality for...
"""

from typing import List, Optional
from pydantic import BaseModel

# Public API
__all__ = ['ClassName', 'function_name']


class ClassName(BaseModel):
    """Class description."""
    ...


def function_name(param: str) -> str:
    """Function description."""
    ...
```

## Questions or Help?

- **Documentation:** Check [README.md](README.md) and [docs/](docs/)
- **Issues:** Search existing issues or create a new one
- **Discussions:** Use GitHub Discussions for questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

Thank you for contributing to the ASN 856 + SSCC Label Generator! 🎉
