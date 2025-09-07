"""
Documentation search system for ComBadge.

This module provides intelligent search capabilities across all ComBadge
documentation, including help topics, user guides, API docs, and tutorials.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result."""
    title: str
    content_preview: str
    file_path: str
    relevance_score: float
    document_type: str  # help_topic, user_guide, api_doc, tutorial
    section: Optional[str] = None
    line_number: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchIndex:
    """Search index for fast document retrieval."""
    terms: Dict[str, Set[str]] = field(default_factory=dict)  # term -> document_ids
    documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # doc_id -> metadata
    ngrams: Dict[str, Set[str]] = field(default_factory=dict)  # ngram -> document_ids
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class SearchFilters:
    """Search filters to narrow results."""
    document_types: Optional[List[str]] = None
    file_extensions: Optional[List[str]] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    min_relevance_score: float = 0.1
    max_results: int = 50
    include_content_preview: bool = True
    highlight_terms: bool = True


class DocumentIndexer:
    """Indexes documentation for fast searching."""
    
    def __init__(self):
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'would', 'you', 'your', 'this',
            'can', 'could', 'should', 'would', 'may', 'might', 'must'
        }
        
    def extract_terms(self, text: str) -> Set[str]:
        """Extract searchable terms from text."""
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        terms = {
            word for word in words
            if word not in self.stop_words and len(word) > 2
        }
        
        return terms
        
    def extract_ngrams(self, text: str, n: int = 3) -> Set[str]:
        """Extract n-grams for phrase searching."""
        words = re.findall(r'\b\w+\b', text.lower())
        ngrams = set()
        
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i + n])
            if not any(word in self.stop_words for word in words[i:i + n]):
                ngrams.add(ngram)
                
        return ngrams
        
    def extract_code_terms(self, text: str) -> Set[str]:
        """Extract code-specific terms (functions, classes, etc.)."""
        code_terms = set()
        
        # Extract function names
        function_matches = re.findall(r'def\s+(\w+)', text)
        code_terms.update(function_matches)
        
        # Extract class names
        class_matches = re.findall(r'class\s+(\w+)', text)
        code_terms.update(class_matches)
        
        # Extract variable names in code blocks
        code_block_pattern = r'```[\s\S]*?```'
        code_blocks = re.findall(code_block_pattern, text)
        for block in code_blocks:
            # Extract identifiers from code
            identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', block)
            code_terms.update(identifiers)
            
        return code_terms
        
    def get_document_type(self, file_path: Path) -> str:
        """Determine document type from file path."""
        path_str = str(file_path).lower()
        
        if 'tutorial' in path_str:
            return 'tutorial'
        elif 'api' in path_str or 'reference' in path_str:
            return 'api_doc'
        elif 'user_guide' in path_str or 'getting_started' in path_str:
            return 'user_guide'
        elif 'admin' in path_str:
            return 'admin_guide'
        elif 'developer' in path_str:
            return 'developer_guide'
        elif 'help' in path_str or 'topic' in path_str:
            return 'help_topic'
        else:
            return 'documentation'


class DocumentationSearcher:
    """Main documentation search engine."""
    
    def __init__(self, docs_directory: Path):
        self.docs_directory = Path(docs_directory)
        self.indexer = DocumentIndexer()
        self.index = SearchIndex()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the search system."""
        if self.is_initialized:
            return
            
        logger.info("Initializing documentation search system...")
        await self.build_index()
        
        self.is_initialized = True
        logger.info(f"Search system initialized with {len(self.index.documents)} documents")
        
    async def build_index(self):
        """Build search index from all documentation files."""
        self.index = SearchIndex()
        
        # Find all documentation files
        doc_files = []
        for pattern in ['**/*.md', '**/*.rst', '**/*.txt', '**/*.json']:
            doc_files.extend(self.docs_directory.glob(pattern))
            
        # Index each file
        for file_path in doc_files:
            try:
                await self._index_file(file_path)
            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
                
        logger.info(f"Indexed {len(self.index.documents)} documents")
        
    async def _index_file(self, file_path: Path):
        """Index a single documentation file."""
        # Generate document ID
        doc_id = hashlib.md5(str(file_path).encode()).hexdigest()
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with different encoding
            content = file_path.read_text(encoding='latin-1')
            
        # Extract metadata
        title = self._extract_title(content)
        document_type = self.indexer.get_document_type(file_path)
        
        # Store document metadata
        self.index.documents[doc_id] = {
            'file_path': str(file_path),
            'title': title,
            'document_type': document_type,
            'content': content,
            'content_length': len(content),
            'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime),
            'sections': self._extract_sections(content)
        }
        
        # Extract and index terms
        terms = self.indexer.extract_terms(content)
        for term in terms:
            if term not in self.index.terms:
                self.index.terms[term] = set()
            self.index.terms[term].add(doc_id)
            
        # Extract and index n-grams
        ngrams = self.indexer.extract_ngrams(content)
        for ngram in ngrams:
            if ngram not in self.index.ngrams:
                self.index.ngrams[ngram] = set()
            self.index.ngrams[ngram].add(doc_id)
            
        # Index code terms if applicable
        if file_path.suffix in ['.md', '.rst'] and '```' in content:
            code_terms = self.indexer.extract_code_terms(content)
            for term in code_terms:
                if term not in self.index.terms:
                    self.index.terms[term] = set()
                self.index.terms[term].add(doc_id)
                
    def _extract_title(self, content: str) -> str:
        """Extract title from document content."""
        lines = content.split('\n')
        
        # Look for markdown title
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('=') and len(line) > 5:
                # RestructuredText title
                prev_line_idx = lines.index(line) - 1
                if prev_line_idx >= 0:
                    return lines[prev_line_idx].strip()
                    
        # Fallback to filename
        return "Untitled Document"
        
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract sections from document content."""
        sections = []
        lines = content.split('\n')
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Detect headers (markdown)
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('# ').strip()
                
                if current_section:
                    current_section['end_line'] = i - 1
                    sections.append(current_section)
                    
                current_section = {
                    'title': title,
                    'level': level,
                    'start_line': i,
                    'end_line': None
                }
                
        # Close last section
        if current_section:
            current_section['end_line'] = len(lines) - 1
            sections.append(current_section)
            
        return sections
        
    async def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None
    ) -> List[SearchResult]:
        """Search documentation with query."""
        if not self.is_initialized:
            await self.initialize()
            
        if not query.strip():
            return []
            
        if filters is None:
            filters = SearchFilters()
            
        # Tokenize query
        query_terms = self.indexer.extract_terms(query)
        query_ngrams = self.indexer.extract_ngrams(query, n=2)  # Use 2-grams for queries
        
        # Score documents
        doc_scores = defaultdict(float)
        
        # Term matching
        for term in query_terms:
            if term in self.index.terms:
                for doc_id in self.index.terms[term]:
                    doc_scores[doc_id] += 1.0
                    
        # N-gram matching (higher weight)
        for ngram in query_ngrams:
            if ngram in self.index.ngrams:
                for doc_id in self.index.ngrams[ngram]:
                    doc_scores[doc_id] += 2.0
                    
        # Phrase matching (highest weight)
        phrase_score = self._score_phrase_matches(query, doc_scores)
        for doc_id, score in phrase_score.items():
            doc_scores[doc_id] += score * 3.0
            
        # Apply filters and build results
        results = []
        for doc_id, score in doc_scores.items():
            if score < filters.min_relevance_score:
                continue
                
            doc_meta = self.index.documents[doc_id]
            
            # Apply document type filter
            if (filters.document_types and 
                doc_meta['document_type'] not in filters.document_types):
                continue
                
            # Apply date range filter
            if filters.date_range:
                start_date, end_date = filters.date_range
                if not (start_date <= doc_meta['last_modified'] <= end_date):
                    continue
                    
            # Create search result
            result = SearchResult(
                title=doc_meta['title'],
                content_preview=self._generate_preview(
                    doc_meta['content'], query_terms, filters.include_content_preview
                ),
                file_path=doc_meta['file_path'],
                relevance_score=score,
                document_type=doc_meta['document_type'],
                keywords=list(query_terms),
                context={
                    'content_length': doc_meta['content_length'],
                    'last_modified': doc_meta['last_modified'],
                    'sections': len(doc_meta['sections'])
                }
            )
            
            results.append(result)
            
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results[:filters.max_results]
        
    def _score_phrase_matches(
        self,
        query: str,
        doc_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """Score exact phrase matches in documents."""
        phrase_scores = defaultdict(float)
        query_lower = query.lower()
        
        for doc_id in doc_scores.keys():
            doc_content = self.index.documents[doc_id]['content'].lower()
            
            # Count exact phrase occurrences
            if query_lower in doc_content:
                phrase_scores[doc_id] = doc_content.count(query_lower)
                
        return phrase_scores
        
    def _generate_preview(
        self,
        content: str,
        query_terms: Set[str],
        include_preview: bool
    ) -> str:
        """Generate content preview with highlighted terms."""
        if not include_preview:
            return ""
            
        content_lower = content.lower()
        
        # Find best preview location (where most query terms appear)
        best_start = 0
        best_score = 0
        window_size = 200
        
        for i in range(0, len(content) - window_size, 50):
            window = content_lower[i:i + window_size]
            score = sum(1 for term in query_terms if term in window)
            
            if score > best_score:
                best_score = score
                best_start = i
                
        # Extract preview
        preview_start = max(0, best_start - 50)
        preview_end = min(len(content), best_start + window_size + 50)
        preview = content[preview_start:preview_end]
        
        # Clean up preview
        if preview_start > 0:
            preview = "..." + preview
        if preview_end < len(content):
            preview = preview + "..."
            
        # Remove excessive whitespace
        preview = re.sub(r'\s+', ' ', preview).strip()
        
        return preview
        
    async def suggest_completions(
        self,
        partial_query: str,
        max_suggestions: int = 5
    ) -> List[str]:
        """Suggest query completions."""
        if not self.is_initialized:
            await self.initialize()
            
        if len(partial_query) < 2:
            return []
            
        partial_lower = partial_query.lower()
        suggestions = set()
        
        # Find matching terms
        for term in self.index.terms.keys():
            if term.startswith(partial_lower):
                suggestions.add(term)
            elif partial_lower in term:
                suggestions.add(term)
                
        # Find matching n-grams
        for ngram in self.index.ngrams.keys():
            if partial_lower in ngram:
                suggestions.add(ngram)
                
        # Sort by relevance (shorter suggestions first)
        suggestions_list = sorted(suggestions, key=len)
        
        return suggestions_list[:max_suggestions]
        
    async def get_related_documents(
        self,
        document_path: str,
        max_related: int = 5
    ) -> List[SearchResult]:
        """Get documents related to the given document."""
        if not self.is_initialized:
            await self.initialize()
            
        # Find the document
        target_doc_id = None
        for doc_id, doc_meta in self.index.documents.items():
            if doc_meta['file_path'] == document_path:
                target_doc_id = doc_id
                break
                
        if not target_doc_id:
            return []
            
        target_doc = self.index.documents[target_doc_id]
        target_terms = self.indexer.extract_terms(target_doc['content'])
        
        # Score other documents by term overlap
        related_scores = defaultdict(float)
        
        for doc_id, doc_meta in self.index.documents.items():
            if doc_id == target_doc_id:
                continue
                
            doc_terms = self.indexer.extract_terms(doc_meta['content'])
            
            # Calculate Jaccard similarity
            intersection = target_terms & doc_terms
            union = target_terms | doc_terms
            
            if union:
                similarity = len(intersection) / len(union)
                related_scores[doc_id] = similarity
                
        # Build results
        results = []
        for doc_id, score in sorted(related_scores.items(), 
                                  key=lambda x: x[1], reverse=True)[:max_related]:
            doc_meta = self.index.documents[doc_id]
            
            result = SearchResult(
                title=doc_meta['title'],
                content_preview=doc_meta['content'][:200] + "...",
                file_path=doc_meta['file_path'],
                relevance_score=score,
                document_type=doc_meta['document_type'],
                context={'similarity_type': 'content_overlap'}
            )
            
            results.append(result)
            
        return results
        
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search system statistics."""
        return {
            'total_documents': len(self.index.documents),
            'total_terms': len(self.index.terms),
            'total_ngrams': len(self.index.ngrams),
            'last_updated': self.index.last_updated,
            'document_types': self._get_document_type_counts(),
            'average_document_length': self._get_average_document_length()
        }
        
    def _get_document_type_counts(self) -> Dict[str, int]:
        """Get count of documents by type."""
        counts = defaultdict(int)
        for doc_meta in self.index.documents.values():
            counts[doc_meta['document_type']] += 1
        return dict(counts)
        
    def _get_average_document_length(self) -> float:
        """Get average document length."""
        if not self.index.documents:
            return 0.0
            
        total_length = sum(doc['content_length'] 
                          for doc in self.index.documents.values())
        return total_length / len(self.index.documents)
        
    async def rebuild_index(self):
        """Rebuild the search index from scratch."""
        logger.info("Rebuilding documentation search index...")
        await self.build_index()
        logger.info("Search index rebuild complete")
        
    async def update_index_for_file(self, file_path: Path):
        """Update index for a specific file."""
        if not file_path.exists():
            # Remove from index if file was deleted
            doc_id_to_remove = None
            for doc_id, doc_meta in self.index.documents.items():
                if doc_meta['file_path'] == str(file_path):
                    doc_id_to_remove = doc_id
                    break
                    
            if doc_id_to_remove:
                # Remove from documents
                del self.index.documents[doc_id_to_remove]
                
                # Remove from term index
                for term_set in self.index.terms.values():
                    term_set.discard(doc_id_to_remove)
                    
                # Remove from n-gram index
                for ngram_set in self.index.ngrams.values():
                    ngram_set.discard(doc_id_to_remove)
                    
        else:
            # Re-index the file
            await self._index_file(file_path)
            
        self.index.last_updated = datetime.now()


class SearchInterface:
    """User interface for documentation search."""
    
    def __init__(self, docs_directory: Path):
        self.searcher = DocumentationSearcher(docs_directory)
        self.search_history: List[str] = []
        self.recent_results: List[SearchResult] = []
        
    async def initialize(self):
        """Initialize the search interface."""
        await self.searcher.initialize()
        
    async def search_with_history(
        self,
        query: str,
        filters: Optional[SearchFilters] = None
    ) -> List[SearchResult]:
        """Search and update search history."""
        results = await self.searcher.search(query, filters)
        
        # Update history
        if query not in self.search_history:
            self.search_history.append(query)
            
        # Keep only recent history
        if len(self.search_history) > 50:
            self.search_history = self.search_history[-50:]
            
        self.recent_results = results
        return results
        
    def get_search_history(self) -> List[str]:
        """Get search history."""
        return self.search_history.copy()
        
    async def search_similar(self, result_index: int) -> List[SearchResult]:
        """Search for documents similar to a recent result."""
        if 0 <= result_index < len(self.recent_results):
            result = self.recent_results[result_index]
            return await self.searcher.get_related_documents(result.file_path)
        return []
        
    def export_search_results(
        self,
        results: List[SearchResult],
        format_type: str = "json"
    ) -> str:
        """Export search results to various formats."""
        if format_type == "json":
            return json.dumps([
                {
                    'title': r.title,
                    'file_path': r.file_path,
                    'relevance_score': r.relevance_score,
                    'document_type': r.document_type,
                    'content_preview': r.content_preview
                }
                for r in results
            ], indent=2)
        elif format_type == "markdown":
            md_content = "# Search Results\n\n"
            for i, result in enumerate(results, 1):
                md_content += f"## {i}. {result.title}\n\n"
                md_content += f"**File:** `{result.file_path}`\n\n"
                md_content += f"**Type:** {result.document_type}\n\n"
                md_content += f"**Relevance:** {result.relevance_score:.2f}\n\n"
                if result.content_preview:
                    md_content += f"**Preview:** {result.content_preview}\n\n"
                md_content += "---\n\n"
            return md_content
        else:
            raise ValueError(f"Unsupported format: {format_type}")