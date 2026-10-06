"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  IconActivity,
  IconApplications,
  IconCopilot,
  IconDashboard,
  IconDocuments,
  IconJobs,
  IconLogout,
  IconProfile,
} from "./icons";

const NAV = [
  { href: "/dashboard", label: "Command Center", icon: IconDashboard },
  { href: "/opportunities", label: "Opportunities", icon: IconJobs },
  { href: "/copilot", label: "Application Copilot", icon: IconCopilot },
  { href: "/documents", label: "Document Workspace", icon: IconDocuments },
  { href: "/applications", label: "Applications", icon: IconApplications },
  { href: "/activity", label: "Agent Activity", icon: IconActivity },
  { href: "/profile", label: "Candidate Profile", icon: IconProfile },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
          AI
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight text-foreground">
            JobAgent
          </p>
          <p className="text-xs text-muted">AI Career Agent</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted hover:bg-background hover:text-foreground"
              }`}
            >
              <Icon />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        <div className="mb-2 px-2">
          <p className="truncate text-xs font-medium text-foreground">
            {user?.full_name || "Signed in"}
          </p>
          <p className="truncate text-xs text-muted">{user?.email}</p>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-background hover:text-danger"
        >
          <IconLogout />
          Sign out
        </button>
      </div>
    </aside>
  );
}
