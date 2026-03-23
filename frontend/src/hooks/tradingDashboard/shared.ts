export const POLLING_INTERVAL_MS = 30000;

export type RefreshOptions = {
  includeAssignments?: boolean;
  includeOverview?: boolean;
  includeTrades?: boolean;
  includeOverlay?: boolean;
  tradeStatus?: string;
  silent?: boolean;
  signal?: AbortSignal;
  token?: string;
};

export const getErrorMessage = (error: unknown, fallback: string) => {
  return error instanceof Error ? error.message : fallback;
};
