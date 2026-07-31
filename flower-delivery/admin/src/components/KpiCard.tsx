import { useEffect, useRef } from "react";
import gsap from "gsap";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { motionState } from "@/lib/motion";

interface KpiCardProps {
  label: string;
  value: number;
  tone: "default" | "success" | "muted" | "destructive";
}

const TONE_CLASSES: Record<KpiCardProps["tone"], string> = {
  default: "bg-primary/5 text-primary border-primary/20",
  success: "bg-success/10 text-success border-success/20",
  muted: "bg-muted text-muted-foreground border-border",
  destructive: "bg-destructive/10 text-destructive border-destructive/20",
};

export function KpiCard({ label, value, tone }: KpiCardProps) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const proxy = { value: 0 };
    const tween = gsap.to(proxy, {
      value,
      duration: motionState.reduceMotion ? 0 : 0.6,
      ease: "power1.out",
      onUpdate: () => {
        el.textContent = String(Math.round(proxy.value));
      },
    });
    return () => {
      tween.kill();
    };
  }, [value]);

  return (
    <Card className={cn("border-2", TONE_CLASSES[tone])}>
      <CardContent className="flex flex-col gap-1">
        <span ref={ref} className="text-4xl font-bold leading-none">0</span>
        <span className="text-xs font-medium opacity-70">{label}</span>
      </CardContent>
    </Card>
  );
}
