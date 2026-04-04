import {
  AgentDefinition,
  BuilderMessage,
  EnhanceToolResponse,
  OllamaModel,
  RunResult,
  ValidateToolsResponse,
} from "./types";

const BASE_URL = "http://localhost:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// Agents
export async function getAgents(): Promise<AgentDefinition[]> {
  return request<AgentDefinition[]>("/api/agents");
}

export async function getAgent(id: string): Promise<AgentDefinition> {
  return request<AgentDefinition>(`/api/agents/${id}`);
}

export async function updateAgent(
  id: string,
  data: Partial<AgentDefinition>
): Promise<AgentDefinition> {
  return request<AgentDefinition>(`/api/agents/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteAgent(id: string): Promise<void> {
  await request<void>(`/api/agents/${id}`, { method: "DELETE" });
}

// Builder
export async function startBuilder(params: {
  name: string;
  description: string;
  model: string;
}): Promise<{ agent_id: string; messages: BuilderMessage[]; status: string }> {
  return request("/api/builder/start", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function sendBuilderMessage(
  agentId: string,
  message: string,
  phase?: string,
  context?: Record<string, any>
): Promise<BuilderMessage> {
  return request<BuilderMessage>(`/api/builder/${agentId}/message`, {
    method: "POST",
    body: JSON.stringify({ message, phase, context }),
  });
}

export async function generateFlow(
  agentId: string
): Promise<any> {
  return request(`/api/builder/${agentId}/generate-flow`, {
    method: "POST",
  });
}

export async function finalizeAgent(
  agentId: string
): Promise<AgentDefinition> {
  return request<AgentDefinition>(`/api/builder/${agentId}/finalize`, {
    method: "POST",
  });
}

// Runs
export async function startRun(
  agentId: string,
  inputData: Record<string, any>
): Promise<RunResult> {
  return request<RunResult>("/api/runs", {
    method: "POST",
    body: JSON.stringify({ agent_id: agentId, input_data: inputData }),
  });
}

export async function getRun(runId: string): Promise<RunResult> {
  return request<RunResult>(`/api/runs/${runId}`);
}

export async function getRuns(agentId?: string): Promise<RunResult[]> {
  const query = agentId ? `?agent_id=${agentId}` : "";
  return request<RunResult[]>(`/api/runs${query}`);
}

export async function cancelRun(runId: string): Promise<RunResult> {
  return request<RunResult>(`/api/runs/${runId}/cancel`, {
    method: "POST",
  });
}

// Builder - Validation & Enhancement
export async function validateTools(agentId: string): Promise<ValidateToolsResponse> {
  return request<ValidateToolsResponse>(`/api/builder/${agentId}/validate-tools`, {
    method: "POST",
  });
}

export async function enhanceTool(
  agentId: string,
  toolName: string,
  instruction: string
): Promise<EnhanceToolResponse> {
  return request<EnhanceToolResponse>(`/api/builder/${agentId}/enhance-tool`, {
    method: "POST",
    body: JSON.stringify({ tool_name: toolName, instruction }),
  });
}

// Tool Library
export async function getToolLibrary(): Promise<any[]> {
  return request<any[]>("/api/tool-library");
}

export async function getToolDetail(name: string): Promise<any> {
  return request(`/api/tool-library/${name}`);
}

// Models
export async function getModels(): Promise<OllamaModel[]> {
  return request<OllamaModel[]>("/api/models");
}
