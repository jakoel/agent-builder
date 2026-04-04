"use client";

interface PromptEditorProps {
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
}

export default function PromptEditor({
  value,
  onChange,
  readOnly = false,
}: PromptEditorProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1.5">
        System Prompt
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        readOnly={readOnly}
        rows={12}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-100 font-mono leading-relaxed resize-y focus:outline-none focus:border-blue-500 read-only:opacity-70"
        placeholder="System prompt will appear here..."
      />
    </div>
  );
}
