export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  code: string;
  filename: string;
}

export interface FlowNode {
  id: string;
  label: string;
  type: "tool_call" | "llm_call" | "condition" | "start" | "end" | "react_agent";
  tool_name?: string;
  prompt_template?: string;
  node_timeout_seconds?: number;
}

export interface FlowEdge {
  source: string;
  target: string;
  condition?: string;
}

export interface FlowDefinition {
  nodes: FlowNode[];
  edges: FlowEdge[];
  entry_node: string;
}

export interface AgentDefinition {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  tools: ToolDefinition[];
  flow?: FlowDefinition;
  status: "draft" | "ready" | "error";
  created_at: string;
  updated_at: string;
}

export interface RunLog {
  timestamp: string;
  node_id: string;
  message: string;
  level: string;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface RunResult {
  run_id: string;
  agent_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  current_node?: string;
  logs: RunLog[];
  input_data?: Record<string, any>;
  output_data?: any;
  error?: string;
  started_at: string;
  completed_at?: string;
  usage?: TokenUsage;
  llm_calls?: number;
  total_llm_latency_ms?: number;
  provider?: string;
  run_timeout_seconds?: number;
}

export interface SuggestedTool {
  name: string;
  description: string;
  parameters?: Record<string, any>;
  prebuilt?: boolean;
}

export interface BuilderMessage {
  role: "user" | "assistant";
  content: string;
  artifacts?: {
    system_prompt?: string;
    tools?: ToolDefinition[];
    suggested_tools?: SuggestedTool[];
    tool?: ToolDefinition;
    flow?: FlowDefinition;
  };
}

export interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
}

export type WizardStep = 1 | 2 | 3 | 4;

export interface ToolValidationResult {
  tool_name: string;
  status: "pass" | "fail";
  error?: string;
  output?: any;
}

export interface ValidateToolsResponse {
  results: ToolValidationResult[];
  all_passed: boolean;
}

export interface EnhanceToolResponse {
  tool: ToolDefinition;
  explanation: string;
}

export interface AppSettings {
  model_provider: string;
  ollama_base_url: string;
  default_model: string;
  openai_api_key: string;
  openai_base_url: string;
  anthropic_api_key: string;
  anthropic_base_url: string;
  default_temperature: number;
  default_max_tokens: number;
  [key: string]: unknown;
}
