.PHONY: clean build release release-patch release-minor release-major version-patch version-minor version-major

clean:
	rm -rf dist/ build/ *.egg-info/

build: clean
	python -m build

# Helper functions to increment version numbers using Python
define increment_version
	$(eval NEW_VERSION := $(shell python -c "import re; \
		version = '$(shell grep '^version = ' pyproject.toml | sed 's/version = \"\(.*\)\"/\1/')'; \
		major, minor, patch = map(int, version.split('.')); \
		$(1); \
		print(f'{major}.{minor}.{patch}')"))
	@sed -i 's/^version = .*/version = "$(NEW_VERSION)"/' pyproject.toml
	@echo "Version updated to $(NEW_VERSION)"
endef

version-patch:
	$(call increment_version,patch += 1)

version-minor:
	$(call increment_version,minor += 1; patch = 0)

version-major:
	$(call increment_version,major += 1; minor = 0; patch = 0)

# Release targets that handle git operations and PyPI upload
define do_release
	@if [ -z "$$PYPI_TOKEN" ]; then \
		echo "Error: PYPI_TOKEN environment variable not set"; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: Working directory not clean. Commit or stash changes first."; \
		exit 1; \
	fi
	@echo "Running $(1) release..."
	@$(MAKE) version-$(1)
	git add pyproject.toml
	git commit -m "Release v$(NEW_VERSION)"
	git tag -a "v$(NEW_VERSION)" -m "Release v$(NEW_VERSION)"
	git push origin master "v$(NEW_VERSION)"
	@$(MAKE) build
	python -m twine upload -u __token__ -p "$$PYPI_TOKEN" dist/*
	@echo "Released v$(NEW_VERSION)"
endef

release-patch:
	$(call do_release,patch)

release-minor:
	$(call do_release,minor)

release-major:
	$(call do_release,major)

# Default release is patch version increment
release: release-patch
