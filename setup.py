"""
Setup script to initialize the project.
Creates necessary directories and checks dependencies.
"""

import os
import sys


def create_directory_structure():
    """Create all necessary directories."""
    directories = [
        "data",
        "data/travel_knowledge",
        "data/chroma_db",
    ]

    print("Creating directory structure...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  {directory}/")

    print("Directory structure created\n")


def check_env_file():
    """Check if .env file exists."""
    if not os.path.exists(".env"):
        print(".env file not found!")
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f:
                content = f.read()
            with open(".env", "w") as f:
                f.write(content)
            print(".env file created from template")
            print("Please edit .env and add your API keys\n")
        else:
            print("Please create a .env file — see .env.example\n")
    else:
        print(".env file exists\n")


def check_dependencies():
    """Check if required packages are installed."""
    print("Checking dependencies...")

    required_packages = [
        ("crewai", "crewai"),
        ("httpx", "httpx"),
        ("fastapi", "fastapi"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic"),
    ]

    missing = []
    for import_name, pip_name in required_packages:
        try:
            __import__(import_name)
            print(f"  OK: {pip_name}")
        except ImportError:
            print(f"  MISSING: {pip_name}")
            missing.append(pip_name)

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt\n")
        return False

    print("All dependencies installed\n")
    return True


def main():
    print("=" * 60)
    print("  Multi-Agent AI Travel Planner v2.0 — Setup")
    print("=" * 60)
    print()

    create_directory_structure()
    check_env_file()
    deps_ok = check_dependencies()

    print("=" * 60)
    if deps_ok:
        print("Setup complete!")
        print()
        print("Next steps:")
        print("1. Add your API keys to .env (see .env.example)")
        print("2. Run: python main.py")
    else:
        print("Setup incomplete. Install missing dependencies:")
        print("  pip install -r requirements.txt")
    print("=" * 60)


if __name__ == "__main__":
    main()
