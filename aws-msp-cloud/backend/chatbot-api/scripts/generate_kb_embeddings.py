#!/usr/bin/env python3
"""
Generate embeddings for knowledge base articles and populate PostgreSQL embeddings table
Uses Sentence-BERT (all-MiniLM-L6-v2) for 384-dimensional embeddings
"""
import os
import sys
import logging
import psycopg2
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Database connection
    pg_host = os.getenv('POSTGRES_HOST', '172.20.0.11')
    pg_port = int(os.getenv('POSTGRES_PORT', '5432'))
    pg_user = os.getenv('POSTGRES_USER', 'postgres')
    pg_password = os.getenv('POSTGRES_PASSWORD', 'hackathon_db_pass')
    pg_database = os.getenv('POSTGRES_DB', 'superops')

    logger.info(f"Connecting to PostgreSQL at {pg_host}:{pg_port}...")

    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            dbname=pg_database,
            user=pg_user,
            password=pg_password
        )
        logger.info("✓ Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"✗ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # Check current state
    cursor.execute("SELECT COUNT(*) FROM knowledge_base.articles")
    article_count = cursor.fetchone()[0]
    logger.info(f"Found {article_count} articles in database")

    cursor.execute("SELECT COUNT(*) FROM knowledge_base.embeddings")
    embedding_count = cursor.fetchone()[0]
    logger.info(f"Current embeddings count: {embedding_count}")

    if article_count == 0:
        logger.warning("No articles found. Please seed articles first.")
        conn.close()
        sys.exit(0)

    # Load Sentence-BERT model
    logger.info("Loading Sentence-BERT model (all-MiniLM-L6-v2)...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✓ Model loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to load model: {e}")
        logger.info("Installing sentence-transformers...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✓ Model loaded successfully after installation")

    # Fetch all articles
    logger.info("Fetching articles from database...")
    cursor.execute("""
        SELECT id, article_id, title, content
        FROM knowledge_base.articles
        ORDER BY created_at ASC
    """)
    articles = cursor.fetchall()
    logger.info(f"Fetched {len(articles)} articles")

    # Clear existing embeddings if any
    if embedding_count > 0:
        logger.info(f"Deleting {embedding_count} existing embeddings...")
        cursor.execute("DELETE FROM knowledge_base.embeddings")
        conn.commit()
        logger.info("✓ Cleared existing embeddings")

    # Generate embeddings
    logger.info("Generating embeddings...")
    logger.info("=" * 60)

    success_count = 0
    error_count = 0

    for idx, (id, article_id, title, content) in enumerate(articles, 1):
        try:
            # Combine title and content for better embedding
            full_text = f"{title}\n\n{content}"

            # Generate embedding (384 dimensions)
            embedding = model.encode(full_text)

            # Convert to list for PostgreSQL array
            embedding_list = embedding.tolist()

            # Truncate chunk_text to first 1000 chars
            chunk_text = full_text[:1000]

            # Insert into embeddings table
            cursor.execute("""
                INSERT INTO knowledge_base.embeddings
                (article_id, chunk_index, chunk_text, embedding_vector, model_version)
                VALUES (%s, %s, %s, %s, %s)
            """, (id, 0, chunk_text, embedding_list, 'all-MiniLM-L6-v2'))

            logger.info(f"[{idx}/{len(articles)}] ✓ {title}")
            success_count += 1

            # Commit every 10 articles
            if idx % 10 == 0:
                conn.commit()
                logger.info(f"  → Committed batch (processed {idx}/{len(articles)})")

        except Exception as e:
            logger.error(f"[{idx}/{len(articles)}] ✗ Failed for '{title}': {e}")
            error_count += 1

    # Final commit
    conn.commit()
    logger.info("=" * 60)
    logger.info(f"✓ Generation complete!")
    logger.info(f"  Success: {success_count}/{len(articles)}")
    logger.info(f"  Errors:  {error_count}/{len(articles)}")

    # Verify final count
    cursor.execute("SELECT COUNT(*) FROM knowledge_base.embeddings")
    final_count = cursor.fetchone()[0]
    logger.info(f"  Final embeddings count: {final_count}")

    # Show sample
    logger.info("\nSample embeddings:")
    cursor.execute("""
        SELECT
            e.id,
            a.title,
            e.model_version,
            array_length(e.embedding_vector, 1) as vector_dims,
            e.created_at
        FROM knowledge_base.embeddings e
        JOIN knowledge_base.articles a ON e.article_id = a.id
        LIMIT 5
    """)

    for row in cursor.fetchall():
        logger.info(f"  - {row[1][:50]}... | dims: {row[3]} | model: {row[2]}")

    cursor.close()
    conn.close()
    logger.info("\n🎉 All done!")

if __name__ == "__main__":
    main()
