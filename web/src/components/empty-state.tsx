import { ReactNode } from "react";

interface Props {
  title: string;
  body?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, body, action }: Props) {
  return (
    <div className="text-center py-16">
      <p className="text-base font-medium">{title}</p>
      {body && <div className="text-sm text-muted-foreground mt-2">{body}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
