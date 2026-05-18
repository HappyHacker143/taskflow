from pathlib import Path

from django.core.exceptions import ValidationError


MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp', 'txt', 'docx'}
ALLOWED_ATTACHMENT_CONTENT_TYPES = {
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/webp',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def _extension(uploaded_file):
    return Path(uploaded_file.name).suffix.lower().lstrip('.')


def validate_attachment_file(uploaded_file):
    if uploaded_file.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError('Файл слишком большой. Максимальный размер — 10 MB.')

    extension = _extension(uploaded_file)
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise ValidationError('Недопустимый тип файла. Разрешены: PDF, PNG, JPG, WEBP, TXT, DOCX.')

    content_type = getattr(uploaded_file, 'content_type', None)
    if content_type and content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
        raise ValidationError('MIME-тип файла не соответствует разрешённым форматам.')

    if extension in {'png', 'jpg', 'jpeg', 'webp'}:
        try:
            from PIL import Image
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            image.verify()
            uploaded_file.seek(0)
        except Exception as exc:
            raise ValidationError('Изображение повреждено или имеет неподдерживаемый формат.') from exc
