SHELL := /bin/bash
PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SOLUTION := $(PROJECT_DIR)/src/scheduler.py
GRADER_DIR := $(PROJECT_DIR)/grader

.PHONY: run test test-public test-custom test-brutal test-professor test-edge test-all \
        fuzz stress deterministic visualize grade clean help

# ── Run ──────────────────────────────────────────────────────────────

run:
	@python3 $(SOLUTION)

# ── Individual test suites ───────────────────────────────────────────

test-public:
	@$(GRADER_DIR)/grade.sh $(PROJECT_DIR)/tests/public

test-custom:
	@$(GRADER_DIR)/grade.sh $(PROJECT_DIR)/tests/custom

test-brutal:
	@$(GRADER_DIR)/grade.sh $(PROJECT_DIR)/tests/brutal

test-professor:
	@$(GRADER_DIR)/grade.sh $(PROJECT_DIR)/tests/professor

test-edge:
	@$(GRADER_DIR)/grade.sh $(PROJECT_DIR)/tests/edge

# ── Combined test targets ───────────────────────────────────────────

test: test-public test-custom test-brutal test-professor test-edge

test-all: test fuzz stress

# ── Fuzz testing ─────────────────────────────────────────────────────

fuzz:
	@python3 $(PROJECT_DIR)/tests/fuzz/fuzz_scheduler.py --runs 1000 --seed 42

# ── Stress testing ───────────────────────────────────────────────────

stress:
	@python3 $(PROJECT_DIR)/tests/stress/generate_stress.py
	@python3 $(PROJECT_DIR)/tests/stress/run_stress.py

# ── Determinism validation ───────────────────────────────────────────

deterministic:
	@python3 $(PROJECT_DIR)/tools/check_determinism.py --runs 100 --all

# ── Visualization ────────────────────────────────────────────────────

visualize:
	@echo "Usage: python3 tools/visualize.py <input_file> [--format ascii|png]"
	@echo "Example: python3 tools/visualize.py tests/public/01_input.txt"

# ── Grader ───────────────────────────────────────────────────────────

grade:
	@python3 $(GRADER_DIR)/grader.py

# ── Cleanup ──────────────────────────────────────────────────────────

clean:
	@rm -f trace.json metrics.json dependency_graph.dot dependency_graph.png
	@rm -f timeline_chart.png resource_usage_chart.png
	@echo "Cleaned generated files."

# ── Help ─────────────────────────────────────────────────────────────

help:
	@echo "Task Scheduler — Available targets:"
	@echo ""
	@echo "  make run            Run the scheduler interactively"
	@echo "  make test           Run all deterministic test suites (150 tests)"
	@echo "  make test-public    Run public tests (5)"
	@echo "  make test-custom    Run custom tests (30)"
	@echo "  make test-brutal    Run brutal tests (35)"
	@echo "  make test-professor Run professor tests (30)"
	@echo "  make test-edge      Run edge case tests (50)"
	@echo "  make fuzz           Run 1000 fuzz tests with invariant checking"
	@echo "  make stress         Run large-scale stress tests"
	@echo "  make deterministic  Verify determinism (100 runs per test)"
	@echo "  make test-all       Run everything: test + fuzz + stress"
	@echo "  make grade          Run categorical grader"
	@echo "  make visualize      Show visualization usage"
	@echo "  make clean          Remove generated files"
