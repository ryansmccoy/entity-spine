"""
Data Quality and Validation Service for EntitySpine.

This module provides:
1. Data validation rules
2. Dirty data detection and cleansing
3. Identifier format validation
4. Name standardization
5. Completeness checking

Design Principles:
- Validation rules are configurable
- Non-destructive: original data preserved
- Clear error messages with fix suggestions
- Batch processing support
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from re import Pattern
from typing import Any

from entityspine.domain import Entity, IdentifierClaim, IdentifierScheme

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION TYPES
# =============================================================================

class ValidationSeverity(Enum):
    """Severity of validation issues."""
    ERROR = "error"        # Data cannot be used as-is
    WARNING = "warning"    # Data usable but has issues
    INFO = "info"          # Informational, no action needed


class ValidationCategory(Enum):
    """Categories of validation rules."""
    FORMAT = "format"              # Format validation (regex, length, etc.)
    COMPLETENESS = "completeness"  # Missing required data
    CONSISTENCY = "consistency"    # Internal consistency
    TEMPORAL = "temporal"          # Date/time validation
    BUSINESS = "business"          # Business logic rules


@dataclass
class ValidationIssue:
    """A single validation issue."""
    field_name: str
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    current_value: Any = None
    suggested_value: Any = None
    rule_id: str = ""


@dataclass
class ValidationResult:
    """Result of validating an entity or claim."""
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    # Convenience properties
    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)


# =============================================================================
# IDENTIFIER VALIDATION PATTERNS
# =============================================================================

class IdentifierPatterns:
    """Validation patterns for common identifier schemes."""

    # CIK: 10 digits, leading zeros ok
    CIK_PATTERN = re.compile(r'^0*[1-9]\d{0,9}$')

    # LEI: 20 alphanumeric chars, check digit algorithm
    LEI_PATTERN = re.compile(r'^[A-Z0-9]{4}[A-Z0-9]{14}[0-9]{2}$')

    # CUSIP: 9 chars, alphanumeric with check digit
    CUSIP_PATTERN = re.compile(r'^[A-Z0-9]{8}[0-9]$')

    # ISIN: 2 letter country + 9 char NSIN + check
    ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')

    # FIGI: 12 chars starting with BBG or currency pair
    FIGI_PATTERN = re.compile(r'^[A-Z]{3}[A-Z0-9]{9}$')

    # EIN: 9 digits with hyphen after first 2
    EIN_PATTERN = re.compile(r'^\d{2}-?\d{7}$')

    # Ticker: 1-5 uppercase letters, may include dot
    TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}\.?[A-Z]?$')

    @classmethod
    def get_pattern(cls, scheme: IdentifierScheme) -> Pattern | None:
        """Get validation pattern for a scheme."""
        patterns = {
            IdentifierScheme.CIK: cls.CIK_PATTERN,
            IdentifierScheme.LEI: cls.LEI_PATTERN,
            IdentifierScheme.CUSIP: cls.CUSIP_PATTERN,
            IdentifierScheme.ISIN: cls.ISIN_PATTERN,
            IdentifierScheme.FIGI: cls.FIGI_PATTERN,
            IdentifierScheme.EIN: cls.EIN_PATTERN,
            IdentifierScheme.TICKER: cls.TICKER_PATTERN,
        }
        return patterns.get(scheme)


# =============================================================================
# IDENTIFIER VALIDATOR
# =============================================================================

class IdentifierValidator:
    """
    Validates identifier claims.
    
    Checks:
    - Format validation per scheme
    - Length constraints
    - Check digit validation (where applicable)
    - Standardization (uppercase, padding)
    """

    # CIK length limits
    CIK_MIN_LENGTH = 1
    CIK_MAX_LENGTH = 10

    # LEI exact length
    LEI_LENGTH = 20

    # CUSIP exact length
    CUSIP_LENGTH = 9

    def validate(self, claim: IdentifierClaim) -> ValidationResult:
        """Validate an identifier claim."""
        issues = []

        # Scheme-specific validation
        if claim.scheme == IdentifierScheme.CIK:
            issues.extend(self._validate_cik(claim))
        elif claim.scheme == IdentifierScheme.LEI:
            issues.extend(self._validate_lei(claim))
        elif claim.scheme == IdentifierScheme.CUSIP:
            issues.extend(self._validate_cusip(claim))
        elif claim.scheme == IdentifierScheme.ISIN:
            issues.extend(self._validate_isin(claim))
        elif claim.scheme == IdentifierScheme.TICKER:
            issues.extend(self._validate_ticker(claim))
        elif claim.scheme == IdentifierScheme.EIN:
            issues.extend(self._validate_ein(claim))
        else:
            # Generic validation for unknown schemes
            issues.extend(self._validate_generic(claim))

        # Temporal validation
        issues.extend(self._validate_temporal(claim))

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(is_valid=is_valid, issues=issues)

    def _validate_cik(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate CIK format."""
        issues = []
        value = claim.value.strip()

        # Remove leading zeros for validation
        numeric_value = value.lstrip('0') or '0'

        if not value.isdigit():
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="CIK must contain only digits",
                current_value=value,
                rule_id="CIK_NUMERIC",
            ))
        elif len(numeric_value) > self.CIK_MAX_LENGTH:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"CIK exceeds maximum length of {self.CIK_MAX_LENGTH}",
                current_value=value,
                rule_id="CIK_LENGTH",
            ))

        # Check padding recommendation
        if value.isdigit() and len(value) < 10:
            padded = value.zfill(10)
            if padded != value:
                issues.append(ValidationIssue(
                    field_name="value",
                    category=ValidationCategory.FORMAT,
                    severity=ValidationSeverity.INFO,
                    message="CIK should be zero-padded to 10 digits",
                    current_value=value,
                    suggested_value=padded,
                    rule_id="CIK_PADDING",
                ))

        return issues

    def _validate_lei(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate LEI format."""
        issues = []
        value = claim.value.strip().upper()

        if len(value) != self.LEI_LENGTH:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"LEI must be exactly {self.LEI_LENGTH} characters",
                current_value=value,
                rule_id="LEI_LENGTH",
            ))
        elif not IdentifierPatterns.LEI_PATTERN.match(value):
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="LEI format invalid (should be 4 letters/digits + 14 letters/digits + 2 check digits)",
                current_value=value,
                rule_id="LEI_FORMAT",
            ))

        # Check case
        if value != claim.value:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                message="LEI should be uppercase",
                current_value=claim.value,
                suggested_value=value,
                rule_id="LEI_CASE",
            ))

        return issues

    def _validate_cusip(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate CUSIP format."""
        issues = []
        value = claim.value.strip().upper()

        if len(value) != self.CUSIP_LENGTH:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message=f"CUSIP must be exactly {self.CUSIP_LENGTH} characters",
                current_value=value,
                rule_id="CUSIP_LENGTH",
            ))
        elif not IdentifierPatterns.CUSIP_PATTERN.match(value):
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="CUSIP format invalid",
                current_value=value,
                rule_id="CUSIP_FORMAT",
            ))

        return issues

    def _validate_isin(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate ISIN format."""
        issues = []
        value = claim.value.strip().upper()

        if len(value) != 12:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="ISIN must be exactly 12 characters",
                current_value=value,
                rule_id="ISIN_LENGTH",
            ))
        elif not IdentifierPatterns.ISIN_PATTERN.match(value):
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="ISIN format invalid (CC + 9 char NSIN + check digit)",
                current_value=value,
                rule_id="ISIN_FORMAT",
            ))

        return issues

    def _validate_ticker(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate ticker symbol format."""
        issues = []
        value = claim.value.strip().upper()

        if len(value) > 6:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                message="Ticker symbol unusually long",
                current_value=value,
                rule_id="TICKER_LENGTH",
            ))

        # Check scope is provided for tickers
        if not claim.scope:
            issues.append(ValidationIssue(
                field_name="scope",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                message="Ticker should have scope (exchange) specified",
                rule_id="TICKER_SCOPE",
            ))

        return issues

    def _validate_ein(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate EIN format."""
        issues = []
        value = claim.value.strip().replace('-', '')

        if not value.isdigit() or len(value) != 9:
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="EIN must be 9 digits",
                current_value=claim.value,
                rule_id="EIN_FORMAT",
            ))

        # Suggest formatted version
        if value.isdigit() and len(value) == 9:
            formatted = f"{value[:2]}-{value[2:]}"
            if formatted != claim.value:
                issues.append(ValidationIssue(
                    field_name="value",
                    category=ValidationCategory.FORMAT,
                    severity=ValidationSeverity.INFO,
                    message="EIN is typically formatted as XX-XXXXXXX",
                    current_value=claim.value,
                    suggested_value=formatted,
                    rule_id="EIN_FORMATTING",
                ))

        return issues

    def _validate_generic(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Generic validation for unknown schemes."""
        issues = []

        if not claim.value or not claim.value.strip():
            issues.append(ValidationIssue(
                field_name="value",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
                message="Identifier value cannot be empty",
                current_value=claim.value,
                rule_id="VALUE_REQUIRED",
            ))

        return issues

    def _validate_temporal(self, claim: IdentifierClaim) -> list[ValidationIssue]:
        """Validate temporal aspects of a claim."""
        issues = []

        # Check valid_to is after valid_from
        if claim.valid_from and claim.valid_to:
            if claim.valid_to < claim.valid_from:
                issues.append(ValidationIssue(
                    field_name="valid_to",
                    category=ValidationCategory.TEMPORAL,
                    severity=ValidationSeverity.ERROR,
                    message="valid_to cannot be before valid_from",
                    current_value=f"{claim.valid_from} - {claim.valid_to}",
                    rule_id="TEMPORAL_RANGE",
                ))

        return issues


# =============================================================================
# ENTITY VALIDATOR
# =============================================================================

class EntityValidator:
    """
    Validates entity records.
    
    Checks:
    - Required fields
    - Name quality
    - Status validity
    - Redirect consistency
    """

    # Known valid entity types
    VALID_ENTITY_TYPES = {
        "company", "individual", "government", "fund", "trust",
        "partnership", "llc", "subsidiary", "branch", "unknown"
    }

    # Known valid statuses
    VALID_STATUSES = {
        "active", "inactive", "merged", "dissolved", "unknown"
    }

    def validate(self, entity: Entity) -> ValidationResult:
        """Validate an entity."""
        issues = []

        # Required fields
        issues.extend(self._validate_required_fields(entity))

        # Name quality
        issues.extend(self._validate_name(entity))

        # Status
        issues.extend(self._validate_status(entity))

        # Redirect
        issues.extend(self._validate_redirect(entity))

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(is_valid=is_valid, issues=issues)

    def _validate_required_fields(self, entity: Entity) -> list[ValidationIssue]:
        """Check required fields are present."""
        issues = []

        if not entity.entity_id:
            issues.append(ValidationIssue(
                field_name="entity_id",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
                message="Entity ID is required",
                rule_id="ENTITY_ID_REQUIRED",
            ))

        if not entity.primary_name:
            issues.append(ValidationIssue(
                field_name="primary_name",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
                message="Primary name is required",
                rule_id="NAME_REQUIRED",
            ))

        return issues

    def _validate_name(self, entity: Entity) -> list[ValidationIssue]:
        """Validate entity name quality."""
        issues = []
        name = entity.primary_name

        if not name:
            return issues

        # Check for very short names
        if len(name.strip()) < 2:
            issues.append(ValidationIssue(
                field_name="primary_name",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                message="Entity name is very short",
                current_value=name,
                rule_id="NAME_TOO_SHORT",
            ))

        # Check for numeric-only names
        if name.strip().isdigit():
            issues.append(ValidationIssue(
                field_name="primary_name",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                message="Entity name is numeric-only",
                current_value=name,
                rule_id="NAME_NUMERIC",
            ))

        # Check for excessive whitespace
        normalized = ' '.join(name.split())
        if normalized != name:
            issues.append(ValidationIssue(
                field_name="primary_name",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.INFO,
                message="Name contains excessive whitespace",
                current_value=name,
                suggested_value=normalized,
                rule_id="NAME_WHITESPACE",
            ))

        # Check for potential encoding issues
        if any(ord(c) > 127 and ord(c) < 160 for c in name):
            issues.append(ValidationIssue(
                field_name="primary_name",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                message="Name contains potential encoding issues",
                current_value=name,
                rule_id="NAME_ENCODING",
            ))

        return issues

    def _validate_status(self, entity: Entity) -> list[ValidationIssue]:
        """Validate entity status."""
        issues = []

        if entity.status and entity.status.lower() not in self.VALID_STATUSES:
            issues.append(ValidationIssue(
                field_name="status",
                category=ValidationCategory.BUSINESS,
                severity=ValidationSeverity.WARNING,
                message=f"Unknown status value: {entity.status}",
                current_value=entity.status,
                rule_id="STATUS_UNKNOWN",
            ))

        return issues

    def _validate_redirect(self, entity: Entity) -> list[ValidationIssue]:
        """Validate redirect consistency."""
        issues = []

        # If entity is merged, should have redirect_to
        if entity.status and entity.status.lower() == "merged":
            if not entity.redirect_to:
                issues.append(ValidationIssue(
                    field_name="redirect_to",
                    category=ValidationCategory.CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    message="Merged entities must have redirect_to set",
                    rule_id="MERGE_REDIRECT",
                ))

        # If entity has redirect_to, status should be merged
        if entity.redirect_to:
            if not entity.status or entity.status.lower() != "merged":
                issues.append(ValidationIssue(
                    field_name="status",
                    category=ValidationCategory.CONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    message="Entity with redirect_to should have 'merged' status",
                    current_value=entity.status,
                    suggested_value="merged",
                    rule_id="REDIRECT_STATUS",
                ))

        # Redirect should not be self
        if entity.redirect_to and entity.redirect_to == entity.entity_id:
            issues.append(ValidationIssue(
                field_name="redirect_to",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                message="Entity cannot redirect to itself",
                current_value=entity.redirect_to,
                rule_id="SELF_REDIRECT",
            ))

        return issues


# =============================================================================
# DATA CLEANSER
# =============================================================================

@dataclass
class CleansingResult:
    """Result of cleansing an entity or claim."""
    original: Any
    cleansed: Any
    changes: list[str] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        return len(self.changes) > 0


class DataCleanser:
    """
    Cleanses and standardizes data.
    
    Operations:
    - Normalize names
    - Standardize identifiers
    - Fix common issues
    - Remove invalid characters
    """

    def cleanse_entity_name(self, name: str) -> str:
        """Cleanse and normalize an entity name."""
        if not name:
            return name

        # Basic cleansing
        cleansed = name.strip()

        # Normalize whitespace
        cleansed = ' '.join(cleansed.split())

        # Remove common problematic characters
        cleansed = cleansed.replace('\x00', '')  # Null chars
        cleansed = cleansed.replace('\r', ' ')   # Carriage returns
        cleansed = cleansed.replace('\n', ' ')   # Newlines
        cleansed = cleansed.replace('\t', ' ')   # Tabs

        # Re-normalize whitespace after character removal
        cleansed = ' '.join(cleansed.split())

        return cleansed

    def standardize_identifier(self, scheme: IdentifierScheme, value: str) -> str:
        """Standardize an identifier value."""
        if not value:
            return value

        value = value.strip()

        if scheme == IdentifierScheme.CIK:
            # Pad CIK to 10 digits
            if value.isdigit():
                return value.zfill(10)

        elif scheme in (IdentifierScheme.LEI, IdentifierScheme.CUSIP,
                        IdentifierScheme.ISIN, IdentifierScheme.FIGI,
                        IdentifierScheme.TICKER):
            # Uppercase alphabetic identifiers
            return value.upper()

        elif scheme == IdentifierScheme.EIN:
            # Normalize EIN format
            digits_only = ''.join(c for c in value if c.isdigit())
            if len(digits_only) == 9:
                return f"{digits_only[:2]}-{digits_only[2:]}"

        return value


# =============================================================================
# BATCH VALIDATOR
# =============================================================================

@dataclass
class BatchValidationResult:
    """Result of validating a batch of records."""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0

    total_errors: int = 0
    total_warnings: int = 0

    results: list[tuple[str, ValidationResult]] = field(default_factory=list)  # (id, result)

    @property
    def error_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return self.invalid_records / self.total_records


class BatchValidator:
    """
    Validates batches of entities and claims.
    
    Provides summary statistics and filtering.
    """

    def __init__(self):
        self.entity_validator = EntityValidator()
        self.identifier_validator = IdentifierValidator()

    def validate_entities(
        self,
        entities: list[Entity],
    ) -> BatchValidationResult:
        """Validate a batch of entities."""
        result = BatchValidationResult(total_records=len(entities))

        for entity in entities:
            entity_result = self.entity_validator.validate(entity)
            result.results.append((entity.entity_id, entity_result))

            if entity_result.is_valid:
                result.valid_records += 1
            else:
                result.invalid_records += 1

            result.total_errors += len(entity_result.errors)
            result.total_warnings += len(entity_result.warnings)

        return result

    def validate_claims(
        self,
        claims: list[IdentifierClaim],
    ) -> BatchValidationResult:
        """Validate a batch of identifier claims."""
        result = BatchValidationResult(total_records=len(claims))

        for claim in claims:
            claim_result = self.identifier_validator.validate(claim)
            result.results.append((claim.claim_id, claim_result))

            if claim_result.is_valid:
                result.valid_records += 1
            else:
                result.invalid_records += 1

            result.total_errors += len(claim_result.errors)
            result.total_warnings += len(claim_result.warnings)

        return result


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Types
    "ValidationSeverity",
    "ValidationCategory",

    # Models
    "ValidationIssue",
    "ValidationResult",
    "CleansingResult",
    "BatchValidationResult",

    # Services
    "IdentifierPatterns",
    "IdentifierValidator",
    "EntityValidator",
    "DataCleanser",
    "BatchValidator",
]
