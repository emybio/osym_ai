"""
Django signals for automatic PDF processing
Triggers processing when PDFDocument is created or updated
"""
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import logging

from .models import PDFDocument, PDFProcessingLog
from .services.pdf_processor_service import trigger_pdf_processing

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PDFDocument)
def process_pdf_on_upload(sender, instance, created, **kwargs):
    """
    Automatically process PDF when uploaded or updated
    """
    # Only process if file is present and not already processed
    if instance.file and not instance.is_processed:
        try:
            # Check if we should process asynchronously (default for production)
            asynchronous = getattr(settings, 'PDF_PROCESSING_ASYNC', True)

            result = trigger_pdf_processing(instance.id, asynchronous=asynchronous)

            if asynchronous:
                logger.info(f"PDF processing queued for document {instance.id}: {result}")

                # Create initial processing log
                PDFProcessingLog.objects.create(
                    pdf_document=instance,
                    status="QUEUED",
                    message=f"Processing queued with task ID: {result['task_id']}",
                    metadata={"task_id": result["task_id"]}
                )
            else:
                logger.info(f"PDF processing completed for document {instance.id}: {result}")

        except Exception as e:
            logger.error(f"Failed to trigger PDF processing for {instance.id}: {str(e)}")

            # Log the error
            PDFProcessingLog.objects.create(
                pdf_document=instance,
                status="ERROR",
                message=f"Failed to queue processing: {str(e)}"
            )


@receiver(pre_delete, sender=PDFDocument)
def cleanup_pdf_embeddings(sender, instance, **kwargs):
    """
    Clean up embeddings when PDF is deleted
    """
    try:
        from .services.pdf_processor_service import PDFProcessorService
        processor = PDFProcessorService()

        # TODO: Implement Chroma collection cleanup
        # This requires Chroma-specific operations to remove collections
        # For now, we'll just log the cleanup action

        logger.info(f"PDF document {instance.id} deleted. Embeddings cleanup needed.")

        # Log the cleanup action
        PDFProcessingLog.objects.create(
            pdf_document=instance,
            status="CLEANUP",
            message="PDF deleted. Embeddings cleanup recommended.",
            metadata={
                "document_id": instance.id,
                "title": instance.title,
                "file_path": instance.file.name if instance.file else None
            }
        )

    except Exception as e:
        logger.error(f"Failed to cleanup embeddings for deleted PDF {instance.id}: {str(e)}")


@receiver(post_save, sender=PDFProcessingLog)
def log_processing_status_change(sender, instance, created, **kwargs):
    """
    Log processing status changes for monitoring
    """
    if created:
        logger.info(f"Processing log created for PDF {instance.pdf_document.id}: {instance.status}")
    else:
        logger.info(f"Processing log updated for PDF {instance.pdf_document.id}: {instance.status}")