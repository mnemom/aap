# Contributing to AAP

Thank you for your interest in contributing to the Agent Alignment Protocol.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/mnemom/aap.git
cd aap

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
pytest
```

## Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
ruff check .
ruff format .
```

## Type Checking

```bash
mypy src
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Reporting Issues

Please use [GitHub Issues](https://github.com/mnemom/aap/issues) for bug reports and feature requests.
