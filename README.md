# Python authentication QA runner — showcase example

Part of the [AI-assisted automation showcase](https://github.com/camiloavilacm/qa-features). Choose a framework to study; running all three together is optional. Start with the [reviewer guide](https://github.com/camiloavilacm/qa-features/blob/main/REVIEWER_GUIDE.md) or [tested one-framework first run](https://github.com/camiloavilacm/qa-features/blob/main/docs/first-run.md).

Runs the approved SEED-1 Gherkin unchanged with pytest-bdd through Playwright and Selenium against either Conduit SUT. Each slot executes AC-1, AC-2 and AC-3; the four-slot matrix requires 12 passes. Selectors come only from the pinned contract's labels, roles and data-testid values. The baseline is read-only; registrations use unique execution identities.

## Install and run

Use Python 3.13 and an isolated environment:

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt -r harness/requirements.txt
.venv/bin/python tools/bootstrap_features.py
.venv/bin/playwright install chromium
```

The relative submodule URL is `../qa-features.git`. The bundled Git objects permit offline bootstrap without enabling file transport. The gitlink, clean submodule HEAD and feature-ref.txt must all equal the approved immutable commit. No parent untracked files are required.

Selenium needs matching Chrome and chromedriver. Set QA_CHROME_BINARY and QA_CHROMEDRIVER when they are not discoverable. Playwright uses its pinned Chromium installation. Both SUTs must be running before acceptance. Set QA_SUT_PYTHON_REVISION and QA_SUT_NODE_REVISION to actual immutable source commits or image SHA-256 identifiers (hex only). Optional QA_SUT_PYTHON_URL and QA_SUT_NODE_URL default to localhost ports 8001 and 8002.

```sh
.venv/bin/python tools/verify.py --check 12-passes
.venv/bin/python tools/verify.py --check observer-complete
```

For a single slot:

```sh
.venv/bin/python -m pytest --driver playwright --sut sut-python \
  --base-url http://localhost:8001 --sut-revision "$QA_SUT_PYTHON_REVISION" \
  --campaign-id local --result-dir reports/my-unique-execution
```

Existing result directories are never overwritten. reports/ contains per-slot schema-valid results.json and hash-bound typed check/network artifacts. Runner revisions hash runner/test/dependency sources, including uncommitted reviewable work. No raw bodies, credentials, tokens or browser traces are persisted. No runtime AI or healing exists.

## Observation and acceptance

Playwright consumes Chromium CDP events; Selenium consumes Chrome performance/CDP network events. Both read real response bodies through durable CDP capture, including error bodies discarded by the UI. Complete observation requires all contract-relevant requests to finish and the scenario's required method/path/status/authentication-presence events to exist. Missing, partial and erroneous instrumentation cannot PASS. Bodies are used only in memory to verify the exact API contract. The negative observer check exercises all three non-complete states through both real browser adapters.

AC-3 independently asserts the 422 response, exact UI error, empty cookies/storage and denial of a direct protected-page visit. The SUT's separate Hurl unauthenticated GET /user check remains part of Step 2; this runner does not replace that evidence.

Development acceptance uses harness/scripts/preflight.py, verify_step.py run --check 12-passes, verify_step.py run --check observer-complete, verify_step.py validate, verify_step.py gate and scope_guard.py against the retained baseline. Supply the operator-owned external QA_AUTHORIZATION_FILE and QA_EVIDENCE_KEY_FILE. The current shared controller and formal outcome contract are distributed locally, with provenance under harness/ and governance/. Runtime reports are excluded only from the source digest and remain in the scope audit.

Claude artifacts are retained and statically checked. Live Claude remains NOT RUN under the approved exception. This repository contains no Cypress runner, tracker, campaign orchestration or release tooling.

Code is [MIT licensed](LICENSE). See [contribution guidance](CONTRIBUTING.md), [security scope](SECURITY.md), and [third-party notices](THIRD_PARTY_NOTICES.md).
