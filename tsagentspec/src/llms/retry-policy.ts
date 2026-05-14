/**
 * RetryPolicy config object (NOT a Component - no id/name).
 */
import { z } from "zod";

export const JitterType = {
  EQUAL: "equal",
  FULL: "full",
  FULL_AND_EQUAL_FOR_THROTTLE: "full_and_equal_for_throttle",
  DECORRELATED: "decorrelated",
} as const;
export type JitterType = (typeof JitterType)[keyof typeof JitterType];

const jitterValues = Object.values(JitterType) as [JitterType, ...JitterType[]];

export const RetryPolicySchema = z.object({
  maxAttempts: z.number().int().min(0).default(2),
  requestTimeout: z.number().positive().optional(),
  initialRetryDelay: z.number().min(0).default(1.0),
  maxRetryDelay: z.number().min(0).default(8.0),
  backoffFactor: z.number().positive().default(2.0),
  jitter: z
    .enum(jitterValues)
    .nullable()
    .optional()
    .default(JitterType.FULL_AND_EQUAL_FOR_THROTTLE),
  serviceErrorRetryOnAny5xx: z.boolean().default(true),
  recoverableStatuses: z
    .record(z.array(z.string()))
    .default({ "409": [], "429": [] }),
});

export type RetryPolicy = z.infer<typeof RetryPolicySchema>;
