"""
Knowledge Base API Routes
Provides semantic search over troubleshooting documentation using RAG
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import get_pool
from services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/knowledge-base",
    tags=["knowledge-base"]
)

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None
    min_similarity: float = 0.7

class SearchResult(BaseModel):
    id: str
    article_code: str
    title: str
    content: str
    category: str
    similarity: float
    matching_chunk: str
    chunk_index: int

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    count: int

class ArticleResponse(BaseModel):
    id: str
    article_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    author: str
    created_at: str
    updated_at: str
    view_count: int
    helpful_count: int

class CreateArticleRequest(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    author: str = "System"

class StatsResponse(BaseModel):
    total_articles: int
    total_embeddings: int
    total_views: int
    total_helpful: int
    by_category: dict


@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(request: SearchRequest):
    """
    Semantic search over knowledge base articles.

    Uses OpenAI embeddings + pgvector for similarity search.
    Returns top_k most relevant articles with similarity scores.
    """
    try:
        pool = await get_pool()
        rag = RAGService(pool)

        results = await rag.search(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            min_similarity=request.min_similarity
        )

        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str):
    """
    Get full article by ID.

    Increments view count automatically.
    """
    try:
        pool = await get_pool()
        rag = RAGService(pool)

        article = await rag.get_article(article_id)
        if not article:
            raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

        return article

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/{article_id}/helpful")
async def mark_article_helpful(article_id: str):
    """
    Mark article as helpful.

    Increments helpful_count for the article.
    """
    try:
        pool = await get_pool()
        rag = RAGService(pool)

        await rag.mark_helpful(article_id)

        return {
            "status": "success",
            "article_id": article_id,
            "message": "Article marked as helpful"
        }

    except Exception as e:
        logger.error(f"Error marking article {article_id} as helpful: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories():
    """
    Get all article categories.

    Returns unique categories from knowledge base.
    """
    try:
        pool = await get_pool()
        rag = RAGService(pool)

        categories = await rag.get_categories()

        return {
            "categories": categories,
            "count": len(categories)
        }

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_statistics():
    """
    Get knowledge base statistics.

    Returns counts of articles, embeddings, views, helpful marks, etc.
    """
    try:
        pool = await get_pool()
        rag = RAGService(pool)

        stats = await rag.get_statistics()

        return stats

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles", response_model=ArticleResponse)
async def create_article(request: CreateArticleRequest):
    """
    Create new knowledge base article.

    Automatically generates embeddings for semantic search.
    This is an async operation - embeddings are generated in background.
    """
    try:
        pool = await get_pool()
        rag = RAGService(pool)

        # Insert article
        async with pool.acquire() as conn:
            article_id = await conn.fetchval("""
                INSERT INTO knowledge_base.articles
                (title, content, category, tags, author)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """,
            request.title,
            request.content,
            request.category,
            request.tags or [],
            request.author)

        # Generate embeddings (async)
        chunk_count = await rag.index_article(
            article_id=str(article_id),
            title=request.title,
            content=request.content
        )

        logger.info(f"Created article {article_id} with {chunk_count} chunks")

        # Get created article
        article = await rag.get_article(str(article_id))

        return article

    except Exception as e:
        logger.error(f"Error creating article: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/articles/{article_id}")
async def delete_article(article_id: str):
    """
    Delete article and its embeddings.

    Cascade deletes embeddings automatically.
    """
    try:
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM knowledge_base.articles
                WHERE id = $1
            """, article_id)

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

        return {
            "status": "success",
            "article_id": article_id,
            "message": "Article deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
