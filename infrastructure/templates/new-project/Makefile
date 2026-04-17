# {{PROJECT_NAME}} — Uniform Contract Makefile
#
# This Makefile implements the monorepo contract. Each target delegates
# to the project's native build system. Edit the commands below to match
# your language and toolchain.
#
# The contract targets are the stable interface between this subproject
# and the CI pipeline. CI calls these targets; it never calls cargo,
# pytest, cmake, etc. directly (Martin: Dependency Inversion Principle).

.PHONY: build test lint fmt-check fmt clean release

# Compile / prepare
build:
	@echo "[{{PROJECT_NAME}}] build not yet configured — edit Makefile"
	@exit 1

# Run all tests
test:
	@echo "[{{PROJECT_NAME}}] test not yet configured — edit Makefile"
	@exit 1

# Static analysis, linting
lint:
	@echo "[{{PROJECT_NAME}}] lint not yet configured — edit Makefile"
	@exit 1

# Verify formatting (no mutation)
fmt-check:
	@echo "[{{PROJECT_NAME}}] fmt-check not yet configured — edit Makefile"
	@exit 1

# Apply formatting
fmt:
	@echo "[{{PROJECT_NAME}}] fmt not yet configured — edit Makefile"
	@exit 1

# Remove build artifacts
clean:
	@echo "[{{PROJECT_NAME}}] clean not yet configured — edit Makefile"

# Produce release artifact (optional — remove if not needed)
release:
	@echo "[{{PROJECT_NAME}}] release not yet configured — edit Makefile"
	@exit 1

# --- Example implementations (uncomment and adapt one block) ---
#
# --- Rust ---
# build:
# 	cargo build
# test:
# 	cargo test
# lint:
# 	cargo clippy -- -D warnings
# fmt-check:
# 	cargo fmt -- --check
# fmt:
# 	cargo fmt
# clean:
# 	cargo clean
# release:
# 	cargo build --release
#
# --- Python ---
# build:
# 	python -m pip install -e .
# test:
# 	python -m pytest tests/
# lint:
# 	python -m ruff check src/ tests/
# fmt-check:
# 	python -m ruff format --check src/ tests/
# fmt:
# 	python -m ruff format src/ tests/
# clean:
# 	rm -rf __pycache__ .pytest_cache *.egg-info dist build
# release:
# 	python -m build
#
# --- C/C++ (CMake) ---
# build:
# 	cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
# 	cmake --build build -j$$(nproc)
# test:
# 	ctest --test-dir build --output-on-failure
# lint:
# 	cmake --build build --target clang-tidy
# 	cmake --build build --target cppcheck
# fmt-check:
# 	find src/ -name '*.cpp' -o -name '*.h' | xargs clang-format --dry-run -Werror
# fmt:
# 	find src/ -name '*.cpp' -o -name '*.h' | xargs clang-format -i
# clean:
# 	rm -rf build
# release:
# 	cmake -B build -DCMAKE_BUILD_TYPE=Release
# 	cmake --build build -j$$(nproc)
#
# --- Go ---
# build:
# 	go build ./...
# test:
# 	go test ./...
# lint:
# 	golangci-lint run
# fmt-check:
# 	gofmt -l . | grep . && exit 1 || true
# fmt:
# 	gofmt -w .
# clean:
# 	go clean ./...
# release:
# 	go build -ldflags="-s -w" -o dist/ ./...
