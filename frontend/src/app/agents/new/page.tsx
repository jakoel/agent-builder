"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import WizardStepper from "@/components/builder/WizardStepper";
import StepConfig from "@/components/builder/StepConfig";
import StepDesign from "@/components/builder/StepDesign";
import StepReview from "@/components/builder/StepReview";
import StepValidate from "@/components/builder/StepValidate";
import ToolEnhanceDialog from "@/components/builder/ToolEnhanceDialog";
import { validateTools, finalizeAgent, generateFlow } from "@/lib/api";
import { WizardStep, ToolDefinition, FlowDefinition, ToolValidationResult } from "@/lib/types";

export default function NewAgentPage() {
  const router = useRouter();
  const [step, setStep] = useState<WizardStep>(1);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [config, setConfig] = useState({ name: "", description: "", model: "" });
  const [systemPrompt, setSystemPrompt] = useState("");
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [flow, setFlow] = useState<FlowDefinition | undefined>();
  const [validationResults, setValidationResults] = useState<ToolValidationResult[]>([]);
  const [validating, setValidating] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [enhancingTool, setEnhancingTool] = useState<ToolDefinition | null>(null);

  const handleConfigNext = (cfg: { name: string; description: string; model: string; agentId: string }) => {
    setConfig(cfg);
    setAgentId(cfg.agentId);
    setStep(2);
  };

  const handleDesignNext = async (artifacts: { systemPrompt: string; tools: ToolDefinition[]; flow?: FlowDefinition }) => {
    setSystemPrompt(artifacts.systemPrompt);
    setTools(artifacts.tools);

    // Auto-generate the flow from approved tools
    if (agentId) {
      try {
        const flowData = await generateFlow(agentId);
        setFlow(flowData);
      } catch {
        // Flow generation is non-critical; proceed without it
      }
    }
    setStep(3);
  };

  const handleValidate = async () => {
    if (!agentId) return;
    setValidating(true);
    try {
      const resp = await validateTools(agentId);
      setValidationResults(resp.results);
    } catch {
      /* handle error */
    }
    setValidating(false);
  };

  const handleFinalize = async () => {
    if (!agentId) return;
    setFinalizing(true);
    try {
      const agent = await finalizeAgent(agentId);
      router.push(`/agents/${agent.id}`);
    } catch {
      /* handle error */
    }
    setFinalizing(false);
  };

  const handleToolEnhanceAccept = (updatedTool: ToolDefinition) => {
    setTools(prev => prev.map(t => t.name === updatedTool.name ? updatedTool : t));
    setValidationResults([]); // clear stale results
    setEnhancingTool(null);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <WizardStepper currentStep={step} />
      <div className="flex-1 overflow-hidden">
        {step === 1 && <StepConfig onNext={handleConfigNext} />}
        {step === 2 && agentId && (
          <StepDesign agentId={agentId} onNext={handleDesignNext} onBack={() => setStep(1)} />
        )}
        {step === 3 && agentId && (
          <StepReview
            agentId={agentId}
            artifacts={{ systemPrompt, tools, flow }}
            validationResults={validationResults}
            onToolUpdate={setTools}
            onBack={() => setStep(2)}
            onNext={() => setStep(4)}
            onEnhanceTool={(tool) => setEnhancingTool(tool)}
          />
        )}
        {step === 4 && agentId && (
          <StepValidate
            agentId={agentId}
            tools={tools}
            validationResults={validationResults}
            onValidate={handleValidate}
            onBack={() => setStep(3)}
            onFinalize={handleFinalize}
            onFixTool={(toolName) => {
              const tool = tools.find(t => t.name === toolName);
              if (tool) setEnhancingTool(tool);
            }}
            validating={validating}
            finalizing={finalizing}
          />
        )}
      </div>
      {enhancingTool && agentId && (
        <ToolEnhanceDialog
          agentId={agentId}
          tool={enhancingTool}
          onAccept={handleToolEnhanceAccept}
          onClose={() => setEnhancingTool(null)}
        />
      )}
    </div>
  );
}
