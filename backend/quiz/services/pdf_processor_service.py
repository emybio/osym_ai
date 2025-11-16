"""
Production-ready PDF Processing Service with Celery Integration
Handles PDF upload, embedding generation, and background processing
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from django.conf import settings
from django.db import transaction
from django.core.files.storage import default_storage
from celery import shared_task
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from ..models import PDFDocument, PDFProcessingLog

logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """PDF processing related errors"""
    pass


class PDFProcessorService:
    """Production-ready PDF processing service"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.chunk_size = 1000
        self.chunk_overlap = 200

    def validate_pdf(self, pdf_document: PDFDocument) -> Dict[str, Any]:
        """
        Validate PDF document before processing
        Returns validation result with error messages if any
        """
        errors = []
        warnings = []

        # Check file size
        if pdf_document.file.size > self.max_file_size:
            errors.append(f"PDF too large: {pdf_document.file.size} bytes (max: {self.max_file_size})")

        # Check file existence
        if not default_storage.exists(pdf_document.file.name):
            errors.append(f"PDF file not found: {pdf_document.file.name}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check file extension
        if not pdf_document.file.name.lower().endswith('.pdf'):
            errors.append(f"Invalid file extension: {pdf_document.file.name}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def process_pdf_document(self, pdf_document: PDFDocument) -> Dict[str, Any]:
        """
        Process PDF document and generate embeddings
        Synchronous version for immediate processing
        """
        try:
            # Validate PDF
            validation = self.validate_pdf(pdf_document)
            if not validation["valid"]:
                raise PDFProcessingError(f"Validation failed: {validation['errors']}")

            # Get file path
            file_path = default_storage.path(pdf_document.file.name)

            # Process PDF and generate embeddings
            result = self._generate_embeddings(file_path, pdf_document)

            # Update document status
            with transaction.atomic():
                pdf_document.is_processed = True
                pdf_document.processed_at = datetime.now(timezone.utc)
                pdf_document.save()

                # Log successful processing
                PDFProcessingLog.objects.create(
                    pdf_document=pdf_document,
                    status="SUCCESS",
                    message=f"Successfully processed {result['chunk_count']} chunks",
                    metadata=result
                )

            logger.info(f"PDF processed successfully: {pdf_document.title} ({result['chunk_count']} chunks)")

            return {
                "success": True,
                "chunk_count": result["chunk_count"],
                "embedding_count": result["embedding_count"],
                "persist_directory": result["persist_directory"],
                "message": "PDF processed successfully"
            }

        except Exception as e:
            logger.error(f"PDF processing failed for {pdf_document.id}: {str(e)}")

            # Log error
            PDFProcessingLog.objects.create(
                pdf_document=pdf_document,
                status="ERROR",
                message=str(e)
            )

            return {
                "success": False,
                "error": str(e),
                "message": "PDF processing failed"
            }

    def _generate_embeddings(self, file_path: str, pdf_document: PDFDocument) -> Dict[str, Any]:
        """Generate embeddings from PDF file"""
        try:
            # Load PDF
            loader = PyPDFLoader(file_path)
            documents = loader.load_and_split()

            if not documents:
                raise PDFProcessingError("No content extracted from PDF")

            # Add metadata to documents
            for i, doc in enumerate(documents):
                doc.metadata.update({
                    'pdf_id': pdf_document.id,
                    'pdf_title': pdf_document.title,
                    'document_type': pdf_document.document_type,
                    'subject': pdf_document.subject.code if pdf_document.subject else None,
                    'exam_type': pdf_document.exam_type,
                    'year': pdf_document.year,
                    'page_number': i + 1,
                    'processed_at': datetime.now(timezone.utc).isoformat()
                })

            # Determine persist directory based on document type
            if pdf_document.document_type == "CURRICULUM":
                persist_dir = "chroma_yks_pdf"
                collection_name = "yks_curriculum"
            else:  # PAST_EXAM
                persist_dir = "chroma_past"
                collection_name = "past_exams"

            # Ensure persist directory exists
            full_persist_path = os.path.join(settings.BASE_DIR, persist_dir)
            os.makedirs(full_persist_path, exist_ok=True)

            # Create or update Chroma database
            embeddings = OpenAIEmbeddings()

            # Generate unique collection name including document ID
            unique_collection_name = f"{collection_name}_{pdf_document.id}"

            # Create new collection for this document
            db = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=full_persist_path,
                collection_name=unique_collection_name
            )

            # Persist changes
            db.persist()

            logger.info(f"Embeddings created: {len(documents)} chunks in {unique_collection_name}")

            return {
                "chunk_count": len(documents),
                "embedding_count": len(documents),
                "persist_directory": persist_dir,
                "collection_name": unique_collection_name,
                "full_path": full_persist_path
            }

        except Exception as e:
            raise PDFProcessingError(f"Embedding generation failed: {str(e)}")

    def search_embeddings(self, query: str, document_type: str = None, limit: int = 5) -> list:
        """
        Search embeddings for similar content
        """
        try:
            embeddings = OpenAIEmbeddings()
            results = []

            # Search in appropriate collections
            if document_type in ["CURRICULUM", None]:
                try:
                    yks_db = Chroma(
                        persist_directory=os.path.join(settings.BASE_DIR, "chroma_yks_pdf"),
                        embedding_function=embeddings
                    )
                    yks_results = yks_db.similarity_search(query, k=limit)
                    results.extend(yks_results)
                except Exception as e:
                    logger.warning(f"YKS PDF search failed: {e}")

            if document_type in ["PAST_EXAM", None]:
                try:
                    past_db = Chroma(
                        persist_directory=os.path.join(settings.BASE_DIR, "chroma_past"),
                        embedding_function=embeddings
                    )
                    past_results = past_db.similarity_search(query, k=limit)
                    results.extend(past_results)
                except Exception as e:
                    logger.warning(f"Past exams search failed: {e}")

            return results[:limit]

        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []


# Celery task for background processing
@shared_task(bind=True, max_retries=3)
def process_pdf_document_task(self, pdf_document_id: int) -> Dict[str, Any]:
    """
    Background task to process PDF document
    Retry on failure with exponential backoff
    """
    try:
        pdf_document = PDFDocument.objects.get(id=pdf_document_id)
        processor = PDFProcessorService()
        result = processor.process_pdf_document(pdf_document)

        logger.info(f"PDF processing task completed for {pdf_document_id}: {result}")
        return result

    except PDFDocument.DoesNotExist:
        logger.error(f"PDFDocument {pdf_document_id} not found")
        return {"success": False, "error": "Document not found"}

    except Exception as e:
        logger.error(f"PDF processing task failed for {pdf_document_id}: {str(e)}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)  # 1min, 2min, 4min
            raise self.retry(countdown=countdown)

        return {"success": False, "error": str(e)}


# Convenience function to trigger processing
def trigger_pdf_processing(pdf_document_id: int, asynchronous: bool = True) -> Dict[str, Any]:
    """
    Trigger PDF processing (synchronous or asynchronous)
    """
    if asynchronous:
        # Queue for background processing
        task = process_pdf_document_task.delay(pdf_document_id)
        return {
            "success": True,
            "task_id": task.id,
            "message": "PDF processing queued",
            "async": True
        }
    else:
        # Process immediately
        pdf_document = PDFDocument.objects.get(id=pdf_document_id)
        processor = PDFProcessorService()
        return processor.process_pdf_document(pdf_document)