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


# Service definitions
SERVICES = [
    {"name": "alert-generator", "type": "core", "port": 8003, "endpoint": "/health"},
    {"name": "ml-processor", "type": "core", "port": 8001, "endpoint": "/health"},
    {"name": "action-orchestrator", "type": "core", "port": 8002, "endpoint": "/health"},
    {"name": "msp-backend", "type": "core", "port": 8000, "endpoint": "/health"},
    {"name": "mock-superops-api", "type": "core", "port": 4000, "endpoint": "/graphql"},
    {"name": "postgres", "type": "infrastructure", "port": 5432, "endpoint": None},
    {"name": "redis", "type": "infrastructure", "port": 6379, "endpoint": None},
    {"name": "kafka", "type": "infrastructure", "port": 9092, "endpoint": None},
    {"name": "prometheus", "type": "infrastructure", "port": 9090, "endpoint": "/-/healthy"},
    {"name": "grafana", "type": "infrastructure", "port": 3001, "endpoint": "/api/health"},
]


async def check_service_health(service: dict) -> ServiceHealth:
    """Check health of a single service"""
    name = service["name"]
    port = service["port"]
    endpoint = service["endpoint"]

    # Infrastructure services without HTTP endpoints
    if endpoint is None:
        return ServiceHealth(
            name=name,
            type=service["type"],
            status="unknown",
            port=port,
            endpoint=None,
            response_time_ms=None,
            error="No HTTP endpoint available"
        )

    # Check HTTP services
    url = f"http://localhost:{port}{endpoint}"

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

        # Query table statistics from pg_stat_user_tables
        # Note: This view shows statistics for user tables only
        query = """
            SELECT
                schemaname as schema_name,
                tablename as table_name,
                n_live_tup as row_count,
                last_vacuum as last_modified
            FROM pg_stat_user_tables
            WHERE schemaname IN ('superops', 'customer', 'audit', 'knowledge_base')
            ORDER BY schemaname, tablename
        """

        rows = await pool.fetch(query)

        # Build table stats
        tables = []
        schema_totals = {}
        total_records = 0

        for row in rows:
            schema_name = row['schema_name']
            table_name = row['table_name']
            row_count = row['row_count'] or 0

            tables.append(TableStats(
                schema_name=schema_name,
                table_name=table_name,
                row_count=row_count,
                last_modified=row['last_modified']
            ))

            schema_totals[schema_name] = schema_totals.get(schema_name, 0) + row_count
            total_records += row_count

        return DatabaseHealthResponse(
            schemas=schema_totals,
            tables=tables,
            total_records=total_records,
            checked_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Error getting database health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database health: {str(e)}")
