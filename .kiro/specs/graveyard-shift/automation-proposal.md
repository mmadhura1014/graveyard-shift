# Automation Proposal — Graveyard Shift

Version: 0.1 — **PROPOSED ONLY. Do not enable until approved.**

---

## 1. Kiro Agent Hooks

Hooks live in `.kiro/hooks/`. Each hook is a YAML file describing the trigger event and the command or prompt to run.

### Hook 1 — Run detector tests on save

**File:** `.kiro/hooks/detector-tests-on-save.yaml`

**Trigger:** `file_save` matching `scanner/detectors/*.py`

**Command:**
```bash
pytest tests/detectors/test_$(basename ${KIRO_SAVED_FILE} .py | sed 's/^/test_/').py -v 2>&1 | tail -20
```

**Rationale:** Gives immediate test feedback when editing a detector, without running the full suite. Catches regressions before the next `make test`.

**Proposed config:**
```yaml
name: "Detector tests on save"
trigger:
  event: file_save
  glob: "scanner/detectors/*.py"
command: |
  cd "${KIRO_WORKSPACE_ROOT}"
  MODULE=$(basename "${KIRO_SAVED_FILE}" .py)
  pytest "tests/detectors/test_${MODULE}.py" -v 2>&1 | tail -30
```

---

### Hook 2 — Regenerate types and validate seed report on schema save

**File:** `.kiro/hooks/schema-change.yaml`

**Trigger:** `file_save` matching `schema/report.schema.json`

**Command:**
```bash
# 1. Validate the schema is itself valid
python -c "
import json, jsonschema
schema = json.load(open('schema/report.schema.json'))
jsonschema.Draft202012Validator.check_schema(schema)
print('Schema is valid.')
"
# 2. Validate seed report against updated schema
python -c "
import json, jsonschema
schema = json.load(open('schema/report.schema.json'))
report = json.load(open('seed/report.json'))
jsonschema.validate(report, schema)
print('seed/report.json validates OK.')
"
```

**Rationale:** Any schema edit that breaks the seed report is caught immediately, before `make test`.

**Proposed config:**
```yaml
name: "Validate schema and seed report on schema save"
trigger:
  event: file_save
  glob: "schema/report.schema.json"
command: |
  cd "${KIRO_WORKSPACE_ROOT}"
  python -c "
import json, jsonschema
schema = json.load(open('schema/report.schema.json'))
jsonschema.Draft202012Validator.check_schema(schema)
report = json.load(open('seed/report.json'))
jsonschema.validate(report, schema)
print('Schema valid. Seed report validates OK.')
"
```

---

### Hook 3 — Pre-commit secret scan

**File:** `.kiro/hooks/pre-commit-secret-scan.yaml`

**Trigger:** `pre_commit` (runs before every git commit in the workspace)

**Command:**
```bash
# Check for patterns that look like real AWS account IDs (12-digit, not 111122223333)
# Check for AWS access key patterns (AKIA...)
# Check for hard-coded ARNs with real account IDs
python - <<'EOF'
import subprocess, sys, re

result = subprocess.run(
    ["git", "diff", "--cached", "--name-only"],
    capture_output=True, text=True
)
staged_files = result.stdout.strip().splitlines()

FAKE_ACCOUNT = "111122223333"
REAL_ACCOUNT_RE = re.compile(r'\b(?!111122223333)\d{12}\b')
ACCESS_KEY_RE   = re.compile(r'\bAKIA[0-9A-Z]{16}\b')
ARN_REAL_RE     = re.compile(r'arn:aws:[^:]+:[^:]*:(?!111122223333)\d{12}:')

violations = []
for path in staged_files:
    try:
        content = open(path).read()
    except (OSError, UnicodeDecodeError):
        continue
    for pattern, label in [
        (REAL_ACCOUNT_RE, "real account ID"),
        (ACCESS_KEY_RE,   "AWS access key"),
        (ARN_REAL_RE,     "ARN with real account ID"),
    ]:
        for m in pattern.finditer(content):
            violations.append(f"{path}: possible {label}: {m.group()!r}")

if violations:
    print("BLOCKED: Possible secrets or real account IDs detected:")
    for v in violations:
        print(" ", v)
    sys.exit(1)

print("Secret scan clean.")
EOF
```

**Rationale:** Prevents accidentally committing real AWS account IDs, access keys, or ARNs. The check is intentionally conservative (false positives acceptable; false negatives are not).

**Proposed config:**
```yaml
name: "Pre-commit secret scan"
trigger:
  event: pre_commit
command: |
  cd "${KIRO_WORKSPACE_ROOT}"
  python scripts/secret_scan.py
```

(The script above is extracted to `scripts/secret_scan.py` during M4.)

---

### Hook 4 — Web lint on save

**File:** `.kiro/hooks/web-lint-on-save.yaml`

**Trigger:** `file_save` matching `web/src/**/*.{ts,tsx}`

**Command:**
```bash
cd web && npx eslint "${KIRO_SAVED_FILE}" --max-warnings 0 2>&1 | tail -20
```

**Rationale:** Surfaces TypeScript/ESLint errors inline as you edit, without running the full lint pass.

**Proposed config:**
```yaml
name: "Web lint on save"
trigger:
  event: file_save
  glob: "web/src/**/*.{ts,tsx}"
command: |
  cd "${KIRO_WORKSPACE_ROOT}/web"
  npx eslint "${KIRO_SAVED_FILE}" --max-warnings 0 2>&1 | tail -20
```

---

## 2. MCP Servers

### 2.1 AWS Pricing MCP Server

**Purpose:** Verify unit prices in `scanner/pricing.json` while building detectors. Use during M2 (T2.7) to look up current on-demand prices for EBS, EIP, NAT Gateway, ALB, NLB, and CloudWatch Logs. Not used at runtime.

**How to use:**
- During T2.7, query the MCP server for each resource type before writing the price into `pricing.json`.
- After `pricing.json` is committed, the MCP server is no longer needed; the scanner reads the bundled file.

**Config snippet for `.kiro/settings/mcp.json`:**
```json
{
  "mcpServers": {
    "awslabs.pricing-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.pricing-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**When to enable:** Before T2.7. Can be disabled after `pricing.json` is verified and committed.

---

### 2.2 AWS Documentation MCP Server

**Purpose:** Verify boto3 API call shapes, pagination behaviour, and response field names while building `fetcher.py` and each detector. Particularly useful for:
- Confirming `StateTransitionReason` format for stopped EC2 instances (T2.3)
- Confirming CloudWatch metric names for LBs and NAT GWs (T2.1, T2.2)
- Confirming IAM `GetAccessKeyLastUsed` response shape (T2.4)

**Config snippet to add to the same `mcpServers` block:**
```json
"awslabs.aws-documentation-mcp-server": {
  "command": "uvx",
  "args": ["awslabs.aws-documentation-mcp-server@latest"],
  "disabled": false,
  "autoApprove": []
}
```

---

### 2.3 Full `.kiro/settings/mcp.json` (proposed)

```json
{
  "mcpServers": {
    "awslabs.pricing-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.pricing-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Prerequisites:**
- `uvx` must be installed (`pip install uv` or `brew install uv`).
- No AWS credentials are required for the Documentation server.
- The Pricing server uses read-only public AWS Pricing API endpoints; it does not require account credentials.
- Do not embed real AWS credentials in this file.

---

## 3. Summary Table

| Automation | Type | Trigger | Benefit |
|------------|------|---------|---------|
| Detector tests on save | Hook | Save `scanner/detectors/*.py` | Instant test feedback per detector |
| Schema change validation | Hook | Save `schema/report.schema.json` | Catch schema/seed mismatches immediately |
| Pre-commit secret scan | Hook | `git commit` | Block real account IDs and access keys from repo |
| Web lint on save | Hook | Save `web/src/**/*.{ts,tsx}` | ESLint feedback without full lint pass |
| AWS Pricing MCP | MCP server | Manual use during M2-T2.7 | Verified unit prices for `pricing.json` |
| AWS Documentation MCP | MCP server | Manual use during M2-M3 | Accurate API shapes for fetcher and detectors |

---

## 4. Activation plan

1. Approve this proposal.
2. Enable MCP servers: write `.kiro/settings/mcp.json` as above.
3. Enable hooks: create `.kiro/hooks/*.yaml` files as specified above.
4. Hooks and MCP take effect immediately on next relevant trigger.

No hook modifies files automatically; all hooks run read-only commands that report results (pass/fail) back to the editor. The pre-commit hook blocks a commit if violations are found, but does not alter any file.
