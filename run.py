"""
KontentPyper - Quick Start
Run with:  python run.py
"""

import uvicorn

if __name__ == "__main__":
    print("server running on http://localhost:8000")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
