import { useState, useRef, useCallback } from "react";

export function usePlanStream() {
  const [status, setStatus] = useState("idle");
  const [agents, setAgents] = useState([]);
  const [agentProgress, setAgentProgress] = useState({});
  const [itinerary, setItinerary] = useState(null);
  const [itineraryId, setItineraryId] = useState(null);
  const [error, setError] = useState(null);
  const [memoryWarning, setMemoryWarning] = useState(null);
  const controllerRef = useRef(null);
  const requestRef = useRef(0);

  const reset = useCallback(() => {
    requestRef.current += 1;
    controllerRef.current?.abort();
    controllerRef.current = null;
    setStatus("idle");
    setAgents([]);
    setAgentProgress({});
    setItinerary(null);
    setItineraryId(null);
    setError(null);
    setMemoryWarning(null);
  }, []);

  const sendRequest = useCallback(async (message, formDetails = null, sessionId = null, tripIdea = null) => {
    reset();
    const requestId = requestRef.current;
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus("connecting");

    let terminal = false;
    const handleEvent = (raw) => {
      const line = raw.split(/\r?\n/).find((part) => part.startsWith("data:"));
      if (!line || requestRef.current !== requestId) return;
      const data = JSON.parse(line.slice(5).trimStart());
      switch (data.type) {
        case "started":
          setStatus("processing");
          setAgents(data.agents);
          setItineraryId(data.itinerary_id);
          setAgentProgress(Object.fromEntries(data.agents.map((agent) => [agent.key, "pending"])));
          break;
        case "agent_progress":
          setAgentProgress((previous) => ({ ...previous, [data.agent_key]: data.status }));
          break;
        case "delta":
          setItinerary((previous) => (previous || "") + data.text);
          break;
        case "completed":
          terminal = true;
          setStatus("completed");
          setItinerary(data.itinerary);
          setItineraryId(data.itinerary_id);
          setAgentProgress((previous) => Object.fromEntries(
            Object.keys(previous).map((key) => [key, "completed"]),
          ));
          break;
        case "error":
          terminal = true;
          setStatus("error");
          setError(/[\u4e00-\u9fff]/.test(data.message || "")
            ? data.message : "行程规划失败，请检查服务配置后重试。");
          break;
        case "memory_warning":
          setMemoryWarning(data.message);
          break;
        default:
          break;
      }
    };

    try {
      const response = await fetch("/api/plan/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ message, form_details: formDetails, session_id: sessionId, trip_idea: tripIdea }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error("stream unavailable");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() || "";
        frames.forEach(handleEvent);
        if (done) break;
      }
      if (buffer.trim()) handleEvent(buffer);
      if (!terminal && requestRef.current === requestId) throw new Error("stream ended early");
    } catch {
      if (!controller.signal.aborted && requestRef.current === requestId) {
        setStatus("error");
        setError("连接中断，请检查后端服务后重试。已生成的行程可在历史行程中查看。");
      }
    } finally {
      if (requestRef.current === requestId) controllerRef.current = null;
    }
  }, [reset]);

  return { status, agents, agentProgress, itinerary, itineraryId, error, memoryWarning, sendRequest, reset };
}
