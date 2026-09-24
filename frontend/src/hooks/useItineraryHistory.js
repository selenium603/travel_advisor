import { useState, useEffect, useCallback } from "react";

const API_BASE = "";

export function useItineraryHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/itineraries`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.itineraries || []);
      }
    } catch {
      // Server might not be running yet
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteItinerary = useCallback(async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/itineraries/${id}`, { method: "DELETE" });
      if (res.ok) {
        setHistory((prev) => prev.filter((item) => item.id !== id));
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return { history, loading, fetchHistory, deleteItinerary };
}
