.PHONY: test vsix install-ext clean

# Run all tests (no browser required)
test:
	python -m pytest unit_tests/ -v

# Build the VS Code extension .vsix package
# Requires: cd vscode-extension && npm install  (already done)
# Requires: npm install -g @vscode/vsce
vsix:
	cd vscode-extension && npx vsce package --out ../bddframe-$(shell python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])").vsix

# Install the extension directly into VS Code (skips marketplace)
install-ext: vsix
	code --install-extension bddframe-$(shell python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])").vsix

# Remove build artefacts
clean:
	rm -f bddframe-*.vsix
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
