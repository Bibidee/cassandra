import { useCallback, useEffect, useRef, useState } from "react";
import { fetchProphecy, type ProphecyEntry } from "./prophecies";

const POLL_MS = 8000;

export function useProphecy(id: number) {
  const [entry, setEntry] = useState<ProphecyEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const entryRef = useRef<ProphecyEntry | null>(null);

  const refresh = useCallback(async () => {
    // Only show loading spinner on the first fetch; subsequent polls update silently.
    if (!entryRef.current) setLoading(true);
    setError(null);
    try {
      const fresh = await fetchProphecy(id);
      entryRef.current = fresh;
      setEntry(fresh);
    } catch (err) {
      if (!entryRef.current) setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return { entry, loading, error, refresh };
}
