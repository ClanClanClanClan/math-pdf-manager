# Math-PDF Manager

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-771%20tests-brightgreen.svg)](tests/)
[![Security](https://img.shields.io/badge/security-1214%20fixes-red.svg)](docs/reports/security_improvements_summary.md)

Academic PDF management system for mathematics research with advanced security, Unicode handling, and dependency injection architecture.

## Features

- 🔍 **Advanced PDF Processing**: Extract and validate academic paper metadata
- 🔐 **Security-First**: 1,214+ security improvements with comprehensive vulnerability mitigation
- 🌐 **Unicode Excellence**: Robust handling of mathematical notation and international text
- 🏗️ **Dependency Injection**: Modern, testable architecture with service containers
- 📊 **Comprehensive Validation**: Academic filename, author, and title validation
- 🧪 **Extensive Testing**: 771 test cases covering edge cases and security scenarios
- 📈 **Performance Optimized**: Caching, threading, and efficient algorithms

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/dylanpossamai/math-pdf-manager.git
cd math-pdf-manager

# Install dependencies
pip install -r config/requirements.txt

# Install development dependencies (optional)
pip install -r config/requirements-security.txt
```

### Basic Usage

```bash
# Process a directory of PDFs
python main.py /path/to/pdf/directory

# Enable debug mode
python main.py /path/to/pdf/directory --debug --verbose

# Generate reports
python main.py /path/to/pdf/directory --output report.html --csv_output report.csv

# Security-enhanced mode
python main.py /path/to/pdf/directory --secure-mode --strict
```

### Configuration

```bash
# Edit main configuration
vim config/config.yaml

# Add known authors
vim data/known_authors_1.txt

# Configure language-specific rules
vim data/languages/[language].yaml
```

## Architecture

### Core Components

- **src/core/**: Core processing engine with dependency injection
- **src/validators/**: Academic content validation
- **src/processing/**: Main processing pipeline
- **src/security/**: Security utilities and vulnerability scanning
- **src/parsers/**: PDF parsing and metadata extraction

### Security Features

- ✅ **Path Traversal Protection**: Prevents `../` attacks
- ✅ **Pickle Deserialization**: Migrated to safe JSON serialization
- ✅ **Unicode Security**: Null byte filtering and dangerous character detection
- ✅ **Thread Safety**: Race condition prevention with proper locking
- ✅ **Input Validation**: Comprehensive sanitization of all inputs

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run security tests only
python -m pytest tests/security/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Development

### Project Structure

```
├── src/                     # Main source code
│   ├── core/               # Core processing engine
│   ├── validators/         # Content validation
│   ├── security/           # Security utilities
│   └── main.py            # Application entry point
├── tests/                  # Test suite (771 tests)
├── config/                 # Configuration files
├── data/                   # Language rules and word lists
├── tools/                  # Development and analysis tools
└── docs/                   # Documentation and reports
```

### Code Quality

- **Type Hints**: Full mypy compliance
- **Security**: Bandit scanning and manual audits
- **Code Style**: Black formatting, isort imports
- **Testing**: pytest with hypothesis property-based testing

## Security Audit Results

Recent comprehensive security audit revealed:

- **1,214 security improvements** implemented
- **Zero critical vulnerabilities** remaining
- **Advanced threat protection** for academic environments
- **Paranoid-level testing** with 771 test cases

See [Security Report](docs/reports/security_improvements_summary.md) for details.

## Configuration

### Environment Variables

```bash
export MATH_PDF_DEBUG=1              # Enable debug mode
export MATH_PDF_SECURE_MODE=1        # Enable enhanced security
export MATH_PDF_CONFIG_DIR=/path     # Custom config directory
```

### Academic Customization

```yaml
# config/config.yaml
academic_settings:
  strict_validation: true
  math_notation_support: true
  unicode_normalization: "NFC"
  author_validation_level: "strict"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python -m pytest tests/`)
4. Run security checks (`bandit -r src/`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: dylan.possamai@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/dylanpossamai/math-pdf-manager/issues)
- 📖 Documentation: [ReadTheDocs](https://math-pdf-manager.readthedocs.io)

## Acknowledgments

- Mathematical notation handling inspired by academic publishing standards
- Security practices based on OWASP guidelines
- Unicode handling follows Unicode Consortium recommendations
- Testing methodology inspired by property-based testing principles