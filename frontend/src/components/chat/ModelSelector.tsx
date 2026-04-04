"use client";

import { useModels } from "@/lib/hooks/useModels";

interface ModelSelectorProps {
  value: string;
  onChange: (model: string) => void;
}

export default function ModelSelector({
  value,
  onChange,
}: ModelSelectorProps) {
  const { models, loading, error } = useModels();

  return (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1.5">
        Model
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 disabled:opacity-50"
      >
        <option value="">
          {loading ? "Loading models..." : "Select a model"}
        </option>
        {models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.name}
          </option>
        ))}
      </select>
      {error && (
        <p className="text-xs text-red-400 mt-1">{error}</p>
      )}
    </div>
  );
}
