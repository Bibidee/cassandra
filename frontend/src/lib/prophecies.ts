import { readClient } from "./genlayer-client";
import { CASSANDRA_ADDRESS, type ProphecyState } from "../config/contracts";

export interface ProphecyEntry {
  id: number;
  state: ProphecyState;
  rationale: string;
}

async function withRetry<T>(fn: () => Promise<T>, retries = 3, delayMs = 800): Promise<T> {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt === retries - 1) throw err;
      await new Promise((r) => setTimeout(r, delayMs * (attempt + 1)));
    }
  }
  throw new Error("unreachable");
}

export async function pooled<T>(tasks: (() => Promise<T>)[], concurrency: number): Promise<(T | null)[]> {
  const results: (T | null)[] = new Array(tasks.length).fill(null);
  let index = 0;
  async function worker() {
    while (index < tasks.length) {
      const i = index++;
      try {
        results[i] = await tasks[i]();
      } catch {
        results[i] = null;
      }
    }
  }
  await Promise.all(Array.from({ length: concurrency }, worker));
  return results;
}

export async function fetchProphecy(id: number): Promise<ProphecyEntry> {
  const [state, rationale] = await Promise.all([
    withRetry(() =>
      readClient.readContract({
        address: CASSANDRA_ADDRESS,
        functionName: "get_prophecy_state",
        args: [id],
      })
    ),
    withRetry(() =>
      readClient.readContract({
        address: CASSANDRA_ADDRESS,
        functionName: "get_resolution_rationale",
        args: [id],
      })
    ),
  ]);
  return { id, state: state as unknown as ProphecyState, rationale: rationale as string };
}

export async function fetchAllProphecies(): Promise<ProphecyEntry[]> {
  const count = (await withRetry(() =>
    readClient.readContract({
      address: CASSANDRA_ADDRESS,
      functionName: "get_prophecy_count",
      args: [],
    })
  )) as number;

  const tasks = Array.from({ length: count }, (_, id) => () => fetchProphecy(id));
  const results = await pooled(tasks, 4);
  return (results.filter(Boolean) as ProphecyEntry[]).reverse();
}

export async function fetchCoverageOf(id: number, address: string): Promise<number | bigint> {
  return (await withRetry(() =>
    readClient.readContract({
      address: CASSANDRA_ADDRESS,
      functionName: "get_coverage_of",
      args: [id, address],
    })
  )) as number | bigint;
}

export async function fetchLiquidityOf(id: number, address: string): Promise<number | bigint> {
  return (await withRetry(() =>
    readClient.readContract({
      address: CASSANDRA_ADDRESS,
      functionName: "get_liquidity_of",
      args: [id, address],
    })
  )) as number | bigint;
}
