const DEFAULT_DETAILS = {
  startDate: "",
  endDate: "",
  travelers: "2",
  travelerDetails: "",
  budget: "mid-range",
  interests: [],
  specialRequirements: "",
  departureCity: "",
};

export function parseSavedRequest(request = "") {
  const idea = request.match(/^Trip Request:\s*([\s\S]*?)\n\s*Essential Details:/m);
  const field = (name) => request.match(new RegExp(`^- ${name}: (.*)$`, "m"))?.[1]?.trim() || "";
  const dates = field("Travel Dates").match(/(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})/);

  return {
    tripIdea: idea ? idea[1].trim() : request.trim(),
    details: {
      ...DEFAULT_DETAILS,
      startDate: dates?.[1] || "",
      endDate: dates?.[2] || "",
      travelers: field("Number of Travelers") || "2",
      travelerDetails: field("Traveler Details"),
      budget: field("Budget Level") || "mid-range",
      interests: field("Interests") ? field("Interests").split(/,\s*/) : [],
      specialRequirements: field("Special Requirements"),
      departureCity: field("Departure City"),
    },
  };
}

export function requestFormDetails(request = "", stored = null) {
  if (stored) return stored;
  if (!request.includes("Essential Details:")) return null;
  const details = parseSavedRequest(request).details;
  if (!details.departureCity || !details.startDate || !details.endDate) return null;
  return {
    origin: details.departureCity,
    departure_date: details.startDate,
    return_date: details.endDate,
    travelers: Number(details.travelers),
    budget_level: details.budget,
    interests: details.interests,
    traveler_details: details.travelerDetails,
    special_requirements: details.specialRequirements,
  };
}

export function detailsForForm(formDetails) {
  if (!formDetails) return null;
  return {
    departureCity: formDetails.origin,
    startDate: formDetails.departure_date,
    endDate: formDetails.return_date,
    travelers: String(formDetails.travelers),
    budget: formDetails.budget_level,
    interests: formDetails.interests || [],
    travelerDetails: formDetails.traveler_details || "",
    specialRequirements: formDetails.special_requirements || "",
  };
}

export function hasPastTravelDate(request = "") {
  const { startDate } = parseSavedRequest(request).details;
  if (!startDate) return false;
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return startDate < today;
}
