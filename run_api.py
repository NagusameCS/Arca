#!/usr/bin/env python3
"""
Run the Arca Bank REST API server for Java mod integration
"""

import uvicorn

from src.integration.java_interface import create_fastapi_app


def main():
    """Run the API server"""
    app = create_fastapi_app()

    print("=" * 50)
    print("  Arca Bank REST API Server")
    print("  For Java Mod Integration")
    print("=" * 50)
    print()
    print("Endpoints available:")
    print("  GET  /api/balance/{uuid}")
    print("  GET  /api/market")
    print("  GET  /api/treasury")
    print("  GET  /api/is_banker/{uuid}")
    print("  POST /api/register")
    print("  POST /api/transfer")
    print("  POST /api/trade/report")
    print("  GET  /api/trade/price/{item}")
    print("  GET  /api/trade/trending")
    print("  GET  /api/trade/history/{uuid}")
    print("  GET  /api/trade/stats/{uuid}")
    print()
    print("Starting server on http://0.0.0.0:8080")
    print("Press Ctrl+C to stop")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
