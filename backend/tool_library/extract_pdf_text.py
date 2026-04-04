import io


def extract_pdf_text(input_data: dict) -> dict:
    """Extract text content from a PDF file or URL.

    Parameters:
        file_path (str, optional): Local path to PDF file.
        url (str, optional): URL to download PDF from.
        pages (list[int], optional): Specific page numbers to extract (0-indexed). Default: all.
        max_pages (int, optional): Maximum pages to process. Default 50.

    Returns:
        dict with keys: text, pages, total_pages, extracted_pages, total_chars, error (optional).
    """
    try:
        if not isinstance(input_data, dict):
            return {
                "text": "",
                "pages": [],
                "total_pages": 0,
                "extracted_pages": 0,
                "total_chars": 0,
                "error": "input_data must be a dict",
            }

        file_path = input_data.get("file_path")
        url = input_data.get("url")
        page_numbers = input_data.get("pages")
        max_pages = int(input_data.get("max_pages", 50))

        if not file_path and not url:
            return {
                "text": "",
                "pages": [],
                "total_pages": 0,
                "extracted_pages": 0,
                "total_chars": 0,
                "error": "Either 'file_path' or 'url' must be provided",
            }

        # Obtain PDF bytes
        pdf_buffer = None

        if url:
            try:
                import requests

                response = requests.get(str(url), timeout=30, stream=True)
                response.raise_for_status()

                # Sanity check content type
                content_type = response.headers.get("Content-Type", "")
                if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                    # Proceed anyway but note the mismatch
                    pass

                pdf_buffer = io.BytesIO(response.content)
            except ImportError:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": "requests library is not available; cannot download PDF from URL",
                }
            except Exception as exc:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": f"Failed to download PDF from URL: {exc}",
                }

        elif file_path:
            try:
                with open(str(file_path), "rb") as f:
                    pdf_buffer = io.BytesIO(f.read())
            except FileNotFoundError:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": f"File not found: {file_path}",
                }
            except PermissionError:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": f"Permission denied: {file_path}",
                }
            except Exception as exc:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": f"Failed to read file: {exc}",
                }

        # Import pypdf (PyPDF2 replacement)
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": "Neither 'pypdf' nor 'PyPDF2' is available",
                }

        # Read the PDF
        try:
            reader = PdfReader(pdf_buffer)
        except Exception as exc:
            error_msg = str(exc).lower()
            if "encrypt" in error_msg or "password" in error_msg:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": 0,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": "PDF is encrypted or password-protected",
                }
            return {
                "text": "",
                "pages": [],
                "total_pages": 0,
                "extracted_pages": 0,
                "total_chars": 0,
                "error": f"Failed to read PDF: {exc}",
            }

        total_pages = len(reader.pages)

        # Handle encrypted PDFs that can still be opened
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return {
                    "text": "",
                    "pages": [],
                    "total_pages": total_pages,
                    "extracted_pages": 0,
                    "total_chars": 0,
                    "error": "PDF is encrypted and could not be decrypted with an empty password",
                }

        # Determine which pages to extract
        if page_numbers is not None:
            if not isinstance(page_numbers, list):
                page_numbers = [page_numbers]
            target_pages = [int(p) for p in page_numbers if 0 <= int(p) < total_pages]
        else:
            target_pages = list(range(total_pages))

        # Apply max_pages limit
        if len(target_pages) > max_pages:
            target_pages = target_pages[:max_pages]

        # Extract text
        pages_result = []
        all_text_parts = []

        for page_num in target_pages:
            try:
                page = reader.pages[page_num]
                page_text = page.extract_text() or ""
            except Exception as exc:
                page_text = f"[Error extracting page {page_num}: {exc}]"

            pages_result.append({
                "page_number": page_num,
                "text": page_text,
                "char_count": len(page_text),
            })
            all_text_parts.append(page_text)

        full_text = "\n\n".join(all_text_parts)

        return {
            "text": full_text,
            "pages": pages_result,
            "total_pages": total_pages,
            "extracted_pages": len(pages_result),
            "total_chars": len(full_text),
        }

    except Exception as exc:
        return {
            "text": "",
            "pages": [],
            "total_pages": 0,
            "extracted_pages": 0,
            "total_chars": 0,
            "error": f"Unexpected error: {exc}",
        }
