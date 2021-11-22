import logging

from celery import shared_task
from papermerge.core.ocr.document import ocr_document

from .models import Document, Folder, Page

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def ocr_document_task(
    self,
    document_id,
    lang,
    namespace=None
):
    """
    OCR whole document, updates document's version and its `text` field
    """

    doc = Document.objects.get(pk=document_id)
    user_id = doc.user.id
    doc_version = doc.document_versions.last()

    ocr_document(
        user_id=user_id,
        document_id=document_id,
        file_name=doc_version.file_name,
        lang=lang,
        namespace=namespace,
        version=doc_version.number,
        target_version=doc_version.number + 1
    )

    # get document model
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist as exception:
        logger.error(exception, exc_info=True)
        return False

    # update document's version
    # doc.version = target_version
    # doc.save()

    # update document text field (i.e so that document will be searchable)
    doc.update_text_field()

    return True


def norm_pages_from_doc(document):
    logger.debug(f"Normalizing document {document.id}")
    for page in Page.objects.filter(document=document):
        page.norm()


def norm_pages_from_folder(folder):
    for descendent in folder.get_descendants():
        if isinstance(descendent, Document):
            norm_pages_from_doc(descendent)
        elif isinstance(descendent, Folder):
            norm_pages_from_folder(descendent)
        else:
            raise ValueError("Unexpected value for descendent instance")


@shared_task
def normalize_pages(origin):
    """
    Normalize Pages. The normalization was triggered model origin.
    origin can be either a Folder or a Document
    """
    if isinstance(origin, Document):
        norm_pages_from_doc(origin)
    elif isinstance(origin, Folder):
        norm_pages_from_folder(origin)
