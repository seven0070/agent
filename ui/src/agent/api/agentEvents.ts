/**
 * Agent SSE Event Stream Client.
 */

export interface AgentEventFrame {
  eventType: string;
  sessionId: string;
  payload: Record<string, any>;
  timestamp: string;
}

export function subscribeToAgentEvents(
  sessionId: string,
  onEvent: (event: AgentEventFrame) => void,
  onError?: (err: any) => void
): () => void {
  // Simple event poller / SSE stream handler abstraction
  const interval = setInterval(async () => {
    try {
      onEvent({
        eventType: "HEARTBEAT",
        sessionId,
        payload: { status: "online" },
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      if (onError) onError(err);
    }
  }, 5000);

  return () => clearInterval(interval);
}
