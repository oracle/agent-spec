# TypeScript SDK Guidance

Keep changes minimal, security-focused, and aligned with the existing
TypeScript patterns.

## Scope

- Do not add new features, adapters, providers, or public API surface unless the
  user explicitly asks for TypeScript SDK work.
- Prefer small fixes for security, correctness, dependency compatibility, or
  repository-wide maintenance.
- If behavior needs to diverge from the Python SDK, document why in the change
  or handoff.

## Security

- Treat serialized Agent Spec files as untrusted configuration data, not
  executable code.
- Consult `../docs/pyagentspec/source/security.rst` before changing prompt
  templating, sensitive field handling, deserialization, remote transports,
  credentials, generated code, or network behavior.
- Never add examples, tests, fixtures, or defaults that contain real credentials,
  tokens, private keys, wallet paths, DSNs, or sensitive headers.
- Keep sensitive values excluded from serialization. When adding or renaming
  credential-bearing fields, update `src/sensitive-field.ts` and the closest
  tests.
- Treat `{{placeholder}}` templating as a trust-boundary surface. Do not route
  untrusted user, tool, RAG, or remote output into privileged instructions or
  sensitive URL/header positions without explicit validation and documentation.
- Deserialization and parsing must not execute code or load remote resources as
  a side effect.

## Validation

- For TypeScript-only changes, run the narrowest relevant check from
  `tsagentspec/`, usually `npm test` or `npm run lint`.
- If validation is skipped because dependencies are unavailable, state that
  clearly in the handoff.
