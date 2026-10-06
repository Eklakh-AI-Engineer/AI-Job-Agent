"""
backend/app/services/semantic_search_service.py

Service layer for semantic job search using pgvector.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.embeddings import get_embedding_provider
from app.core.metrics import semantic_search_total, semantic_search_duration_seconds
from app.models.job import JobPosting
from app.schemas.job import JobPostingRead
from app.services.embedding_service import generate_search_embedding

logger = logging.getLogger(__name__)


# Default similarity threshold (cosine similarity)
DEFAULT_SIMILARITY_THRESHOLD = 0.75
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


async def semantic_search_jobs(
    db: AsyncSession,
    query: str,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    filters: Optional[dict] = None,
) -> Tuple[List[JobPosting], int]:
    """
    Perform semantic search on job postings using pgvector.
    
    Args:
        db: Database session
        query: Search query text
        limit: Maximum number of results
        offset: Number of results to skip
        similarity_threshold: Minimum cosine similarity (0-1)
        filters: Optional dict with keys: company, source, work_mode, location
        
    Returns:
        Tuple of (jobs, total_count)
    """
    start_time = __import__('time').time()
    
    # Generate query embedding
    query_embedding = await generate_search_embedding(query)
    
    # Build similarity search query
    # Using cosine similarity: 1 - (embedding <=> query_embedding)
    # cosine_similarity = 1 - cosine_distance
    # cosine_distance = embedding <=> query_embedding (pgvector operator)
    
    similarity_expr = 1 - JobPosting.embedding.cosine_distance(query_embedding)
    
    stmt = (
        select(JobPosting, similarity_expr.label("similarity"))
        .where(
            JobPosting.embedding.is_not(None),
            similarity_expr >= similarity_threshold,
        )
        .order_by(similarity_expr.desc())
        .limit(min(limit, MAX_LIMIT))
        .offset(max(offset, 0))
    )
    
    # Apply filters
    if filters:
        if filters.get("company"):
            stmt = stmt.where(JobPosting.company.ilike(f"%{filters['company']}%"))
        if filters.get("source"):
            stmt = stmt.where(JobPosting.source == filters["source"])
        if filters.get("work_mode"):
            stmt = stmt.where(JobPosting.work_mode == filters["work_mode"])
        if filters.get("location"):
            stmt = stmt.where(JobPosting.location.ilike(f"%{filters['location']}%"))
    
    # Execute main query
    result = await db.execute(stmt)
    rows = result.all()
    jobs = [row[0] for row in rows]
    
    # Get total count (without limit/offset)
    count_stmt = (
        select(func.count())
        .select_from(JobPosting)
        .where(
            JobPosting.embedding.is_not(None),
            similarity_expr >= similarity_threshold,
        )
    )
    
    if filters:
        if filters.get("company"):
            count_stmt = count_stmt.where(JobPosting.company.ilike(f"%{filters['company']}%"))
        if filters.get("source"):
            count_stmt = count_stmt.where(JobPosting.source == filters["source"])
        if filters.get("work_mode"):
            count_stmt = count_stmt.where(JobPosting.work_mode == filters["work_mode"])
        if filters.get("location"):
            count_stmt = count_stmt.where(JobPosting.location.ilike(f"%{filters['location']}%"))
    
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Record metrics
    duration = __import__('time').time() - start_time
    semantic_search_total.labels(
        status="success",
        has_filters="true" if filters else "false",
    ).inc()
    semantic_search_duration_seconds.observe(duration)
    
    logger.info(f"Semantic search: '{query[:50]}...' -> {len(jobs)} results (total: {total}, {duration:.3f}s)")
    
    return jobs, total


async def hybrid_search_jobs(
    db: AsyncSession,
    query: str,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    keyword_weight: float = 0.3,
    semantic_weight: float = 0.7,
    filters: Optional[dict] = None,
) -> Tuple[List[JobPosting], int]:
    """
    Perform hybrid search combining keyword and semantic search.
    
    Uses RRF (Reciprocal Rank Fusion) to combine results.
    
    Args:
        db: Database session
        query: Search query text
        limit: Maximum number of results
        offset: Number of results to skip
        similarity_threshold: Minimum cosine similarity for semantic part
        keyword_weight: Weight for keyword search (0-1)
        semantic_weight: Weight for semantic search (0-1)
        filters: Optional filters
        
    Returns:
        Tuple of (jobs, total_count)
    """
    # For simplicity, we'll do a combined query that ranks by both
    # In production, you might want to use a more sophisticated RRF implementation
    
    query_embedding = await generate_search_embedding(query)
    
    # Build combined ranking
    # Normalize both scores to 0-1 and combine
    similarity_expr = 1 - JobPosting.embedding.cosine_distance(query_embedding)
    
    # Keyword match: simple ILIKE on title, description, skills
    keyword_conditions = []
    if query:
        keywords = query.lower().split()
        for kw in keywords:
            keyword_conditions.append(
                func.concat(
                    JobPosting.title,
                    ' ', JobPosting.job_description,
                    ' ', func.coalesce(JobPosting.required_skills, ''),
                    ' ', func.coalesce(JobPosting.preferred_skills, ''),
                ).ilike(f"%{kw}%")
            )
    
    keyword_match = func.sum(
        *[case((cond, 1), else_=0) for cond in keyword_conditions]
    ) if keyword_conditions else 0
    
    # Normalize keyword match to 0-1 (max keywords = len(keywords))
    max_keywords = len(query.split()) if query else 1
    keyword_score = keyword_match / max_keywords
    
    # Combined score
    combined_score = (semantic_weight * similarity_expr) + (keyword_weight * keyword_score)
    
    stmt = (
        select(JobPosting, combined_score.label("combined_score"), similarity_expr.label("similarity"))
        .where(
            JobPosting.embedding.is_not(None),
            similarity_expr >= similarity_threshold,
        )
        .order_by(combined_score.desc())
        .limit(min(limit, MAX_LIMIT))
        .offset(max(offset, 0))
    )
    
    if filters:
        if filters.get("company"):
            stmt = stmt.where(JobPosting.company.ilike(f"%{filters['company']}%"))
        if filters.get("source"):
            stmt = stmt.where(JobPosting.source == filters["source"])
        if filters.get("work_mode"):
            stmt = stmt.where(JobPosting.work_mode == filters["work_mode"])
        if filters.get("location"):
            stmt = stmt.where(JobPosting.location.ilike(f"%{filters['location']}%"))
    
    result = await db.execute(stmt)
    rows = result.all()
    jobs = [row[0] for row in rows]
    
    # Get total count
    count_stmt = (
        select(func.count())
        .select_from(JobPosting)
        .where(
            JobPosting.embedding.is_not(None),
            similarity_expr >= similarity_threshold,
        )
    )
    if filters:
        if filters.get("company"):
            count_stmt = count_stmt.where(JobPosting.company.ilike(f"%{filters['company']}%"))
        if filters.get("source"):
            count_stmt = count_stmt.where(JobPosting.source == filters["source"])
        if filters.get("work_mode"):
            count_stmt = count_stmt.where(JobPosting.work_mode == filters["work_mode"])
        if filters.get("location"):
            count_stmt = count_stmt.where(JobPosting.location.ilike(f"%{filters['location']}%"))
    
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    return jobs, total


async def get_similar_jobs(
    db: AsyncSession,
    job_id: int,
    limit: int = 10,
    similarity_threshold: float = 0.8,
) -> List[JobPosting]:
    """
    Find jobs similar to a given job using its embedding.
    
    Args:
        db: Database session
        job_id: Reference job ID
        limit: Maximum number of similar jobs
        similarity_threshold: Minimum similarity (higher = more similar)
        
    Returns:
        List of similar jobs (excluding the reference job)
    """
    # Get reference job embedding
    result = await db.execute(
        select(JobPosting.embedding).where(JobPosting.id == job_id)
    )
    embedding = result.scalar_one_or_none()
    
    if not embedding:
        logger.warning(f"Job {job_id} has no embedding")
        return []
    
    similarity_expr = 1 - JobPosting.embedding.cosine_distance(embedding)
    
    stmt = (
        select(JobPosting, similarity_expr.label("similarity"))
        .where(
            JobPosting.id != job_id,
            JobPosting.embedding.is_not(None),
            similarity_expr >= similarity_threshold,
        )
        .order_by(similarity_expr.desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    return [row[0] for row in rows]


async def create_hnsw_index(db: AsyncSession, m: int = 16, ef_construction: int = 64) -> bool:
    """
    Create HNSW index on embedding column for fast ANN search.
    
    Note: Run once after data is loaded. Requires pgvector 0.5+.
    
    Args:
        db: Database session
        m: Max connections per layer (default 16)
        ef_construction: Size of dynamic candidate list (default 64)
        
    Returns:
        True if created, False if already exists
    """
    try:
        await db.execute(text(f"""
            CREATE INDEX IF NOT EXISTS job_postings_embedding_hnsw_idx
            ON job_postings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = {m}, ef_construction = {ef_construction});
        """))
        await db.commit()
        logger.info(f"Created HNSW index on job_postings.embedding (m={m}, ef_construction={ef_construction})")
        return True
    except Exception as e:
        logger.exception("Failed to create HNSW index")
        return False


async def create_ivfflat_index(db: AsyncSession, lists: int = 100) -> bool:
    """
    Create IVFFlat index on embedding column (alternative to HNSW).
    
    Args:
        db: Database session
        lists: Number of inverted lists (default 100)
        
    Returns:
        True if created, False if already exists
    """
    try:
        await db.execute(text(f"""
            CREATE INDEX IF NOT EXISTS job_postings_embedding_ivfflat_idx
            ON job_postings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {lists});
        """))
        await db.commit()
        logger.info(f"Created IVFFlat index on job_postings.embedding (lists={lists})")
        return True
    except Exception as e:
        logger.exception("Failed to create IVFFlat index")
        return False