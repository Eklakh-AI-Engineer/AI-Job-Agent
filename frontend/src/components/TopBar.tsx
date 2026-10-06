"use client";

import { Badge } from "./ui";

export function TopBar({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {title}
        </h1>
        {subtitle ? <p className="text-sm text-muted">{subtitle}</p> : null}
      </div>
      <div className="flex items-center gap-3">
        {actions}
        <Badge tone="success">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          Agent active
        </Badge>
      </div>
    </header>
  );
}
