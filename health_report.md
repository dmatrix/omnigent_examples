# Code Project Health Report
## Repository: [dmatrix/omnigent_examples](https://github.com/dmatrix/omnigent_examples)
**Inspection date:** 2026-07-03  
**Inspector:** Harness Portability Supervisor (Claude SDK)  
**Sub-agents dispatched:** 4 (structure_inspector · test_inspector · dependency_inspector · security_inspector)

---

## Overall Score: D+

| Category | Sub-Agent | Harness | Grade |
|---|---|---|---|
| 📁 Project Structure & Documentation | `structure_inspector` | Claude SDK | **B−** |
| 🧪 Test Coverage & CI | `test_inspector` | Codex | **F** |
| 📦 Dependency Health | `dependency_inspector` | Pi | **C+** |
| 🔒 Code Quality & Security | `security_inspector` | Hermes | **N/A** ⚠️ |

> **Note on Security grade:** The `security_inspector` (Hermes harness) failed on both attempts with exit code 1. The overall score is computed from the three available grades; a successful security inspection may alter the final result.

**Grade scale:** A=4.0, B=3.0, C=2.0, D=1.0, F=0.0  
**Computed average (3 of 4 categories):** B−(2.7) + F(0.0) + C+(2.3) = 5.0 ÷ 3 = **1.67 → D+**

---

## Category 1: Project Structure & Documentation
**Sub-agent:** `structure_inspector` (Claude SDK harness) — **Grade: B−**

### Findings

#### ✅ README Quality — A
- **Root `README.md`** is 382 lines with 9 shields.io badges, a full prerequisites section, install/usage docs, an annotated YAML config anatomy, a 15-row supported-models table, and a project structure tree.
- **Per-example READMEs** are exceptionally thorough — four files ranging from 306 to 427 lines, each embedding its own SVG architecture diagram.
- Minor gap: no testing section and no pointer to `CONTRIBUTING.md` in the root README.

#### ⚠️ LICENSE — C
- Apache License 2.0 is the correct choice and the full text is present.
- **The copyright appendix boilerplate was never filled in.** The file still reads `Copyright [yyyy] [name of copyright owner]` — making the copyright assertion legally incomplete.

#### ✅ `.gitignore` — A
- Full Python gitignore template plus custom Omnigent/MLflow entries (`.env`, `omnigent_generated_code/`, `omniagents.db`, `mlflow.db`). All expected patterns covered.

#### ✅ Directory Organization — B+
- Clean 5-level hierarchy; `snake_case` naming throughout all example directories.
- **One outlier:** `skills/customer-report/` uses kebab-case, inconsistent with the rest.
- **One name mismatch:** `pyproject.toml` identifies the project as `omniagents-harness`; the repo is `omnigent_examples`.
- Complete absence of a `tests/` directory is a meaningful structural gap.

#### ❌ Contributor Documentation — D
- `CLAUDE.md` and the `docs/` folder are solid for AI-assisted development.
- **Nothing** exists for human contributors: no `CONTRIBUTING.md`, no `CHANGELOG.md`, no `CODE_OF_CONDUCT.md`, no `SECURITY.md`, no `.github/` templates (issue or PR).

### Recommendations
1. Fix `LICENSE` — replace `[yyyy]` and `[name of copyright owner]` with actual values.
2. Add `CONTRIBUTING.md` covering how to add a new example, naming conventions, and the PR checklist.
3. Add `.github/ISSUE_TEMPLATE/` (bug + feature-request) and a PR template.
4. Add a `CHANGELOG.md`.
5. Rename `skills/customer-report/` → `skills/customer_report/` for naming consistency.
6. Fix `pyproject.toml` `name` field: `omniagents-harness` → `omnigent-examples`.

---

## Category 2: Test Coverage & CI
**Sub-agent:** `test_inspector` (Codex harness) — **Grade: F**

### Findings

#### ❌ Test Files & Directories — F
- **0 test files** found matching any common pattern (`test_*.py`, `*_test.py`, `conftest.py`, etc.).
- **0 test directories** found (`tests/`, `__tests__/`, `spec/`).
- The codebase contains **6 Python source files** across two examples and a shared tools folder — none are tested.

#### ❌ Test-to-Source Ratio — F
- **Ratio: 0 / 6 = 0.00.** No regression protection exists for any of the helper scripts or the SQLite database generation script.

#### ❌ CI/CD Configuration — F
- No `.github/workflows/` directory.
- No GitLab CI, CircleCI, Jenkins, Travis, or any other CI runner configuration found.
- No `Makefile` with test targets.

#### ⚠️ Test Framework Detection — D
- `pytest>=9.1.1` is declared in `pyproject.toml` and present in `uv.lock`.
- The `cross_harness_coding` example references pytest in its README and `config.yaml` — but those references describe a *demo use-case* for the agent, not actual project tests.
- No `pytest.ini`, `tox.ini`, `[tool.pytest.ini_options]`, `conftest.py`, or coverage configuration.

### Recommendations
1. Add a `tests/` directory with at minimum smoke tests for `create_telco_db.py` and the telco query tools.
2. Add a GitHub Actions workflow (`.github/workflows/tests.yml`) that runs `pytest` on every push/PR.
3. Move `pytest` to a `[dependency-groups] dev` section and add coverage reporting (`pytest-cov`, `codecov.yml`).

---

## Category 3: Dependency Health
**Sub-agent:** `dependency_inspector` (Pi harness) — **Grade: C+**

### Findings

#### ✅ Manifest Quality — B
- A single, clean `pyproject.toml` is present — no stray `requirements.txt` or conflicting manifests.
- **Gap:** `omnigent_client` is imported by all 5 Python tool files but is **not declared** in `pyproject.toml` and absent from `uv.lock`. It is an undeclared implicit runtime dependency.

#### ❌ Version Pinning — D
- **0 of 5 declared dependencies have exact pins.**
- 4 of 5 runtime packages (`pandas`, `mlflow`, `numpy`, `openai`) are completely unconstrained bare names.
- All four have had breaking API changes across major versions. Without upper bounds, a fresh resolve could pick up a future breaking major.
- The lock file mitigates day-to-day risk but the manifest gives zero reproducibility guarantees on its own.

#### ✅ Lock File — A
- `uv.lock` is present (2,534 lines), resolves **104 packages**, and includes **1,506 SHA-256 hashes** covering sdists and per-platform wheels — strong supply-chain integrity.
- No VCS/git-source dependencies.
- **Mild concern:** all packages resolve from a Databricks-internal PyPI proxy (`pypi-proxy.dev.databricks.com`), which is not explicitly configured in `pyproject.toml`. External contributors may get different resolution sources.

#### ✅ Dependency Count — B
- Only 5 direct dependencies — very lean. The 20× transitive expansion (5 → 104) is standard for ML/data stacks (MLflow alone pulls in FastAPI, Flask, Docker, scikit-learn, etc.).

#### ❌ Dev/Prod Separation — D
- `pytest` is placed in `[project].dependencies` alongside runtime packages. No `[dependency-groups]`, `[project.optional-dependencies]`, or `[tool.uv.dev-dependencies]` separation exists.

### Recommendations
1. Add version bounds to all direct dependencies:
   ```toml
   dependencies = [
       "pandas>=2.2,<3",
       "mlflow>=3.14,<4",
       "numpy>=2.0,<3",
       "openai>=2.40,<3",
   ]
   ```
2. Move `pytest` to a dev group:
   ```toml
   [dependency-groups]
   dev = ["pytest>=9.1.1"]
   ```
3. Declare (or document) `omnigent_client` in `pyproject.toml`.
4. Commit the Databricks PyPI proxy in `pyproject.toml`:
   ```toml
   [tool.uv]
   index-url = "https://pypi-proxy.dev.databricks.com/simple/"
   ```
5. Add a `.python-version` file (e.g. `3.12`) for exact Python reproducibility.

---

## Category 4: Code Quality & Security
**Sub-agent:** `security_inspector` (Hermes harness) — **Grade: N/A ⚠️**

The Hermes harness exited with code 1 on both dispatch attempts. No security findings were produced. A manual or re-run security scan is recommended covering:
- Hardcoded secrets or API keys in YAML configs and Python tool files.
- Use of `eval()`, `exec()`, `subprocess` with shell=True, or raw SQL string formatting.
- TODO/FIXME/HACK annotations that signal incomplete or unsafe code.
- SQLite injection risks in the telco query tools.

---

## Priority Action Items

| Priority | Action | Category |
|---|---|---|
| 🔴 High | Add any tests at all — even basic smoke tests | Tests |
| 🔴 High | Add a GitHub Actions CI workflow | Tests |
| 🔴 High | Fill in the LICENSE copyright placeholder | Structure |
| 🟠 Medium | Add version bounds to all 4 runtime dependencies | Dependencies |
| 🟠 Medium | Move `pytest` to a dev dependency group | Dependencies |
| 🟠 Medium | Add `CONTRIBUTING.md` and `.github/` templates | Structure |
| 🟡 Low | Declare/document `omnigent_client` dependency | Dependencies |
| 🟡 Low | Add `CHANGELOG.md` | Structure |
| 🟡 Low | Fix `pyproject.toml` project name | Structure |
| 🟡 Low | Rename `skills/customer-report/` to `skills/customer_report/` | Structure |
| 🟡 Low | Add `.python-version` file | Dependencies |
| 🟡 Low | Re-run security scan when Hermes is available | Security |
