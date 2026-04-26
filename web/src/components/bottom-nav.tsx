"use client";
/**
 * BottomNav — fixed bottom on mobile, hidden on md+.
 * Uses controlled `value` from parent so it works with the existing Tabs.
 */
import { LayoutDashboard, LineChart, Plane, PlusCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

const ITEMS = [
  { value: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { value: "flights", label: "Flights", icon: Plane },
  { value: "trends", label: "Trends", icon: LineChart },
  { value: "trips", label: "Trips", icon: PlusCircle },
] as const;

export function BottomNav({ value, onChange }: Props) {
  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-background/90 backdrop-blur border-t"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <div className="grid grid-cols-4">
        {ITEMS.map(({ value: v, label, icon: Icon }) => {
          const active = v === value;
          return (
            <button
              key={v}
              type="button"
              onClick={() => onChange(v)}
              className={cn(
                "flex flex-col items-center gap-1 py-2 text-[10px] transition-colors",
                active ? "text-foreground" : "text-muted-foreground",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="size-5" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
