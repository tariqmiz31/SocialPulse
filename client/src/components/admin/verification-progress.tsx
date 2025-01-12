import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Check, Clock, XCircle } from "lucide-react";

interface VerificationStep {
  step: number;
  label: string;
  completed: boolean;
  current: boolean;
  error?: string;
}

interface VerificationProgressProps {
  steps: VerificationStep[];
  currentStep: number;
}

export function VerificationProgress({ steps, currentStep }: VerificationProgressProps) {
  const progress = (currentStep / steps.length) * 100;

  return (
    <Card className="mb-6">
      <CardContent className="pt-6">
        <Progress value={progress} className="mb-4" />
        <div className="space-y-4">
          {steps.map((step) => (
            <div
              key={step.step}
              className={`flex items-center gap-3 p-3 rounded-lg border ${
                step.current ? 'bg-primary/10 border-primary' : 'border-border'
              }`}
            >
              {step.completed ? (
                <Check className="h-5 w-5 text-green-500" />
              ) : step.current ? (
                <Clock className="h-5 w-5 text-primary animate-pulse" />
              ) : (
                <div className="h-5 w-5 rounded-full border-2 border-muted-foreground" />
              )}
              <div className="flex-1">
                <p className="font-medium">خطوة {step.step}: {step.label}</p>
                {step.error && (
                  <div className="flex items-center gap-2 mt-2 text-sm text-destructive">
                    <XCircle className="h-4 w-4" />
                    <p>{step.error}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
