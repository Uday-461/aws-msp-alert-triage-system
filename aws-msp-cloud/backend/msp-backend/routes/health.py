"""
Health and system status API routes
GET /api/health/services - Get all service health status
GET /api/health/ml-models - Get ML model performance statistics
GET /api/health/database - Get database statistics
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional, Dict
import logging
import httpx
import asyncio
import socket

from database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])

# Response models
class ServiceHealth(BaseModel):
    name: str
    type: str  # core, infrastructure
    status: str  # healthy, degraded, unhealthy, unknown
    port: Optional[int]
    endpoint: Optional[str]
    response_time_ms: Optional[float]
    error: Optional[str]

class ServicesHealthResponse(BaseModel):
    services: List[ServiceHealth]
    total: int
    healthy: int
    degraded: int
    unhealthy: int
    checked_at: datetime

class MLModelStats(BaseModel):
    tier: int
    model_name: str
    total_processed: int
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[float]
    max_latency_ms: Optional[float]
    accuracy_pct: Optional[float]
    last_processed: Optional[datetime]

class MLModelsHealthResponse(BaseModel):
    models: List[MLModelStats]
    total_classifications: int
    avg_pipeline_latency_ms: Optional[float]
    checked_at: datetime

class TableStats(BaseModel):
    schema_name: str
    table_name: str
    row_count: int
    last_modified: Optional[datetime]

class DatabaseHealthResponse(BaseModel):
    schemas: Dict[str, int]  # schema_name -> total_rows
    tables: List[TableStats]
    total_records: int
    checked_at: datetime


# Service definitions with Docker network IPs
SERVICES = [
    {"name": "alert-generator", "type": "core", "host": "172.20.0.24", "port": 8003, "endpoint": "/health"},
    {"name": "ml-processor", "type": "core", "host": "172.20.0.2", "port": 8001, "endpoint": None},  # Faust - no HTTP endpoint
    {"name": "action-orchestrator", "type": "core", "host": "172.20.0.23", "port": 8002, "endpoint": None},  # Faust - no HTTP endpoint
    {"name": "msp-backend", "type": "core", "host": "172.20.0.30", "port": 8000, "endpoint": "/health"},
    {"name": "mock-superops-api", "type": "core", "host": "172.20.0.21", "port": 4000, "endpoint": "/graphql"},
    {"name": "postgres", "type": "infrastructure", "host": "172.20.0.11", "port": 5432, "endpoint": None},
    {"name": "redis", "type": "infrastructure", "host": "172.20.0.12", "port": 6379, "endpoint": None},
    {"name": "kafka", "type": "infrastructure", "host": "172.20.0.13", "port": 9092, "endpoint": None},
    {"name": "prometheus", "type": "infrastructure", "host": "172.20.0.60", "port": 9090, "endpoint": "/-/healthy"},
    {"name": "grafana", "type": "infrastructure", "host": "172.20.0.61", "port": 3001, "endpoint": None},  # Accessible via browser only
]


async def check_tcp_health(host: str, port: int, name: str, service_type: str) -> ServiceHealth:
    """
    Check TCP connectivity to service (for non-HTTP services like postgres, redis, kafka)

    Args:
        host: Service host IP
        port: Service port
        name: Service name
        service_type: Service type (core or infrastructure)

    Returns:
        ServiceHealth with status based on TCP connectivity
    """
    try:
        start_time = asyncio.get_event_loop().time()

        # Run blocking socket call in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)

        # socket.connect_ex returns 0 on success, error code otherwise
        result = await loop.run_in_executor(
            None,
            sock.connect_ex,
            (host, port)
        )

        end_time = asyncio.get_event_loop().time()
        response_time_ms = (end_time - start_time) * 1000

        sock.close()

        return ServiceHealth(
            name=name,
            type=service_type,
            status="healthy" if result == 0 else "unhealthy",
            port=port,
            endpoint=None,
            response_time_ms=round(response_time_ms, 2) if result == 0 else None,
            error=None if result == 0 else f"Port {port} unreachable (TCP connect failed)"
        )

    except socket.timeout:
        return ServiceHealth(
            name=name,
            type=service_type,
            status="unhealthy",
            port=port,
            endpoint=None,
            response_time_ms=None,
            error="TCP connection timeout"
        )
    except Exception as e:
        return ServiceHealth(
            name=name,
            type=service_type,
            status="unhealthy",
            port=port,
            endpoint=None,
            response_time_ms=None,
            error=f"TCP check failed: {str(e)}"
        )


async def check_service_health(service: dict) -> ServiceHealth:
    """Check health of a single service (HTTP or TCP)"""
    name = service["name"]
    host = service["host"]
    port = service["port"]
    endpoint = service["endpoint"]
    service_type = service["type"]

    # Services without HTTP endpoints - use TCP check
    if endpoint is None:
        return await check_tcp_health(host, port, name, service_type)

    # Check HTTP services using Docker network IPs
    url = f"http://{host}:{port}{endpoint}"

    try:
        start_time = asyncio.get_event_loop().time()

        async with httpx.AsyncClient(timeout=3.0) as client:
            if name == "mock-superops-api":
                # GraphQL endpoint needs POST
                response = await client.post(url, json={"query": "{__schema{types{name}}}"})
            else:
                response = await client.get(url)

        end_time = asyncio.get_event_loop().time()
        response_time_ms = (end_time - start_time) * 1000

        # Determine status based on response
        if response.status_code == 200:
            status = "healthy"
        elif 200 < response.status_code < 300:
            status = "healthy"
        elif response.status_code < 500:
            status = "degraded"
        else:
            status = "unhealthy"

        return ServiceHealth(
            name=name,
            type=service["type"],
            status=status,
            port=port,
            endpoint=endpoint,
            response_time_ms=round(response_time_ms, 2),
            error=None
        )

    except httpx.TimeoutException:
        return ServiceHealth(
            name=name,
            type=service["type"],
            status="unhealthy",
            port=port,
            endpoint=endpoint,
            response_time_ms=None,
            error="Timeout"
        )
    except httpx.ConnectError:
        return ServiceHealth(
            name=name,
            type=service["type"],
            status="unhealthy",
            port=port,
            endpoint=endpoint,
            response_time_ms=None,
            error="Connection refused"
        )
    except Exception as e:
        return ServiceHealth(
            name=name,
            type=service["type"],
            status="unhealthy",
            port=port,
            endpoint=endpoint,
            response_time_ms=None,
            error=str(e)
        )


@router.get("/services", response_model=ServicesHealthResponse)
async def get_services_health():
    """
    Check health status of all services

    Returns:
    - List of all services with their health status
    - Response time for HTTP-accessible services
    - Count of healthy/degraded/unhealthy services
    """
    try:
        # Check all services concurrently
        tasks = [check_service_health(service) for service in SERVICES]
        services = await asyncio.gather(*tasks)

        # Count statuses
        healthy = sum(1 for s in services if s.status == "healthy")
        degraded = sum(1 for s in services if s.status == "degraded")
        unhealthy = sum(1 for s in services if s.status == "unhealthy")

        return ServicesHealthResponse(
            services=services,
            total=len(services),
            healthy=healthy,
            degraded=degraded,
            unhealthy=unhealthy,
            checked_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Error checking services health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check services health: {str(e)}")


@router.get("/ml-models", response_model=MLModelsHealthResponse)
async def get_ml_models_health():
    """
    Get ML model performance statistics

    Returns:
    - Statistics for each tier (Sentence-BERT, DistilBERT, RLM)
    - Processing counts, latencies, accuracy
    - Overall pipeline performance
    """
    try:
        pool = await get_pool()

        # Query ML classifications for model statistics
        query = """
            SELECT
                COUNT(*) as total_classifications,
                AVG(total_latency_ms) as avg_pipeline_latency,
                AVG(tier1_latency_ms) as avg_tier1_latency,
                AVG(tier2_latency_ms) as avg_tier2_latency,
                AVG(tier3_latency_ms) as avg_tier3_latency,
                MIN(tier1_latency_ms) as min_tier1_latency,
                MIN(tier2_latency_ms) as min_tier2_latency,
                MIN(tier3_latency_ms) as min_tier3_latency,
                MAX(tier1_latency_ms) as max_tier1_latency,
                MAX(tier2_latency_ms) as max_tier2_latency,
                MAX(tier3_latency_ms) as max_tier3_latency,
                MAX(created_at) as last_processed,
                -- Classification accuracy (% of each type)
                COUNT(*) FILTER (WHERE classification = 'DUPLICATE') * 100.0 / NULLIF(COUNT(*), 0) as duplicate_pct,
                COUNT(*) FILTER (WHERE classification = 'NOISE') * 100.0 / NULLIF(COUNT(*), 0) as noise_pct,
                COUNT(*) FILTER (WHERE classification = 'ACTIONABLE') * 100.0 / NULLIF(COUNT(*), 0) as actionable_pct,
                COUNT(*) FILTER (WHERE classification = 'CRITICAL') * 100.0 / NULLIF(COUNT(*), 0) as critical_pct
            FROM superops.ml_classifications
        """

        stats = await pool.fetchrow(query)

        total_classifications = stats['total_classifications'] or 0
        avg_pipeline_latency = float(stats['avg_pipeline_latency']) if stats['avg_pipeline_latency'] else None

        # Build model stats
        models = [
            MLModelStats(
                tier=1,
                model_name="Sentence-BERT (Duplicate Detection)",
                total_processed=total_classifications,
                avg_latency_ms=round(float(stats['avg_tier1_latency']), 2) if stats['avg_tier1_latency'] else None,
                min_latency_ms=round(float(stats['min_tier1_latency']), 2) if stats['min_tier1_latency'] else None,
                max_latency_ms=round(float(stats['max_tier1_latency']), 2) if stats['max_tier1_latency'] else None,
                accuracy_pct=round(float(stats['duplicate_pct']), 2) if stats['duplicate_pct'] else None,
                last_processed=stats['last_processed']
            ),
            MLModelStats(
                tier=2,
                model_name="DistilBERT (Classification)",
                total_processed=total_classifications,
                avg_latency_ms=round(float(stats['avg_tier2_latency']), 2) if stats['avg_tier2_latency'] else None,
                min_latency_ms=round(float(stats['min_tier2_latency']), 2) if stats['min_tier2_latency'] else None,
                max_latency_ms=round(float(stats['max_tier2_latency']), 2) if stats['max_tier2_latency'] else None,
                accuracy_pct=round(float(stats['noise_pct']) + float(stats['actionable_pct']) + float(stats['critical_pct']), 2) if stats['noise_pct'] else None,
                last_processed=stats['last_processed']
            ),
            MLModelStats(
                tier=3,
                model_name="RLM/T5 (Contextual Scoring)",
                total_processed=total_classifications,
                avg_latency_ms=round(float(stats['avg_tier3_latency']), 2) if stats['avg_tier3_latency'] else None,
                min_latency_ms=round(float(stats['min_tier3_latency']), 2) if stats['min_tier3_latency'] else None,
                max_latency_ms=round(float(stats['max_tier3_latency']), 2) if stats['max_tier3_latency'] else None,
                accuracy_pct=None,  # RLM doesn't have classification accuracy
                last_processed=stats['last_processed']
            )
        ]

        return MLModelsHealthResponse(
            models=models,
            total_classifications=total_classifications,
            avg_pipeline_latency_ms=round(avg_pipeline_latency, 2) if avg_pipeline_latency else None,
            checked_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Error getting ML models health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ML models health: {str(e)}")


@router.get("/database", response_model=DatabaseHealthResponse)
async def get_database_health():
    """
    Get database statistics

    Returns:
    - Row counts per schema
    - Row counts per table
    - Last modified timestamps
    - Total records
    """
    try:
        pool = await get_pool()

        # Get table list and row counts
        # Query each schema's tables individually
        tables = []
        schema_totals = {}
        total_records = 0

        schemas = ['superops', 'customer', 'audit', 'knowledge_base']

        for schema in schemas:
            # Get tables in this schema
            table_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = $1 AND table_type = 'BASE TABLE'
            """
            schema_tables = await pool.fetch(table_query, schema)

            schema_total = 0
            for table_row in schema_tables:
                table_name = table_row['table_name']

                # Get row count for this table
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {schema}.{table_name}"
                    count_result = await pool.fetchrow(count_query)
                    row_count = count_result['count'] or 0
                except Exception as e:
                    logger.warning(f"Could not count rows in {schema}.{table_name}: {e}")
                    row_count = 0

                tables.append(TableStats(
                    schema_name=schema,
                    table_name=table_name,
                    row_count=row_count,
                    last_modified=None  # Not easily available without additional queries
                ))

                schema_total += row_count
                total_records += row_count

            schema_totals[schema] = schema_total

        return DatabaseHealthResponse(
            schemas=schema_totals,
            tables=tables,
            total_records=total_records,
            checked_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database health: {str(e)}")
