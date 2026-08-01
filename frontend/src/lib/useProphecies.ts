import { useCallback, useEffect, useState } from "react";
import { fetchAllProphecies, type ProphecyEntry } from "./prophecies";

const POLL_MS = 20000;

export function useProphecies() {
  const [prophecies, setProphecies] = useState<ProphecyEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (prophecies.length === 0) setLoading(true);
    try {
      const fresh = await fetchAllProphecies();
      setProphecies(fresh);
    } catch {
      // keep stale data visible on error
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return { prophecies, loading, refresh };
}
