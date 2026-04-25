"use client";

import { useEffect, useState } from "react";
import { getSettings, resetSettings, updateSettings, getModels } from "@/lib/api";
import { AppSettings, OllamaModel } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";
import { Eye, EyeOff, RotateCcw, Save } from "lucide-react";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionCard({ title, description, children }: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
        {description && (
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        )}
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({ label, hint, children }: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-600 mt-1">{hint}</p>}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, mono }: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  mono?: boolean;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 transition-all ${mono ? "font-mono" : ""}`}
    />
  );
}

function SecretInput({ value, onChange, placeholder }: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? "sk-…"}
        className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 pr-10 text-sm text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 transition-all"
      />
      <button
        type="button"
        onClick={() => setShow((v) => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
      >
        {show ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  );
}

function NumberInput({ value, onChange, min, max, step }: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      min={min}
      max={max}
      step={step}
      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 transition-all"
    />
  );
}

function SelectInput({ value, onChange, options }: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 transition-all appearance-none"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-slate-800">
          {o.label}
        </option>
      ))}
    </select>
  );
}

const PROVIDERS = [
  { value: "ollama",    label: "Ollama",    desc: "Local models" },
  { value: "openai",   label: "OpenAI",    desc: "GPT-4o, o1…" },
  { value: "anthropic",label: "Anthropic", desc: "Claude 4…" },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const [form, setForm] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getSettings(),
      getModels().catch(() => [] as OllamaModel[]),
    ]).then(([s, models]) => {
      setForm(s);
      setOllamaModels(models);
    }).finally(() => setLoading(false));
  }, []);

  function set<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setForm((prev) => prev ? { ...prev, [key]: value } : prev);
    if (saveStatus === "saved") setSaveStatus("idle");
  }

  async function handleSave() {
    if (!form) return;
    setSaveStatus("saving");
    setSaveError(null);
    try {
      const saved = await updateSettings(form as Record<string, unknown>);
      setForm(saved);
      setSaveStatus("saved");
    } catch (e) {
      setSaveError((e as Error).message);
      setSaveStatus("error");
    }
  }

  async function handleReset() {
    setSaveStatus("saving");
    try {
      const defaults = await resetSettings();
      setForm(defaults);
      setSaveStatus("idle");
    } catch (e) {
      setSaveError((e as Error).message);
      setSaveStatus("error");
    }
  }

  if (loading || !form) {
    return (
      <div className="p-6 max-w-2xl space-y-4">
        <Skeleton className="h-20 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
        <Skeleton className="h-36 w-full rounded-2xl" />
      </div>
    );
  }

  const provider = form.model_provider;

  const modelOptions = ollamaModels.length > 0
    ? ollamaModels.map((m) => ({ value: m.name, label: m.name }))
    : [{ value: form.default_model, label: form.default_model }];

  return (
    <div className="p-6 max-w-2xl space-y-5">

      {/* Provider selector */}
      <SectionCard
        title="Model Provider"
        description="Which LLM backend agents will use by default."
      >
        <div className="grid grid-cols-3 gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p.value}
              onClick={() => set("model_provider", p.value)}
              className={`flex flex-col items-start px-4 py-3 rounded-xl border text-left transition-all ${
                provider === p.value
                  ? "bg-violet-500/10 border-violet-500/40 text-violet-300"
                  : "bg-slate-800/40 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-200"
              }`}
            >
              <span className="text-sm font-medium">{p.label}</span>
              <span className="text-xs mt-0.5 opacity-60">{p.desc}</span>
            </button>
          ))}
        </div>
      </SectionCard>

      {/* Ollama */}
      {provider === "ollama" && (
        <SectionCard title="Ollama" description="Locally running Ollama instance.">
          <Field label="Base URL" hint="Default: http://localhost:11434">
            <TextInput
              value={form.ollama_base_url}
              onChange={(v) => set("ollama_base_url", v)}
              placeholder="http://localhost:11434"
              mono
            />
          </Field>
          <Field label="Default Model">
            {ollamaModels.length > 0 ? (
              <SelectInput
                value={form.default_model}
                onChange={(v) => set("default_model", v)}
                options={modelOptions}
              />
            ) : (
              <TextInput
                value={form.default_model}
                onChange={(v) => set("default_model", v)}
                placeholder="qwen3-vl:8b"
                mono
              />
            )}
          </Field>
        </SectionCard>
      )}

      {/* OpenAI */}
      {provider === "openai" && (
        <SectionCard title="OpenAI" description="OpenAI API or any OpenAI-compatible endpoint.">
          <Field label="API Key">
            <SecretInput
              value={form.openai_api_key}
              onChange={(v) => set("openai_api_key", v)}
            />
          </Field>
          <Field label="Base URL" hint="Change this for Azure OpenAI or other compatible APIs.">
            <TextInput
              value={form.openai_base_url}
              onChange={(v) => set("openai_base_url", v)}
              placeholder="https://api.openai.com/v1"
              mono
            />
          </Field>
          <Field label="Default Model">
            <SelectInput
              value={form.default_model}
              onChange={(v) => set("default_model", v)}
              options={[
                { value: "gpt-4o",        label: "gpt-4o" },
                { value: "gpt-4o-mini",   label: "gpt-4o-mini" },
                { value: "o1",            label: "o1" },
                { value: "o1-mini",       label: "o1-mini" },
                { value: form.default_model, label: form.default_model },
              ].filter((o, i, arr) => arr.findIndex((x) => x.value === o.value) === i)}
            />
          </Field>
        </SectionCard>
      )}

      {/* Anthropic */}
      {provider === "anthropic" && (
        <SectionCard title="Anthropic" description="Claude models via the Anthropic API.">
          <Field label="API Key">
            <SecretInput
              value={form.anthropic_api_key}
              onChange={(v) => set("anthropic_api_key", v)}
              placeholder="sk-ant-…"
            />
          </Field>
          <Field label="Base URL" hint="Only change if using a proxy or custom endpoint.">
            <TextInput
              value={form.anthropic_base_url}
              onChange={(v) => set("anthropic_base_url", v)}
              placeholder="https://api.anthropic.com"
              mono
            />
          </Field>
          <Field label="Default Model">
            <SelectInput
              value={form.default_model}
              onChange={(v) => set("default_model", v)}
              options={[
                { value: "claude-opus-4-7",           label: "Claude Opus 4.7" },
                { value: "claude-sonnet-4-6",         label: "Claude Sonnet 4.6" },
                { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
                { value: form.default_model,          label: form.default_model },
              ].filter((o, i, arr) => arr.findIndex((x) => x.value === o.value) === i)}
            />
          </Field>
        </SectionCard>
      )}

      {/* Generation defaults */}
      <SectionCard
        title="Generation Defaults"
        description="Applied to all agent runs unless overridden per-agent."
      >
        <Field
          label={`Temperature — ${form.default_temperature}`}
          hint="0 = deterministic, 1 = creative"
        >
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={form.default_temperature}
              onChange={(e) => set("default_temperature", parseFloat(e.target.value))}
              className="flex-1 accent-violet-500"
            />
            <span className="text-xs font-mono text-slate-400 w-8 text-right">
              {form.default_temperature}
            </span>
          </div>
        </Field>
        <Field label="Max Tokens" hint="Maximum tokens per LLM response.">
          <NumberInput
            value={form.default_max_tokens}
            onChange={(v) => set("default_max_tokens", v)}
            min={256}
            max={32768}
            step={256}
          />
        </Field>
      </SectionCard>

      {/* Footer */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saveStatus === "saving"}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 text-sm font-medium text-white shadow-lg shadow-violet-500/20 transition-all"
          >
            <Save size={14} />
            {saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved" : "Save changes"}
          </button>
          <button
            onClick={handleReset}
            disabled={saveStatus === "saving"}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-sm font-medium text-slate-400 hover:text-slate-200 transition-all"
          >
            <RotateCcw size={13} />
            Reset defaults
          </button>
        </div>
        {saveStatus === "error" && saveError && (
          <p className="text-xs text-red-400">{saveError}</p>
        )}
        {saveStatus === "saved" && (
          <p className="text-xs text-emerald-400">Settings saved.</p>
        )}
      </div>
    </div>
  );
}
