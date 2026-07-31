// Live pipeline status via Server-Sent Events (/api/events). One held connection,
// pushed on every job/document change — no polling. EventSource auto-reconnects
// on error, so a worker/api restart heals itself. `connected` tracks the link so
// the UI can show a live/offline dot.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { StatusSnapshot } from "@/api";

interface StatusCtx {
  status: StatusSnapshot | null;
  connected: boolean;
}

const Ctx = createContext<StatusCtx>({ status: null, connected: false });

export function StatusProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<StatusSnapshot | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = new EventSource("/api/events");
    es.onopen = () => setConnected(true);
    es.onmessage = (e) => {
      try {
        setStatus(JSON.parse(e.data));
      } catch {
        /* heartbeat / partial */
      }
    };
    es.onerror = () => setConnected(false); // browser retries automatically
    return () => es.close();
  }, []);

  return <Ctx.Provider value={{ status, connected }}>{children}</Ctx.Provider>;
}

export function useStatus(): StatusCtx {
  return useContext(Ctx);
}
