# Additional Security Considerations

## Considerations regarding tools

This Adapter allows LLMs to interact with applications via **Tools** (`ClientTool`, `ServerTool`, or `RemoteTool`),
granting access to state or operations. Since tool inputs often come from LLMs or users,
rigorous input sanitization and validation are crucial.

**Key Principles for Tool Security:**

*   **Mandatory Input Validation**: Always validate tool inputs.

    *   For `ClientTool` and `ServerTool`, define/enforce schemas (types and descriptions) as a primary defense.
    *   For `RemoteTool`, which constructs HTTP requests, validation is critical for all parameters
        that can be templated (e.g., `url`, `http_method`, `api_spec_uri`, `data`, `query_params`, `headers`).
*   **Output Scrutiny**: Define expected outputs with `output_descriptors`.
    For `ClientTool`, clients post results;
    for `ServerTool`, the tool's implementation generates them.
    Calling Flows/Agents must treat incoming tool result content as untrusted until validated/sanitized.
*   **Least Privilege**: Grant tools only permissions essential for their function.

## Tool Security Specifics

Rigorously sanitize all tool inputs. Tools, bridging LLM understanding with system operations, are prime targets.
Validate types, lengths, and semantic correctness before core logic execution.

**`ServerTool` Considerations:**

*   **Callable Security (`func`)**: The `func` callable in ServerTool is the primary security concern. Harden this server-executed code against vulnerabilities.
*   **Isolation for High-Risk Tools**: Run high-risk ServerTool instances (e.g., with elevated permissions, network/filesystem access) in sandboxed environments (containers/pods) with minimal IAM roles.
    Deny network/filesystem writes unless essential.

**`ClientTool` Considerations:**

*   **Client-Side Execution**: `ClientTool` execution is supposed to occur on the client. Client environment security, though outside adapter's control, impacts overall application security.
*   **Untrusted tool requests**: Clients receive a tool request. Client code must parse `args` with a strict schema, avoiding direct use in shell commands or sensitive OS functions.
*   **Untrusted Client tool results**: Server-side components must treat tool results from clients as untrusted. Validate its `content` before processing.

**`RemoteTool` Considerations:**

*   **Templated Request Arguments**: RemoteTool allows various parts of the HTTP request (URL, method, body, headers, etc.) to be templated with placeholders. This is powerful but introduces risks if the inputs to these templates are not strictly controlled. Maliciously crafted inputs could lead to information leakage (e.g., exposing sensitive data in URLs or headers) or enable attacks like SSRF (Server-Side Request Forgery) or automated DDoS.
*   **URL Allow List**: This is a critical security feature. Consider defining a `url_allow_list` to restrict the tool to a predefined set of allowed URLs or URL patterns. This significantly mitigates the risk of the tool being used to make requests to unintended or malicious endpoints.
*   **Secure Connections**: By default, RemoteTool allows non-HTTPS URLs. Maintain this default unless there's an explicit, well-justified reason to allow insecure HTTP, and ensure the risks are understood.
*   **Credential Handling**: By default, URLs can contain credentials (e.g., `https://user:pass@example.com`). If your use case does not require this, prevent accidental leakage or misuse of credentials in URLs.
*   **URL Fragments**: Control whether URL fragments (e.g., `#section`) are permitted in requested URLs and allow list entries.

As highlighted in the RemoteTool API, since the Agent can generate arguments
(url, http_method, api_spec_uri, data, query_params, headers) or parts of these arguments in the respective
templates, this can impose a security risk of information leakage and enable specific attack
vectors like automated DDOS attacks. Please use RemoteTool responsibly and ensure
that only valid URLs can be given as arguments or that no sensitive information is used for any of these
arguments by the agent.

## Harden All Tools (ServerTool, ClientTool and RemoteTool)

- **Unvalidated arguments (leading to injection, DoS, etc.)**
  - For `ClientTool` & `ServerTool`: Use input schemas for basic type checking.
    In ServerTool's implementation, add comprehensive validation (string length limits, numeric ranges, format constraints).
    Cap string lengths and numeric ranges in tool implementation code.
  - For `RemoteTool`:
    *  Rigorously validate and sanitize any inputs used in templated arguments (`url`, `method`, `api_spec_uri`, `data`, `query_params`, `headers`).
    *  **Crucially, always configure an `url_allow_list`** to restrict outbound requests to known, trusted endpoints.
- **Excessive privileges (for ServerTool)**
  - Run in least-privilege containers/pods.
  - Separate network namespaces for sensitive data/external system access.
  - Explicitly deny unnecessary filesystem/network access.
- **Stateful tools**
  - Prefer stateless tools.
  - Implement optimistic locking and rigorous input sanitization for state-modifying operations.
- **ClientTool misuse (client-side vulnerabilities)**
  - Client apps handling tool requests must treat its parameters as untrusted.
  - Validate/sanitize client-side parameters before local execution (esp. OS commands, sensitive API calls).
- **Insecure underlying components (for tools from Flows, Nodes)**
  - Ensure source Flows or Nodes tools for ServerTool are vetted; the tool inherits their security.
  - **Data leakage via tool results**
    - Define output schemas clearly.
    - Ensure `ServerTool` implementation and `ClientTool` client code return only necessary data.
    - Consuming Agent/Flow must validate/sanitize tool result content.
