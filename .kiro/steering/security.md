# Security rules (non-negotiable)

- **Hard rule for the AI assistant: never make real AWS API calls, never read `~/.aws`, never use `--profile` or real credentials, never run `cdk deploy`/`terraform apply`.** The only AWS-shaped execution allowed is `moto`-mocked tests with fake credentials (`AWS_ACCESS_KEY_ID=testing`). The developer's AWS account is an org account and must not be touched.
- Scanner uses **read-only** AWS APIs only (Describe*, List*, Get*, CloudWatch GetMetricData). Ship the exact IAM policy in `infra/` and in the README. Never request write permissions.
- The tool never modifies or deletes resources. "Exorcism" output is text the user runs themselves.
- No hard-coded secrets, account IDs, keys or ARNs of real accounts anywhere in the repo, seed data, screenshots or git history. Seed data uses fake IDs (account `111122223333`).
- Credentials come only from the standard AWS credential chain / named profile. Never log credentials or full ARNs at INFO level.
- The web app has no backend and never uploads a user's report anywhere. Say so in the UI.
- CloudFront: HTTPS only, S3 bucket private behind OAC, no public bucket ACLs, security headers (CSP, X-Content-Type-Options, Referrer-Policy).
- Treat all values from AWS (tags, names) as untrusted: escape when rendering in the web app, no `dangerouslySetInnerHTML`.
- Do not add `.kiro/` to `.gitignore`. It is a submission requirement.
