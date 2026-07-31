import { NavLink, Outlet } from "react-router-dom";
import { Shield, FileText, Inbox, Activity, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/theme";
import { useStatus } from "@/lib/status";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Shield;
  end?: boolean;
  badge?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Vault", icon: Shield, end: true },
  { to: "/library", label: "Library", icon: FileText },
  { to: "/review", label: "Review", icon: Inbox, badge: true },
  { to: "/status", label: "Status", icon: Activity },
];

export function Layout() {
  const { resolved, toggleTheme } = useTheme();
  const { status, connected } = useStatus();
  const review = status?.fields?.review ?? 0;
  const isDark = resolved === "dark";

  return (
    <>
      <header className="sticky top-0 z-20 border-b bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1040px] items-center gap-5 px-5 py-3">
          <NavLink to="/" aria-label="Field Vault — home" className="mr-auto inline-flex items-center gap-3">
            <span className="flex size-[34px] flex-none items-center justify-center rounded-[10px] border border-primary/25 bg-primary/10 text-primary">
              <Shield className="size-5" strokeWidth={1.6} />
            </span>
            <span className="flex flex-col leading-none">
              <span className="text-[1.2rem] font-semibold tracking-tight">The Archive</span>
              <span className="mono mt-0.5 text-[0.625rem] uppercase tracking-[0.22em] text-muted-foreground max-[620px]:hidden">
                field vault
              </span>
            </span>
          </NavLink>

          <nav className="flex items-center gap-1 max-[620px]:hidden" aria-label="Primary">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  cn(
                    "mono inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                    isActive && "bg-primary/10 text-primary hover:bg-primary/10 hover:text-primary",
                  )
                }
              >
                <span>{n.label}</span>
                {n.badge && review > 0 && (
                  <span className="mono flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-danger px-1 text-[0.6875rem] font-medium text-white">
                    {review}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          <span
            className={cn(
              "mono ml-4 inline-flex items-center gap-1.5 text-[0.6875rem] uppercase tracking-[0.12em] text-muted-foreground/70 max-[620px]:ml-auto",
              connected && "text-primary",
            )}
            title={connected ? "Live updates connected" : "Reconnecting…"}
          >
            <span
              className={cn(
                "size-[7px] rounded-full bg-muted-foreground/50",
                connected && "bg-vault shadow-[0_0_0_3px_var(--vault-wash)]",
              )}
            />
            <span className="max-[620px]:hidden">{connected ? "live" : "offline"}</span>
          </span>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            title={isDark ? "Light mode" : "Dark mode"}
            className="ml-3 flex size-9 flex-none items-center justify-center rounded-full border text-muted-foreground transition-colors hover:border-primary hover:bg-primary/10 hover:text-primary"
          >
            {isDark ? <Sun className="size-[17px]" /> : <Moon className="size-[17px]" />}
          </button>
        </div>
      </header>

      <Outlet />

      {/* mobile: bottom tab bar for thumb-reach navigation */}
      <nav
        className="fixed inset-x-0 bottom-0 z-30 hidden grid-cols-4 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md max-[620px]:grid"
        aria-label="Primary"
      >
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) =>
              cn(
                "mono flex min-h-[54px] flex-col items-center justify-center gap-0.5 py-2 text-[0.625rem] tracking-wide text-muted-foreground",
                isActive && "text-primary",
              )
            }
          >
            {({ isActive }) => (
              <>
                <span className="relative flex items-center justify-center">
                  <n.icon className="size-[21px]" strokeWidth={isActive ? 2 : 1.6} />
                  {n.badge && review > 0 && (
                    <span className="mono absolute -right-2 -top-1.5 flex h-[15px] min-w-[15px] items-center justify-center rounded-full bg-danger px-1 text-[0.5625rem] font-medium text-white">
                      {review > 9 ? "9+" : review}
                    </span>
                  )}
                </span>
                <span className="leading-none">{n.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
