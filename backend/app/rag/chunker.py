"""
Text chunking strategies for RAG pipeline.

Supports:
- Recursive character splitting with overlap
- Token-based chunking (using tiktoken)
- Semantic chunking (future)
"""
import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)


class TextChunker:
    """Text chunker with multiple strategies."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 51,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Target size in tokens
            chunk_overlap: Overlap size in tokens (10% of chunk_size recommended)
            encoding_name: Tiktoken encoding name (cl100k_base for GPT-4, text-embedding-ada-002)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name
        
        # Initialize tiktoken encoder
        try:
            import tiktoken
            self.encoder = tiktoken.get_encoding(encoding_name)
            logger.info(f"Initialized TextChunker: {chunk_size} tokens, {chunk_overlap} overlap")
        except ImportError:
            logger.warning("tiktoken not installed, falling back to character-based estimation")
            self.encoder = None
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Chunk text using recursive character splitting.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include in each chunk
            
        Returns:
            List of chunk dictionaries with 'text', 'token_count', 'char_count', 'metadata'
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # Split text into chunks
        text_chunks = self._recursive_character_split(
            text=text,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # Create chunk objects with metadata
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_dict = {
                'text': chunk_text,
                'token_count': self.count_tokens(chunk_text),
                'char_count': len(chunk_text),
                'chunk_index': i,
                'metadata': metadata or {}
            }
            chunks.append(chunk_dict)
        
        logger.info(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks
    
    def _recursive_character_split(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        separators: Optional[List[str]] = None
    ) -> List[str]:
        """
        Recursively split text by characters.
        
        Algorithm:
        1. Try to split by paragraph (\\n\\n)
        2. Then by sentence (. ! ?)
        3. Then by line (\\n)
        4. Then by word ( )
        5. Finally by character
        
        Args:
            text: Text to split
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap size in tokens
            separators: Custom separators (optional)
            
        Returns:
            List of text chunks
        """
        if separators is None:
            separators = [
                "\n\n",  # Paragraphs
                "\n",    # Lines
                ". ",    # Sentences
                "! ",    # Exclamations
                "? ",    # Questions
                "; ",    # Semicolons
                ", ",    # Commas
                " ",     # Words
                ""       # Characters (last resort)
            ]
        
        # Convert token size to approximate character size
        # Approximation: 1 token ≈ 4 characters
        chars_per_token = 4
        chunk_size_chars = chunk_size * chars_per_token
        overlap_chars = chunk_overlap * chars_per_token
        
        chunks = []
        
        # If text is already small enough, return it
        if self.count_tokens(text) <= chunk_size:
            return [text.strip()] if text.strip() else []
        
        # Try each separator
        for separator in separators:
            if separator == "":
                # Last resort: split by character
                for i in range(0, len(text), chunk_size_chars - overlap_chars):
                    chunk = text[i:i + chunk_size_chars]
                    if chunk.strip():
                        chunks.append(chunk.strip())
                break
            
            if separator in text:
                # Split by separator
                splits = text.split(separator)
                
                current_chunk = ""
                for split in splits:
                    # Add split to current chunk
                    test_chunk = current_chunk + separator + split if current_chunk else split
                    
                    # Check if adding this split exceeds chunk size
                    if self.count_tokens(test_chunk) > chunk_size and current_chunk:
                        # Save current chunk
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        
                        # Start new chunk with overlap
                        if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                            current_chunk = current_chunk[-overlap_chars:] + separator + split
                        else:
                            current_chunk = split
                    else:
                        current_chunk = test_chunk
                
                # Add last chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                break
        
        # Filter out chunks that are too small (< 50 characters)
        chunks = [c for c in chunks if len(c) >= 50]
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count
            
        Returns:
            Number of tokens
        """
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Tiktoken encoding failed: {e}")
        
        # Fallback: approximate
        return len(text) // 4
    
    def split_by_tokens(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int = 0
    ) -> List[str]:
        """
        Split text by exact token count (no separators).
        
        Use when you need precise token-based splitting.
        
        Args:
            text: Text to split
            chunk_size: Chunk size in tokens
            chunk_overlap: Overlap size in tokens
            
        Returns:
            List of text chunks
        """
        if not self.encoder:
            raise ValueError("Tiktoken encoder not available")
        
        # Encode entire text
        tokens = self.encoder.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Get chunk of tokens
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start position with overlap
            start = end - chunk_overlap
        
        return chunks
    
    def extract_page_number(self, text: str) -> Optional[int]:
        """
        Extract page number from text markers.
        
        Looks for patterns like:
        - === Page 5 ===
        - === Slide 3 ===
        - Page 10
        
        Args:
            text: Text to search
            
        Returns:
            Page number or None
        """
        patterns = [
            r"=== Page (\d+) ===",
            r"=== Slide (\d+) ===",
            r"Page (\d+)",
            r"page (\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def optimize_chunk_boundaries(self, chunks: List[str]) -> List[str]:
        """
        Optimize chunk boundaries to avoid cutting in the middle of sentences.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            Optimized chunks
        """
        optimized = []
        
        for i, chunk in enumerate(chunks):
            # For last chunk, keep as is
            if i == len(chunks) - 1:
                optimized.append(chunk)
                continue
            
            # Try to find a sentence boundary near the end
            sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
            
            # Look for sentence ending in last 100 chars
            search_area = chunk[-100:] if len(chunk) > 100 else chunk
            
            last_sentence_end = -1
            for ending in sentence_endings:
                pos = search_area.rfind(ending)
                if pos > last_sentence_end:
                    last_sentence_end = pos
            
            if last_sentence_end > 0:
                # Cut at sentence boundary
                cut_point = len(chunk) - len(search_area) + last_sentence_end + 1
                optimized.append(chunk[:cut_point].strip())
            else:
                # No good boundary found, keep original
                optimized.append(chunk)
        
        return optimized
    
    def get_chunk_statistics(self, chunks: List[Dict]) -> Dict:
        """
        Get statistics about chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {
                'total_chunks': 0,
                'total_tokens': 0,
                'total_chars': 0,
                'avg_tokens_per_chunk': 0,
                'avg_chars_per_chunk': 0,
                'min_tokens': 0,
                'max_tokens': 0
            }
        
        token_counts = [c['token_count'] for c in chunks]
        char_counts = [c['char_count'] for c in chunks]
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(token_counts),
            'total_chars': sum(char_counts),
            'avg_tokens_per_chunk': sum(token_counts) / len(chunks),
            'avg_chars_per_chunk': sum(char_counts) / len(chunks),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'min_chars': min(char_counts),
            'max_chars': max(char_counts)
        }


class SemanticChunker:
    """
    Semantic-based chunker (future enhancement).
    
    Uses embeddings to determine optimal chunk boundaries based on semantic similarity.
    """
    
    def __init__(self, embedding_model=None):
        """Initialize semantic chunker."""
        self.embedding_model = embedding_model
        logger.info("Semantic chunker initialized (placeholder for future)")
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text based on semantic boundaries.
        
        TODO: Implement in future sprint when embedding model is available.
        """
        raise NotImplementedError("Semantic chunking not yet implemented")