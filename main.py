"""
Multi-Agent AI Travel Planner — CLI Entry Point

Architecture:
    - 3 AI agents (planning, knowledge, compilation) for reasoning
    - 4 API services (flights, accommodation, activities, logistics) for real-time data
    - AI only handles analysis; data comes from real APIs

Usage:
    python main.py
"""

import os
import asyncio
from dotenv import load_dotenv


async def main():
    load_dotenv()

    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY")):
        print("Error: OPENROUTER_API_KEY or GEMINI_API_KEY is required")
        print("Please create a .env file — see .env.example for reference")
        return

    print("=" * 80)
    print("  MULTI-AGENT AI TRAVEL PLANNER v2.0")
    print("  Real-time data from APIs + AI-powered analysis")
    print("=" * 80)
    print()

    # Sample requests
    user_requests = [
        """
        Plan a 10-day luxury honeymoon to Italy, focusing on food and history.
        We want to visit Rome and Florence, staying in 5-star hotels.
        We love wine, authentic Italian cuisine, Renaissance art, and romantic experiences.
        Budget is flexible for a once-in-a-lifetime trip.
        """,
        """
        Plan a 5-day trip to Paris for a solo traveler who loves art and food.
        Mid-range budget around $200/day for accommodation.
        Interested in visiting museums (especially Impressionist art),
        trying authentic French cuisine, and exploring charming neighborhoods.
        """,
        """
        Plan a 7-day family trip to Barcelona with 2 adults and 2 kids (ages 8 and 12).
        We want a mix of culture, beaches, and kid-friendly activities.
        Budget-conscious but willing to splurge on special experiences.
        Interested in Gaudi architecture, local food markets, and Mediterranean beaches.
        """,
    ]

    selected_request = user_requests[1]  # Paris solo trip

    print("User Request:")
    print("-" * 80)
    print(selected_request.strip())
    print("-" * 80)
    print()

    try:
        from backend.crew.orchestrator import run_travel_pipeline

        print("Starting travel planning pipeline...\n")

        async def cli_progress(step_key: str, label: str, status: str):
            icon = "..." if status == "running" else "[done]"
            print(f"  {icon} {label}")

        result = await run_travel_pipeline(
            user_request=selected_request,
            progress_callback=cli_progress,
        )

        print()
        print("=" * 80)
        print("  TRAVEL PLANNING COMPLETE!")
        print("=" * 80)
        print()
        print(result)
        print("=" * 80)

        # Save to file
        output_file = "travel_itinerary.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Travel Itinerary\n\n")
            f.write(f"## Original Request\n\n{selected_request}\n\n")
            f.write(f"## Complete Itinerary\n\n{result}\n")

        print(f"\nItinerary saved to: {output_file}")

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
