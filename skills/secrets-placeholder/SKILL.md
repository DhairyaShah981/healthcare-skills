---
name: secrets-placeholder
description: |
  Scaffold the placeholder-token + Secret-Manager-substitution pattern for files
  that must ship to git but reference per-environment secrets (voice-agent JSON,
  Retell / Vapi configs, integration YAMLs, infra Terraform). Use when the user
  asks "how do I keep secrets out of this committed JSON", needs to manage per-
  environment webhook secrets, or fixes a `*.ngrok.io` URL baked into a prod
  file.
when_to_use: |
  Activate when the user:
  - Has a JSON / YAML config that must be committed but contains environment-
    specific secrets or URLs
  - Mentions Secret Manager, AWS SecretsManager, GCP Secret Manager, or
    HashiCorp Vault
  - Is about to commit a webhook secret, API key, or ngrok URL
  - Hits the `voice-agent-lint` RTL-016 or RTL-017 rule
  - Asks "where do I put this secret?"
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [secrets, security, healthcare, devops]
incident: |
  Six separate Eva-scheduling agents shipped to production with `*.ngrok.io`
  URLs baked into committed JSON. Each broke the moment the developer closed
  the dev laptop on Friday. Worse, when the agents *did* run, they accepted
  webhook calls without verifying a secret because the secret was either
  missing or hardcoded for development. This skill scaffolds the
  placeholder-token pattern so every committed JSON references a placeholder
  like `<<RETELL_WEBHOOK_SECRET>>` that gets substituted from Secret Manager
  at deploy time.
---

# secrets-placeholder

> Commit the structure, not the secret. Placeholder tokens + Secret Manager substitution + deploy-time injection.

## When to use

- The user has a config file (voice-agent JSON, integration YAML, Terraform) that must live in git but contains secrets or per-env URLs.
- The user is fixing a `voice-agent-lint` RTL-016 / RTL-017 finding.
- The user mentions Secret Manager, Vault, or rotating webhook secrets.
- A security review finds a hardcoded secret in a committed file.

## How it works

1. **Adopt the placeholder convention.** Use `<<SCREAMING_SNAKE_CASE>>` for every spot a secret or env-specific value lives. Examples:
   ```json
   "url": "<<TOOL_URL_CHECK_AVAILABILITY>>"
   "webhook_secret": "<<RETELL_WEBHOOK_SECRET_STOCKTON>>"
   "kb_id": "<<KB_ID_STOCKTON_SERVICES>>"
   ```

2. **Store the mapping per environment.** A single `secrets.<env>.yaml` per environment lists which Secret Manager / Vault path provides each placeholder:
   ```yaml
   # secrets.prod.yaml
   provider: gcp_secret_manager
   project: my-clinic-prod
   mapping:
     TOOL_URL_CHECK_AVAILABILITY:
       secret: agent-check-availability-url
       version: latest
     RETELL_WEBHOOK_SECRET_STOCKTON:
       secret: retell-webhook-stockton
   ```

3. **Substitute at deploy time.** Provide a small script that:
   - Reads the committed file with placeholders
   - Looks up each `<<…>>` in `secrets.<env>.yaml`
   - Fetches the value from Secret Manager
   - Writes the resolved file to a temp path
   - Invokes the deploy command (Retell upload, Vapi push, kubectl apply)
   - Never writes the resolved file to disk for longer than the deploy needs

4. **Add a pre-commit hook** that rejects any committed file containing what looks like a real secret (high-entropy string, certain prefixes like `sk_live_…`, JWT shapes). The hook understands `<<…>>` is acceptable.

5. **Rotate by changing Secret Manager**, not by editing committed files. Rotation becomes a one-step Secret Manager update + re-deploy, with zero code review.

## Example layout

```
your-repo/
├── agents/
│   ├── eva-scheduling.committed.json     # <- has <<PLACEHOLDERS>>
│   └── eva-router.committed.json
├── secrets/
│   ├── secrets.dev.yaml
│   ├── secrets.staging.yaml
│   └── secrets.prod.yaml
├── scripts/
│   ├── render_secrets.py                  # substitute <<...>> at deploy
│   └── precommit_no_secrets.sh
└── .github/workflows/deploy.yml
```

`agents/eva-scheduling.committed.json` (committed):
```json
{
  "agent_name": "eva-scheduling",
  "conversationFlow": {"is_transfer_cf": false, ...},
  "tools": [
    {
      "name": "check_availability",
      "url": "<<TOOL_URL_CHECK_AVAILABILITY>>",
      "webhook_secret": "<<RETELL_WEBHOOK_SECRET_STOCKTON>>",
      ...
    }
  ]
}
```

`secrets/secrets.prod.yaml`:
```yaml
provider: gcp_secret_manager
project: my-clinic-prod
mapping:
  TOOL_URL_CHECK_AVAILABILITY: {secret: agent-check-availability-url}
  RETELL_WEBHOOK_SECRET_STOCKTON: {secret: retell-webhook-stockton}
```

Deploy command:
```bash
python scripts/render_secrets.py --env prod agents/eva-scheduling.committed.json \
  | retell agent upload --stdin
```

## Edge cases

- **`<<NESTED>>` placeholders.** If a placeholder appears inside a string with other content (`"https://api.example.com/<<TENANT_ID>>/webhooks"`), the substitution must be partial, not whole-value. The renderer handles both.
- **Same placeholder in multiple files.** Define it once in `secrets.<env>.yaml`; reference everywhere. Don't duplicate.
- **JSON vs YAML.** Use the same placeholder syntax across both; the renderer reads the file as text and substitutes, then re-validates as JSON / YAML.
- **Pre-commit can't catch *everything*.** A genuinely high-entropy random string the engineer wrote could pass entropy heuristics. Use [gitleaks](https://github.com/gitleaks/gitleaks) or [TruffleHog](https://github.com/trufflesecurity/trufflehog) as the second layer.
- **Don't store rendered files.** The output of `render_secrets.py` is the deploy payload; pipe it straight to the deployer or write it to `/tmp` and delete immediately.
- **CI access to Secret Manager.** The CI runner needs IAM permission to read the secrets it's substituting. Lock this down to specific secrets, not "all secrets in the project".
- **Same template, multiple environments.** The committed file's placeholders are the contract; `secrets.<env>.yaml` is the binding. Same template renders to dev, staging, prod.

## References

- GCP Secret Manager: <https://cloud.google.com/secret-manager>
- AWS Secrets Manager: <https://docs.aws.amazon.com/secretsmanager/>
- HashiCorp Vault: <https://www.vaultproject.io/>
- gitleaks: <https://github.com/gitleaks/gitleaks>
- TruffleHog: <https://github.com/trufflesecurity/trufflehog>
- [`scripts/render_secrets.py`](./scripts/render_secrets.py) — reference renderer
- [`examples/eva-scheduling.committed.json`](./examples/eva-scheduling.committed.json)
- [`examples/secrets.prod.yaml`](./examples/secrets.prod.yaml)
- See also `voice-agent-lint` (RTL-016, RTL-017)
