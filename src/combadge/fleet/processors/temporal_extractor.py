"""Temporal Extractor for Fleet Management Date/Time Processing

Advanced natural language date and time processing that handles relative references,
multiple formats, timezone handling, and recurring patterns for fleet scheduling.
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
from dateutil import parser, relativedelta
from dateutil.tz import tzlocal, tzutc, gettz
from enum import Enum
import calendar

from ...core.logging_manager import LoggingManager


class TemporalType(Enum):
    """Types of temporal expressions."""
    ABSOLUTE_DATE = "absolute_date"        # Specific date (2024-03-15)
    RELATIVE_DATE = "relative_date"        # Relative to now (tomorrow, next week)
    TIME_OF_DAY = "time_of_day"           # Specific time (3:30 PM)
    DURATION = "duration"                  # Time span (2 hours, 3 days)
    DATE_RANGE = "date_range"             # Period (March 1-15, next month)
    RECURRING = "recurring"               # Repeating pattern (every Monday)
    CONTEXTUAL = "contextual"             # Context dependent (end of day)
    UNKNOWN = "unknown"


class TemporalPrecision(Enum):
    """Precision level of temporal extraction."""
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"


class RecurrencePattern(Enum):
    """Types of recurring patterns."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"
    NONE = "none"


@dataclass
class TimezonInfo:
    """Timezone information."""
    timezone_name: str
    timezone_offset: Optional[str] = None
    is_dst: Optional[bool] = None
    detected_from: str = "system"  # system, context, explicit


@dataclass
class RecurrenceInfo:
    """Recurring pattern information."""
    pattern: RecurrencePattern
    frequency: int = 1  # Every N units (every 2 weeks)
    days_of_week: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    days_of_month: List[int] = field(default_factory=list)  # 1-31
    months: List[int] = field(default_factory=list)  # 1-12
    end_date: Optional[datetime] = None
    occurrence_count: Optional[int] = None


@dataclass
class TemporalExtraction:
    """Individual temporal extraction result."""
    temporal_type: TemporalType
    original_text: str
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    precision: Optional[TemporalPrecision] = None
    timezone_info: Optional[TimezonInfo] = None
    recurrence_info: Optional[RecurrenceInfo] = None
    confidence: float = 0.0
    extraction_notes: List[str] = field(default_factory=list)
    format_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalExtractionResult:
    """Complete temporal extraction result."""
    original_text: str
    extractions: List[TemporalExtraction] = field(default_factory=list)
    primary_extraction: Optional[TemporalExtraction] = None
    context_datetime: datetime = field(default_factory=datetime.now)
    default_timezone: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_notes: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


class TemporalExtractor:
    """Advanced temporal expression extractor for fleet management."""
    
    def __init__(self, default_timezone: Optional[str] = None):
        """Initialize temporal extractor with patterns and configurations.
        
        Args:
            default_timezone: Default timezone for extractions (e.g., 'US/Eastern')
        """
        self.logger = LoggingManager.get_logger(__name__)
        self.default_timezone = default_timezone or str(tzlocal())
        
        # Relative date patterns
        self.relative_patterns = self._build_relative_patterns()
        
        # Absolute date patterns
        self.absolute_patterns = self._build_absolute_patterns()
        
        # Time patterns
        self.time_patterns = self._build_time_patterns()
        
        # Duration patterns
        self.duration_patterns = self._build_duration_patterns()
        
        # Recurring patterns
        self.recurring_patterns = self._build_recurring_patterns()
        
        # Contextual patterns
        self.contextual_patterns = self._build_contextual_patterns()
        
        # Timezone patterns
        self.timezone_patterns = self._build_timezone_patterns()
        
        # Month and day name mappings
        self.month_names = self._build_month_names()
        self.day_names = self._build_day_names()
        
        # Common date format patterns
        self.date_formats = self._build_date_formats()
        
    def _build_relative_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for relative date expressions.
        
        Returns:
            List of relative date pattern configurations
        """
        return [
            {
                "pattern": r"\b(today|now)\b",
                "type": "same_day",
                "delta_func": lambda: timedelta(days=0),
                "confidence": 0.95
            },
            {
                "pattern": r"\b(tomorrow|tmrw)\b",
                "type": "next_day",
                "delta_func": lambda: timedelta(days=1),
                "confidence": 0.95
            },
            {
                "pattern": r"\b(yesterday)\b",
                "type": "previous_day",
                "delta_func": lambda: timedelta(days=-1),
                "confidence": 0.95
            },
            {
                "pattern": r"\b(next|this)\s+(week)\b",
                "type": "relative_week",
                "delta_func": lambda m: timedelta(weeks=1) if m.group(1) == "next" else timedelta(days=0),
                "confidence": 0.9
            },
            {
                "pattern": r"\b(last|previous)\s+(week)\b",
                "type": "relative_week",
                "delta_func": lambda: timedelta(weeks=-1),
                "confidence": 0.9
            },
            {
                "pattern": r"\b(next|this)\s+(month)\b",
                "type": "relative_month",
                "delta_func": lambda m: relativedelta.relativedelta(months=1) if m.group(1) == "next" else relativedelta.relativedelta(months=0),
                "confidence": 0.9
            },
            {
                "pattern": r"\b(last|previous)\s+(month)\b",
                "type": "relative_month",
                "delta_func": lambda: relativedelta.relativedelta(months=-1),
                "confidence": 0.9
            },
            {
                "pattern": r"\bin\s+(\d+)\s+(day|week|month|year)s?\b",
                "type": "future_offset",
                "delta_func": lambda m: self._parse_offset_delta(m.group(1), m.group(2)),
                "confidence": 0.85
            },
            {
                "pattern": r"\b(\d+)\s+(day|week|month|year)s?\s+(ago|from now)\b",
                "type": "past_future_offset",
                "delta_func": lambda m: self._parse_offset_delta(
                    m.group(1), m.group(2), m.group(3) == "ago"
                ),
                "confidence": 0.85
            },
            {
                "pattern": r"\b(this|next|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                "type": "relative_weekday",
                "delta_func": lambda m: self._calculate_weekday_delta(m.group(2), m.group(1)),
                "confidence": 0.9
            }
        ]
    
    def _build_absolute_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for absolute date expressions.
        
        Returns:
            List of absolute date pattern configurations
        """
        return [
            {
                "pattern": r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b",
                "type": "iso_date",
                "format": "%Y-%m-%d",
                "confidence": 0.95
            },
            {
                "pattern": r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b",
                "type": "us_date",
                "format": "%m/%d/%Y",
                "confidence": 0.9
            },
            {
                "pattern": r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b",
                "type": "short_date",
                "format": "%m/%d/%y",
                "confidence": 0.8
            },
            {
                "pattern": r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})\b",
                "type": "month_day_year",
                "confidence": 0.95
            },
            {
                "pattern": r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b",
                "type": "day_month_year",
                "confidence": 0.95
            },
            {
                "pattern": r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\b",
                "type": "month_day_current_year",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(\d{1,2})(?:st|nd|rd|th)?\s+of\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b",
                "type": "day_of_month",
                "confidence": 0.85
            }
        ]
    
    def _build_time_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for time expressions.
        
        Returns:
            List of time pattern configurations
        """
        return [
            {
                "pattern": r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)\b",
                "type": "12_hour_time",
                "confidence": 0.95
            },
            {
                "pattern": r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b",
                "type": "24_hour_time",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(\d{1,2})\s*(am|pm)\b",
                "type": "hour_only",
                "confidence": 0.8
            },
            {
                "pattern": r"\b(noon|midnight)\b",
                "type": "named_time",
                "confidence": 0.9
            },
            {
                "pattern": r"\b(morning|afternoon|evening|night)\b",
                "type": "time_of_day_general",
                "confidence": 0.6
            },
            {
                "pattern": r"\b(early|late)\s+(morning|afternoon|evening)\b",
                "type": "time_of_day_modified",
                "confidence": 0.7
            },
            {
                "pattern": r"\b(end of|start of)\s+(day|business day|work day)\b",
                "type": "business_time",
                "confidence": 0.8
            }
        ]
    
    def _build_duration_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for duration expressions.
        
        Returns:
            List of duration pattern configurations
        """
        return [
            {
                "pattern": r"\b(\d+(?:\.\d+)?)\s+(second|minute|hour|day|week|month|year)s?\b",
                "type": "simple_duration",
                "confidence": 0.9
            },
            {
                "pattern": r"\b(\d+):(\d{2})(?::(\d{2}))?\s*(hour|hr|minute|min)s?\b",
                "type": "time_duration",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(half|quarter)\s+(hour|day|week|month|year)\b",
                "type": "fractional_duration",
                "confidence": 0.8
            },
            {
                "pattern": r"\b(\d+)\s*-\s*(\d+)\s+(minute|hour|day|week)s?\b",
                "type": "range_duration",
                "confidence": 0.8
            },
            {
                "pattern": r"\bfor\s+(\d+(?:\.\d+)?)\s+(second|minute|hour|day|week|month|year)s?\b",
                "type": "duration_for",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(overnight|all day|all week|all month)\b",
                "type": "named_duration",
                "confidence": 0.8
            }
        ]
    
    def _build_recurring_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for recurring temporal expressions.
        
        Returns:
            List of recurring pattern configurations
        """
        return [
            {
                "pattern": r"\bevery\s+(day|weekday|business day)\b",
                "type": "daily_recurrence",
                "recurrence": RecurrencePattern.DAILY,
                "confidence": 0.95
            },
            {
                "pattern": r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                "type": "weekly_day_recurrence",
                "recurrence": RecurrencePattern.WEEKLY,
                "confidence": 0.95
            },
            {
                "pattern": r"\bevery\s+(\d+)\s+(day|week|month|year)s?\b",
                "type": "interval_recurrence",
                "confidence": 0.9
            },
            {
                "pattern": r"\b(weekly|monthly|quarterly|annually|yearly)\b",
                "type": "named_recurrence",
                "confidence": 0.9
            },
            {
                "pattern": r"\bevery\s+(other|second|third)\s+(day|week|month|year)\b",
                "type": "ordinal_recurrence",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(first|second|third|last)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+of\s+(each|every)\s+month\b",
                "type": "monthly_weekday_recurrence",
                "recurrence": RecurrencePattern.MONTHLY,
                "confidence": 0.9
            }
        ]
    
    def _build_contextual_patterns(self) -> List[Dict[str, Any]]:
        """Build patterns for contextual temporal expressions.
        
        Returns:
            List of contextual pattern configurations
        """
        return [
            {
                "pattern": r"\b(asap|as soon as possible|immediately|right away|urgently)\b",
                "type": "immediate",
                "confidence": 0.9
            },
            {
                "pattern": r"\b(soon|shortly|in a bit|in a while)\b",
                "type": "near_future",
                "confidence": 0.7
            },
            {
                "pattern": r"\bby\s+(end of|close of)\s+(day|business|today|tomorrow)\b",
                "type": "deadline_contextual",
                "confidence": 0.85
            },
            {
                "pattern": r"\b(during|while|throughout)\s+(the\s+)?(day|week|month|year)\b",
                "type": "duration_contextual",
                "confidence": 0.75
            },
            {
                "pattern": r"\b(before|after)\s+(lunch|dinner|breakfast|work|business hours)\b",
                "type": "meal_work_context",
                "confidence": 0.8
            },
            {
                "pattern": r"\b(peak hours|rush hour|off hours|after hours)\b",
                "type": "traffic_business_context",
                "confidence": 0.8
            }
        ]
    
    def _build_timezone_patterns(self) -> Dict[str, str]:
        """Build timezone detection patterns.
        
        Returns:
            Dictionary mapping timezone patterns to timezone names
        """
        return {
            r"\b(EST|Eastern|ET)\b": "US/Eastern",
            r"\b(CST|Central|CT)\b": "US/Central",
            r"\b(MST|Mountain|MT)\b": "US/Mountain",
            r"\b(PST|Pacific|PT)\b": "US/Pacific",
            r"\b(UTC|GMT)\b": "UTC",
            r"\b(EDT)\b": "US/Eastern",  # Eastern Daylight Time
            r"\b(CDT)\b": "US/Central",  # Central Daylight Time
            r"\b(MDT)\b": "US/Mountain", # Mountain Daylight Time
            r"\b(PDT)\b": "US/Pacific",  # Pacific Daylight Time
            r"\bUTC([+-]\d{1,2})\b": "UTC{offset}"  # UTC offset format
        }
    
    def _build_month_names(self) -> Dict[str, int]:
        """Build month name to number mapping.
        
        Returns:
            Dictionary mapping month names to numbers
        """
        months = {}
        for i, name in enumerate(calendar.month_name[1:], 1):
            months[name.lower()] = i
            months[name[:3].lower()] = i  # Abbreviated
        return months
    
    def _build_day_names(self) -> Dict[str, int]:
        """Build day name to weekday number mapping.
        
        Returns:
            Dictionary mapping day names to weekday numbers (0=Monday)
        """
        days = {}
        for i, name in enumerate(calendar.day_name):
            days[name.lower()] = i
            days[name[:3].lower()] = i  # Abbreviated
        return days
    
    def _build_date_formats(self) -> List[str]:
        """Build common date format strings for parsing.
        
        Returns:
            List of date format strings
        """
        return [
            "%Y-%m-%d",        # 2024-03-15
            "%m/%d/%Y",        # 03/15/2024
            "%d/%m/%Y",        # 15/03/2024
            "%m/%d/%y",        # 03/15/24
            "%d/%m/%y",        # 15/03/24
            "%Y%m%d",          # 20240315
            "%B %d, %Y",       # March 15, 2024
            "%b %d, %Y",       # Mar 15, 2024
            "%d %B %Y",        # 15 March 2024
            "%d %b %Y",        # 15 Mar 2024
            "%B %d",           # March 15 (current year)
            "%b %d",           # Mar 15 (current year)
            "%m-%d",           # 03-15 (current year)
        ]
    
    def extract_temporal(
        self,
        text: str,
        context_datetime: Optional[datetime] = None,
        timezone: Optional[str] = None
    ) -> TemporalExtractionResult:
        """Extract temporal expressions from text with comprehensive parsing.
        
        Args:
            text: Input text containing temporal expressions
            context_datetime: Reference datetime for relative calculations
            timezone: Target timezone for extractions
            
        Returns:
            Complete temporal extraction result
        """
        self.logger.debug("Starting temporal extraction")
        
        # Set context datetime and timezone
        if context_datetime is None:
            context_datetime = datetime.now()
        
        target_timezone = timezone or self.default_timezone
        
        # Normalize text for processing
        normalized_text = self._normalize_text(text)
        
        # Detect timezone from text
        detected_timezone = self._detect_timezone(normalized_text)
        if detected_timezone:
            target_timezone = detected_timezone
        
        # Extract different types of temporal expressions
        extractions = []
        
        # Extract relative dates
        relative_extractions = self._extract_relative_dates(
            normalized_text, context_datetime
        )
        extractions.extend(relative_extractions)
        
        # Extract absolute dates
        absolute_extractions = self._extract_absolute_dates(
            normalized_text, context_datetime
        )
        extractions.extend(absolute_extractions)
        
        # Extract times
        time_extractions = self._extract_times(normalized_text)
        extractions.extend(time_extractions)
        
        # Extract durations
        duration_extractions = self._extract_durations(normalized_text)
        extractions.extend(duration_extractions)
        
        # Extract recurring patterns
        recurring_extractions = self._extract_recurring_patterns(
            normalized_text, context_datetime
        )
        extractions.extend(recurring_extractions)
        
        # Extract contextual expressions
        contextual_extractions = self._extract_contextual_expressions(
            normalized_text, context_datetime
        )
        extractions.extend(contextual_extractions)
        
        # Combine date and time extractions
        combined_extractions = self._combine_date_time_extractions(extractions)
        
        # Apply timezone information
        final_extractions = self._apply_timezone_info(
            combined_extractions, target_timezone
        )
        
        # Select primary extraction
        primary_extraction = self._select_primary_extraction(final_extractions)
        
        # Calculate overall confidence
        extraction_confidence = self._calculate_extraction_confidence(
            final_extractions, primary_extraction
        )
        
        # Generate extraction notes
        extraction_notes = self._generate_extraction_notes(
            text, normalized_text, final_extractions
        )
        
        # Create extraction metadata
        extraction_metadata = self._create_extraction_metadata(
            text, final_extractions, context_datetime
        )
        
        result = TemporalExtractionResult(
            original_text=text,
            extractions=final_extractions,
            primary_extraction=primary_extraction,
            context_datetime=context_datetime,
            default_timezone=target_timezone,
            extraction_confidence=extraction_confidence,
            extraction_notes=extraction_notes,
            extraction_metadata=extraction_metadata
        )
        
        self.logger.info(
            f"Temporal extraction complete: found {len(final_extractions)} expressions, "
            f"confidence={extraction_confidence:.2f}"
        )
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for temporal processing.
        
        Args:
            text: Raw input text
            
        Returns:
            Normalized text
        """
        # Convert to lowercase for pattern matching
        normalized = text.lower()
        
        # Standardize common variations
        replacements = {
            r"\btmrw\b": "tomorrow",
            r"\btdy\b": "today",
            r"\bystrdy\b": "yesterday",
            r"\bweekend\b": "saturday sunday",
            r"\bwknd\b": "weekend",
            r"\b(\d+)([ap])m\b": r"\1 \2m",  # Add space: 3pm -> 3 pm
            r"\b(\d+):(\d+)([ap])m\b": r"\1:\2 \3m",  # Add space: 3:30pm -> 3:30 pm
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _detect_timezone(self, text: str) -> Optional[str]:
        """Detect timezone from text content.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected timezone name or None
        """
        for pattern, timezone_name in self.timezone_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if "{offset}" in timezone_name:
                    offset = match.group(1)
                    return f"UTC{offset}"
                return timezone_name
        
        return None
    
    def _extract_relative_dates(
        self,
        text: str,
        context_datetime: datetime
    ) -> List[TemporalExtraction]:
        """Extract relative date expressions.
        
        Args:
            text: Normalized text
            context_datetime: Reference datetime
            
        Returns:
            List of relative date extractions
        """
        extractions = []
        
        for pattern_config in self.relative_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    delta_func = pattern_config["delta_func"]
                    
                    # Calculate delta (may need the match object)
                    if callable(delta_func):
                        if pattern_config["type"] in ["relative_week", "relative_month"]:
                            delta = delta_func(match)
                        elif pattern_config["type"] in ["future_offset", "past_future_offset"]:
                            delta = delta_func(match)
                        elif pattern_config["type"] == "relative_weekday":
                            delta = delta_func(match)
                        else:
                            delta = delta_func()
                    else:
                        delta = delta_func
                    
                    # Apply delta to context datetime
                    if isinstance(delta, relativedelta.relativedelta):
                        result_datetime = context_datetime + delta
                    else:
                        result_datetime = context_datetime + delta
                    
                    # Determine precision
                    precision = self._determine_precision_from_type(pattern_config["type"])
                    
                    extraction = TemporalExtraction(
                        temporal_type=TemporalType.RELATIVE_DATE,
                        original_text=match.group(0),
                        start_datetime=result_datetime,
                        precision=precision,
                        confidence=pattern_config["confidence"],
                        format_details={
                            "relative_type": pattern_config["type"],
                            "delta": str(delta)
                        }
                    )
                    
                    extractions.append(extraction)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing relative date '{match.group(0)}': {e}")
        
        return extractions
    
    def _extract_absolute_dates(
        self,
        text: str,
        context_datetime: datetime
    ) -> List[TemporalExtraction]:
        """Extract absolute date expressions.
        
        Args:
            text: Normalized text
            context_datetime: Reference datetime for current year assumptions
            
        Returns:
            List of absolute date extractions
        """
        extractions = []
        
        for pattern_config in self.absolute_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    parsed_date = self._parse_absolute_date(
                        match, pattern_config, context_datetime
                    )
                    
                    if parsed_date:
                        extraction = TemporalExtraction(
                            temporal_type=TemporalType.ABSOLUTE_DATE,
                            original_text=match.group(0),
                            start_datetime=parsed_date,
                            precision=TemporalPrecision.DAY,
                            confidence=pattern_config["confidence"],
                            format_details={
                                "date_type": pattern_config["type"],
                                "format": pattern_config.get("format", "parsed")
                            }
                        )
                        
                        extractions.append(extraction)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing absolute date '{match.group(0)}': {e}")
        
        return extractions
    
    def _extract_times(self, text: str) -> List[TemporalExtraction]:
        """Extract time expressions.
        
        Args:
            text: Normalized text
            
        Returns:
            List of time extractions
        """
        extractions = []
        
        for pattern_config in self.time_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    parsed_time = self._parse_time_expression(match, pattern_config)
                    
                    if parsed_time:
                        extraction = TemporalExtraction(
                            temporal_type=TemporalType.TIME_OF_DAY,
                            original_text=match.group(0),
                            start_datetime=parsed_time,
                            precision=self._determine_time_precision(pattern_config["type"]),
                            confidence=pattern_config["confidence"],
                            format_details={
                                "time_type": pattern_config["type"]
                            }
                        )
                        
                        extractions.append(extraction)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing time '{match.group(0)}': {e}")
        
        return extractions
    
    def _extract_durations(self, text: str) -> List[TemporalExtraction]:
        """Extract duration expressions.
        
        Args:
            text: Normalized text
            
        Returns:
            List of duration extractions
        """
        extractions = []
        
        for pattern_config in self.duration_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    duration = self._parse_duration_expression(match, pattern_config)
                    
                    if duration:
                        extraction = TemporalExtraction(
                            temporal_type=TemporalType.DURATION,
                            original_text=match.group(0),
                            start_datetime=None,  # Duration doesn't have fixed start
                            end_datetime=None,
                            precision=self._determine_duration_precision(pattern_config["type"]),
                            confidence=pattern_config["confidence"],
                            format_details={
                                "duration_type": pattern_config["type"],
                                "duration_seconds": duration.total_seconds()
                            }
                        )
                        
                        extractions.append(extraction)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing duration '{match.group(0)}': {e}")
        
        return extractions
    
    def _extract_recurring_patterns(
        self,
        text: str,
        context_datetime: datetime
    ) -> List[TemporalExtraction]:
        """Extract recurring pattern expressions.
        
        Args:
            text: Normalized text
            context_datetime: Reference datetime
            
        Returns:
            List of recurring pattern extractions
        """
        extractions = []
        
        for pattern_config in self.recurring_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    recurrence_info = self._parse_recurrence_pattern(
                        match, pattern_config, context_datetime
                    )
                    
                    if recurrence_info:
                        # Calculate next occurrence
                        next_occurrence = self._calculate_next_occurrence(
                            recurrence_info, context_datetime
                        )
                        
                        extraction = TemporalExtraction(
                            temporal_type=TemporalType.RECURRING,
                            original_text=match.group(0),
                            start_datetime=next_occurrence,
                            precision=TemporalPrecision.DAY,
                            recurrence_info=recurrence_info,
                            confidence=pattern_config["confidence"],
                            format_details={
                                "recurrence_type": pattern_config["type"]
                            }
                        )
                        
                        extractions.append(extraction)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing recurrence '{match.group(0)}': {e}")
        
        return extractions
    
    def _extract_contextual_expressions(
        self,
        text: str,
        context_datetime: datetime
    ) -> List[TemporalExtraction]:
        """Extract contextual temporal expressions.
        
        Args:
            text: Normalized text
            context_datetime: Reference datetime
            
        Returns:
            List of contextual extractions
        """
        extractions = []
        
        for pattern_config in self.contextual_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    contextual_datetime = self._parse_contextual_expression(
                        match, pattern_config, context_datetime
                    )
                    
                    if contextual_datetime:
                        extraction = TemporalExtraction(
                            temporal_type=TemporalType.CONTEXTUAL,
                            original_text=match.group(0),
                            start_datetime=contextual_datetime,
                            precision=self._determine_contextual_precision(pattern_config["type"]),
                            confidence=pattern_config["confidence"],
                            format_details={
                                "contextual_type": pattern_config["type"]
                            }
                        )
                        
                        extractions.append(extraction)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing contextual '{match.group(0)}': {e}")
        
        return extractions
    
    def _parse_offset_delta(
        self,
        amount: str,
        unit: str,
        is_past: bool = False
    ) -> Union[timedelta, relativedelta.relativedelta]:
        """Parse offset delta from amount and unit.
        
        Args:
            amount: Numeric amount
            unit: Time unit
            is_past: Whether this is a past offset
            
        Returns:
            Appropriate delta object
        """
        num = int(amount)
        if is_past:
            num = -num
        
        if unit.startswith("day"):
            return timedelta(days=num)
        elif unit.startswith("week"):
            return timedelta(weeks=num)
        elif unit.startswith("month"):
            return relativedelta.relativedelta(months=num)
        elif unit.startswith("year"):
            return relativedelta.relativedelta(years=num)
        
        return timedelta(days=num)  # Default fallback
    
    def _calculate_weekday_delta(self, weekday_name: str, modifier: str) -> timedelta:
        """Calculate delta to reach specific weekday.
        
        Args:
            weekday_name: Name of target weekday
            modifier: this/next/last modifier
            
        Returns:
            Timedelta to target weekday
        """
        target_weekday = self.day_names.get(weekday_name.lower(), 0)
        current_weekday = datetime.now().weekday()
        
        if modifier == "this":
            # This week - find the day in current week
            days_ahead = target_weekday - current_weekday
            if days_ahead < 0:  # Already passed this week
                days_ahead += 7
        elif modifier == "next":
            # Next occurrence (next week if today is the day)
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
        else:  # "last"
            days_ahead = target_weekday - current_weekday - 7
            if days_ahead >= 0:  # Shouldn't happen for "last"
                days_ahead -= 7
        
        return timedelta(days=days_ahead)
    
    def _parse_absolute_date(
        self,
        match: re.Match,
        pattern_config: Dict[str, Any],
        context_datetime: datetime
    ) -> Optional[datetime]:
        """Parse absolute date from regex match.
        
        Args:
            match: Regex match object
            pattern_config: Pattern configuration
            context_datetime: Context for current year
            
        Returns:
            Parsed datetime or None
        """
        date_type = pattern_config["type"]
        
        try:
            if date_type in ["iso_date", "us_date", "short_date"]:
                # Use format string
                date_format = pattern_config["format"]
                date_str = match.group(0)
                
                # Handle 2-digit years
                if date_type == "short_date":
                    parsed = datetime.strptime(date_str, date_format)
                    # Assume years 70-99 are 1970-1999, 00-69 are 2000-2069
                    if parsed.year < 70:
                        parsed = parsed.replace(year=parsed.year + 2000)
                    elif parsed.year < 100:
                        parsed = parsed.replace(year=parsed.year + 1900)
                    return parsed
                else:
                    return datetime.strptime(date_str, date_format)
            
            elif date_type in ["month_day_year", "day_month_year"]:
                # Named month formats
                if date_type == "month_day_year":
                    month_name, day, year = match.groups()
                else:
                    day, month_name, year = match.groups()
                
                month_num = self.month_names.get(month_name.lower())
                if month_num:
                    return datetime(int(year), month_num, int(day))
            
            elif date_type in ["month_day_current_year", "day_of_month"]:
                # Current year assumed
                if date_type == "month_day_current_year":
                    month_name, day = match.groups()
                else:
                    day, month_name = match.groups()
                
                month_num = self.month_names.get(month_name.lower())
                if month_num:
                    return datetime(context_datetime.year, month_num, int(day))
            
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Error parsing date '{match.group(0)}': {e}")
        
        return None
    
    def _parse_time_expression(
        self,
        match: re.Match,
        pattern_config: Dict[str, Any]
    ) -> Optional[datetime]:
        """Parse time expression from regex match.
        
        Args:
            match: Regex match object
            pattern_config: Pattern configuration
            
        Returns:
            Parsed datetime (date will be today) or None
        """
        time_type = pattern_config["type"]
        today = datetime.now().date()
        
        try:
            if time_type == "12_hour_time":
                hour, minute, second, ampm = match.groups()
                hour = int(hour)
                minute = int(minute)
                second = int(second) if second else 0
                
                # Convert to 24-hour
                if ampm.lower() == "pm" and hour != 12:
                    hour += 12
                elif ampm.lower() == "am" and hour == 12:
                    hour = 0
                
                return datetime.combine(today, time(hour, minute, second))
            
            elif time_type == "24_hour_time":
                hour, minute, second = match.groups()
                hour = int(hour)
                minute = int(minute)
                second = int(second) if second else 0
                
                return datetime.combine(today, time(hour, minute, second))
            
            elif time_type == "hour_only":
                hour, ampm = match.groups()
                hour = int(hour)
                
                # Convert to 24-hour
                if ampm.lower() == "pm" and hour != 12:
                    hour += 12
                elif ampm.lower() == "am" and hour == 12:
                    hour = 0
                
                return datetime.combine(today, time(hour, 0))
            
            elif time_type == "named_time":
                time_name = match.group(1).lower()
                if time_name == "noon":
                    return datetime.combine(today, time(12, 0))
                elif time_name == "midnight":
                    return datetime.combine(today, time(0, 0))
            
            elif time_type == "time_of_day_general":
                time_name = match.group(1).lower()
                time_map = {
                    "morning": time(9, 0),
                    "afternoon": time(14, 0),
                    "evening": time(18, 0),
                    "night": time(21, 0)
                }
                
                if time_name in time_map:
                    return datetime.combine(today, time_map[time_name])
            
            elif time_type == "time_of_day_modified":
                modifier, time_period = match.groups()
                base_times = {
                    "morning": time(9, 0),
                    "afternoon": time(14, 0),
                    "evening": time(18, 0)
                }
                
                if time_period in base_times:
                    base_time = base_times[time_period]
                    if modifier == "early":
                        # 2 hours earlier
                        adjusted_time = (datetime.combine(today, base_time) - 
                                       timedelta(hours=2)).time()
                    else:  # "late"
                        # 2 hours later
                        adjusted_time = (datetime.combine(today, base_time) + 
                                       timedelta(hours=2)).time()
                    
                    return datetime.combine(today, adjusted_time)
            
            elif time_type == "business_time":
                modifier, day_type = match.groups()
                if modifier == "end of":
                    return datetime.combine(today, time(17, 0))  # 5 PM
                else:  # "start of"
                    return datetime.combine(today, time(9, 0))   # 9 AM
        
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Error parsing time '{match.group(0)}': {e}")
        
        return None
    
    def _parse_duration_expression(
        self,
        match: re.Match,
        pattern_config: Dict[str, Any]
    ) -> Optional[timedelta]:
        """Parse duration expression from regex match.
        
        Args:
            match: Regex match object
            pattern_config: Pattern configuration
            
        Returns:
            Parsed timedelta or None
        """
        duration_type = pattern_config["type"]
        
        try:
            if duration_type == "simple_duration":
                amount, unit = match.groups()
                amount = float(amount)
                
                unit_map = {
                    "second": timedelta(seconds=amount),
                    "minute": timedelta(minutes=amount),
                    "hour": timedelta(hours=amount),
                    "day": timedelta(days=amount),
                    "week": timedelta(weeks=amount),
                    "month": timedelta(days=amount * 30),  # Approximate
                    "year": timedelta(days=amount * 365)   # Approximate
                }
                
                return unit_map.get(unit.rstrip('s'))
            
            elif duration_type == "fractional_duration":
                fraction, unit = match.groups()
                multiplier = 0.5 if fraction == "half" else 0.25  # quarter
                
                unit_map = {
                    "hour": timedelta(hours=multiplier),
                    "day": timedelta(days=multiplier),
                    "week": timedelta(weeks=multiplier),
                    "month": timedelta(days=multiplier * 30),
                    "year": timedelta(days=multiplier * 365)
                }
                
                return unit_map.get(unit)
            
            elif duration_type == "named_duration":
                duration_name = match.group(1)
                
                duration_map = {
                    "overnight": timedelta(hours=12),
                    "all day": timedelta(hours=24),
                    "all week": timedelta(weeks=1),
                    "all month": timedelta(days=30)
                }
                
                return duration_map.get(duration_name)
        
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Error parsing duration '{match.group(0)}': {e}")
        
        return None
    
    def _parse_recurrence_pattern(
        self,
        match: re.Match,
        pattern_config: Dict[str, Any],
        context_datetime: datetime
    ) -> Optional[RecurrenceInfo]:
        """Parse recurrence pattern from regex match.
        
        Args:
            match: Regex match object
            pattern_config: Pattern configuration
            context_datetime: Reference datetime
            
        Returns:
            RecurrenceInfo or None
        """
        recurrence_type = pattern_config["type"]
        
        try:
            if recurrence_type == "daily_recurrence":
                pattern_name = match.group(1)
                
                if pattern_name == "day":
                    return RecurrenceInfo(pattern=RecurrencePattern.DAILY)
                elif pattern_name in ["weekday", "business day"]:
                    return RecurrenceInfo(
                        pattern=RecurrencePattern.WEEKLY,
                        days_of_week=[0, 1, 2, 3, 4]  # Monday-Friday
                    )
            
            elif recurrence_type == "weekly_day_recurrence":
                day_name = match.group(1)
                day_num = self.day_names.get(day_name.lower())
                
                if day_num is not None:
                    return RecurrenceInfo(
                        pattern=RecurrencePattern.WEEKLY,
                        days_of_week=[day_num]
                    )
            
            elif recurrence_type == "interval_recurrence":
                frequency, unit = match.groups()
                frequency = int(frequency)
                
                pattern_map = {
                    "day": RecurrencePattern.DAILY,
                    "week": RecurrencePattern.WEEKLY,
                    "month": RecurrencePattern.MONTHLY,
                    "year": RecurrencePattern.YEARLY
                }
                
                pattern = pattern_map.get(unit.rstrip('s'))
                if pattern:
                    return RecurrenceInfo(pattern=pattern, frequency=frequency)
            
            elif recurrence_type == "named_recurrence":
                pattern_name = match.group(1)
                
                pattern_map = {
                    "weekly": RecurrencePattern.WEEKLY,
                    "monthly": RecurrencePattern.MONTHLY,
                    "quarterly": RecurrencePattern.MONTHLY,
                    "annually": RecurrencePattern.YEARLY,
                    "yearly": RecurrencePattern.YEARLY
                }
                
                pattern = pattern_map.get(pattern_name)
                if pattern:
                    frequency = 3 if pattern_name == "quarterly" else 1
                    return RecurrenceInfo(pattern=pattern, frequency=frequency)
        
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Error parsing recurrence '{match.group(0)}': {e}")
        
        return None
    
    def _parse_contextual_expression(
        self,
        match: re.Match,
        pattern_config: Dict[str, Any],
        context_datetime: datetime
    ) -> Optional[datetime]:
        """Parse contextual expression from regex match.
        
        Args:
            match: Regex match object
            pattern_config: Pattern configuration
            context_datetime: Reference datetime
            
        Returns:
            Parsed datetime or None
        """
        contextual_type = pattern_config["type"]
        
        if contextual_type == "immediate":
            # Return current time
            return context_datetime
        
        elif contextual_type == "near_future":
            # Return time in 1-2 hours
            return context_datetime + timedelta(hours=1)
        
        elif contextual_type == "deadline_contextual":
            # End of day/business
            today = context_datetime.date()
            return datetime.combine(today, time(17, 0))  # 5 PM
        
        elif contextual_type == "meal_work_context":
            modifier, context_type = match.groups()
            today = context_datetime.date()
            
            context_times = {
                "breakfast": time(8, 0),
                "lunch": time(12, 0),
                "dinner": time(18, 0),
                "work": time(9, 0),
                "business hours": time(9, 0)
            }
            
            base_time = context_times.get(context_type, time(12, 0))
            base_datetime = datetime.combine(today, base_time)
            
            if modifier == "before":
                return base_datetime - timedelta(hours=1)
            else:  # "after"
                return base_datetime + timedelta(hours=1)
        
        return None
    
    def _calculate_next_occurrence(
        self,
        recurrence_info: RecurrenceInfo,
        context_datetime: datetime
    ) -> datetime:
        """Calculate next occurrence of recurring pattern.
        
        Args:
            recurrence_info: Recurrence pattern information
            context_datetime: Reference datetime
            
        Returns:
            Next occurrence datetime
        """
        if recurrence_info.pattern == RecurrencePattern.DAILY:
            return context_datetime + timedelta(days=recurrence_info.frequency)
        
        elif recurrence_info.pattern == RecurrencePattern.WEEKLY:
            if recurrence_info.days_of_week:
                # Find next occurrence of specified weekday(s)
                current_weekday = context_datetime.weekday()
                
                # Find next matching day
                for days_ahead in range(7):
                    check_date = context_datetime + timedelta(days=days_ahead)
                    if check_date.weekday() in recurrence_info.days_of_week:
                        if days_ahead > 0 or check_date.hour < context_datetime.hour:
                            return check_date.replace(hour=9, minute=0, second=0)
                
                # Fallback to next week
                return context_datetime + timedelta(weeks=recurrence_info.frequency)
            else:
                return context_datetime + timedelta(weeks=recurrence_info.frequency)
        
        elif recurrence_info.pattern == RecurrencePattern.MONTHLY:
            return context_datetime + relativedelta.relativedelta(
                months=recurrence_info.frequency
            )
        
        elif recurrence_info.pattern == RecurrencePattern.YEARLY:
            return context_datetime + relativedelta.relativedelta(
                years=recurrence_info.frequency
            )
        
        # Fallback
        return context_datetime + timedelta(days=1)
    
    def _combine_date_time_extractions(
        self,
        extractions: List[TemporalExtraction]
    ) -> List[TemporalExtraction]:
        """Combine separate date and time extractions into datetime extractions.
        
        Args:
            extractions: List of all extractions
            
        Returns:
            List with combined extractions
        """
        # Group extractions by proximity in original text
        date_extractions = [e for e in extractions 
                           if e.temporal_type == TemporalType.ABSOLUTE_DATE]
        time_extractions = [e for e in extractions 
                           if e.temporal_type == TemporalType.TIME_OF_DAY]
        
        combined = []
        used_time_indices = set()
        
        for date_extraction in date_extractions:
            best_time_extraction = None
            best_time_index = None
            
            # Find closest time extraction in text
            for i, time_extraction in enumerate(time_extractions):
                if i in used_time_indices:
                    continue
                
                # Simple proximity check - could be enhanced
                date_pos = self._find_text_position(date_extraction.original_text)
                time_pos = self._find_text_position(time_extraction.original_text)
                
                if abs(date_pos - time_pos) < 50:  # Within 50 characters
                    best_time_extraction = time_extraction
                    best_time_index = i
                    break
            
            if best_time_extraction and date_extraction.start_datetime:
                # Combine date and time
                date_part = date_extraction.start_datetime.date()
                time_part = best_time_extraction.start_datetime.time()
                
                combined_datetime = datetime.combine(date_part, time_part)
                
                # Create combined extraction
                combined_extraction = TemporalExtraction(
                    temporal_type=TemporalType.ABSOLUTE_DATE,
                    original_text=f"{date_extraction.original_text} {best_time_extraction.original_text}",
                    start_datetime=combined_datetime,
                    precision=TemporalPrecision.MINUTE,
                    confidence=(date_extraction.confidence + best_time_extraction.confidence) / 2,
                    format_details={
                        "combined": True,
                        "date_part": date_extraction.format_details,
                        "time_part": best_time_extraction.format_details
                    }
                )
                
                combined.append(combined_extraction)
                used_time_indices.add(best_time_index)
            else:
                combined.append(date_extraction)
        
        # Add unused time extractions
        for i, time_extraction in enumerate(time_extractions):
            if i not in used_time_indices:
                combined.append(time_extraction)
        
        # Add all other extractions
        other_extractions = [e for e in extractions 
                           if e.temporal_type not in [TemporalType.ABSOLUTE_DATE, 
                                                     TemporalType.TIME_OF_DAY]]
        combined.extend(other_extractions)
        
        return combined
    
    def _find_text_position(self, text: str) -> int:
        """Find approximate position of text in original string.
        
        Args:
            text: Text to find
            
        Returns:
            Approximate position (simplified implementation)
        """
        # This is a simplified implementation
        # In a real scenario, you'd track original positions during extraction
        return len(text)  # Placeholder
    
    def _apply_timezone_info(
        self,
        extractions: List[TemporalExtraction],
        timezone: str
    ) -> List[TemporalExtraction]:
        """Apply timezone information to extractions.
        
        Args:
            extractions: List of extractions
            timezone: Target timezone
            
        Returns:
            List with timezone information applied
        """
        try:
            target_tz = gettz(timezone)
        except Exception:
            target_tz = tzlocal()
        
        for extraction in extractions:
            if extraction.start_datetime:
                # Apply timezone if datetime is naive
                if extraction.start_datetime.tzinfo is None:
                    extraction.start_datetime = extraction.start_datetime.replace(tzinfo=target_tz)
                
                # Create timezone info
                extraction.timezone_info = TimezonInfo(
                    timezone_name=timezone,
                    timezone_offset=extraction.start_datetime.strftime("%z") if extraction.start_datetime.tzinfo else None,
                    detected_from="context"
                )
            
            if extraction.end_datetime:
                if extraction.end_datetime.tzinfo is None:
                    extraction.end_datetime = extraction.end_datetime.replace(tzinfo=target_tz)
        
        return extractions
    
    def _select_primary_extraction(
        self,
        extractions: List[TemporalExtraction]
    ) -> Optional[TemporalExtraction]:
        """Select the primary temporal extraction from multiple candidates.
        
        Args:
            extractions: List of extractions
            
        Returns:
            Primary extraction or None
        """
        if not extractions:
            return None
        
        # Prioritize by type and confidence
        type_priorities = {
            TemporalType.ABSOLUTE_DATE: 10,
            TemporalType.RELATIVE_DATE: 9,
            TemporalType.RECURRING: 8,
            TemporalType.TIME_OF_DAY: 7,
            TemporalType.CONTEXTUAL: 6,
            TemporalType.DURATION: 5,
            TemporalType.DATE_RANGE: 4,
            TemporalType.UNKNOWN: 1
        }
        
        # Score each extraction
        scored_extractions = []
        for extraction in extractions:
            type_score = type_priorities.get(extraction.temporal_type, 1)
            total_score = (type_score * 10) + (extraction.confidence * 100)
            scored_extractions.append((total_score, extraction))
        
        # Return highest scoring extraction
        scored_extractions.sort(key=lambda x: x[0], reverse=True)
        return scored_extractions[0][1]
    
    def _calculate_extraction_confidence(
        self,
        extractions: List[TemporalExtraction],
        primary_extraction: Optional[TemporalExtraction]
    ) -> float:
        """Calculate overall extraction confidence.
        
        Args:
            extractions: All extractions
            primary_extraction: Primary extraction
            
        Returns:
            Overall confidence score
        """
        if not extractions:
            return 0.0
        
        if primary_extraction:
            base_confidence = primary_extraction.confidence
        else:
            base_confidence = sum(e.confidence for e in extractions) / len(extractions)
        
        # Adjust based on number of successful extractions
        extraction_bonus = min(0.1, len(extractions) * 0.02)
        
        return min(1.0, base_confidence + extraction_bonus)
    
    def _determine_precision_from_type(self, relative_type: str) -> TemporalPrecision:
        """Determine precision from relative date type.
        
        Args:
            relative_type: Type of relative expression
            
        Returns:
            Appropriate precision level
        """
        precision_map = {
            "same_day": TemporalPrecision.DAY,
            "next_day": TemporalPrecision.DAY,
            "previous_day": TemporalPrecision.DAY,
            "relative_week": TemporalPrecision.DAY,
            "relative_month": TemporalPrecision.MONTH,
            "future_offset": TemporalPrecision.DAY,
            "past_future_offset": TemporalPrecision.DAY,
            "relative_weekday": TemporalPrecision.DAY
        }
        
        return precision_map.get(relative_type, TemporalPrecision.DAY)
    
    def _determine_time_precision(self, time_type: str) -> TemporalPrecision:
        """Determine precision from time type.
        
        Args:
            time_type: Type of time expression
            
        Returns:
            Appropriate precision level
        """
        precision_map = {
            "12_hour_time": TemporalPrecision.MINUTE,
            "24_hour_time": TemporalPrecision.MINUTE,
            "hour_only": TemporalPrecision.HOUR,
            "named_time": TemporalPrecision.MINUTE,
            "time_of_day_general": TemporalPrecision.HOUR,
            "time_of_day_modified": TemporalPrecision.HOUR,
            "business_time": TemporalPrecision.HOUR
        }
        
        return precision_map.get(time_type, TemporalPrecision.HOUR)
    
    def _determine_duration_precision(self, duration_type: str) -> TemporalPrecision:
        """Determine precision from duration type.
        
        Args:
            duration_type: Type of duration expression
            
        Returns:
            Appropriate precision level
        """
        # Duration precision based on the smallest unit mentioned
        return TemporalPrecision.MINUTE  # Default for durations
    
    def _determine_contextual_precision(self, contextual_type: str) -> TemporalPrecision:
        """Determine precision from contextual type.
        
        Args:
            contextual_type: Type of contextual expression
            
        Returns:
            Appropriate precision level
        """
        precision_map = {
            "immediate": TemporalPrecision.MINUTE,
            "near_future": TemporalPrecision.HOUR,
            "deadline_contextual": TemporalPrecision.HOUR,
            "meal_work_context": TemporalPrecision.HOUR
        }
        
        return precision_map.get(contextual_type, TemporalPrecision.HOUR)
    
    def _generate_extraction_notes(
        self,
        original_text: str,
        normalized_text: str,
        extractions: List[TemporalExtraction]
    ) -> List[str]:
        """Generate notes about the extraction process.
        
        Args:
            original_text: Original input text
            normalized_text: Normalized text
            extractions: List of extractions
            
        Returns:
            List of extraction notes
        """
        notes = []
        
        # Text processing notes
        if original_text.lower() != normalized_text:
            notes.append("Text was normalized for processing")
        
        # Extraction results summary
        if not extractions:
            notes.append("No temporal expressions found")
        else:
            type_counts = {}
            for extraction in extractions:
                type_name = extraction.temporal_type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            type_summary = ", ".join([f"{count} {type_name}" 
                                    for type_name, count in type_counts.items()])
            notes.append(f"Found temporal expressions: {type_summary}")
        
        # Confidence and quality notes
        if extractions:
            avg_confidence = sum(e.confidence for e in extractions) / len(extractions)
            if avg_confidence < 0.7:
                notes.append("Low confidence in some extractions")
            
            # Check for ambiguous dates
            ambiguous_count = sum(1 for e in extractions 
                                if any("ambiguous" in note.lower() 
                                      for note in e.extraction_notes))
            if ambiguous_count > 0:
                notes.append(f"{ambiguous_count} potentially ambiguous temporal expressions")
        
        return notes
    
    def _create_extraction_metadata(
        self,
        original_text: str,
        extractions: List[TemporalExtraction],
        context_datetime: datetime
    ) -> Dict[str, Any]:
        """Create metadata about the extraction process.
        
        Args:
            original_text: Original input text
            extractions: List of extractions
            context_datetime: Reference datetime
            
        Returns:
            Extraction metadata dictionary
        """
        return {
            "original_length": len(original_text),
            "extraction_count": len(extractions),
            "extraction_types": list(set(e.temporal_type.value for e in extractions)),
            "has_absolute_dates": any(e.temporal_type == TemporalType.ABSOLUTE_DATE 
                                   for e in extractions),
            "has_relative_dates": any(e.temporal_type == TemporalType.RELATIVE_DATE 
                                   for e in extractions),
            "has_times": any(e.temporal_type == TemporalType.TIME_OF_DAY 
                           for e in extractions),
            "has_recurring": any(e.temporal_type == TemporalType.RECURRING 
                               for e in extractions),
            "highest_confidence": max((e.confidence for e in extractions), default=0.0),
            "lowest_confidence": min((e.confidence for e in extractions), default=0.0),
            "timezone_detected": any(e.timezone_info for e in extractions),
            "context_datetime": context_datetime.isoformat(),
            "processing_timestamp": datetime.now().isoformat()
        }