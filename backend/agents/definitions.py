"""
AI Agent definitions — only the 3 agents that still require LLM reasoning.
The 4 data-fetching agents (flights, accommodation, activities, logistics)
are now pure API services and no longer need AI.
"""

from crewai import Agent
from typing import List
from backend.agents.llm import create_gemini_llm


def create_travel_manager(tools: List = None) -> Agent:
    """
    ORCHESTRATOR AGENT
    Parses user requests into structured travel parameters.
    """
    return Agent(
        role="Travel Planning Manager",
        goal=(
            "Analyze user travel requests and extract structured parameters: "
            "destinations, dates, duration, number of travelers, budget level, "
            "interests, cabin class, and special requirements. "
            "Output a clear, structured breakdown that downstream services can use."
        ),
        backstory=(
            "You are a seasoned travel planning expert with 15 years of experience. "
            "You have a talent for understanding what travelers really want, even when "
            "they don't articulate it fully. You extract precise details from vague requests "
            "and fill in reasonable defaults for missing information. You think about the "
            "traveler's experience holistically and anticipate needs they haven't mentioned."
        ),
        tools=tools or [],
        llm=create_gemini_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )


def create_travel_knowledge_agent(tools: List = None) -> Agent:
    """
    TRAVEL KNOWLEDGE EXPERT AGENT
    Provides cultural insights, visa info, and practical advice via RAG.
    """
    return Agent(
        role="Travel Knowledge Expert",
        goal=(
            "Provide destination-specific travel advice supported by excerpts from "
            "the local travel knowledge base. State clearly when it has no match."
        ),
        backstory=(
            "You are a careful travel researcher. Treat retrieved documents as dated source "
            "material, cite their filenames, and never fill a knowledge-base gap from memory. "
            "Current visa, entry, price, and opening-hour rules require fresh official verification."
        ),
        tools=tools or [],
        llm=create_gemini_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_itinerary_compiler(tools: List = None) -> Agent:
    """
    ITINERARY COMPILER AGENT
    Takes all real API data + knowledge and creates the final itinerary.
    This is where the AI adds the most value — synthesis and personalization.
    """
    return Agent(
        role="Itinerary Compiler & Optimizer",
        goal=(
            "Synthesize real-time travel data (flights, hotels, activities, logistics) "
            "and expert knowledge into a comprehensive, personalized day-by-day itinerary. "
            "Ensure logical flow, optimal timing, geographic efficiency, and balanced pacing. "
            "Create a beautiful, easy-to-follow travel plan."
        ),
        backstory=(
            "You are a master travel planner known for creating perfectly orchestrated "
            "itineraries. You have an eye for detail and spatial awareness — you group "
            "activities by neighborhood to minimize transit time. You understand the rhythm "
            "of travel: when to have early starts vs. leisurely mornings, when to have a "
            "big day vs. downtime. You create itineraries that are ambitious yet realistic, "
            "with built-in flexibility. Your itineraries read like a story, building excitement "
            "throughout the trip. You include all practical details: addresses, prices, "
            "booking links, and insider tips."
        ),
        tools=tools or [],
        llm=create_gemini_llm(),
        verbose=True,
        allow_delegation=False,
    )
