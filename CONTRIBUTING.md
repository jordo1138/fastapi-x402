# Contributing to FastAPI x402

Thank you for your interest in contributing to FastAPI x402! We welcome contributions from the community.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/fastapi-x402.git
   cd fastapi-x402
   ```

2. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .[dev]
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following the existing style
   - Add tests for new functionality
   - Update documentation if needed

3. **Run tests and checks**
   ```bash
   # Format code
   black src tests
   isort src tests
   
   # Type checking
   mypy src
   
   # Run tests
   pytest
   
   # Run all checks
   pre-commit run --all-files
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - Use a descriptive title
   - Include details about the changes
   - Reference any related issues

## Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Tests
```bash
# Make sure you have test wallets set up
pytest tests/integration/
```

### End-to-End Tests
```bash
# Requires Base Sepolia testnet setup
pytest tests/e2e/
```

## Code Style

We use:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **pytest** for testing

## Commit Messages

We follow conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test changes
- `refactor:` for code refactoring

## What to Contribute

### Bug Reports
- Use GitHub Issues
- Include reproduction steps
- Include environment details

### Feature Requests
- Use GitHub Issues
- Describe the use case
- Include implementation ideas if you have them

### Code Contributions
- Bug fixes
- New features (discuss in an issue first)
- Documentation improvements
- Test coverage improvements

## Getting Help

- **Discord**: [x402 Community](https://discord.gg/x402)
- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
