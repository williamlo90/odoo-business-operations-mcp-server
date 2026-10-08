# Credential handling

Runtime passwords, provider keys and signing material belong in ignored local
configuration or an approved secret store. Never include them in source,
screenshots, recordings, issues or test output. Environment-variable references
in Compose are configuration templates, not embedded credential values.

## Repository checks

- GitHub secret scanning and push protection are enabled for this repository.
- The Secret scan workflow runs checksum-pinned Gitleaks on push and pull request.
  It scans all fetched Git history and redacts findings in job output.
- `.gitleaksignore` contains five reviewed, exact historical fingerprints:
  three demo request-idempotency UUID occurrences and two OpenAPI file checksums.
  It does not exclude entire files, directories, commits or detector categories.
- Keep raw scanner reports under ignored `local/security-audit/`. Never upload
  an unredacted finding as a public issue or workflow artifact.

To reproduce the history scan with Gitleaks 8.30.1:

```bash
gitleaks git . --log-opts="--all" --redact=100 --no-banner
```

## Responding to an alert

Inspect the exact revision and location privately. Determine whether the value
is an authentication secret, a synthetic test value, an identifier, a checksum
or a configuration-variable reference. Do not disable a detector to silence a
single false positive. Mark a verified false positive in the service that raised
the incident; local scanner exceptions do not close third-party dashboard alerts.

If an actual credential is exposed, revoke or rotate it first. Then remove it
from active files and assess whether historical cleanup is necessary. Coordinate
any history rewrite because it changes learning checkpoints and manifests.
Report suspected vulnerabilities privately to the repository owner; do not
publish working credentials or private records in GitHub issues.

References: [GitHub credential-removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
and [GitGuardian ignore behavior](https://docs.gitguardian.com/internal-repositories-monitoring/gg_shield/commands/ignore).
