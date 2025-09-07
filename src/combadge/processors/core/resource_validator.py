"""Vehicle ID Validation Processor for Fleet Management

Comprehensive vehicle identification validation including VINs, fleet IDs, 
license plates, and other vehicle identifiers with region-specific validation.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...core.logging_manager import LoggingManager


class ValidationType(Enum):
    """Types of vehicle identification validation."""
    VIN = "vin"                    # Vehicle Identification Number
    FLEET_ID = "fleet_id"          # Internal fleet identifier
    LICENSE_PLATE = "license_plate" # License plate number
    REGISTRATION = "registration"   # Registration number
    ASSET_TAG = "asset_tag"        # Asset tag/number
    UNKNOWN = "unknown"


class ValidationMode(Enum):
    """Validation strictness modes."""
    STRICT = "strict"              # Full validation with all checks
    LENIENT = "lenient"           # Relaxed validation, format warnings only
    FORMAT_ONLY = "format_only"   # Basic format checking only


class ValidationStatus(Enum):
    """Validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    FORMAT_ERROR = "format_error"
    CHECKSUM_FAILED = "checksum_failed"
    REGION_UNKNOWN = "region_unknown"


class Region(Enum):
    """Supported regions for license plate validation."""
    US = "us"
    CANADA = "canada"
    UK = "uk"
    EU = "eu"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Individual validation result."""
    is_valid: bool
    validation_type: ValidationType
    status: ValidationStatus
    confidence: float = 0.0
    error_details: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_value: Optional[str] = None
    region: Optional[Region] = None
    format_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VehicleValidationResult:
    """Complete vehicle validation result."""
    original_input: str
    detected_type: ValidationType
    validation_results: List[ValidationResult] = field(default_factory=list)
    primary_result: Optional[ValidationResult] = None
    validation_confidence: float = 0.0
    validation_notes: List[str] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


class VehicleValidator:
    """Advanced vehicle identification validator."""
    
    def __init__(self):
        """Initialize vehicle validator with patterns and configurations."""
        self.logger = LoggingManager.get_logger(__name__)
        
        # VIN validation patterns and weights
        self.vin_patterns = self._build_vin_patterns()
        
        # Fleet ID patterns
        self.fleet_id_patterns = self._build_fleet_id_patterns()
        
        # License plate patterns by region
        self.license_plate_patterns = self._build_license_plate_patterns()
        
        # VIN check digit weights and transliteration
        self.vin_weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
        self.vin_transliteration = self._build_vin_transliteration()
        
        # Known manufacturer codes
        self.manufacturer_codes = self._build_manufacturer_codes()
        
        # Region detection patterns
        self.region_patterns = self._build_region_patterns()
        
    def _build_vin_patterns(self) -> Dict[str, Any]:
        """Build VIN validation patterns and rules.
        
        Returns:
            Dictionary with VIN validation configuration
        """
        return {
            "basic_format": r"^[A-HJ-NPR-Z0-9]{17}$",
            "excluded_chars": r"[IOQ]",
            "positions": {
                "wmi": (0, 3),      # World Manufacturer Identifier
                "vds": (3, 9),      # Vehicle Descriptor Section
                "check_digit": 8,   # Check digit position
                "model_year": 9,    # Model year position
                "plant_code": 10,   # Manufacturing plant
                "serial": (10, 17)  # Serial number section
            },
            "year_codes": {
                "A": 2010, "B": 2011, "C": 2012, "D": 2013, "E": 2014,
                "F": 2015, "G": 2016, "H": 2017, "J": 2018, "K": 2019,
                "L": 2020, "M": 2021, "N": 2022, "P": 2023, "R": 2024,
                "S": 2025, "T": 2026, "V": 2027, "W": 2028, "X": 2029,
                "Y": 2030, "1": 2001, "2": 2002, "3": 2003, "4": 2004,
                "5": 2005, "6": 2006, "7": 2007, "8": 2008, "9": 2009
            }
        }
    
    def _build_fleet_id_patterns(self) -> List[Dict[str, Any]]:
        """Build fleet ID validation patterns.
        
        Returns:
            List of fleet ID pattern configurations
        """
        return [
            {
                "name": "alpha_numeric",
                "pattern": r"^[A-Z]{2,4}-?\d{3,6}$",
                "description": "Standard fleet ID (ABC-1234)",
                "confidence": 0.9
            },
            {
                "name": "sequential",
                "pattern": r"^[A-Z]*\d{4,8}$",
                "description": "Sequential fleet number",
                "confidence": 0.8
            },
            {
                "name": "department_code",
                "pattern": r"^[A-Z]{2,3}\d{2,3}[A-Z]?\d{2,4}$",
                "description": "Department coded fleet ID",
                "confidence": 0.85
            },
            {
                "name": "location_based",
                "pattern": r"^[A-Z]{2,3}[A-Z]{2,3}\d{3,5}$",
                "description": "Location-based fleet ID",
                "confidence": 0.8
            },
            {
                "name": "uuid_short",
                "pattern": r"^[A-Z0-9]{8,12}$",
                "description": "Short UUID-style fleet ID",
                "confidence": 0.7
            }
        ]
    
    def _build_license_plate_patterns(self) -> Dict[Region, List[Dict[str, Any]]]:
        """Build license plate patterns by region.
        
        Returns:
            Dictionary mapping regions to pattern configurations
        """
        return {
            Region.US: [
                {
                    "name": "standard_us",
                    "pattern": r"^[A-Z0-9]{2,3}\s?[A-Z0-9]{3,4}$",
                    "description": "Standard US format (ABC-1234)",
                    "confidence": 0.9
                },
                {
                    "name": "specialty_us",
                    "pattern": r"^[A-Z]{1,3}\s?\d{2,4}\s?[A-Z]{0,2}$",
                    "description": "US specialty/vanity plates",
                    "confidence": 0.85
                },
                {
                    "name": "commercial_us",
                    "pattern": r"^[A-Z]{2}\s?\d{4,5}$",
                    "description": "US commercial vehicle plates",
                    "confidence": 0.8
                }
            ],
            
            Region.CANADA: [
                {
                    "name": "standard_ca",
                    "pattern": r"^[A-Z]{1,3}\s?\d{2,4}\s?[A-Z]{0,2}$",
                    "description": "Standard Canadian format",
                    "confidence": 0.9
                },
                {
                    "name": "quebec_ca",
                    "pattern": r"^\d{3}\s?[A-Z]{3}$",
                    "description": "Quebec format (123 ABC)",
                    "confidence": 0.95
                }
            ],
            
            Region.UK: [
                {
                    "name": "current_uk",
                    "pattern": r"^[A-Z]{2}\d{2}\s?[A-Z]{3}$",
                    "description": "Current UK format (AB12 CDE)",
                    "confidence": 0.95
                },
                {
                    "name": "prefix_uk",
                    "pattern": r"^[A-Z]\d{1,3}\s?[A-Z]{3}$",
                    "description": "UK prefix format (A123 BCD)",
                    "confidence": 0.9
                },
                {
                    "name": "suffix_uk",
                    "pattern": r"^[A-Z]{3}\s?\d{1,3}[A-Z]$",
                    "description": "UK suffix format (ABC 123D)",
                    "confidence": 0.9
                }
            ],
            
            Region.EU: [
                {
                    "name": "standard_eu",
                    "pattern": r"^[A-Z]{1,3}\s?-?\s?\d{2,4}\s?[A-Z]{1,3}$",
                    "description": "Standard EU format",
                    "confidence": 0.85
                },
                {
                    "name": "german_eu",
                    "pattern": r"^[A-Z]{1,3}\s?-\s?[A-Z]{1,2}\s?\d{1,4}$",
                    "description": "German format (B-MW 123)",
                    "confidence": 0.9
                }
            ]
        }
    
    def _build_vin_transliteration(self) -> Dict[str, int]:
        """Build VIN character to number transliteration for check digit.
        
        Returns:
            Dictionary mapping VIN characters to numeric values
        """
        return {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
            'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
            'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
        }
    
    def _build_manufacturer_codes(self) -> Dict[str, str]:
        """Build known manufacturer WMI codes.
        
        Returns:
            Dictionary mapping WMI codes to manufacturer names
        """
        return {
            "1G1": "Chevrolet (USA)",
            "1G6": "Cadillac (USA)",
            "1GM": "Pontiac (USA)",
            "1GC": "Chevrolet Truck (USA)",
            "2G1": "Chevrolet (Canada)",
            "3G1": "Chevrolet (Mexico)",
            "JHM": "Honda (USA)",
            "JH4": "Acura (USA)",
            "1HG": "Honda (USA)",
            "1FA": "Ford (USA)",
            "1FT": "Ford Truck (USA)",
            "2FA": "Ford (Canada)",
            "WBA": "BMW (Germany)",
            "WDB": "Mercedes-Benz (Germany)",
            "WDD": "Mercedes-Benz (Germany)",
            "WVW": "Volkswagen (Germany)",
            "WAU": "Audi (Germany)",
            "YV1": "Volvo (Sweden)",
            "VF1": "Renault (France)",
            "VF7": "Citroën (France)",
            "SAJ": "Jaguar (UK)",
            "SAL": "Land Rover (UK)"
        }
    
    def _build_region_patterns(self) -> Dict[str, Region]:
        """Build patterns to detect region from context.
        
        Returns:
            Dictionary mapping keywords to regions
        """
        return {
            "usa": Region.US,
            "united states": Region.US,
            "america": Region.US,
            "us": Region.US,
            "canada": Region.CANADA,
            "canadian": Region.CANADA,
            "ontario": Region.CANADA,
            "quebec": Region.CANADA,
            "uk": Region.UK,
            "england": Region.UK,
            "britain": Region.UK,
            "scotland": Region.UK,
            "wales": Region.UK,
            "germany": Region.EU,
            "france": Region.EU,
            "spain": Region.EU,
            "italy": Region.EU,
            "netherlands": Region.EU,
            "belgium": Region.EU,
            "europe": Region.EU,
            "european": Region.EU
        }
    
    def validate_vehicle_id(
        self,
        vehicle_id: str,
        validation_mode: ValidationMode = ValidationMode.STRICT,
        context: Optional[str] = None
    ) -> VehicleValidationResult:
        """Validate vehicle identification with comprehensive checking.
        
        Args:
            vehicle_id: Vehicle identifier to validate
            validation_mode: Validation strictness mode
            context: Optional context for region detection
            
        Returns:
            Complete vehicle validation result
        """
        self.logger.debug(f"Starting validation for vehicle ID: {vehicle_id}")
        
        # Clean and normalize input
        normalized_id = self._normalize_vehicle_id(vehicle_id)
        
        # Detect identification type
        detected_type = self._detect_identification_type(normalized_id)
        
        # Detect region from context if provided
        detected_region = self._detect_region(context) if context else None
        
        # Perform validation based on type
        validation_results = []
        
        if detected_type == ValidationType.VIN:
            result = self._validate_vin(normalized_id, validation_mode)
            validation_results.append(result)
        
        elif detected_type == ValidationType.FLEET_ID:
            result = self._validate_fleet_id(normalized_id, validation_mode)
            validation_results.append(result)
        
        elif detected_type == ValidationType.LICENSE_PLATE:
            result = self._validate_license_plate(
                normalized_id, validation_mode, detected_region
            )
            validation_results.append(result)
        
        else:
            # Try all validation types for unknown format
            validation_results = self._validate_all_types(
                normalized_id, validation_mode, detected_region
            )
        
        # Select primary result
        primary_result = self._select_primary_result(validation_results)
        
        # Calculate overall confidence
        validation_confidence = self._calculate_validation_confidence(
            validation_results, primary_result
        )
        
        # Generate validation notes
        validation_notes = self._generate_validation_notes(
            vehicle_id, normalized_id, detected_type, validation_results
        )
        
        # Create extraction metadata
        extraction_metadata = self._create_extraction_metadata(
            vehicle_id, normalized_id, validation_results
        )
        
        result = VehicleValidationResult(
            original_input=vehicle_id,
            detected_type=detected_type,
            validation_results=validation_results,
            primary_result=primary_result,
            validation_confidence=validation_confidence,
            validation_notes=validation_notes,
            extraction_metadata=extraction_metadata
        )
        
        self.logger.info(
            f"Vehicle validation complete: type={detected_type.value}, "
            f"valid={primary_result.is_valid if primary_result else False}, "
            f"confidence={validation_confidence:.2f}"
        )
        
        return result
    
    def _normalize_vehicle_id(self, vehicle_id: str) -> str:
        """Normalize vehicle ID for validation.
        
        Args:
            vehicle_id: Raw vehicle ID
            
        Returns:
            Normalized vehicle ID
        """
        # Convert to uppercase
        normalized = vehicle_id.upper().strip()
        
        # Remove common separators for initial processing
        normalized = re.sub(r'[-\s_.]', '', normalized)
        
        # Remove any invalid VIN characters
        if len(normalized) == 17:
            normalized = re.sub(r'[IOQ]', '', normalized)
        
        return normalized
    
    def _detect_identification_type(self, vehicle_id: str) -> ValidationType:
        """Detect the type of vehicle identification.
        
        Args:
            vehicle_id: Normalized vehicle ID
            
        Returns:
            Detected identification type
        """
        # Check VIN format (17 characters, no I, O, Q)
        if len(vehicle_id) == 17 and re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vehicle_id):
            return ValidationType.VIN
        
        # Check fleet ID patterns
        for pattern_config in self.fleet_id_patterns:
            # Re-add separators for fleet ID checking
            for separator in ['-', ' ', '']:
                test_id = self._reformat_with_separator(vehicle_id, separator)
                if re.match(pattern_config["pattern"], test_id):
                    return ValidationType.FLEET_ID
        
        # Check license plate patterns (shorter, mixed format)
        if 2 <= len(vehicle_id) <= 10:
            return ValidationType.LICENSE_PLATE
        
        return ValidationType.UNKNOWN
    
    def _reformat_with_separator(self, vehicle_id: str, separator: str) -> str:
        """Reformat vehicle ID with specific separator for pattern matching.
        
        Args:
            vehicle_id: Clean vehicle ID
            separator: Separator to use
            
        Returns:
            Reformatted vehicle ID
        """
        if not separator:
            return vehicle_id
        
        # Common formatting patterns
        if len(vehicle_id) >= 6:
            # Try ABC-123 format
            if vehicle_id[:3].isalpha() and vehicle_id[3:].isdigit():
                return f"{vehicle_id[:3]}{separator}{vehicle_id[3:]}"
        
        return vehicle_id
    
    def _detect_region(self, context: str) -> Optional[Region]:
        """Detect region from context text.
        
        Args:
            context: Context text to analyze
            
        Returns:
            Detected region or None
        """
        if not context:
            return None
        
        context_lower = context.lower()
        
        for keyword, region in self.region_patterns.items():
            if keyword in context_lower:
                return region
        
        return None
    
    def _validate_vin(
        self,
        vin: str,
        validation_mode: ValidationMode
    ) -> ValidationResult:
        """Validate VIN using check digit algorithm.
        
        Args:
            vin: VIN to validate
            validation_mode: Validation mode
            
        Returns:
            VIN validation result
        """
        result = ValidationResult(
            is_valid=True,
            validation_type=ValidationType.VIN,
            status=ValidationStatus.VALID,
            normalized_value=vin
        )
        
        # Basic format check
        if len(vin) != 17:
            result.is_valid = False
            result.status = ValidationStatus.FORMAT_ERROR
            result.error_details.append(f"VIN must be 17 characters, got {len(vin)}")
            return result
        
        # Character validation
        if re.search(r'[IOQ]', vin):
            result.is_valid = False
            result.status = ValidationStatus.FORMAT_ERROR
            result.error_details.append("VIN contains invalid characters (I, O, Q)")
            return result
        
        # Check digit validation (position 8)
        if validation_mode in [ValidationMode.STRICT, ValidationMode.LENIENT]:
            check_digit_valid = self._validate_vin_check_digit(vin)
            if not check_digit_valid:
                if validation_mode == ValidationMode.STRICT:
                    result.is_valid = False
                    result.status = ValidationStatus.CHECKSUM_FAILED
                    result.error_details.append("VIN check digit validation failed")
                else:
                    result.status = ValidationStatus.WARNING
                    result.warnings.append("VIN check digit validation failed")
        
        # Extract and validate components
        wmi = vin[:3]
        model_year_code = vin[9]
        
        # Manufacturer validation
        if wmi in self.manufacturer_codes:
            result.format_details["manufacturer"] = self.manufacturer_codes[wmi]
            result.confidence += 0.2
        else:
            result.warnings.append(f"Unknown manufacturer code: {wmi}")
        
        # Model year validation
        if model_year_code in self.vin_patterns["year_codes"]:
            year = self.vin_patterns["year_codes"][model_year_code]
            result.format_details["model_year"] = year
            
            # Check for reasonable year range
            current_year = datetime.now().year
            if not (1980 <= year <= current_year + 1):
                result.warnings.append(f"Unusual model year: {year}")
            else:
                result.confidence += 0.1
        else:
            result.warnings.append(f"Invalid model year code: {model_year_code}")
        
        # Calculate confidence
        base_confidence = 0.7  # Base for valid format
        if result.status == ValidationStatus.VALID:
            result.confidence = min(1.0, base_confidence + result.confidence)
        else:
            result.confidence = 0.3
        
        return result
    
    def _validate_vin_check_digit(self, vin: str) -> bool:
        """Validate VIN check digit using ISO 3779 algorithm.
        
        Args:
            vin: VIN string
            
        Returns:
            True if check digit is valid
        """
        if len(vin) != 17:
            return False
        
        # Calculate weighted sum
        total = 0
        for i, char in enumerate(vin):
            if i == 8:  # Skip check digit position
                continue
            
            char_value = self.vin_transliteration.get(char, 0)
            weight = self.vin_weights[i]
            total += char_value * weight
        
        # Calculate check digit
        remainder = total % 11
        expected_check = 'X' if remainder == 10 else str(remainder)
        
        return vin[8] == expected_check
    
    def _validate_fleet_id(
        self,
        fleet_id: str,
        validation_mode: ValidationMode
    ) -> ValidationResult:
        """Validate fleet ID against common patterns.
        
        Args:
            fleet_id: Fleet ID to validate
            validation_mode: Validation mode
            
        Returns:
            Fleet ID validation result
        """
        result = ValidationResult(
            is_valid=False,
            validation_type=ValidationType.FLEET_ID,
            status=ValidationStatus.FORMAT_ERROR,
            normalized_value=fleet_id
        )
        
        best_match = None
        best_confidence = 0.0
        
        # Test against all fleet ID patterns
        for pattern_config in self.fleet_id_patterns:
            # Test with different separators
            for separator in ['-', ' ', '']:
                test_id = self._reformat_with_separator(fleet_id, separator)
                
                if re.match(pattern_config["pattern"], test_id):
                    confidence = pattern_config["confidence"]
                    
                    if confidence > best_confidence:
                        best_match = pattern_config
                        best_confidence = confidence
                        result.normalized_value = test_id
        
        if best_match:
            result.is_valid = True
            result.status = ValidationStatus.VALID
            result.confidence = best_confidence
            result.format_details = {
                "pattern": best_match["name"],
                "description": best_match["description"]
            }
        else:
            result.error_details.append("Fleet ID does not match any known patterns")
            result.confidence = 0.1
        
        return result
    
    def _validate_license_plate(
        self,
        plate: str,
        validation_mode: ValidationMode,
        region: Optional[Region] = None
    ) -> ValidationResult:
        """Validate license plate format.
        
        Args:
            plate: License plate to validate
            validation_mode: Validation mode
            region: Target region for validation
            
        Returns:
            License plate validation result
        """
        result = ValidationResult(
            is_valid=False,
            validation_type=ValidationType.LICENSE_PLATE,
            status=ValidationStatus.FORMAT_ERROR,
            normalized_value=plate,
            region=region
        )
        
        # If no region specified, try all regions
        regions_to_test = [region] if region else list(Region)
        regions_to_test = [r for r in regions_to_test if r != Region.UNKNOWN]
        
        best_match = None
        best_confidence = 0.0
        best_region = None
        
        for test_region in regions_to_test:
            if test_region not in self.license_plate_patterns:
                continue
            
            for pattern_config in self.license_plate_patterns[test_region]:
                # Test with different spacing
                for test_plate in [plate, plate.replace(' ', ''), 
                                 self._add_standard_spacing(plate, test_region)]:
                    
                    if re.match(pattern_config["pattern"], test_plate, re.IGNORECASE):
                        confidence = pattern_config["confidence"]
                        
                        # Boost confidence if region was specified
                        if region == test_region:
                            confidence += 0.1
                        
                        if confidence > best_confidence:
                            best_match = pattern_config
                            best_confidence = confidence
                            best_region = test_region
                            result.normalized_value = test_plate
        
        if best_match:
            result.is_valid = True
            result.status = ValidationStatus.VALID
            result.confidence = best_confidence
            result.region = best_region
            result.format_details = {
                "pattern": best_match["name"],
                "description": best_match["description"],
                "region": best_region.value if best_region else None
            }
        else:
            if region:
                result.error_details.append(f"License plate does not match {region.value} patterns")
            else:
                result.error_details.append("License plate does not match any known regional patterns")
            result.confidence = 0.1
        
        return result
    
    def _add_standard_spacing(self, plate: str, region: Region) -> str:
        """Add standard spacing for license plate format.
        
        Args:
            plate: License plate without spacing
            region: Target region
            
        Returns:
            License plate with standard spacing
        """
        if region == Region.UK and len(plate) == 7:
            # UK format: AB12 CDE
            return f"{plate[:4]} {plate[4:]}"
        elif region == Region.CANADA and len(plate) == 6:
            # Quebec format: 123 ABC
            if plate[:3].isdigit() and plate[3:].isalpha():
                return f"{plate[:3]} {plate[3:]}"
        elif region == Region.US and len(plate) in [6, 7]:
            # Common US formats: ABC 1234 or AB 12345
            if len(plate) == 7:
                if plate[:3].isalpha():
                    return f"{plate[:3]} {plate[3:]}"
                elif plate[:2].isalpha():
                    return f"{plate[:2]} {plate[2:]}"
        
        return plate
    
    def _validate_all_types(
        self,
        vehicle_id: str,
        validation_mode: ValidationMode,
        region: Optional[Region] = None
    ) -> List[ValidationResult]:
        """Attempt validation against all identification types.
        
        Args:
            vehicle_id: Vehicle ID to validate
            validation_mode: Validation mode
            region: Optional region for license plates
            
        Returns:
            List of all validation results
        """
        results = []
        
        # Try VIN validation
        if len(vehicle_id) == 17:
            vin_result = self._validate_vin(vehicle_id, validation_mode)
            results.append(vin_result)
        
        # Try fleet ID validation
        fleet_result = self._validate_fleet_id(vehicle_id, validation_mode)
        results.append(fleet_result)
        
        # Try license plate validation
        if len(vehicle_id) <= 10:
            plate_result = self._validate_license_plate(
                vehicle_id, validation_mode, region
            )
            results.append(plate_result)
        
        return results
    
    def _select_primary_result(
        self,
        validation_results: List[ValidationResult]
    ) -> Optional[ValidationResult]:
        """Select the primary validation result from multiple attempts.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Primary result or None
        """
        if not validation_results:
            return None
        
        # Sort by validity and confidence
        valid_results = [r for r in validation_results if r.is_valid]
        
        if valid_results:
            return max(valid_results, key=lambda r: r.confidence)
        else:
            # Return result with highest confidence even if invalid
            return max(validation_results, key=lambda r: r.confidence)
    
    def _calculate_validation_confidence(
        self,
        validation_results: List[ValidationResult],
        primary_result: Optional[ValidationResult]
    ) -> float:
        """Calculate overall validation confidence.
        
        Args:
            validation_results: All validation results
            primary_result: Primary selected result
            
        Returns:
            Overall confidence score
        """
        if not primary_result:
            return 0.0
        
        base_confidence = primary_result.confidence
        
        # Boost confidence if multiple validation types agree
        valid_count = sum(1 for result in validation_results if result.is_valid)
        if valid_count > 1:
            base_confidence += 0.1
        
        # Reduce confidence if there are conflicting results
        if len(validation_results) > 1 and valid_count == 1:
            base_confidence -= 0.05
        
        return min(1.0, max(0.0, base_confidence))
    
    def _generate_validation_notes(
        self,
        original_input: str,
        normalized_input: str,
        detected_type: ValidationType,
        validation_results: List[ValidationResult]
    ) -> List[str]:
        """Generate notes about the validation process.
        
        Args:
            original_input: Original input string
            normalized_input: Normalized input string
            detected_type: Detected identification type
            validation_results: All validation results
            
        Returns:
            List of validation notes
        """
        notes = []
        
        # Input normalization
        if original_input != normalized_input:
            notes.append("Input was normalized for validation")
        
        # Type detection
        if detected_type == ValidationType.UNKNOWN:
            notes.append("Could not determine identification type")
        else:
            notes.append(f"Detected as {detected_type.value}")
        
        # Validation results summary
        valid_results = [r for r in validation_results if r.is_valid]
        if valid_results:
            notes.append(f"Passed {len(valid_results)}/{len(validation_results)} validation tests")
        else:
            notes.append("Failed all validation tests")
        
        # Specific validation issues
        for result in validation_results:
            if result.error_details:
                notes.extend([f"{result.validation_type.value}: {error}" 
                             for error in result.error_details])
            if result.warnings:
                notes.extend([f"{result.validation_type.value} warning: {warning}" 
                             for warning in result.warnings])
        
        return notes
    
    def _create_extraction_metadata(
        self,
        original_input: str,
        normalized_input: str,
        validation_results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """Create metadata about the validation process.
        
        Args:
            original_input: Original input string
            normalized_input: Normalized input string
            validation_results: All validation results
            
        Returns:
            Extraction metadata dictionary
        """
        return {
            "original_length": len(original_input),
            "normalized_length": len(normalized_input),
            "input_changed": original_input != normalized_input,
            "validation_types_tested": [r.validation_type.value for r in validation_results],
            "valid_results_count": sum(1 for r in validation_results if r.is_valid),
            "highest_confidence": max((r.confidence for r in validation_results), default=0.0),
            "regions_tested": list(set(r.region.value for r in validation_results 
                                     if r.region and r.region != Region.UNKNOWN)),
            "has_warnings": any(r.warnings for r in validation_results),
            "has_errors": any(r.error_details for r in validation_results),
            "processing_timestamp": datetime.now().isoformat()
        }