"""
Knowledge graph relationship and role enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class RoleType(str, Enum):
    """
    Type of role a person holds at an organization.

    Used in PersonRole edges to represent person ↔ org relationships.
    """

    # C-Suite
    CEO = "ceo"
    CFO = "cfo"
    COO = "coo"
    CTO = "cto"
    CHRO = "chro"
    CIO = "cio"
    CLO = "clo"
    CMO = "cmo"

    # Board
    DIRECTOR = "director"
    CHAIR = "chair"
    VICE_CHAIR = "vice_chair"
    LEAD_DIRECTOR = "lead_director"

    # Officers
    OFFICER = "officer"
    PRESIDENT = "president"
    EVP = "evp"
    SVP = "svp"
    VP = "vp"
    SECRETARY = "secretary"
    TREASURER = "treasurer"
    CONTROLLER = "controller"

    # Compliance/Governance
    SIGNATORY = "signatory"
    PRINCIPAL_ACCOUNTING_OFFICER = "principal_accounting_officer"
    PRINCIPAL_FINANCIAL_OFFICER = "principal_financial_officer"
    PRINCIPAL_EXECUTIVE_OFFICER = "principal_executive_officer"

    # Ownership
    BENEFICIAL_OWNER_10PCT = "beneficial_owner_10pct"
    REPORTING_OWNER = "reporting_owner"
    INSIDER = "insider"

    # External
    AUDITOR = "auditor"
    AUDITOR_PARTNER = "auditor_partner"
    UNDERWRITER = "underwriter"
    UNDERWRITER_CONTACT = "underwriter_contact"
    COUNSEL = "counsel"

    # Other
    EMPLOYEE = "employee"
    CONSULTANT = "consultant"
    OTHER = "other"


class ParticipantType(str, Enum):
    """
    Type of participation in a filing.

    Used in FilingParticipant to represent who appears in filings and how.
    """

    SIGNER = "signer"
    OFFICER = "officer"
    DIRECTOR = "director"
    REPORTING_OWNER = "reporting_owner"
    BENEFICIAL_OWNER = "beneficial_owner"
    AUDITOR = "auditor"
    COUNSEL = "counsel"
    UNDERWRITER = "underwriter"
    CONTACT = "contact"
    MENTIONED = "mentioned"
    OTHER = "other"


class PositionType(str, Enum):
    """
    Type of ownership position.

    Used in OwnershipPosition to categorize holdings.
    """

    BENEFICIAL_OWNER = "beneficial_owner"
    DIRECT_OWNER = "direct_owner"
    INDIRECT_OWNER = "indirect_owner"
    INSTITUTIONAL_HOLDER = "institutional_holder"
    INSIDER = "insider"
    REPORTING_OWNER = "reporting_owner"
    GROUP_MEMBER = "group_member"
    OTHER = "other"


class ClusterRole(str, Enum):
    """
    Role of an entity within a cluster.

    Used for gradual entity consolidation without destructive merges.
    """

    CANONICAL = "canonical"  # The "winner" entity in the cluster
    MEMBER = "member"  # A potential duplicate
    PROVISIONAL = "provisional"  # Unconfirmed membership


class RelationshipType(str, Enum):
    """
    Type of relationship between two nodes.

    Used in EntityRelationship for entity ↔ entity edges,
    and in Relationship for polymorphic NodeRef edges.

    v2.2.4: Extended to support Asset, Contract, Product, Brand, Event nodes.
    """

    # Corporate structure
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"
    AFFILIATE = "affiliate"
    SUCCESSOR = "successor"
    PREDECESSOR = "predecessor"

    # Business relationships
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    VENDOR = "vendor"
    PARTNER = "partner"
    COMPETITOR = "competitor"

    # Financial relationships
    INVESTOR = "investor"
    INVESTEE = "investee"
    LENDER = "lender"
    BORROWER = "borrower"
    GUARANTOR = "guarantor"
    BENEFICIAL_OWNER_OF = "beneficial_owner_of"

    # Service relationships
    AUDITOR = "auditor"
    COUNSEL = "counsel"
    UNDERWRITER = "underwriter"
    ADVISOR = "advisor"

    # Employment/Position
    OFFICER_OF = "officer_of"
    DIRECTOR_OF = "director_of"
    EMPLOYED_BY = "employed_by"

    # Regulatory
    REGULATED_BY = "regulated_by"
    REGULATES = "regulates"  # Inverse

    # Listing
    LISTED_ON = "listed_on"

    # Geographic
    LOCATED_IN = "located_in"
    LOCATED_AT = "located_at"  # More precise than located_in
    INCORPORATED_IN = "incorporated_in"
    HEADQUARTERED_IN = "headquartered_in"

    # =========================================================================
    # Asset relationships (v2.2.4)
    # =========================================================================
    OWNS_ASSET = "owns_asset"  # Entity owns Asset
    OPERATES_ASSET = "operates_asset"  # Entity operates Asset
    LEASES_ASSET = "leases_asset"  # Entity leases Asset

    # =========================================================================
    # Contract relationships (v2.2.4)
    # =========================================================================
    PARTY_TO = "party_to"  # Entity is party to Contract
    COUNTERPARTY_TO = "counterparty_to"  # Entity is counterparty in Contract
    GOVERNS = "governs"  # Contract governs (Asset, Product, etc.)

    # =========================================================================
    # Product relationships (v2.2.4)
    # =========================================================================
    MANUFACTURES = "manufactures"  # Entity manufactures Product
    SELLS = "sells"  # Entity sells Product
    DISTRIBUTES = "distributes"  # Entity distributes Product
    LICENSES_PRODUCT = "licenses_product"  # Entity licenses Product
    DEVELOPS = "develops"  # Entity develops Product

    # =========================================================================
    # Brand relationships (v2.2.4)
    # =========================================================================
    OWNS_BRAND = "owns_brand"  # Entity owns Brand
    LICENSES_BRAND = "licenses_brand"  # Entity licenses Brand
    BRAND_OF = "brand_of"  # Brand applies to Product

    # =========================================================================
    # Event relationships (v2.2.4)
    # =========================================================================
    SUBJECT_OF = "subject_of"  # Entity is subject of Event
    INVOLVED_IN = "involved_in"  # Entity involved in Event
    TRIGGERED_BY = "triggered_by"  # Event triggered by (another Event)
    RESULTED_IN = "resulted_in"  # Event resulted in (another Event)
    ANNOUNCED_BY = "announced_by"  # Event announced by Entity

    # Other
    RELATED_PARTY = "related_party"
    ACQUIRED = "acquired"
    OTHER = "other"
