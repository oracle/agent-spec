/**
 * Message transform types.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { LlmConfigUnion, type LlmConfig } from "../llms/index.js";

export const MessageSummarizationTransformSchema = ComponentBaseSchema.extend({
  componentType: z.literal("MessageSummarizationTransform"),
  llm: LlmConfigUnion,
  maxMessageSize: z.number().int().default(20000),
  summarizationInstructions: z.string().default(
    "Please make a summary of this message. Include relevant information and keep it short. " +
      "Your response will replace the message, so just output the summary directly, no introduction needed.",
  ),
  summarizedMessageTemplate: z
    .string()
    .default("Summarized message: {{summary}}"),
  maxCacheSize: z.number().int().optional().default(10000),
  maxCacheLifetime: z.number().int().optional().default(14400),
  cacheCollectionName: z
    .string()
    .default("summarized_messages_cache"),
  datastore: z.record(z.unknown()).optional(),
});

export type MessageSummarizationTransform = z.infer<
  typeof MessageSummarizationTransformSchema
>;

export const ConversationSummarizationTransformSchema =
  ComponentBaseSchema.extend({
    componentType: z.literal("ConversationSummarizationTransform"),
    llm: LlmConfigUnion,
    maxNumMessages: z.number().int().default(50),
    minNumMessages: z.number().int().default(10),
    summarizationInstructions: z.string().default(
      "Please make a summary of this conversation. Include relevant information and keep it short. " +
        "Your response will replace the messages, so just output the summary directly, no introduction needed.",
    ),
    summarizedConversationTemplate: z
      .string()
      .default("Summarized conversation: {{summary}}"),
    maxCacheSize: z.number().int().optional().default(10000),
    maxCacheLifetime: z.number().int().optional().default(14400),
    cacheCollectionName: z
      .string()
      .default("summarized_conversations_cache"),
    datastore: z.record(z.unknown()).optional(),
  });

export type ConversationSummarizationTransform = z.infer<
  typeof ConversationSummarizationTransformSchema
>;

export const MessageTransformUnion = z.discriminatedUnion("componentType", [
  MessageSummarizationTransformSchema,
  ConversationSummarizationTransformSchema,
]);

export type MessageTransform = z.infer<typeof MessageTransformUnion>;

export function createMessageSummarizationTransform(opts: {
  name: string;
  llm: LlmConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  maxMessageSize?: number;
  summarizationInstructions?: string;
  summarizedMessageTemplate?: string;
  maxCacheSize?: number | null;
  maxCacheLifetime?: number | null;
  cacheCollectionName?: string;
  datastore?: Record<string, unknown>;
}): MessageSummarizationTransform {
  return Object.freeze(
    MessageSummarizationTransformSchema.parse({
      ...opts,
      componentType: "MessageSummarizationTransform" as const,
    }),
  );
}

export function createConversationSummarizationTransform(opts: {
  name: string;
  llm: LlmConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  maxNumMessages?: number;
  minNumMessages?: number;
  summarizationInstructions?: string;
  summarizedConversationTemplate?: string;
  maxCacheSize?: number | null;
  maxCacheLifetime?: number | null;
  cacheCollectionName?: string;
  datastore?: Record<string, unknown>;
}): ConversationSummarizationTransform {
  return Object.freeze(
    ConversationSummarizationTransformSchema.parse({
      ...opts,
      componentType: "ConversationSummarizationTransform" as const,
    }),
  );
}
