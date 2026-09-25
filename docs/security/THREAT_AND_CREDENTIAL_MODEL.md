# Threat and Credential Model

## Assets

- Authoritative Git history and repositories
- Product intent, requirements, and accepted ADRs
- Worker and control-plane credentials
- Enrollment authority
- Sanitized fixtures and project configuration
- Production systems and credentials

## Primary threats

- Lost or stolen installer media or worker
- Leaked deploy key, token, or AI-provider auth cache
- Compromised worker or dependency
- Unauthorized task injection
- Malicious repository instructions attempting to redefine authority
- Accidental force-push, branch deletion, production action, or secret publication
- CIC Station compromise or loss

## Boundaries

- The universal installer contains no permanent owner credential or worker private identity.
- Each installation generates a new worker identity.
- Enrollment explicitly binds that public identity to approved scope.
- Workers receive no production credentials by default.
- Project content cannot override owner/control-plane authority.
- External destructive actions require separate policy and approval.

## GitHub authorization direction

Use unique worker identity and narrowly scoped repository authorization. Repository-specific deploy keys may be adequate for early limited proofs, but a GitHub App or another short-lived scoped mechanism is preferred as one worker needs controlled access to multiple repositories.

Personal access tokens are not preferred as permanent worker identities because they remain tied to a person and may be broader than necessary. Never embed any operational Git credential in installer media or ordinary Git state.

## AI-provider authentication

Provider-specific authentication belongs behind Vincent's provider-adapter boundary. Codex is the initial provider. Prefer supported device/interactive authorization for human-bound accounts when available.

CIC Station may later assign desired non-secret provider identity/profile policy, but reusable provider credentials never belong in Git. Any unattended credential delivery must use a separately protected secret mechanism with unique/scoped/rotatable/revocable credentials.

## Revocation

Revocation must disable one worker without disabling others, prevent new managed assignments, mark active ownership uncertain, and trigger review of recent remote changes.
