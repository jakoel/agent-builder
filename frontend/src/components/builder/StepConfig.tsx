"use client";

import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import ModelSelector from "@/components/chat/ModelSelector";
import { startBuilder } from "@/lib/api";

interface StepConfigProps {
  onNext: (config: {
    name: string;
    description: string;
    model: string;
    agentId: string;
  }) => void;
}

export default function StepConfig({ onNext }: StepConfigProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [model, setModel] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canProceed = name.trim().length > 0 && model.length > 0;

  const handleNext = async () => {
    if (!canProceed) return;
    setCreating(true);
    setError(null);
    try {
      const resp = await startBuilder({
        name: name.trim(),
        description: description.trim(),
        model,
      });
      onNext({
        name: name.trim(),
        description: description.trim(),
        model,
        agentId: resp.agent_id,
      });
    } catch (err: any) {
      setError(err.message ?? "Failed to create agent");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto mt-12 px-4">
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 space-y-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-100 mb-1">
            Configure your agent
          </h2>
          <p className="text-sm text-gray-500">
            Give your agent a name, description, and choose a model.
          </p>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">
            Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Agent"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What does this agent do?"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 resize-none focus:outline-none focus:border-blue-500"
          />
        </div>

        <ModelSelector value={model} onChange={setModel} />

        {error && (
          <p className="text-sm text-red-400">{error}</p>
        )}

        <button
          onClick={handleNext}
          disabled={!canProceed || creating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {creating ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Creating...
            </>
          ) : (
            <>
              Next
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
