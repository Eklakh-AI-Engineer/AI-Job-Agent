"""
backend/app/api/v1/semantic_search.py

Semantic search API endpoints.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.job import JobPostingList, JobPostingRead
from app.services.semantic_search_service import (
    semantic_search_jobs,
    hybrid_search_jobs,
    get_similar_jobs,
    create_hnsw_index,
    create_ivfflat_index,
)

router = APIRouter(prefix="/search", tags=["Semantic Search"])


@router.get(
    "/semantic",
    response_model=JobPostingList,
    summary="Semantic search for jobs",
    description="""
    Perform semantic search on job postings using vector similarity.
    
    Uses pgvector cosine similarity on job embeddings.
    """,
)
async def semantic_search(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="Minimum similarity (0-1)"),
    company: Optional[str] = Query(None, description="Filter by company"),
    source: Optional[str] = Query(None, description="Filter by source"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode (remote/hybrid/onsite)"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostingList:
    """
    Semantic search for jobs.
    
    Returns jobs ranked by semantic similarity to the query.
    """
    filters = {}
    if company:
        filters["company"] = company
    if source:
        filters["source"] = source
    if work_mode:
        filters["work_mode"] = work_mode
    if location:
        filters["location"] = location
    
    jobs, total = await semantic_search_jobs(
        db=db,
        query=q,
        limit=limit,
        offset=offset,
        similarity_threshold=threshold,
        filters=filters if filters else None,
    )
    
    return JobPostingList(
        items=[JobPostingRead.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/hybrid",
    response_model=JobPostingList,
    summary="Hybrid search for jobs",
    description="""
    Perform hybrid search combining keyword and semantic search.
    
    Uses RRF (Reciprocal Rank Fusion) to combine keyword and semantic results.
    """,
)
async def hybrid_search(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="Minimum semantic similarity (0-1)"),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0, description="Keyword search weight"),
    semantic_weight: float = Query(0.7, ge=0.0, le=1.0, description="Semantic search weight"),
    company: Optional[str] = Query(None, description="Filter by company"),
    source: Optional[str] = Query(None, description="Filter by source"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostingList:
    """
    Hybrid search for jobs.
    
    Combines keyword matching with semantic similarity using weighted scores.
    """
    filters = {}
    if company:
        filters["company"] = company
    if source:
        filters["source"] = source
    if work_mode:
        filters["work_mode"] = work_mode
    if location:
        filters["location"] = location
    
    jobs, total = await hybrid_search_jobs(
        db=db,
        query=q,
        limit=limit,
        offset=offset,
        similarity_threshold=threshold,
        keyword_weight=keyword_weight,
        semantic_weight=semantic_weight,
        filters=filters if filters else None,
    )
    
    return JobPostingList(
        items=[JobPostingRead.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/similar/{job_id}",
    response_model=JobPostingList,
    summary="Find similar jobs",
    description="""
    Find jobs similar to a given job using its embedding.
    
    Returns jobs with high semantic similarity, excluding the reference job.
    """,
)
async def similar_jobs(
    job_id: int,
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Minimum similarity (0-1)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostingList:
    """
    Find jobs similar to a given job.
    """
    jobs = await get_similar_jobs(
        db=db,
        job_id=job_id,
        limit=limit,
        similarity_threshold=threshold,
    )
    
    return JobPostingList(
        items=[JobPostingRead.model_validate(job) for job in jobs],
        total=len(jobs),
        limit=limit,
        offset=0,
    )


@router.post(
    "/index/hnsw",
    status_code=status.HTTP_201_CREATED,
    summary="Create HNSW index",
    description="""
    Create HNSW index on job embeddings for fast ANN search.
    
    Run once after data is loaded. Requires pgvector 0.5+.
    """,
)
async def create_hnsw_index_endpoint(
    m: int = Query(16, ge=4, le=64, description="Max connections per layer"),
    ef_construction: int = Query(64, ge=16, le=256, description="Candidate list size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create HNSW index on job embeddings.
    """
    success = await create_hnsw_index(db, m=m, ef_construction=ef_construction)
    
    if success:
        return {"status": "created", "index_type": "hnsw", "m": m, "ef_construction": ef_construction}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create HNSW index",
        )


@router.post(
    "/index/ivfflat",
    status_code=status.HTTP_201_CREATED,
    summary="Create IVFFlat index",
    description="""
    Create IVFFlat index on job embeddings (alternative to HNSW).
    
    Run once after data is loaded.
    """,
)
async def create_ivfflat_index_endpoint(
    lists: int = Query(100, ge=10, le=1000, description="Number of inverted lists"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create IVFFlat index on job embeddings.
    """
    success = await create_ivfflat_index(db, lists=lists)
    
    if success:
        return {"status": "created", "index_type": "ivfflat", "lists": lists}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create IVFFlat index",
        )