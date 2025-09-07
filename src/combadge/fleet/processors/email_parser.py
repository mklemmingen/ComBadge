"""Email Parser for Fleet Management Communications

Intelligent email parsing that handles various email formats, forwarded chains,
header detection, and content cleaning for fleet management processing.
"""

import re
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import base64
import quopri

from ...core.logging_manager import LoggingManager


class EmailFormat(Enum):
    """Detected email format types."""
    OUTLOOK = "outlook"
    GMAIL = "gmail"
    THUNDERBIRD = "thunderbird"
    APPLE_MAIL = "apple_mail"
    PLAIN_TEXT = "plain_text"
    UNKNOWN = "unknown"


class EmailType(Enum):
    """Types of email content."""
    DIRECT = "direct"        # Direct message
    FORWARDED = "forwarded"  # Forwarded message
    REPLY = "reply"         # Reply message
    THREAD = "thread"       # Email thread/chain
    UNKNOWN = "unknown"


@dataclass
class EmailHeader:
    """Parsed email header information."""
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: List[str] = field(default_factory=list)
    cc_addresses: List[str] = field(default_factory=list)
    bcc_addresses: List[str] = field(default_factory=list)
    subject: Optional[str] = None
    date_sent: Optional[datetime] = None
    message_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: Optional[str] = None


@dataclass
class ForwardedChain:
    """Information about forwarded email chain."""
    depth: int = 0
    original_sender: Optional[str] = None
    original_date: Optional[datetime] = None
    original_subject: Optional[str] = None
    forward_history: List[str] = field(default_factory=list)


@dataclass
class EmailParseResult:
    """Complete email parsing result."""
    headers: EmailHeader
    body_content: str
    cleaned_content: str
    email_format: EmailFormat
    email_type: EmailType
    forwarded_chain: Optional[ForwardedChain] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    parsing_confidence: float = 0.0
    parsing_notes: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


class EmailParser:
    """Advanced email parser for fleet management communications."""
    
    def __init__(self):
        """Initialize email parser with patterns and configurations."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # Email format detection patterns
        self.format_patterns = self._build_format_patterns()
        
        # Header parsing patterns
        self.header_patterns = self._build_header_patterns()
        
        # Content cleaning patterns
        self.cleaning_patterns = self._build_cleaning_patterns()
        
        # Forwarding detection patterns
        self.forwarding_patterns = self._build_forwarding_patterns()
        
        # Signature detection patterns
        self.signature_patterns = self._build_signature_patterns()
        
    def _build_format_patterns(self) -> Dict[EmailFormat, List[str]]:
        """Build patterns to detect email client formats.
        
        Returns:
            Dictionary mapping formats to detection patterns
        """
        return {
            EmailFormat.OUTLOOK: [
                r"microsoft outlook",
                r"x-mailer:.*outlook",
                r"x-originalarrivaltime:",
                r"thread-index:",
                r"x-ms-exchange",
                r"-----original message-----"
            ],
            
            EmailFormat.GMAIL: [
                r"x-gmail",
                r"delivered-to:.*gmail\.com",
                r"x-google",
                r"gmail\.com",
                r"---------- forwarded message ----------"
            ],
            
            EmailFormat.THUNDERBIRD: [
                r"x-mailer:.*thunderbird",
                r"user-agent:.*thunderbird",
                r"mozilla thunderbird"
            ],
            
            EmailFormat.APPLE_MAIL: [
                r"x-mailer:.*apple mail",
                r"x-apple",
                r"mail \(.*\) version"
            ]
        }
    
    def _build_header_patterns(self) -> Dict[str, str]:
        """Build regex patterns for header extraction.
        
        Returns:
            Dictionary mapping header fields to patterns
        """
        return {
            "from": r"from:\s*([^<\n]+(?:<[^>]+>)?)",
            "to": r"to:\s*([^\n]+)",
            "cc": r"cc:\s*([^\n]+)", 
            "bcc": r"bcc:\s*([^\n]+)",
            "subject": r"subject:\s*([^\n]+)",
            "date": r"date:\s*([^\n]+)",
            "sent": r"sent:\s*([^\n]+)",
            "message_id": r"message-id:\s*(<[^>]+>)",
            "reply_to": r"reply-to:\s*([^\n]+)",
            "priority": r"(?:priority|importance):\s*([^\n]+)"
        }
    
    def _build_cleaning_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for content cleaning.
        
        Returns:
            List of cleaning pattern configurations
        """
        return [
            {
                "name": "quoted_printable_decode",
                "pattern": r"=([0-9A-F]{2})",
                "action": "decode_quoted_printable"
            },
            {
                "name": "base64_decode",
                "pattern": r"^[A-Za-z0-9+/]+=*$",
                "action": "decode_base64",
                "min_length": 50
            },
            {
                "name": "html_tags",
                "pattern": r"<[^>]+>",
                "replacement": ""
            },
            {
                "name": "html_entities",
                "pattern": r"&(?:amp|lt|gt|quot|#39|#x27|nbsp);",
                "replacement": {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', 
                              "&#39;": "'", "&#x27;": "'", "&nbsp;": " "}
            },
            {
                "name": "multiple_whitespace",
                "pattern": r"\s+",
                "replacement": " "
            },
            {
                "name": "email_separators",
                "pattern": r"[=\-_]{3,}",
                "replacement": "\n---\n"
            },
            {
                "name": "outlook_formatting",
                "pattern": r"\*\s*([^*]+)\s*\*",
                "replacement": r"\1"
            }
        ]
    
    def _build_forwarding_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns to detect forwarded email chains.
        
        Returns:
            List of forwarding detection patterns
        """
        return [
            {
                "pattern": r"-----?original message-----?",
                "type": "outlook_forward",
                "confidence": 0.9
            },
            {
                "pattern": r"---------- forwarded message ----------",
                "type": "gmail_forward", 
                "confidence": 0.95
            },
            {
                "pattern": r"begin forwarded message:",
                "type": "apple_forward",
                "confidence": 0.9
            },
            {
                "pattern": r"forwarded by [^\n]+ on [^\n]+",
                "type": "lotus_forward",
                "confidence": 0.8
            },
            {
                "pattern": r"from:\s*[^\n]+\nsent:\s*[^\n]+\nto:\s*[^\n]+\nsubject:",
                "type": "generic_forward",
                "confidence": 0.7
            },
            {
                "pattern": r"on .+ wrote:",
                "type": "reply_chain",
                "confidence": 0.6
            },
            {
                "pattern": r">{1,3}\s*[^\n]+",
                "type": "quoted_reply",
                "confidence": 0.5
            }
        ]
    
    def _build_signature_patterns(self) -> List[str]:
        """Build patterns to detect email signatures.
        
        Returns:
            List of signature detection patterns
        """
        return [
            r"--\s*\n",  # Standard signature separator
            r"best regards?[,\n]",
            r"sincerely[,\n]",
            r"thank you[,\n]",
            r"sent from my (?:iphone|android|mobile)",
            r"this email was sent from",
            r"confidential[:\s]",
            r"disclaimer[:\s]",
            r"[\w\s]+ \| [\w\s]+ \| [\w@\.\s]+",  # Name | Title | Email pattern
            r"phone:?\s*[\d\-\(\)\s]+",
            r"mobile:?\s*[\d\-\(\)\s]+"
        ]
    
    def parse_email(self, email_text: str) -> EmailParseResult:
        """Parse email text and extract structured information.
        
        Args:
            email_text: Raw email text content
            
        Returns:
            Complete email parsing result
        """
        self.logger.debug("Starting email parsing")
        
        # Detect email format
        email_format = self._detect_email_format(email_text)
        
        # Parse headers
        headers = self._parse_headers(email_text, email_format)
        
        # Extract body content
        body_content = self._extract_body_content(email_text, email_format)
        
        # Clean content
        cleaned_content = self._clean_content(body_content)
        
        # Detect email type and forwarding
        email_type, forwarded_chain = self._analyze_email_structure(email_text)
        
        # Extract attachments info
        attachments = self._extract_attachment_info(email_text)
        
        # Calculate parsing confidence
        parsing_confidence = self._calculate_parsing_confidence(
            headers, body_content, email_format, email_type
        )
        
        # Generate parsing notes
        parsing_notes = self._generate_parsing_notes(
            email_text, headers, body_content, email_format
        )
        
        # Create extraction metadata
        extraction_metadata = self._create_extraction_metadata(
            email_text, headers, body_content
        )
        
        result = EmailParseResult(
            headers=headers,
            body_content=body_content,
            cleaned_content=cleaned_content,
            email_format=email_format,
            email_type=email_type,
            forwarded_chain=forwarded_chain,
            attachments=attachments,
            parsing_confidence=parsing_confidence,
            parsing_notes=parsing_notes,
            extraction_metadata=extraction_metadata
        )
        
        self.logger.info(
            f"Email parsing complete: format={email_format.value}, "
            f"type={email_type.value}, confidence={parsing_confidence:.2f}"
        )
        
        return result
    
    def _detect_email_format(self, email_text: str) -> EmailFormat:
        """Detect email client format from content patterns.
        
        Args:
            email_text: Email text content
            
        Returns:
            Detected email format
        """
        text_lower = email_text.lower()
        
        # Check each format's patterns
        format_scores = {}
        
        for email_format, patterns in self.format_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower, re.MULTILINE):
                    score += 1
            format_scores[email_format] = score
        
        # Return format with highest score
        if format_scores:
            best_format = max(format_scores, key=format_scores.get)
            if format_scores[best_format] > 0:
                return best_format
        
        # Default based on simple heuristics
        if "-----original message-----" in text_lower:
            return EmailFormat.OUTLOOK
        elif "---------- forwarded message ----------" in text_lower:
            return EmailFormat.GMAIL
        elif re.search(r"^[a-zA-Z-]+:\s*[^\n]+$", email_text, re.MULTILINE):
            return EmailFormat.PLAIN_TEXT
        
        return EmailFormat.UNKNOWN
    
    def _parse_headers(self, email_text: str, email_format: EmailFormat) -> EmailHeader:
        """Parse email headers from content.
        
        Args:
            email_text: Email text content
            email_format: Detected email format
            
        Returns:
            Parsed email header information
        """
        headers = EmailHeader()
        
        # Try parsing as RFC 2822 email first
        try:
            if email_text.startswith(('From:', 'Return-Path:', 'Received:')):
                parsed_email = email.message_from_string(email_text)
                
                headers.from_address = parsed_email.get('From')
                headers.to_addresses = self._parse_address_list(parsed_email.get('To', ''))
                headers.cc_addresses = self._parse_address_list(parsed_email.get('Cc', ''))
                headers.subject = parsed_email.get('Subject')
                headers.message_id = parsed_email.get('Message-ID')
                headers.reply_to = parsed_email.get('Reply-To')
                
                # Parse date
                date_str = parsed_email.get('Date')
                if date_str:
                    headers.date_sent = self._parse_email_date(date_str)
                
                return headers
        except Exception as e:
            self.logger.debug(f"RFC 2822 parsing failed: {e}")
        
        # Fall back to pattern-based parsing
        for field, pattern in self.header_patterns.items():
            matches = re.findall(pattern, email_text, re.MULTILINE | re.IGNORECASE)
            
            if matches:
                value = matches[0].strip()
                
                if field == "from":
                    # Parse from address and name
                    from_match = re.match(r'([^<]+)<([^>]+)>|([^<>\s]+@[^<>\s]+)', value)
                    if from_match:
                        if from_match.group(2):  # Name <email> format
                            headers.from_name = from_match.group(1).strip(' "')
                            headers.from_address = from_match.group(2)
                        else:  # Just email
                            headers.from_address = from_match.group(3)
                
                elif field == "to":
                    headers.to_addresses = self._parse_address_list(value)
                
                elif field == "cc":
                    headers.cc_addresses = self._parse_address_list(value)
                
                elif field == "bcc":
                    headers.bcc_addresses = self._parse_address_list(value)
                
                elif field == "subject":
                    headers.subject = value
                
                elif field in ("date", "sent"):
                    headers.date_sent = self._parse_email_date(value)
                
                elif field == "message_id":
                    headers.message_id = value
                
                elif field == "reply_to":
                    headers.reply_to = value
                
                elif field == "priority":
                    headers.priority = value
        
        return headers
    
    def _parse_address_list(self, address_string: str) -> List[str]:
        """Parse comma-separated email addresses.
        
        Args:
            address_string: String containing email addresses
            
        Returns:
            List of parsed email addresses
        """
        if not address_string:
            return []
        
        # Split by comma and clean up addresses
        addresses = []
        for addr in address_string.split(','):
            addr = addr.strip()
            
            # Extract email from "Name <email>" format
            email_match = re.search(r'<([^>]+)>', addr)
            if email_match:
                addresses.append(email_match.group(1))
            elif '@' in addr:
                # Remove any remaining quotes or brackets
                clean_addr = re.sub(r'["\'\[\]<>]', '', addr).strip()
                if '@' in clean_addr:
                    addresses.append(clean_addr)
        
        return addresses
    
    def _parse_email_date(self, date_string: str) -> Optional[datetime]:
        """Parse email date string to datetime.
        
        Args:
            date_string: Date string from email
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        # Common email date formats
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S"
        ]
        
        # Clean up date string
        date_clean = re.sub(r'\s*\([^)]+\)\s*', '', date_string)  # Remove timezone names in parentheses
        date_clean = re.sub(r'\s+', ' ', date_clean).strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_clean, fmt)
            except ValueError:
                continue
        
        # Try parsing with email.utils
        try:
            import email.utils
            parsed_date = email.utils.parsedate_to_datetime(date_string)
            return parsed_date
        except Exception:
            pass
        
        self.logger.warning(f"Could not parse date: {date_string}")
        return None
    
    def _extract_body_content(self, email_text: str, email_format: EmailFormat) -> str:
        """Extract main body content from email.
        
        Args:
            email_text: Full email text
            email_format: Detected email format
            
        Returns:
            Extracted body content
        """
        # Try to parse as structured email first
        try:
            if email_text.startswith(('From:', 'Return-Path:', 'Received:')):
                parsed_email = email.message_from_string(email_text)
                
                if parsed_email.is_multipart():
                    # Get text/plain part from multipart email
                    for part in parsed_email.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if isinstance(payload, bytes):
                                return payload.decode('utf-8', errors='ignore')
                            return str(payload)
                else:
                    # Single part email
                    payload = parsed_email.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode('utf-8', errors='ignore')
                    return str(payload)
        except Exception as e:
            self.logger.debug(f"Structured email parsing failed: {e}")
        
        # Fall back to heuristic extraction
        body_start_patterns = [
            r"\n\n",  # Double newline after headers
            r"\n\r\n",  # Windows line endings
            r"-----original message-----",
            r"---------- forwarded message ----------",
            r"^[^\n]*\n[^\n]*\n\n"  # Skip first two lines then find content
        ]
        
        for pattern in body_start_patterns:
            match = re.search(pattern, email_text, re.MULTILINE | re.IGNORECASE)
            if match:
                return email_text[match.end():].strip()
        
        # If no clear separation, return everything after first few header-like lines
        lines = email_text.split('\n')
        body_lines = []
        header_ended = False
        
        for line in lines:
            if not header_ended:
                # Skip lines that look like headers
                if ':' in line and not line.strip().startswith('>'):
                    continue
                elif line.strip() == '':
                    header_ended = True
                    continue
                else:
                    header_ended = True
            
            body_lines.append(line)
        
        return '\n'.join(body_lines).strip()
    
    def _clean_content(self, content: str) -> str:
        """Clean email content by removing formatting and artifacts.
        
        Args:
            content: Raw email content
            
        Returns:
            Cleaned content
        """
        cleaned = content
        
        # Apply cleaning patterns
        for cleaning_config in self.cleaning_patterns:
            pattern = cleaning_config.get("pattern")
            action = cleaning_config.get("action")
            replacement = cleaning_config.get("replacement", "")
            
            if action == "decode_quoted_printable":
                cleaned = self._decode_quoted_printable(cleaned)
            elif action == "decode_base64":
                if len(cleaned) > cleaning_config.get("min_length", 0):
                    cleaned = self._try_decode_base64(cleaned)
            elif isinstance(replacement, dict):
                # Multiple replacements
                for old, new in replacement.items():
                    cleaned = cleaned.replace(old, new)
            else:
                # Single regex replacement
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.MULTILINE)
        
        # Remove signatures
        cleaned = self._remove_signatures(cleaned)
        
        # Remove quoted text in replies
        cleaned = self._remove_quoted_replies(cleaned)
        
        # Final cleanup
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Multiple blank lines
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _decode_quoted_printable(self, text: str) -> str:
        """Decode quoted-printable encoded text.
        
        Args:
            text: Quoted-printable encoded text
            
        Returns:
            Decoded text
        """
        try:
            return quopri.decodestring(text).decode('utf-8', errors='ignore')
        except Exception:
            return text
    
    def _try_decode_base64(self, text: str) -> str:
        """Try to decode base64 text.
        
        Args:
            text: Potentially base64 encoded text
            
        Returns:
            Decoded text or original if not base64
        """
        try:
            # Check if it looks like base64
            if re.match(r'^[A-Za-z0-9+/]+=*$', text.strip()):
                decoded = base64.b64decode(text)
                return decoded.decode('utf-8', errors='ignore')
        except Exception:
            pass
        return text
    
    def _remove_signatures(self, content: str) -> str:
        """Remove email signatures from content.
        
        Args:
            content: Email content
            
        Returns:
            Content without signatures
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        in_signature = False
        for line in lines:
            # Check for signature patterns
            for sig_pattern in self.signature_patterns:
                if re.search(sig_pattern, line, re.IGNORECASE):
                    in_signature = True
                    break
            
            if not in_signature:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _remove_quoted_replies(self, content: str) -> str:
        """Remove quoted reply text (lines starting with >).
        
        Args:
            content: Email content
            
        Returns:
            Content without quoted replies
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines that start with > (quoted replies)
            if not re.match(r'^\s*>+\s', line):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _analyze_email_structure(self, email_text: str) -> Tuple[EmailType, Optional[ForwardedChain]]:
        """Analyze email structure to detect forwarding and type.
        
        Args:
            email_text: Full email text
            
        Returns:
            Tuple of (email_type, forwarded_chain_info)
        """
        forwarded_chain = None
        email_type = EmailType.DIRECT
        
        # Check for forwarding patterns
        for forward_config in self.forwarding_patterns:
            pattern = forward_config["pattern"]
            fwd_type = forward_config["type"]
            confidence = forward_config["confidence"]
            
            matches = re.findall(pattern, email_text, re.MULTILINE | re.IGNORECASE)
            
            if matches:
                if fwd_type.endswith("_forward"):
                    email_type = EmailType.FORWARDED
                    forwarded_chain = self._extract_forward_chain(email_text, fwd_type)
                elif fwd_type in ("reply_chain", "quoted_reply"):
                    email_type = EmailType.REPLY
                
                break
        
        # Check for thread indicators
        if re.search(r"re:\s*", email_text, re.IGNORECASE):
            if email_type == EmailType.DIRECT:
                email_type = EmailType.REPLY
        
        # Check for multiple forward/reply patterns (thread)
        forward_count = sum(
            len(re.findall(config["pattern"], email_text, re.MULTILINE | re.IGNORECASE))
            for config in self.forwarding_patterns
        )
        
        if forward_count > 2:
            email_type = EmailType.THREAD
        
        return email_type, forwarded_chain
    
    def _extract_forward_chain(self, email_text: str, forward_type: str) -> ForwardedChain:
        """Extract forwarded email chain information.
        
        Args:
            email_text: Email text content
            forward_type: Type of forwarding detected
            
        Returns:
            Forwarded chain information
        """
        chain = ForwardedChain()
        
        # Extract original sender from forwarded content
        original_from_patterns = [
            r"from:\s*([^\n]+)",
            r"sent by:\s*([^\n]+)",
            r"original sender:\s*([^\n]+)"
        ]
        
        for pattern in original_from_patterns:
            match = re.search(pattern, email_text, re.IGNORECASE)
            if match:
                chain.original_sender = match.group(1).strip()
                break
        
        # Extract original subject
        original_subject_match = re.search(
            r"subject:\s*([^\n]+)", 
            email_text, 
            re.IGNORECASE
        )
        if original_subject_match:
            chain.original_subject = original_subject_match.group(1).strip()
        
        # Count forwarding depth
        forward_indicators = [
            r"-----?original message-----?",
            r"---------- forwarded message ----------",
            r"begin forwarded message:",
            r"forwarded by"
        ]
        
        depth = 0
        for indicator in forward_indicators:
            depth += len(re.findall(indicator, email_text, re.IGNORECASE))
        
        chain.depth = depth
        
        return chain
    
    def _extract_attachment_info(self, email_text: str) -> List[Dict[str, Any]]:
        """Extract attachment information from email.
        
        Args:
            email_text: Email text content
            
        Returns:
            List of attachment information dictionaries
        """
        attachments = []
        
        # Common attachment indicators
        attachment_patterns = [
            r"attachment:\s*([^\n]+)",
            r"attached file[s]?:\s*([^\n]+)",
            r"please find attached:\s*([^\n]+)",
            r"content-disposition:\s*attachment[^;]*;\s*filename=([^\s\n;]+)",
            r"filename[=:]\s*([^\s\n;]+)"
        ]
        
        for pattern in attachment_patterns:
            matches = re.findall(pattern, email_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    filename = match[0] if match else "unknown"
                else:
                    filename = match
                
                # Clean filename
                filename = filename.strip(' "\'<>')
                
                if filename and filename != "unknown":
                    attachments.append({
                        "filename": filename,
                        "size": None,
                        "type": self._guess_file_type(filename),
                        "description": "Detected from email content"
                    })
        
        return attachments
    
    def _guess_file_type(self, filename: str) -> str:
        """Guess file type from filename extension.
        
        Args:
            filename: Filename string
            
        Returns:
            Guessed file type
        """
        extension = filename.split('.')[-1].lower() if '.' in filename else ""
        
        type_map = {
            "pdf": "document",
            "doc": "document", 
            "docx": "document",
            "xls": "spreadsheet",
            "xlsx": "spreadsheet",
            "ppt": "presentation",
            "pptx": "presentation",
            "txt": "text",
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gif": "image",
            "zip": "archive",
            "rar": "archive"
        }
        
        return type_map.get(extension, "unknown")
    
    def _calculate_parsing_confidence(
        self,
        headers: EmailHeader,
        body_content: str,
        email_format: EmailFormat,
        email_type: EmailType
    ) -> float:
        """Calculate confidence score for email parsing.
        
        Args:
            headers: Parsed headers
            body_content: Extracted body content
            email_format: Detected email format
            email_type: Detected email type
            
        Returns:
            Parsing confidence score
        """
        confidence = 0.0
        
        # Header completeness score
        header_fields = [
            headers.from_address,
            headers.subject,
            headers.date_sent
        ]
        header_score = sum(1 for field in header_fields if field) / len(header_fields)
        confidence += header_score * 0.4
        
        # Body content score
        if body_content and len(body_content.strip()) > 10:
            body_score = min(1.0, len(body_content) / 100)
            confidence += body_score * 0.3
        
        # Format detection score
        if email_format != EmailFormat.UNKNOWN:
            confidence += 0.2
        
        # Structure analysis score
        if email_type != EmailType.UNKNOWN:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_parsing_notes(
        self,
        email_text: str,
        headers: EmailHeader,
        body_content: str,
        email_format: EmailFormat
    ) -> List[str]:
        """Generate notes about the parsing process.
        
        Args:
            email_text: Original email text
            headers: Parsed headers
            body_content: Extracted body content
            email_format: Detected email format
            
        Returns:
            List of parsing notes
        """
        notes = []
        
        # Text length analysis
        text_length = len(email_text)
        if text_length < 100:
            notes.append("Very short email - may be incomplete")
        elif text_length > 10000:
            notes.append("Very long email - may contain multiple messages")
        
        # Header completeness
        missing_headers = []
        if not headers.from_address:
            missing_headers.append("from")
        if not headers.subject:
            missing_headers.append("subject")
        if not headers.date_sent:
            missing_headers.append("date")
        
        if missing_headers:
            notes.append(f"Missing headers: {', '.join(missing_headers)}")
        
        # Body content analysis
        if not body_content or len(body_content.strip()) < 10:
            notes.append("Little or no body content extracted")
        
        # Format detection
        if email_format == EmailFormat.UNKNOWN:
            notes.append("Could not determine email client format")
        else:
            notes.append(f"Detected format: {email_format.value}")
        
        return notes
    
    def _create_extraction_metadata(
        self,
        email_text: str,
        headers: EmailHeader,
        body_content: str
    ) -> Dict[str, Any]:
        """Create metadata about the extraction process.
        
        Args:
            email_text: Original email text
            headers: Parsed headers
            body_content: Extracted body content
            
        Returns:
            Extraction metadata dictionary
        """
        return {
            "original_length": len(email_text),
            "body_length": len(body_content),
            "header_fields_found": sum(1 for field in [
                headers.from_address, headers.to_addresses, headers.subject,
                headers.date_sent, headers.message_id
            ] if field),
            "has_attachments": bool(re.search(r"attachment|content-disposition", email_text, re.IGNORECASE)),
            "line_count": len(email_text.split('\n')),
            "character_encoding_issues": bool(re.search(r'[\x00-\x08\x0E-\x1F\x7F-\x9F]', email_text)),
            "parsing_timestamp": datetime.now().isoformat()
        }