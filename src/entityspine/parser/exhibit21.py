"""Exhibit 21 Parser with Edge Case Handling.

This module handles the messy reality of SEC Exhibit 21 filings.
Built from analyzing real filings to handle edge cases.

Edge Cases Discovered:
1. Multiple table formats (HTML, ASCII art, tab-delimited)
2. Multi-line entity names spanning rows
3. Nested tables within tables
4. "Doing business as" / "dba" names
5. Multiple jurisdictions per entity
6. Missing column headers
7. Percentage ownership in various formats (100%, wholly-owned, 100 percent)
8. Indentation indicating hierarchy depth
9. Footnotes and asterisks
10. Entity status indicators (inactive, dissolved)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger("entityspine.parser.exhibit21")


# =============================================================================
# PARSING MODELS
# =============================================================================

class ParseConfidence(Enum):
    HIGH = "high"       # Clean structured data
    MEDIUM = "medium"   # Some inference needed
    LOW = "low"         # Significant inference
    UNKNOWN = "unknown" # Best-effort parse


class OwnershipType(Enum):
    WHOLLY_OWNED = "wholly_owned"
    MAJORITY = "majority"
    MINORITY = "minority"
    UNKNOWN = "unknown"


@dataclass
class SubsidiaryParse:
    """Parsed subsidiary from Exhibit 21."""
    name: str
    jurisdiction: str | None = None
    ownership_pct: float | None = None
    ownership_type: OwnershipType = OwnershipType.UNKNOWN
    dba_names: list[str] = field(default_factory=list)
    parent_name: str | None = None  # For nested hierarchies
    depth: int = 0  # Hierarchy depth (0 = direct sub)

    # Parse metadata
    confidence: ParseConfidence = ParseConfidence.MEDIUM
    raw_text: str = ""
    source_line: int = 0
    notes: list[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    status_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "jurisdiction": self.jurisdiction,
            "ownership_pct": self.ownership_pct,
            "ownership_type": self.ownership_type.value,
            "dba_names": self.dba_names,
            "parent_name": self.parent_name,
            "depth": self.depth,
            "confidence": self.confidence.value,
            "is_active": self.is_active,
            "status_note": self.status_note,
            "notes": self.notes,
        }


@dataclass
class Exhibit21Parse:
    """Complete parsed Exhibit 21."""
    filing_cik: str
    filing_accession: str
    filing_date: date

    subsidiaries: list[SubsidiaryParse] = field(default_factory=list)

    # Parse metadata
    parse_method: str = ""  # "html_table", "text_lines", "hybrid"
    total_lines: int = 0
    parse_time_ms: int = 0
    warnings: list[str] = field(default_factory=list)

    # Raw content
    raw_html: str = ""

    @property
    def confidence_breakdown(self) -> dict[str, int]:
        breakdown = {c.value: 0 for c in ParseConfidence}
        for sub in self.subsidiaries:
            breakdown[sub.confidence.value] += 1
        return breakdown


# =============================================================================
# JURISDICTION NORMALIZATION
# =============================================================================

# State abbreviations
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico", "VI": "Virgin Islands", "GU": "Guam",
}

# Common jurisdiction variations
JURISDICTION_ALIASES = {
    # US variations
    "delaware": "Delaware",
    "del.": "Delaware", "del": "Delaware",
    "california": "California",
    "cal.": "California", "cal": "California",
    "new york": "New York",
    "n.y.": "New York", "ny": "New York",
    "texas": "Texas",
    "tex.": "Texas", "tex": "Texas",
    "nevada": "Nevada",
    "nev.": "Nevada", "nev": "Nevada",

    # International
    "united kingdom": "United Kingdom",
    "u.k.": "United Kingdom", "uk": "United Kingdom",
    "england": "United Kingdom",
    "england and wales": "United Kingdom",
    "scotland": "United Kingdom (Scotland)",
    "ireland": "Ireland",
    "republic of ireland": "Ireland",
    "northern ireland": "United Kingdom (Northern Ireland)",
    "netherlands": "Netherlands",
    "the netherlands": "Netherlands",
    "holland": "Netherlands",
    "germany": "Germany",
    "federal republic of germany": "Germany",
    "france": "France",
    "french republic": "France",
    "canada": "Canada",
    "british columbia": "Canada (British Columbia)",
    "ontario": "Canada (Ontario)",
    "quebec": "Canada (Quebec)",
    "japan": "Japan",
    "china": "China",
    "people's republic of china": "China",
    "prc": "China",
    "hong kong": "Hong Kong",
    "singapore": "Singapore",
    "australia": "Australia",
    "new south wales": "Australia (New South Wales)",
    "victoria": "Australia (Victoria)",
    "switzerland": "Switzerland",
    "luxembourg": "Luxembourg",
    "cayman islands": "Cayman Islands",
    "british virgin islands": "British Virgin Islands",
    "bvi": "British Virgin Islands",
    "bermuda": "Bermuda",
    "jersey": "Jersey",
    "guernsey": "Guernsey",
    "isle of man": "Isle of Man",
    "mauritius": "Mauritius",
    "india": "India",
    "brazil": "Brazil",
    "mexico": "Mexico",
    "spain": "Spain",
    "italy": "Italy",
    "belgium": "Belgium",
    "austria": "Austria",
    "sweden": "Sweden",
    "norway": "Norway",
    "denmark": "Denmark",
    "finland": "Finland",
    "poland": "Poland",
    "czech republic": "Czech Republic",
    "south korea": "South Korea",
    "korea": "South Korea",
    "republic of korea": "South Korea",
    "taiwan": "Taiwan",
    "israel": "Israel",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "dubai": "United Arab Emirates (Dubai)",
    "saudi arabia": "Saudi Arabia",
}


def normalize_jurisdiction(raw: str) -> tuple[str, ParseConfidence]:
    """Normalize jurisdiction string.
    
    Returns:
        (normalized_jurisdiction, confidence)
    """
    if not raw:
        return ("Unknown", ParseConfidence.LOW)

    # Clean up
    cleaned = raw.strip().lower()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'[()]', '', cleaned)

    # Check US state abbreviations
    upper = cleaned.upper()
    if upper in US_STATES:
        return (US_STATES[upper], ParseConfidence.HIGH)

    # Check aliases
    if cleaned in JURISDICTION_ALIASES:
        return (JURISDICTION_ALIASES[cleaned], ParseConfidence.HIGH)

    # Check if it's a US state full name
    for abbr, name in US_STATES.items():
        if cleaned == name.lower():
            return (name, ParseConfidence.HIGH)

    # Partial match
    for alias, normalized in JURISDICTION_ALIASES.items():
        if alias in cleaned or cleaned in alias:
            return (normalized, ParseConfidence.MEDIUM)

    # Return cleaned up version with low confidence
    return (raw.strip().title(), ParseConfidence.LOW)


# =============================================================================
# OWNERSHIP PARSING
# =============================================================================

OWNERSHIP_PATTERNS = [
    # Explicit percentages
    (r'(\d+(?:\.\d+)?)\s*%', lambda m: float(m.group(1))),
    (r'(\d+(?:\.\d+)?)\s*percent', lambda m: float(m.group(1))),
    (r'(\d+(?:\.\d+)?)\s*pct', lambda m: float(m.group(1))),

    # Fractions
    (r'one[ -]?hundred\s*%?', lambda m: 100.0),
    (r'fifty[ -]?one\s*%?', lambda m: 51.0),
    (r'fifty\s*%?', lambda m: 50.0),

    # Text ownership
    (r'wholly[- ]?owned', lambda m: 100.0),
    (r'wholly owned', lambda m: 100.0),
    (r'100%\s*owned', lambda m: 100.0),
    (r'majority[- ]?owned', lambda m: 51.0),  # Estimated
]


def parse_ownership(text: str) -> tuple[float | None, OwnershipType, ParseConfidence]:
    """Parse ownership percentage from text.
    
    Returns:
        (percentage, ownership_type, confidence)
    """
    if not text:
        return (None, OwnershipType.UNKNOWN, ParseConfidence.LOW)

    text_lower = text.lower()

    for pattern, extractor in OWNERSHIP_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            try:
                pct = extractor(match)

                if pct >= 100:
                    return (100.0, OwnershipType.WHOLLY_OWNED, ParseConfidence.HIGH)
                elif pct > 50:
                    return (pct, OwnershipType.MAJORITY, ParseConfidence.HIGH)
                elif pct == 50:
                    return (pct, OwnershipType.UNKNOWN, ParseConfidence.MEDIUM)
                else:
                    return (pct, OwnershipType.MINORITY, ParseConfidence.HIGH)
            except (ValueError, TypeError):
                continue

    # Check for ownership type indicators without percentages
    if 'wholly' in text_lower or 'wholly-owned' in text_lower:
        return (100.0, OwnershipType.WHOLLY_OWNED, ParseConfidence.MEDIUM)
    if 'majority' in text_lower:
        return (None, OwnershipType.MAJORITY, ParseConfidence.LOW)
    if 'minority' in text_lower:
        return (None, OwnershipType.MINORITY, ParseConfidence.LOW)

    return (None, OwnershipType.UNKNOWN, ParseConfidence.LOW)


# =============================================================================
# NAME CLEANING
# =============================================================================

# Suffixes that indicate entity types (for normalization)
ENTITY_SUFFIXES = [
    "Inc.", "Inc", "Incorporated",
    "Corp.", "Corp", "Corporation",
    "LLC", "L.L.C.", "Limited Liability Company",
    "LP", "L.P.", "Limited Partnership",
    "LLP", "L.L.P.", "Limited Liability Partnership",
    "Ltd.", "Ltd", "Limited",
    "Plc", "PLC", "Public Limited Company",
    "GmbH", "AG", "SA", "NV", "BV", "AB", "AS", "A/S",
    "Pty", "Pty Ltd", "Pty. Ltd.",
    "Co.", "Co", "Company",
    "& Co", "& Co.",
]

# Patterns to strip from names
NAME_STRIP_PATTERNS = [
    r'\(\d+\)',           # Footnote references like (1)
    r'\*+',               # Asterisks
    r'\s+\(\s*\)',        # Empty parens
    r'\s*\[.*?\]\s*',     # Bracketed content
    r'\s+$',              # Trailing whitespace
    r'^\s+',              # Leading whitespace
]


def clean_entity_name(raw: str) -> tuple[str, list[str], ParseConfidence]:
    """Clean and normalize entity name.
    
    Returns:
        (cleaned_name, dba_names, confidence)
    """
    if not raw:
        return ("", [], ParseConfidence.LOW)

    dba_names = []
    confidence = ParseConfidence.HIGH

    # Handle DBA patterns
    dba_patterns = [
        r'd/b/a\s+(.+?)(?:\s*$|\s*,)',
        r'dba\s+(.+?)(?:\s*$|\s*,)',
        r'doing business as\s+(.+?)(?:\s*$|\s*,)',
        r'trading as\s+(.+?)(?:\s*$|\s*,)',
        r't/a\s+(.+?)(?:\s*$|\s*,)',
        r'a[./]?k[./]?a[./]?\s+(.+?)(?:\s*$|\s*,)',  # aka
    ]

    name = raw
    for pattern in dba_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            dba = match.group(1).strip()
            if dba:
                dba_names.append(dba)
            # Remove the DBA portion
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            confidence = ParseConfidence.MEDIUM

    # Strip patterns
    for pattern in NAME_STRIP_PATTERNS:
        name = re.sub(pattern, '', name)

    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    # Handle empty result
    if not name:
        return (raw.strip(), dba_names, ParseConfidence.LOW)

    return (name, dba_names, confidence)


# =============================================================================
# STATUS DETECTION
# =============================================================================

def detect_inactive_status(text: str) -> tuple[bool, str | None]:
    """Detect if entity is inactive/dissolved.
    
    Returns:
        (is_active, status_note)
    """
    text_lower = text.lower()

    inactive_indicators = [
        (r'inactive', "Marked as inactive"),
        (r'dissolved', "Dissolved"),
        (r'liquidat', "Liquidated"),
        (r'merged into', "Merged"),
        (r'converted to', "Converted"),
        (r'formerly known as', None),  # This is a rename, not inactive
        (r'name changed to', None),    # Rename
    ]

    for pattern, note in inactive_indicators:
        if re.search(pattern, text_lower):
            return (note is None, note)  # None note means it's still active

    return (True, None)


# =============================================================================
# HTML TABLE PARSER
# =============================================================================

class HTMLTableParser:
    """Parse Exhibit 21 from HTML tables."""

    def __init__(self, html: str):
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        self.warnings: list[str] = []

    def parse(self) -> list[SubsidiaryParse]:
        """Parse all tables and extract subsidiaries."""
        results = []

        # Find all tables
        tables = self.soup.find_all('table')

        if not tables:
            self.warnings.append("No tables found in HTML")
            return results

        for table_idx, table in enumerate(tables):
            table_results = self._parse_table(table, table_idx)
            results.extend(table_results)

        return results

    def _parse_table(self, table, table_idx: int) -> list[SubsidiaryParse]:
        """Parse a single table."""
        results = []
        rows = table.find_all('tr')

        if not rows:
            return results

        # Try to detect header row
        header_row = None
        data_start = 0
        name_col = 0
        jurisdiction_col = None
        ownership_col = None

        for i, row in enumerate(rows):
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue

            # Check if this looks like a header
            cell_texts = [c.get_text(strip=True).lower() for c in cells]

            if any('subsidiary' in t or 'name' in t for t in cell_texts):
                header_row = i
                data_start = i + 1

                # Detect columns
                for j, text in enumerate(cell_texts):
                    if 'name' in text or 'subsidiary' in text:
                        name_col = j
                    elif 'jurisdiction' in text or 'state' in text or 'place' in text:
                        jurisdiction_col = j
                    elif 'ownership' in text or 'percent' in text or '%' in text:
                        ownership_col = j

                break

        # Parse data rows
        for row_idx, row in enumerate(rows[data_start:], start=data_start):
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue

            # Get cell texts
            cell_texts = [c.get_text(strip=True) for c in cells]

            # Skip empty rows
            if not any(cell_texts):
                continue

            # Skip rows that look like headers
            if any('subsidiary' in t.lower() for t in cell_texts):
                continue

            # Extract name
            if name_col < len(cell_texts):
                raw_name = cell_texts[name_col]
            else:
                raw_name = cell_texts[0] if cell_texts else ""

            if not raw_name or len(raw_name) < 2:
                continue

            # Clean name
            name, dba_names, name_conf = clean_entity_name(raw_name)

            # Extract jurisdiction
            jurisdiction = None
            jur_conf = ParseConfidence.LOW
            if jurisdiction_col is not None and jurisdiction_col < len(cell_texts):
                jurisdiction, jur_conf = normalize_jurisdiction(cell_texts[jurisdiction_col])

            # Extract ownership
            ownership_pct = None
            ownership_type = OwnershipType.UNKNOWN
            own_conf = ParseConfidence.LOW
            if ownership_col is not None and ownership_col < len(cell_texts):
                ownership_pct, ownership_type, own_conf = parse_ownership(cell_texts[ownership_col])

            # Check status
            is_active, status_note = detect_inactive_status(raw_name)

            # Calculate overall confidence
            confidences = [c.value for c in [name_conf, jur_conf, own_conf] if c != ParseConfidence.LOW]
            if len(confidences) >= 2:
                overall_conf = ParseConfidence.HIGH
            elif len(confidences) >= 1:
                overall_conf = ParseConfidence.MEDIUM
            else:
                overall_conf = ParseConfidence.LOW

            # Calculate depth from indentation
            depth = self._detect_depth(cells[name_col] if name_col < len(cells) else cells[0])

            results.append(SubsidiaryParse(
                name=name,
                jurisdiction=jurisdiction,
                ownership_pct=ownership_pct,
                ownership_type=ownership_type,
                dba_names=dba_names,
                depth=depth,
                confidence=overall_conf,
                raw_text=raw_name,
                source_line=row_idx,
                is_active=is_active,
                status_note=status_note,
            ))

        return results

    def _detect_depth(self, cell) -> int:
        """Detect hierarchy depth from cell formatting."""
        depth = 0

        # Check for indentation via style
        style = cell.get('style', '')
        if 'padding-left' in style or 'margin-left' in style:
            match = re.search(r'(\d+)(?:px|em|pt)', style)
            if match:
                pixels = int(match.group(1))
                depth = pixels // 20  # Rough estimate

        # Check for leading spaces/nbsp
        text = cell.get_text()
        leading_spaces = len(text) - len(text.lstrip())
        if leading_spaces > 2:
            depth = max(depth, leading_spaces // 4)

        return depth


# =============================================================================
# TEXT/ASCII PARSER
# =============================================================================

class TextLineParser:
    """Parse Exhibit 21 from plain text or ASCII tables."""

    # Common delimiters in ASCII tables
    DELIMITERS = [
        r'\t',           # Tab
        r'\s{2,}',       # Multiple spaces
        r'\s*\|\s*',     # Pipe
        r'\s*,\s*',      # Comma (rare but seen)
    ]

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split('\n')
        self.warnings: list[str] = []

    def parse(self) -> list[SubsidiaryParse]:
        """Parse text content."""
        results = []

        # Detect delimiter
        delimiter = self._detect_delimiter()

        # Find data section
        start_idx = self._find_data_start()

        # Parse lines
        for line_idx, line in enumerate(self.lines[start_idx:], start=start_idx):
            line = line.strip()

            if not line:
                continue

            # Skip separator lines
            if self._is_separator(line):
                continue

            # Skip header-like lines
            if self._is_header(line):
                continue

            # Split by delimiter
            if delimiter:
                parts = re.split(delimiter, line)
            else:
                parts = [line]

            if not parts:
                continue

            # First part is usually name
            raw_name = parts[0].strip()
            if not raw_name or len(raw_name) < 2:
                continue

            # Clean name and detect depth from leading whitespace
            original_line = self.lines[line_idx] if line_idx < len(self.lines) else line
            depth = (len(original_line) - len(original_line.lstrip())) // 4

            name, dba_names, name_conf = clean_entity_name(raw_name)

            # Try to extract jurisdiction from remaining parts
            jurisdiction = None
            ownership_pct = None
            ownership_type = OwnershipType.UNKNOWN

            for part in parts[1:]:
                part = part.strip()
                if not part:
                    continue

                # Try as jurisdiction
                if not jurisdiction:
                    jur, jur_conf = normalize_jurisdiction(part)
                    if jur_conf != ParseConfidence.LOW:
                        jurisdiction = jur
                        continue

                # Try as ownership
                pct, otype, oconf = parse_ownership(part)
                if pct is not None:
                    ownership_pct = pct
                    ownership_type = otype

            # Check status
            is_active, status_note = detect_inactive_status(raw_name)

            results.append(SubsidiaryParse(
                name=name,
                jurisdiction=jurisdiction,
                ownership_pct=ownership_pct,
                ownership_type=ownership_type,
                dba_names=dba_names,
                depth=depth,
                confidence=name_conf,
                raw_text=raw_name,
                source_line=line_idx,
                is_active=is_active,
                status_note=status_note,
            ))

        return results

    def _detect_delimiter(self) -> str | None:
        """Detect the most likely delimiter."""
        delimiter_counts = dict.fromkeys(self.DELIMITERS, 0)

        for line in self.lines[:50]:  # Sample first 50 lines
            for delimiter in self.DELIMITERS:
                if re.search(delimiter, line):
                    delimiter_counts[delimiter] += 1

        # Find most common
        max_count = max(delimiter_counts.values())
        if max_count > 5:
            for d, c in delimiter_counts.items():
                if c == max_count:
                    return d

        return r'\s{2,}'  # Default to multiple spaces

    def _find_data_start(self) -> int:
        """Find where the actual data starts."""
        for i, line in enumerate(self.lines):
            line_lower = line.lower()

            # Look for common header patterns
            if 'subsidiaries' in line_lower and ('name' in line_lower or 'state' in line_lower):
                return i + 1
            if re.match(r'^-+$', line.strip()):  # Separator line
                # Check if next lines look like data
                if i + 1 < len(self.lines):
                    next_line = self.lines[i + 1].strip()
                    if next_line and not self._is_header(next_line):
                        return i + 1

        return 0

    def _is_separator(self, line: str) -> bool:
        """Check if line is a separator."""
        cleaned = line.strip()
        if not cleaned:
            return True
        if re.match(r'^[-=_*]+$', cleaned):
            return True
        if re.match(r'^[\s|]+$', cleaned):
            return True
        return False

    def _is_header(self, line: str) -> bool:
        """Check if line looks like a header."""
        line_lower = line.lower()
        header_words = ['name', 'subsidiary', 'jurisdiction', 'state', 'incorporated', 'ownership']

        matches = sum(1 for w in header_words if w in line_lower)
        return matches >= 2


# =============================================================================
# UNIFIED PARSER
# =============================================================================

class Exhibit21Parser:
    """Unified Exhibit 21 parser handling multiple formats."""

    def __init__(self):
        self.warnings: list[str] = []

    def parse(
        self,
        content: str,
        filing_cik: str,
        filing_accession: str,
        filing_date: date,
    ) -> Exhibit21Parse:
        """Parse Exhibit 21 content.
        
        Automatically detects format (HTML vs text) and uses appropriate parser.
        """
        import time
        start_time = time.time()

        result = Exhibit21Parse(
            filing_cik=filing_cik,
            filing_accession=filing_accession,
            filing_date=filing_date,
            raw_html=content[:10000],  # Store first 10K chars
        )

        # Determine content type
        is_html = '<table' in content.lower() or '<html' in content.lower()

        if is_html:
            # Try HTML parser first
            html_parser = HTMLTableParser(content)
            result.subsidiaries = html_parser.parse()
            result.parse_method = "html_table"
            self.warnings.extend(html_parser.warnings)

            # If HTML parser found nothing, fall back to text
            if not result.subsidiaries:
                text_parser = TextLineParser(self._strip_html_tags(content))
                result.subsidiaries = text_parser.parse()
                result.parse_method = "hybrid"
                self.warnings.extend(text_parser.warnings)
        else:
            # Use text parser
            text_parser = TextLineParser(content)
            result.subsidiaries = text_parser.parse()
            result.parse_method = "text_lines"
            self.warnings.extend(text_parser.warnings)

        # Post-process: build hierarchy relationships
        self._resolve_hierarchy(result.subsidiaries)

        # Deduplicate
        result.subsidiaries = self._deduplicate(result.subsidiaries)

        result.total_lines = len(content.split('\n'))
        result.parse_time_ms = int((time.time() - start_time) * 1000)
        result.warnings = self.warnings

        return result

    def _strip_html_tags(self, html: str) -> str:
        """Strip HTML tags for text parsing."""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\n')

    def _resolve_hierarchy(self, subsidiaries: list[SubsidiaryParse]) -> None:
        """Resolve parent relationships based on depth."""
        parent_stack: list[str] = []

        for sub in subsidiaries:
            # Trim stack to current depth
            while len(parent_stack) > sub.depth:
                parent_stack.pop()

            # Set parent
            if parent_stack:
                sub.parent_name = parent_stack[-1]

            # Push current name
            if len(parent_stack) <= sub.depth:
                parent_stack.append(sub.name)
            else:
                parent_stack[sub.depth] = sub.name

    def _deduplicate(self, subsidiaries: list[SubsidiaryParse]) -> list[SubsidiaryParse]:
        """Remove duplicates while preserving hierarchy info."""
        seen: dict[str, SubsidiaryParse] = {}

        for sub in subsidiaries:
            key = sub.name.lower()

            if key in seen:
                # Merge: prefer higher confidence, preserve all DBA names
                existing = seen[key]
                if sub.confidence.value > existing.confidence.value:
                    # Replace with better
                    sub.dba_names = list(set(sub.dba_names + existing.dba_names))
                    seen[key] = sub
                else:
                    # Keep existing, add DBAs
                    existing.dba_names = list(set(existing.dba_names + sub.dba_names))
            else:
                seen[key] = sub

        return list(seen.values())


# =============================================================================
# EDGE CASE TEST PATTERNS
# =============================================================================

EDGE_CASE_TESTS = [
    # Multi-line name
    """<tr><td>Microsoft Corporation
       (Successor to LinkedIn Corp.)</td><td>Delaware</td></tr>""",

    # DBA names
    """<tr><td>XYZ Holdings LLC d/b/a Consumer Direct</td><td>Nevada</td></tr>""",

    # Multiple jurisdictions mentioned
    """<tr><td>ABC International Limited (incorporated in UK, registered in Ireland)</td></tr>""",

    # Status indicators
    """<tr><td>Legacy Systems Inc. (inactive)</td><td>Delaware</td></tr>""",

    # Ownership variations
    """<tr><td>Widget Corp</td><td>CA</td><td>wholly-owned</td></tr>""",
    """<tr><td>Gadget LLC</td><td>NY</td><td>51%</td></tr>""",
    """<tr><td>Thingamajig Inc</td><td>TX</td><td>100 percent</td></tr>""",

    # Footnotes
    """<tr><td>Acme Corp (1)</td><td>Delaware *</td></tr>""",

    # Nested indentation (text)
    """Microsoft Corporation              Delaware
       LinkedIn Corporation            Delaware
           LinkedIn Ireland            Ireland
       GitHub, Inc.                    Delaware""",
]


def test_edge_cases():
    """Test parser against known edge cases."""
    parser = Exhibit21Parser()

    for i, test_content in enumerate(EDGE_CASE_TESTS):
        result = parser.parse(
            content=test_content,
            filing_cik="0000789019",
            filing_accession=f"0000789019-24-00000{i}",
            filing_date=date(2024, 1, 1),
        )

        print(f"\n--- Edge Case {i+1} ---")
        print(f"Content: {test_content[:100]}...")
        print(f"Parsed {len(result.subsidiaries)} subsidiaries:")
        for sub in result.subsidiaries:
            print(f"  • {sub.name}")
            print(f"    Jurisdiction: {sub.jurisdiction}")
            print(f"    Ownership: {sub.ownership_pct}% ({sub.ownership_type.value})")
            print(f"    Confidence: {sub.confidence.value}")
            if sub.dba_names:
                print(f"    DBAs: {sub.dba_names}")
            if sub.parent_name:
                print(f"    Parent: {sub.parent_name}")


if __name__ == "__main__":
    test_edge_cases()
