## Pull Request Checklist
- [ ] Tests pass: pytest tests/ -v
- [ ] Black formatted: black ingestion/ scripts/ tests/
- [ ] Imports sorted: isort ingestion/ scripts/ tests/
- [ ] Linting clean: flake8 ingestion/ scripts/ tests/
- [ ] Type checking: mypy ingestion/ --ignore-missing-imports
- [ ] README updated if needed
- [ ] ADR added if major decision made
