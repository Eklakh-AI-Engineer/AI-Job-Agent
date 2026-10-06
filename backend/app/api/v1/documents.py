"""
backend/app/api/v1/documents.py

Document generation and human-review API endpoints.

Generation is synchronous for simplicity (documents are small); a Celery task
is also provided for background generation. Documents begin as drafts and must
be approved before use in an application.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentContentUpdate,
    DocumentGenerateRequest,
    DocumentList,
    DocumentRead,
    DocumentStatusUpdate,
)
from app.services.candidate_kb_service import CandidateKBNotFoundError
from app.services.document_service import (
    DOC_TYPE_COVER_LETTER,
    DOC_TYPE_RESUME,
    DocumentGenerationError,
    DocumentNotFoundError,
    generate_cover_letter,
    generate_resume,
    get_document,
    list_documents,
    regenerate_document,
    update_document_content,
    update_document_status,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/generate",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a tailored resume or cover letter",
)
async def generate_document(
    payload: DocumentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """
    Generate a document for a job from the user's Candidate KB.

    Only public candidate evidence is used. The result is saved as a draft
    and must be approved before use.
    """
    if payload.doc_type not in (DOC_TYPE_RESUME, DOC_TYPE_COVER_LETTER):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="doc_type must be 'resume' or 'cover_letter'",
        )

    try:
        if payload.doc_type == DOC_TYPE_RESUME:
            doc = await generate_resume(
                db, current_user.id, payload.job_id, payload.store_artifact
            )
        else:
            doc = await generate_cover_letter(
                db, current_user.id, payload.job_id, payload.store_artifact
            )
    except CandidateKBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Candidate KB found. Create one first via PUT /api/v1/profile/kb.",
        ) from exc
    except DocumentGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return DocumentRead.model_validate(doc)


@router.get(
    "",
    response_model=DocumentList,
    summary="List the current user's generated documents",
)
async def list_my_documents(
    job_id: Optional[int] = Query(None, description="Filter by job posting id"),
    doc_type: Optional[str] = Query(None, description="Filter by type"),
    doc_status: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentList:
    """List generated documents for the authenticated user."""
    docs = await list_documents(
        db, current_user.id, job_id=job_id, doc_type=doc_type, status=doc_status
    )
    return DocumentList(
        items=[DocumentRead.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Get one generated document",
)
async def get_my_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """Return a single document owned by the authenticated user."""
    try:
        doc = await get_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return DocumentRead.model_validate(doc)


@router.patch(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Edit a generated document",
)
async def edit_my_document(
    document_id: int,
    payload: DocumentContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """Apply a manual edit. Editing resets the document to draft."""
    try:
        doc = await update_document_content(
            db, current_user.id, document_id, payload.content
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return DocumentRead.model_validate(doc)


@router.post(
    "/{document_id}/status",
    response_model=DocumentRead,
    summary="Approve or reject a document",
)
async def set_document_status(
    document_id: int,
    payload: DocumentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """
    Approve or reject a document. This is the human-review gate before an
    application may be submitted.
    """
    try:
        doc = await update_document_status(
            db, current_user.id, document_id, payload.status
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return DocumentRead.model_validate(doc)


@router.post(
    "/{document_id}/regenerate",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate a document as a new version",
)
async def regenerate_my_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    """Regenerate a document, creating a new version."""
    try:
        doc = await regenerate_document(db, current_user.id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DocumentGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return DocumentRead.model_validate(doc)