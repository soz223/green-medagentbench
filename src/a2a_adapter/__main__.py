"""
Main entry point for running A2A Green Server as a module.

Usage:
    python -m src.a2a_adapter --host 0.0.0.0 --port 8000
"""

if __name__ == "__main__":
    from .a2a_green_server import main
    main()
