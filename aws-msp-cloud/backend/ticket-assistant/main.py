import os
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional
import asyncpg
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

# FastAPI app
app = FastAPI(title="Ticket Assistant API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database config
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '172.20.0.11'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'superops'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'hackathon_db_pass'),
}

# SuperOps API
SUPEROPS_API_URL = os.getenv('SUPEROPS_API_URL', 'http://172.20.0.14:4000/graphql')

# Database pool
db_pool = None

# Prometheus metrics
request_counter = Counter('ticket_assistant_requests_total', 'Total requests', ['endpoint'])
request_duration = Histogram('ticket_assistant_request_duration_seconds', 'Request duration', ['endpoint'])

# Models
class TicketCreate(BaseModel):
    customer_id: str
    subject: str
    description: str
    priority: str = 'medium'
    client_id: Optional[str] = None
    conversation_id: Optional[str] = None

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None

# Startup/shutdown
@app.on_event('startup')
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)

@app.on_event('shutdown')
async def shutdown():
    if db_pool:
        await db_pool.close()

# Routes
@app.get('/')
async def root():
    return {
        'service': 'ticket-assistant',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'tickets': '/tickets',
            'create': 'POST /tickets',
            'sync': 'POST /sync/{ticket_id}'
        }
    }

@app.get('/health')
async def health():
    request_counter.labels(endpoint='health').inc()
    db_status = 'connected' if db_pool else 'disconnected'

    # Check SuperOps API
    superops_status = 'disconnected'
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(SUPEROPS_API_URL, json={'query': '{__schema{types{name}}}'})
            if resp.status_code == 200:
                superops_status = 'connected'
    except:
        pass

    return {
        'status': 'healthy',
        'service': 'ticket-assistant',
        'database': db_status,
        'superops_api': superops_status
    }

@app.get('/metrics')
async def metrics():
    return generate_latest(REGISTRY)

@app.post('/tickets')
async def create_ticket(ticket: TicketCreate):
    request_counter.labels(endpoint='create_ticket').inc()

    # Generate ticket number
    async with db_pool.acquire() as conn:
        max_num = await conn.fetchval('SELECT MAX(CAST(SUBSTRING(ticket_number FROM 5) AS INTEGER)) FROM customer.tickets WHERE ticket_number LIKE \'TKT-%\'')
        ticket_num = max_num + 1 if max_num else 1
        ticket_number = f'TKT-{ticket_num:06d}'

        # Insert ticket
        ticket_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO customer.tickets
            (id, ticket_number, customer_id, client_id, conversation_id, subject, description, priority, status, created_via, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''', ticket_id, ticket_number, ticket.customer_id, ticket.client_id, ticket.conversation_id,
            ticket.subject, ticket.description, ticket.priority, 'open', 'api', datetime.now(timezone.utc))

        # Fetch created ticket
        row = await conn.fetchrow('SELECT * FROM customer.tickets WHERE id = $1', ticket_id)

    return {
        'id': str(row['id']),
        'ticket_number': row['ticket_number'],
        'customer_id': row['customer_id'],
        'subject': row['subject'],
        'description': row['description'],
        'status': row['status'],
        'priority': row['priority'],
        'created_at': row['created_at'].isoformat()
    }

@app.get('/tickets')
async def list_tickets(customer_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    request_counter.labels(endpoint='list_tickets').inc()

    query = 'SELECT * FROM customer.tickets WHERE 1=1'
    params = []

    if customer_id:
        params.append(customer_id)
        query += f' AND customer_id = ${len(params)}'

    if status:
        params.append(status)
        query += f' AND status = ${len(params)}'

    query += ' ORDER BY created_at DESC LIMIT $' + str(len(params) + 1)
    params.append(limit)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return {
        'tickets': [
            {
                'id': str(r['id']),
                'ticket_number': r['ticket_number'],
                'customer_id': r['customer_id'],
                'subject': r['subject'],
                'status': r['status'],
                'priority': r['priority'],
                'created_at': r['created_at'].isoformat()
            }
            for r in rows
        ],
        'count': len(rows)
    }

@app.get('/tickets/{ticket_id}')
async def get_ticket(ticket_id: str):
    request_counter.labels(endpoint='get_ticket').inc()

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM customer.tickets WHERE id = $1', ticket_id)

    if not row:
        raise HTTPException(status_code=404, detail='Ticket not found')

    return {
        'id': str(row['id']),
        'ticket_number': row['ticket_number'],
        'customer_id': row['customer_id'],
        'subject': row['subject'],
        'description': row['description'],
        'status': row['status'],
        'priority': row['priority'],
        'created_at': row['created_at'].isoformat(),
        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
    }

@app.put('/tickets/{ticket_id}')
async def update_ticket(ticket_id: str, update: TicketUpdate):
    request_counter.labels(endpoint='update_ticket').inc()

    updates = []
    params = []

    if update.status:
        params.append(update.status)
        updates.append(f'status = ${len(params)}')

    if update.priority:
        params.append(update.priority)
        updates.append(f'priority = ${len(params)}')

    if update.description:
        params.append(update.description)
        updates.append(f'description = ${len(params)}')

    if not updates:
        raise HTTPException(status_code=400, detail='No updates provided')

    params.append(datetime.now(timezone.utc))
    updates.append(f'updated_at = ${len(params)}')

    params.append(ticket_id)

    query = f'UPDATE customer.tickets SET {", ".join(updates)} WHERE id = ${len(params)} RETURNING *'

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)

    if not row:
        raise HTTPException(status_code=404, detail='Ticket not found')

    return {
        'id': str(row['id']),
        'ticket_number': row['ticket_number'],
        'status': row['status'],
        'priority': row['priority'],
        'updated_at': row['updated_at'].isoformat()
    }

@app.post('/sync/{ticket_id}')
async def sync_ticket(ticket_id: str):
    request_counter.labels(endpoint='sync_ticket').inc()

    # Get ticket
    async with db_pool.acquire() as conn:
        ticket = await conn.fetchrow('SELECT * FROM customer.tickets WHERE id = $1', ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket not found')

    # Sync to SuperOps
    mutation = '''
        mutation CreateTicket($input: CreateTicketInput!) {
          createTicket(input: $input) {
            id
            subject
            status
          }
        }
    '''

    variables = {
        'input': {
            'customerId': ticket['customer_id'],
            'clientId': str(ticket['client_id']) if ticket['client_id'] else ticket['customer_id'],
            'subject': ticket['subject'],
            'description': ticket['description'],
            'priority': ticket['priority'].upper() if ticket['priority'] else 'MEDIUM'
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(SUPEROPS_API_URL, json={'query': mutation, 'variables': variables})
            result = resp.json()

            if 'errors' in result:
                raise HTTPException(status_code=500, detail=f"SuperOps sync failed: {result['errors']}")

            superops_id = result['data']['createTicket']['id']

            # Update ticket with SuperOps ID
            async with db_pool.acquire() as conn:
                await conn.execute(
                    'UPDATE customer.tickets SET superops_ticket_id = $1, updated_at = $2 WHERE id = $3',
                    superops_id, datetime.now(timezone.utc), ticket_id
                )

            return {
                'success': True,
                'ticket_id': ticket_id,
                'superops_id': superops_id,
                'message': 'Ticket synced successfully'
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f'SuperOps API error: {str(e)}')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
