"use client";

import { CheckCircle } from "lucide-react";
import { WizardStep } from "@/lib/types";

interface WizardStepperProps {
  currentStep: WizardStep;
}

const steps = [
  { number: 1 as WizardStep, label: "Configure" },
  { number: 2 as WizardStep, label: "Design" },
  { number: 3 as WizardStep, label: "Review & Refine" },
  { number: 4 as WizardStep, label: "Validate & Launch" },
];

export default function WizardStepper({ currentStep }: WizardStepperProps) {
  return (
    <div className="border-b border-gray-800 bg-gray-950 px-8 py-4">
      <div className="flex items-center justify-center max-w-3xl mx-auto">
        {steps.map((s, i) => {
          const isCompleted = s.number < currentStep;
          const isCurrent = s.number === currentStep;
          const isFuture = s.number > currentStep;

          return (
            <div key={s.number} className="flex items-center">
              {/* Step circle */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                    isCurrent
                      ? "bg-blue-500 text-white"
                      : isCompleted
                      ? "bg-green-500 text-white"
                      : "bg-gray-700 text-gray-400"
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle size={16} />
                  ) : (
                    s.number
                  )}
                </div>
                <span
                  className={`mt-1.5 text-xs font-medium whitespace-nowrap ${
                    isCurrent
                      ? "text-blue-400"
                      : isCompleted
                      ? "text-green-400"
                      : "text-gray-500"
                  }`}
                >
                  {s.label}
                </span>
              </div>

              {/* Connector line */}
              {i < steps.length - 1 && (
                <div
                  className={`w-24 h-0.5 mx-3 mt-[-1.25rem] ${
                    s.number < currentStep ? "bg-green-500" : "bg-gray-700"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
