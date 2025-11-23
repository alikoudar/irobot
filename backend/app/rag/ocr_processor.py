"""
OCR Processor using Mistral OCR API (FIXED VERSION).

This version correctly formats base64 images as data URIs for the Mistral OCR API.
"""
import logging
from typing import Union, Optional, List, Tuple
from pathlib import Path
import base64
import io
import concurrent.futures

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class MistralOCRClient:
    """
    Mistral OCR client using official Document AI API.
    
    FIXED: Properly formats base64 images as data URIs.
    """
    
    def __init__(self, api_key: str, model: str = "mistral-ocr-latest"):
        """
        Initialize Mistral OCR client.
        
        Args:
            api_key: Mistral API key
            model: Model to use for OCR (default: mistral-ocr-latest)
        """
        try:
            # Try new import (version >= 1.0.0)
            from mistralai import Mistral
            self.client = Mistral(api_key=api_key)
        except ImportError:
            # Fallback for older versions (0.x)
            try:
                from mistralai.client import MistralClient
                self.client = MistralClient(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "Install mistralai: pip install mistralai\n"
                    "Or upgrade: pip install --upgrade mistralai"
                )
        
        self.model = model
        logger.info(f"Initialized Mistral OCR client with model: {model}")
    
    def extract_text_from_image(
        self, 
        image: Union[Image.Image, Path, str],
        include_image_base64: bool = False
    ) -> str:
        """
        Extract text from a single image using Mistral OCR.
        
        Args:
            image: PIL Image, file path, or URL
            include_image_base64: Include base64 images in response
            
        Returns:
            Extracted text in markdown format
        """
        try:
            # Prepare document based on input type
            if isinstance(image, str) and (image.startswith('http://') or image.startswith('https://')):
                # URL
                document = {
                    "type": "image_url",
                    "image_url": image
                }
            else:
                # Local file or PIL Image - convert to data URI
                image_data_uri = self._image_to_data_uri(image)
                document = {
                    "type": "image_url",
                    "image_url": image_data_uri
                }
            
            # Call Mistral OCR API
            response = self.client.ocr.process(
                model=self.model,
                document=document,
                include_image_base64=include_image_base64
            )
            
            # Extract markdown text from response
            extracted_text = self._extract_markdown_from_response(response)
            
            logger.info(f"OCR extracted {len(extracted_text)} characters")
            return extracted_text
        
        except Exception as e:
            logger.error(f"Mistral OCR failed: {e}")
            return f"[OCR Error: {str(e)}]"
    
    def extract_text_from_pdf(
        self,
        pdf_path: Union[Path, str],
        include_image_base64: bool = False
    ) -> str:
        """
        Extract text from a PDF document using Mistral OCR.
        
        Args:
            pdf_path: Path to PDF file or URL
            include_image_base64: Include base64 images in response
            
        Returns:
            Extracted text in markdown format
        """
        try:
            # Prepare document based on input type
            if isinstance(pdf_path, str) and (pdf_path.startswith('http://') or pdf_path.startswith('https://')):
                # URL
                document = {
                    "type": "document_url",
                    "document_url": pdf_path
                }
            else:
                # Local file - convert to data URI
                pdf_data_uri = self._pdf_to_data_uri(pdf_path)
                document = {
                    "type": "document_url",
                    "document_url": pdf_data_uri
                }
            
            # Call Mistral OCR API
            response = self.client.ocr.process(
                model=self.model,
                document=document,
                include_image_base64=include_image_base64
            )
            
            # Extract markdown text from response
            extracted_text = self._extract_markdown_from_response(response)
            
            logger.info(f"OCR extracted {len(extracted_text)} characters from PDF")
            return extracted_text
        
        except Exception as e:
            logger.error(f"PDF OCR failed: {e}")
            return f"[OCR Error: {str(e)}]"
    
    def batch_process_images(
        self,
        images: List[Union[Image.Image, Path, str]],
        max_workers: int = 3
    ) -> List[Tuple[int, str]]:
        """
        Process multiple images in parallel.
        
        Args:
            images: List of PIL Images, file paths, or URLs
            max_workers: Maximum concurrent workers
            
        Returns:
            List of (index, extracted_text) tuples
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.extract_text_from_image, img): idx
                for idx, img in enumerate(images)
            }
            
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    text = future.result()
                    results.append((idx, text))
                    logger.info(f"Processed image {idx}: {len(text)} chars")
                except Exception as e:
                    logger.error(f"Failed to process image {idx}: {e}")
                    results.append((idx, f"[OCR Error: {str(e)}]"))
        
        # Sort by index
        results.sort(key=lambda x: x[0])
        return results
    
    def _image_to_data_uri(self, image: Union[Image.Image, Path, str]) -> str:
        """
        Convert image to data URI.
        
        Args:
            image: PIL Image or file path
            
        Returns:
            Data URI string (data:image/jpeg;base64,...)
        """
        if Image is None:
            raise ImportError("PIL (Pillow) is required for image processing")
        
        # Load image if path
        if isinstance(image, (Path, str)):
            image_path = Path(image)
            pil_image = Image.open(image_path)
            
            # Determine MIME type from extension
            ext = image_path.suffix.lower()
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')
        else:
            pil_image = image
            mime_type = 'image/jpeg'
        
        # Convert to bytes
        buffer = io.BytesIO()
        
        # Save as JPEG or PNG
        if mime_type == 'image/png':
            pil_image.save(buffer, format='PNG')
        else:
            # Convert RGBA to RGB if necessary
            if pil_image.mode == 'RGBA':
                pil_image = pil_image.convert('RGB')
            pil_image.save(buffer, format='JPEG', quality=95)
            mime_type = 'image/jpeg'
        
        # Encode to base64
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Return as data URI
        return f"data:{mime_type};base64,{image_data}"
    
    def _pdf_to_data_uri(self, pdf_path: Union[Path, str]) -> str:
        """
        Convert PDF to data URI.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Data URI string (data:application/pdf;base64,...)
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:application/pdf;base64,{pdf_data}"
    
    def _extract_markdown_from_response(self, response) -> str:
        """
        Extract markdown text from OCR API response.
        
        Args:
            response: OCR API response object
            
        Returns:
            Extracted markdown text
        """
        try:
            # Response structure: response.pages[0].markdown
            if hasattr(response, 'pages') and len(response.pages) > 0:
                # Combine all pages
                all_text = []
                for page_num, page in enumerate(response.pages, 1):
                    if hasattr(page, 'markdown'):
                        page_text = page.markdown
                        all_text.append(f"\n\n=== Page {page_num} ===\n\n{page_text}")
                
                return "".join(all_text) if all_text else "[No text extracted]"
            else:
                logger.warning("No pages found in OCR response")
                return "[No text extracted]"
        
        except Exception as e:
            logger.error(f"Failed to extract markdown from response: {e}")
            return f"[Extraction Error: {str(e)}]"
    
    def estimate_cost(
        self,
        num_pages: int = 1,
        pricing_per_1000: float = 1.0
    ) -> float:
        """
        Estimate cost for OCR operations.
        
        Mistral OCR pricing: $1 per 1000 pages
        
        Args:
            num_pages: Number of pages to process
            pricing_per_1000: Price per 1000 pages (default: $1.0)
            
        Returns:
            Estimated cost in USD
        """
        return (num_pages / 1000) * pricing_per_1000


class OCRFallbackClient:
    """
    Fallback OCR client using free alternatives (Tesseract).
    """
    
    def __init__(self):
        """Initialize fallback OCR client."""
        try:
            import pytesseract
            self.available = True
            logger.info("Fallback OCR (Tesseract) available")
        except ImportError:
            self.available = False
            logger.warning("Fallback OCR not available (install pytesseract)")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text using Tesseract."""
        if not self.available:
            return "[Fallback OCR not available]"
        
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            
            logger.info(f"Fallback OCR extracted {len(text)} chars")
            return text
            
        except Exception as e:
            logger.error(f"Fallback OCR failed: {e}")
            return f"[Fallback OCR Error: {str(e)}]"