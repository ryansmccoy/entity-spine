"""
VS Code Copilot Chat domain models (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.3.1 DESIGN:
- ChatWorkspace represents a VS Code workspace with chat sessions
- ChatSession represents a single conversation session
- ChatMessage represents a single message (user or assistant)
- Support for grouping by project → session → message hierarchy
- Hash-based deduplication for feedspine integration
- Provenance tracking (workspace path, session file, timestamps)

Use Cases:
- Ingest VS Code Copilot chat history
- Replay chats in chronological or reverse order
- Deduplicate on incremental feed ingestion
- Extract TODOs and track conversation origins
"""

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256

from entityspine.domain.timestamps import generate_ulid, utc_now

# =============================================================================
# Enums for Chat domain
# =============================================================================

# Note: Using strings instead of Enum for simplicity and JSON serialization
# Could be promoted to entityspine.domain.enums if needed

CHAT_ROLE_USER = "user"
CHAT_ROLE_ASSISTANT = "assistant"
CHAT_ROLE_SYSTEM = "system"


# =============================================================================
# ChatMessage - Single message in a conversation
# =============================================================================


@dataclass(slots=True)
class ChatMessage:
    """
    A single message in a chat session (user prompt or assistant response).
    
    Attributes:
        message_id: Unique identifier (ULID)
        session_id: Parent session this message belongs to
        role: 'user', 'assistant', or 'system'
        content: The message text content
        timestamp: When the message was sent/received
        model_id: The AI model used (e.g., 'claude-sonnet-4-20250514')
        sequence: Order within the session (1-indexed)
        
        # Deduplication
        content_hash: SHA256 of content for deduplication
        
        # Project tagging
        project_tags: List of project tags (e.g., ['capture-spine', 'frontend'])
        tagged_at: When project tags were assigned
        tagged_method: How tags were assigned ('auto', 'llm', 'manual')
        
        # Optional metadata
        tool_calls: List of tool names invoked (for assistant messages)
        tokens_in: Input tokens (if available)
        tokens_out: Output tokens (if available)
        
        # Provenance
        captured_at: When this was ingested into entityspine
    """

    # Identity
    message_id: str = field(default_factory=generate_ulid)
    session_id: str = ""

    # Core content
    role: str = CHAT_ROLE_USER
    content: str = ""
    timestamp: datetime | None = None
    model_id: str | None = None
    sequence: int = 0

    # Deduplication
    content_hash: str = ""

    # Project tagging (v2.3.2)
    project_tags: list[str] = field(default_factory=list)
    tagged_at: datetime | None = None
    tagged_method: str | None = None  # 'auto', 'llm', 'manual'

    # Optional metadata
    tool_calls: list[str] = field(default_factory=list)
    tokens_in: int | None = None
    tokens_out: int | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        """Compute content hash if not provided."""
        if not self.content_hash and self.content:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA256 hash of content for deduplication."""
        payload = f"{self.session_id}|{self.sequence}|{self.role}|{self.content}"
        return sha256(payload.encode()).hexdigest()[:16]

    @property
    def is_user(self) -> bool:
        """True if this is a user message."""
        return self.role == CHAT_ROLE_USER

    @property
    def is_assistant(self) -> bool:
        """True if this is an assistant response."""
        return self.role == CHAT_ROLE_ASSISTANT

    @property
    def preview(self) -> str:
        """First 100 chars of content for display."""
        if len(self.content) <= 100:
            return self.content
        return self.content[:97] + "..."


# =============================================================================
# ChatSession - A conversation session
# =============================================================================


@dataclass(slots=True)
class ChatSession:
    """
    A VS Code Copilot chat session (one conversation).
    
    Attributes:
        session_id: Unique identifier from VS Code (or generated ULID)
        workspace_id: Parent workspace this session belongs to
        project_name: Human-readable project name (derived from workspace path)
        
        # Timestamps
        created_at: When the session was created
        last_message_at: When the last message was sent
        
        # Session metadata
        title: Auto-generated or user-provided title
        message_count: Number of messages in this session
        
        # Project tagging (aggregated from messages)
        project_tags: List of all project tags from messages in this session
        
        # Deduplication
        session_hash: Hash of session metadata for change detection
        
        # Source provenance
        source_file: Path to the original JSON file
        workspace_path: Full path to the VS Code workspace
        
        # Ingestion provenance
        captured_at: When this was ingested into entityspine
    """

    # Identity
    session_id: str = field(default_factory=generate_ulid)
    workspace_id: str = ""
    project_name: str = ""

    # Timestamps
    created_at: datetime | None = None
    last_message_at: datetime | None = None

    # Session metadata
    title: str = ""
    message_count: int = 0

    # Project tagging (v2.3.2 - aggregated from messages)
    project_tags: list[str] = field(default_factory=list)

    # Deduplication
    session_hash: str = ""

    # Source provenance
    source_file: str = ""
    workspace_path: str = ""

    # Ingestion provenance
    captured_at: datetime = field(default_factory=utc_now)

    # Messages (not stored, populated on load)
    messages: list[ChatMessage] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Compute session hash if not provided."""
        if not self.session_hash:
            self.session_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash for change detection."""
        payload = f"{self.session_id}|{self.message_count}|{self.last_message_at}"
        return sha256(payload.encode()).hexdigest()[:16]

    @property
    def duration_minutes(self) -> int | None:
        """Duration of session in minutes (if timestamps available)."""
        if self.created_at and self.last_message_at:
            delta = self.last_message_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_empty(self) -> bool:
        """True if session has no messages."""
        return self.message_count == 0

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to this session."""
        message.session_id = self.session_id
        message.sequence = len(self.messages) + 1
        self.messages.append(message)
        self.message_count = len(self.messages)
        if message.timestamp:
            if not self.created_at or message.timestamp < self.created_at:
                self.created_at = message.timestamp
            if not self.last_message_at or message.timestamp > self.last_message_at:
                self.last_message_at = message.timestamp
        # Aggregate project tags from message
        if message.project_tags:
            self._update_project_tags()
        # Recompute hash
        self.session_hash = self._compute_hash()

    def _update_project_tags(self) -> None:
        """Aggregate unique project tags from all messages."""
        all_tags: set[str] = set()
        for msg in self.messages:
            all_tags.update(msg.project_tags)
        self.project_tags = sorted(all_tags)


# =============================================================================
# ChatWorkspace - A VS Code workspace with chat history
# =============================================================================


@dataclass(slots=True)
class ChatWorkspace:
    """
    A VS Code workspace containing chat sessions.
    
    Attributes:
        workspace_id: Unique identifier (the VS Code storage hash)
        workspace_path: Full filesystem path to the workspace
        project_name: Human-readable name (e.g., 'py-sec-edgar')
        
        # Statistics
        session_count: Number of chat sessions
        total_messages: Total messages across all sessions
        
        # Timestamps
        first_session_at: Earliest session creation
        last_activity_at: Most recent message across all sessions
        
        # Provenance
        storage_path: Path to VS Code's workspaceStorage folder
        captured_at: When this was ingested
    """

    # Identity
    workspace_id: str = ""  # The hash from VS Code storage
    workspace_path: str = ""
    project_name: str = ""

    # Statistics
    session_count: int = 0
    total_messages: int = 0

    # Timestamps
    first_session_at: datetime | None = None
    last_activity_at: datetime | None = None

    # Provenance
    storage_path: str = ""
    captured_at: datetime = field(default_factory=utc_now)

    # Sessions (not stored, populated on load)
    sessions: list[ChatSession] = field(default_factory=list)

    def add_session(self, session: ChatSession) -> None:
        """Add a session to this workspace."""
        session.workspace_id = self.workspace_id
        session.project_name = self.project_name
        self.sessions.append(session)
        self.session_count = len(self.sessions)
        self.total_messages += session.message_count

        # Update timestamps
        if session.created_at:
            if not self.first_session_at or session.created_at < self.first_session_at:
                self.first_session_at = session.created_at
        if session.last_message_at:
            if not self.last_activity_at or session.last_message_at > self.last_activity_at:
                self.last_activity_at = session.last_message_at

    @property
    def sessions_chronological(self) -> list[ChatSession]:
        """Sessions sorted oldest-first."""
        return sorted(self.sessions, key=lambda s: s.created_at or datetime.min)

    @property
    def sessions_reverse(self) -> list[ChatSession]:
        """Sessions sorted newest-first."""
        return sorted(self.sessions, key=lambda s: s.created_at or datetime.min, reverse=True)


# =============================================================================
# Factory functions
# =============================================================================


def create_chat_message(
    content: str,
    role: str = CHAT_ROLE_USER,
    session_id: str = "",
    timestamp: datetime | None = None,
    model_id: str | None = None,
    sequence: int = 0,
) -> ChatMessage:
    """Create a ChatMessage with defaults."""
    return ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        timestamp=timestamp or utc_now(),
        model_id=model_id,
        sequence=sequence,
    )


def create_chat_session(
    session_id: str,
    project_name: str,
    source_file: str = "",
    workspace_path: str = "",
) -> ChatSession:
    """Create a ChatSession with defaults."""
    return ChatSession(
        session_id=session_id,
        project_name=project_name,
        source_file=source_file,
        workspace_path=workspace_path,
    )


def create_chat_workspace(
    workspace_id: str,
    workspace_path: str,
    project_name: str = "",
) -> ChatWorkspace:
    """Create a ChatWorkspace with defaults."""
    if not project_name:
        # Extract project name from path
        project_name = workspace_path.rstrip("/\\").split("/")[-1].split("\\")[-1]

    return ChatWorkspace(
        workspace_id=workspace_id,
        workspace_path=workspace_path,
        project_name=project_name,
    )
