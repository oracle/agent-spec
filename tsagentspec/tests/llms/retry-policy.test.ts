import { describe, it, expect } from "vitest";
import {
  RetryPolicySchema,
  JitterType,
  AgentSpecSerializer,
  AgentSpecDeserializer,
  createOpenAiCompatibleConfig,
} from "../../src/index.js";

describe("RetryPolicy", () => {
  it("should parse with all defaults", () => {
    const policy = RetryPolicySchema.parse({});
    expect(policy.maxAttempts).toBe(2);
    expect(policy.initialRetryDelay).toBe(1.0);
    expect(policy.maxRetryDelay).toBe(8.0);
    expect(policy.backoffFactor).toBe(2.0);
    expect(policy.jitter).toBe(JitterType.FULL_AND_EQUAL_FOR_THROTTLE);
    expect(policy.serviceErrorRetryOnAny5xx).toBe(true);
    expect(policy.recoverableStatuses).toEqual({ "409": [], "429": [] });
  });

  it("should accept custom values", () => {
    const policy = RetryPolicySchema.parse({
      maxAttempts: 5,
      requestTimeout: 30,
      initialRetryDelay: 0.5,
      maxRetryDelay: 60,
      backoffFactor: 1.5,
      jitter: JitterType.EQUAL,
      serviceErrorRetryOnAny5xx: false,
      recoverableStatuses: { "503": ["Unavailable"] },
    });
    expect(policy.maxAttempts).toBe(5);
    expect(policy.requestTimeout).toBe(30);
    expect(policy.jitter).toBe(JitterType.EQUAL);
    expect(policy.serviceErrorRetryOnAny5xx).toBe(false);
    expect(policy.recoverableStatuses).toEqual({ "503": ["Unavailable"] });
  });

  it("should allow jitter to be null", () => {
    const policy = RetryPolicySchema.parse({ jitter: null });
    expect(policy.jitter).toBeNull();
  });

  it("should reject negative maxAttempts", () => {
    expect(() => RetryPolicySchema.parse({ maxAttempts: -1 })).toThrow();
  });

  it("should reject non-positive backoffFactor", () => {
    expect(() => RetryPolicySchema.parse({ backoffFactor: 0 })).toThrow();
  });

  it("should round-trip through serialization with non-default values", () => {
    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const config = createOpenAiCompatibleConfig({
      id: "test-id",
      name: "llm",
      url: "http://localhost",
      modelId: "model",
      retryPolicy: {
        maxAttempts: 5,
        serviceErrorRetryOnAny5xx: false,
        jitter: JitterType.EQUAL,
        recoverableStatuses: { "503": ["ServiceUnavailable"] },
      },
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).toContain("service_error_retry_on_any_5xx: false");
    expect(yaml).toContain("max_attempts: 5");
    const restored = deserializer.fromYaml(yaml) as typeof config;
    expect(restored.retryPolicy?.maxAttempts).toBe(5);
    expect(restored.retryPolicy?.serviceErrorRetryOnAny5xx).toBe(false);
    expect(restored.retryPolicy?.jitter).toBe(JitterType.EQUAL);
    expect(restored.retryPolicy?.recoverableStatuses).toEqual({
      "503": ["ServiceUnavailable"],
    });
  });

  it("should expose all JitterType values", () => {
    expect(JitterType.EQUAL).toBe("equal");
    expect(JitterType.FULL).toBe("full");
    expect(JitterType.FULL_AND_EQUAL_FOR_THROTTLE).toBe(
      "full_and_equal_for_throttle",
    );
    expect(JitterType.DECORRELATED).toBe("decorrelated");
  });
});
