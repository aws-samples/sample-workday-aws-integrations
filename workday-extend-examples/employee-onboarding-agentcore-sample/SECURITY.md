# Security

## What this sample is NOT

This sample is a **demonstration of Amazon Bedrock AgentCore**, not a production
deployment blueprint. It is not:

- **Production-hardened.** There is no rate limiting, request throttling beyond
  the built-in model-throttle retry, input validation, or output filtering
  beyond section-tag parsing.
- **Multi-tenant.** The Cognito user pool created by `deploy.sh` has a single
  client-credentials app client. There is no per-user isolation.
- **Audited.** No independent security review has been performed. The defaults
  are chosen for learnability, not for defense-in-depth.

## How cleanup identifies resources

`complete_cleanup.sh` identifies resources to delete using three mechanisms,
in priority order:

1. **Tag query** — `Sample=sample-amazon-bedrock-agentcore-employee-onboarding`.
   Applied to the AgentCore runtime, gateway, Cognito user pool, Lambda
   function, Lambda execution role, and any S3 buckets this sample creates.
2. **IAM path** — `/bedrock-employee-onboarding/`. Applied to IAM roles this
   sample creates directly (currently just the Lambda execution role).
3. **Exact-name or unique-suffix match** — for resources the AgentCore
   starter toolkit creates automatically (ECR repository, CodeBuild project,
   CloudWatch log group, toolkit IAM roles), whose names we only partially
   control. The unique suffix is the agent name
   `employee_onboarding`, which combined with the toolkit's own
   `bedrock-agentcore-` prefix produces a unique string unlikely to
   collide with unrelated resources in your account.

Cleanup does not use generic substring matching on words like `agentcore`,
`gateway`, or `onboarding`. If you rename resources after deployment or
deploy an older version of this sample in the same account, cleanup may
miss them.

## Shared AgentCore resources that cleanup deliberately skips

Two resources are created once per AWS account by the AgentCore starter
toolkit and **shared across every AgentCore deployment** in that account:

- The S3 bucket `bedrock-agentcore-codebuild-sources-<account>-<region>`,
  used by CodeBuild to stage source archives.
- The service-linked role `AWSServiceRoleForBedrockAgentCoreRuntimeIdentity`.

Deleting either from this sample's cleanup could break any other AgentCore
work in the same account. `complete_cleanup.sh` leaves them alone and
prints a notice saying so. If this is the last AgentCore sample you use
in the account and you want them gone, remove them by hand:

```bash
aws s3 rb s3://bedrock-agentcore-codebuild-sources-<account>-<region> --force
aws iam delete-service-linked-role \
  --role-name AWSServiceRoleForBedrockAgentCoreRuntimeIdentity
```

## Residual risk after `make clean`

After cleanup completes successfully, the following are not deleted:

- CloudWatch metrics data — retained per your account's metrics policy.
- Bedrock model-invocation usage history visible in cost and usage reports.
- Local shell history that may contain your `.env` values. Clear it
  yourself if you've used interactive shells with those values.

Confirm cleanup with:

```bash
make verify-clean
```

## Known considerations

### Prompt injection

The agent consumes free-form user text and passes it through to the model.
A crafted prompt can instruct the model to deviate from the system prompt
(for example, to ignore the eight-block format or to emit content unrelated
to onboarding). This is inherent to LLM-based agents and is not specific to
this sample. Treat outputs as untrusted.

Do not feed the output of this agent
into downstream systems without appropriate validation.

### Credential handling

`deploy.sh` writes the Cognito app client secret to `.env` in the repo root.
`.env` is gitignored. Treat it the same way you would any credential file:
do not commit it, do not share it, and rotate the client secret if it's ever
exposed. When you finish testing, run `make clean`, which
deletes the Cognito user pool and therefore invalidates the secret.

### IAM permissions for `deploy.sh`

The scripts need broad permissions to create and then tear down resources
across multiple services. For local testing in a sandbox account, attaching
`AdministratorAccess` is the simplest path. For CI or any shared account,
see the scoped action list in [DEPLOYMENT.md](DEPLOYMENT.md#aws-credentials--permissions).

## Reporting a security issue

If you discover a potential security issue in this sample, please **do not**
open a public GitHub issue. Instead, notify AWS Security via
<https://aws.amazon.com/security/vulnerability-reporting/>.
