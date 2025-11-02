"""
RAG (Retrieval-Augmented Generation) Service
Semantic search over knowledge base using OpenAI embeddings + pgvector
"""
import os
import logging
import httpx
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class RAGService:
    """
    Handles semantic search over knowledge base articles.
    Uses OpenAI text-embedding-3-small (1536 dimensions) + pgvector cosine similarity.
    """

    def __init__(self, db_pool):
        self.db = db_pool
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536
        self.chunk_size = 500  # tokens per chunk
        self.chunk_overlap = 50  # token overlap between chunks

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        min_similarity: float = 0.7
    ) -> List[Dict]:
        """
        Semantic search for relevant articles.

        Args:
            query: Search query text
            top_k: Number of results to return
            category: Optional category filter
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of articles with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embed_text(query)

            # Search similar chunks
            async with self.db.acquire() as conn:
                # Use pgvector semantic search
                query_sql = """
                    SELECT
                        e.article_id,
                        a.title,
                        a.content,
                        a.category,
                        a.article_id as article_code,
                        e.chunk_text,
                        e.chunk_index,
                        1 - (e.embedding <=> $1::vector) AS similarity
                    FROM knowledge_base.embeddings e
                    JOIN knowledge_base.articles a ON e.article_id = a.id
                    WHERE e.embedding IS NOT NULL
                """
                params = [str(query_embedding)]

                if category:
                    query_sql += " AND a.category = $" + str(len(params) + 1)
                    params.append(category)

                query_sql += """
                    ORDER BY e.embedding <=> $1::vector
                    LIMIT $""" + str(len(params) + 1)
                params.append(top_k * 3)  # Get more chunks to aggregate

                rows = await conn.fetch(query_sql, *params)

            # Group by article and select best chunk
            articles_dict = {}
            for row in rows:
                article_id = str(row['article_id'])
                similarity = float(row['similarity'])

                if similarity < min_similarity:
                    continue

                if article_id not in articles_dict:
                    articles_dict[article_id] = {
                        'id': article_id,
                        'article_code': row['article_code'],
                        'title': row['title'],
                        'content': row['content'],
                        'category': row['category'],
                        'similarity': similarity,
                        'matching_chunk': row['chunk_text'],
                        'chunk_index': row['chunk_index']
                    }
                else:
                    # Keep highest similarity chunk
                    if similarity > articles_dict[article_id]['similarity']:
                        articles_dict[article_id]['similarity'] = similarity
                        articles_dict[article_id]['matching_chunk'] = row['chunk_text']
                        articles_dict[article_id]['chunk_index'] = row['chunk_index']

            # Sort by similarity and return top_k
            results = sorted(
                articles_dict.values(),
                key=lambda x: x['similarity'],
                reverse=True
            )[:top_k]

            # Log search
            await self._log_search(query, len(results), results[0]['id'] if results else None)

            return results

        except Exception as e:
            logger.error(f"Error in RAG search: {e}")
            raise

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI API"""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.embedding_model,
                        "input": text
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['data'][0]['embedding']

        except httpx.HTTPError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def index_article(
        self,
        article_id: str,
        title: str,
        content: str
    ) -> int:
        """
        Index article by generating embeddings for chunks.

        Args:
            article_id: Article UUID
            title: Article title
            content: Article content

        Returns:
            Number of chunks created
        """
        # Combine title and content
        full_text = f"{title}\n\n{content}"

        # Split into chunks (simple by paragraphs)
        chunks = self._split_into_chunks(full_text)

        # Generate embeddings for all chunks
        chunk_count = 0
        for idx, chunk in enumerate(chunks):
            try:
                embedding = await self.embed_text(chunk)

                async with self.db.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO knowledge_base.embeddings
                        (article_id, chunk_index, chunk_text, embedding, model_version)
                        VALUES ($1, $2, $3, $4::vector, $5)
                        ON CONFLICT (article_id, chunk_index)
                        DO UPDATE SET
                            chunk_text = EXCLUDED.chunk_text,
                            embedding = EXCLUDED.embedding,
                            model_version = EXCLUDED.model_version
                    """,
                    article_id, idx, chunk, str(embedding), self.embedding_model)

                chunk_count += 1
                logger.info(f"Indexed chunk {idx} for article {article_id}")

            except Exception as e:
                logger.error(f"Error indexing chunk {idx} for article {article_id}: {e}")

        return chunk_count

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks of approximately chunk_size tokens.
        Simple implementation: split by paragraphs and combine to ~500 words.
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_words = len(para.split())

            if current_length + para_words > self.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_words
            else:
                current_chunk.append(para)
                current_length += para_words

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    async def _log_search(
        self,
        query: str,
        results_count: int,
        top_result_id: Optional[str]
    ):
        """Log search for analytics"""
        try:
            async with self.db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO knowledge_base.search_logs
                    (query, results_count, top_result_id, searched_at)
                    VALUES ($1, $2, $3, NOW())
                """, query, results_count, top_result_id)
        except Exception as e:
            logger.error(f"Error logging search: {e}")

    async def get_article(self, article_id: str) -> Optional[Dict]:
        """Get full article by ID"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM knowledge_base.articles WHERE id = $1
            """, article_id)

            if not row:
                return None

            # Increment view count
            await conn.execute("""
                UPDATE knowledge_base.articles
                SET view_count = view_count + 1
                WHERE id = $1
            """, article_id)

        article = dict(row)
        article['id'] = str(article['id'])
        if article.get('created_at'):
            article['created_at'] = article['created_at'].isoformat()
        if article.get('updated_at'):
            article['updated_at'] = article['updated_at'].isoformat()
        return article

    async def mark_helpful(self, article_id: str):
        """Mark article as helpful"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE knowledge_base.articles
                SET helpful_count = helpful_count + 1
                WHERE id = $1
            """, article_id)

    async def get_categories(self) -> List[str]:
        """Get all article categories"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT category
                FROM knowledge_base.articles
                WHERE category IS NOT NULL
                ORDER BY category
            """)

        return [row['category'] for row in rows]

    async def get_statistics(self) -> Dict:
        """Get knowledge base statistics"""
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT a.id) as total_articles,
                    COUNT(e.id) as total_embeddings,
                    SUM(a.view_count) as total_views,
                    SUM(a.helpful_count) as total_helpful
                FROM knowledge_base.articles a
                LEFT JOIN knowledge_base.embeddings e ON a.id = e.article_id
            """)

            # Get by category
            by_category = await conn.fetch("""
                SELECT category, COUNT(*) as count
                FROM knowledge_base.articles
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)

        return {
            'total_articles': int(stats['total_articles']),
            'total_embeddings': int(stats['total_embeddings']),
            'total_views': int(stats['total_views'] or 0),
            'total_helpful': int(stats['total_helpful'] or 0),
            'by_category': {row['category']: int(row['count']) for row in by_category}
        }
