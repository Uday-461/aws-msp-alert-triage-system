"""
MSP Backend Service
FastAPI + WebSocket server for MSP dashboard real-time updates
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from database import get_pool, close_pool
from routes import alerts, metrics, clients, audit, demo, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
websocket_connections = Counter('websocket_connections_total', 'Total WebSocket connections')
websocket_messages = Counter('websocket_messages_total', 'Total messages sent via WebSocket')
redis_messages = Counter('redis_messages_total', 'Total messages received from Redis')
request_duration = Histogram('request_duration_seconds', 'Request duration')

# Global state
class ConnectionManager:
    """Manages active WebSocket connections"""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.redis_client = None
        self.pubsub = None
        self.listener_task = None

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        websocket_connections.inc()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
                websocket_messages.inc()
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def start_redis_listener(self):
        """Start listening to Redis pub/sub channels"""
        try:
            # Connect to Redis
            self.redis_client = await aioredis.from_url(
                "redis://:hackathon_redis_pass@172.20.0.12:6379",
                encoding="utf-8",
                decode_responses=True
            )

            # Subscribe to alert channels
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(
                "superops:alerts:suppressed",
                "superops:alerts:escalated",
                "superops:alerts:review"
            )

            logger.info("Redis pub/sub listener started")

            # Listen for messages
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        redis_messages.inc()
                        channel = message['channel']
                        data = json.loads(message['data'])

                        # Broadcast to WebSocket clients
                        await self.broadcast({
                            'type': 'alert_update',
                            'channel': channel,
                            'data': data
                        })

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")

        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            # Retry connection after delay
            await asyncio.sleep(5)
            self.listener_task = asyncio.create_task(self.start_redis_listener())

    async def stop_redis_listener(self):
        """Stop Redis listener and cleanup"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("Redis pub/sub listener stopped")


# Initialize connection manager
manager = ConnectionManager()

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info("Starting MSP Backend service...")
    await get_pool()  # Initialize database connection pool
    manager.listener_task = asyncio.create_task(manager.start_redis_listener())
    yield
    # Shutdown
    logger.info("Shutting down MSP Backend service...")
    await manager.stop_redis_listener()
    await close_pool()  # Close database connection pool

# Create FastAPI app
app = FastAPI(
    title="MSP Backend API",
    description="Backend service for MSP dashboard with real-time WebSocket updates",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://192.168.1.7:5173"],  # MSP dashboard frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(alerts.router)
app.include_router(metrics.router)
app.include_router(clients.router)
app.include_router(audit.router)
app.include_router(demo.router)
app.include_router(health.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_healthy = manager.redis_client is not None

    return {
        "status": "healthy",
        "service": "msp-backend",
        "websocket_connections": len(manager.active_connections),
        "redis_connected": redis_healthy
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alert updates
    Clients connect here to receive live alert notifications
    """
    await manager.connect(websocket)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to MSP Backend WebSocket"
        })

        # Keep connection alive and handle client messages
        while True:
            # Receive messages from client (ping/pong, subscriptions, etc.)
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get('type')

                if message_type == 'ping':
                    await websocket.send_json({'type': 'pong'})
                elif message_type == 'subscribe':
                    # Future: handle subscription to specific alert types
                    await websocket.send_json({
                        'type': 'subscribed',
                        'message': 'Subscription acknowledged'
                    })
                else:
                    logger.warning(f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MSP Backend API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "websocket": "/ws",
            "api": "/api/*"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
