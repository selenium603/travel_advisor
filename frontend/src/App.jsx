import { useState, useEffect } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ChatInput from "./components/ChatInput";
import TripDetailsForm from "./components/TripDetailsForm";
import AgentProgress from "./components/AgentProgress";
import ItineraryDisplay from "./components/ItineraryDisplay";
import SavedRequestDetails from "./components/SavedRequestDetails";
import MemoryProfile from "./components/MemoryProfile";
import WelcomeScreen from "./components/WelcomeScreen";
import { usePlanStream } from "./hooks/usePlanStream";
import { useItineraryHistory } from "./hooks/useItineraryHistory";
import { parseSavedRequest, requestFormDetails, detailsForForm } from "./utils/savedRequest";
import { getSessionId, profileBudgetToForm } from "./utils/sessionMemory";

// App flow: idle -> form -> processing -> completed
//                       \-> error

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tripIdea, setTripIdea] = useState("");       // Step 1: user's free-text idea
  const [currentRequest, setCurrentRequest] = useState(""); // Full structured prompt sent to backend
  const [currentFormDetails, setCurrentFormDetails] = useState(null);
  const [selectedItinerary, setSelectedItinerary] = useState(null);
  const [initialDetails, setInitialDetails] = useState(null);
  const [sessionId] = useState(getSessionId);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [preferences, setPreferences] = useState({});

  const {
    status,
    agents,
    agentProgress,
    itinerary,
    error,
    memoryWarning,
    sendRequest,
    reset,
  } = usePlanStream();

  const { history, fetchHistory, refreshItinerary, deleteItinerary } = useItineraryHistory();

  useEffect(() => {
    fetch("/api/memory/profile")
      .then((response) => response.ok ? response.json() : null)
      .then((profile) => { if (profile) setPreferences(profile.preferences); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!["completed", "error"].includes(status)) return;
    fetch("/api/memory/profile")
      .then((response) => response.ok ? response.json() : null)
      .then((profile) => { if (profile) setPreferences(profile.preferences); })
      .catch(() => {});
  }, [status]);

  useEffect(() => {
    if (["processing", "completed", "error"].includes(status)) {
      fetchHistory();
    }
  }, [status, fetchHistory]);

  // Step 1: User types trip idea -> show details form
  const handleTripIdea = (message) => {
    setMemoryOpen(false);
    reset();
    setSelectedItinerary(null);
    setInitialDetails(null);
    setCurrentRequest("");
    setCurrentFormDetails(null);
    setTripIdea(message);
  };

  // Step 2: User fills details form -> send to backend
  const handleDetailsSubmit = (structuredPrompt, formDetails) => {
    setCurrentRequest(structuredPrompt);
    setCurrentFormDetails(formDetails);
    sendRequest(structuredPrompt, formDetails, sessionId, tripIdea);
  };

  // Go back from form to input
  const handleBackToInput = () => {
    setTripIdea("");
    setInitialDetails(null);
  };

  const handleSelectHistory = (item) => {
    setMemoryOpen(false);
    reset();
    setTripIdea("");
    setInitialDetails(null);
    setSelectedItinerary(item);
    setCurrentRequest(item.request);
    setCurrentFormDetails(requestFormDetails(item.request, item.form_details));
  };

  const handleRetryRequest = (request, storedFormDetails = null) => {
    const formDetails = requestFormDetails(request, storedFormDetails);
    setSelectedItinerary(null);
    setTripIdea("");
    setInitialDetails(null);
    setCurrentRequest(request);
    setCurrentFormDetails(formDetails);
    sendRequest(request, formDetails, sessionId, parseSavedRequest(request).tripIdea);
  };

  const handleEditRequest = (request, storedFormDetails = null) => {
    setMemoryOpen(false);
    const saved = parseSavedRequest(request);
    reset();
    setSelectedItinerary(null);
    setCurrentRequest("");
    setInitialDetails(detailsForForm(storedFormDetails) || saved.details);
    setTripIdea(saved.tripIdea);
  };

  const handleRefreshSelected = async () => {
    if (!selectedItinerary) return;
    const item = await refreshItinerary(selectedItinerary.id);
    if (item) {
      setSelectedItinerary((current) => current?.id === item.id ? item : current);
    }
  };

  const handleNewTrip = () => {
    setMemoryOpen(false);
    reset();
    setTripIdea("");
    setSelectedItinerary(null);
    setCurrentRequest("");
    setInitialDetails(null);
    setCurrentFormDetails(null);
  };

  const isProcessing = status === "processing" || status === "connecting";
  const showForm = tripIdea && status === "idle" && !selectedItinerary && !memoryOpen;
  const showWelcome = status === "idle" && !tripIdea && !selectedItinerary && !memoryOpen;
  const budgetDefault = profileBudgetToForm(preferences.budget?.value);
  const showItinerary =
    (isProcessing && itinerary) ||
    (status === "completed" && itinerary) ||
    (selectedItinerary && selectedItinerary.status === "completed");

  const displayedItinerary = selectedItinerary
    ? selectedItinerary.itinerary
    : itinerary;
  const displayedRequest = selectedItinerary
    ? selectedItinerary.request
    : currentRequest;

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          history={history}
          onSelect={handleSelectHistory}
          onDelete={deleteItinerary}
          onMemory={() => setMemoryOpen(true)}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Scrollable content area */}
          <div className="flex-1 overflow-y-auto">
            {memoryOpen && <MemoryProfile sessionId={sessionId}
              onBack={() => setMemoryOpen(false)} onProfileChange={setPreferences} />}

            {showWelcome && <WelcomeScreen />}

            {/* Step 2: Trip details form */}
            {showForm && (
              <TripDetailsForm
                tripIdea={tripIdea}
                initialDetails={initialDetails || (budgetDefault ? { budget: budgetDefault } : null)}
                onSubmit={handleDetailsSubmit}
                onBack={handleBackToInput}
                disabled={false}
              />
            )}

            {!memoryOpen && memoryWarning && <p role="status" className="mx-4 mt-3 text-sm text-amber-700">{memoryWarning}</p>}

            {!memoryOpen && status === "error" && (
              <SavedRequestDetails
                item={{ request: currentRequest, form_details: currentFormDetails, status: "failed" }}
                error={error}
                onRetry={() => handleRetryRequest(currentRequest, currentFormDetails)}
                onEdit={() => handleEditRequest(currentRequest, currentFormDetails)}
              />
            )}

            {!memoryOpen && selectedItinerary && selectedItinerary.status !== "completed" && (
              <SavedRequestDetails
                item={selectedItinerary}
                onRetry={() => handleRetryRequest(selectedItinerary.request, selectedItinerary.form_details)}
                onEdit={() => handleEditRequest(selectedItinerary.request, selectedItinerary.form_details)}
                onRefresh={handleRefreshSelected}
              />
            )}

            {/* Agent progress */}
            {!memoryOpen && isProcessing && (
              <AgentProgress agents={agents} agentProgress={agentProgress} />
            )}

            {/* Itinerary display */}
            {!memoryOpen && showItinerary && (
              <ItineraryDisplay
                itinerary={displayedItinerary}
                request={displayedRequest}
                streaming={isProcessing}
              />
            )}

            {/* New trip button */}
            {!memoryOpen && ((status === "completed" && showItinerary) || status === "error") && (
              <div className="text-center py-4">
                <button
                  onClick={handleNewTrip}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-6 py-2.5 rounded-xl transition-colors"
                >
                  规划新行程
                </button>
              </div>
            )}
          </div>

          {/* Step 1: Chat input — only visible when no form is showing */}
          {!showForm && !memoryOpen && (
            <ChatInput onSend={handleTripIdea} disabled={isProcessing} />
          )}
        </main>
      </div>
    </div>
  );
}
