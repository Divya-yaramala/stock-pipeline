# ADR 014 - WebSocket for Real-Time Streaming

## Status

Accepted

## Context

The batch pipeline runs once daily after market close. Stakeholders wanted live price updates during trading hours without resorting to HTTP polling, which wastes bandwidth and adds unnecessary server load at short intervals.

## Decision

Build a WebSocket server in `api/websocket_server.py` that pushes live price updates and alerts to connected clients, running on port 8002 alongside the REST (8000) and GraphQL (8001) APIs.

## Reasons

- **WebSocket eliminates constant HTTP polling**: A single persistent connection replaces hundreds of short-lived HTTP requests, reducing both client and server overhead.
- **Push-based updates reduce latency to < 1 second**: Once a price update is ready, it is pushed immediately to all connected clients without waiting for the next poll interval.
- **FastAPI has native WebSocket support**: FastAPI's `WebSocket` class and `WebSocketDisconnect` exception handle the full connection lifecycle without additional libraries beyond `websockets`.
- **Single connection handles continuous data stream**: One WebSocket connection streams prices for all five tickers, compared to five separate REST calls per polling interval.

## Consequences

- **Third port to manage (8002)**: Docker Compose, firewalls, and load balancers must expose and route a third port alongside 8000 and 8001.
- **Connection state management required**: The server must handle client disconnections, reconnections, and broadcast failures gracefully to avoid silent data loss.
- **Not suitable for one-time queries (use REST instead)**: WebSocket is designed for continuous streams; single point-in-time lookups are better served by REST or GraphQL.
