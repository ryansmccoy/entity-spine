"""Tests for Chat domain models."""

import pytest
from datetime import datetime, timezone

from entityspine.domain.chat import (
    CHAT_ROLE_USER,
    CHAT_ROLE_ASSISTANT,
    ChatMessage,
    ChatSession,
    ChatWorkspace,
    create_chat_message,
    create_chat_session,
    create_chat_workspace,
)


class TestChatMessage:
    """Tests for ChatMessage."""

    def test_create_basic_message(self):
        """Test creating a basic message."""
        msg = ChatMessage(
            content="Hello, can you help me?",
            role=CHAT_ROLE_USER,
        )
        assert msg.content == "Hello, can you help me?"
        assert msg.role == CHAT_ROLE_USER
        assert msg.is_user
        assert not msg.is_assistant
        assert msg.content_hash  # Auto-computed

    def test_content_hash_computed(self):
        """Test that content hash is auto-computed."""
        msg1 = ChatMessage(content="Test", session_id="s1", sequence=1)
        msg2 = ChatMessage(content="Test", session_id="s1", sequence=1)
        msg3 = ChatMessage(content="Different", session_id="s1", sequence=1)
        
        assert msg1.content_hash == msg2.content_hash  # Same content
        assert msg1.content_hash != msg3.content_hash  # Different content

    def test_preview_truncation(self):
        """Test preview truncates long content."""
        short = ChatMessage(content="Short message")
        long = ChatMessage(content="A" * 200)
        
        assert short.preview == "Short message"
        assert len(long.preview) == 100
        assert long.preview.endswith("...")

    def test_factory_function(self):
        """Test create_chat_message factory."""
        msg = create_chat_message(
            content="Test content",
            role=CHAT_ROLE_ASSISTANT,
            model_id="claude-sonnet-4-20250514",
        )
        assert msg.content == "Test content"
        assert msg.is_assistant
        assert msg.model_id == "claude-sonnet-4-20250514"


class TestChatSession:
    """Tests for ChatSession."""

    def test_create_basic_session(self):
        """Test creating a basic session."""
        session = ChatSession(
            session_id="sess-123",
            project_name="test-project",
        )
        assert session.session_id == "sess-123"
        assert session.project_name == "test-project"
        assert session.is_empty
        assert session.message_count == 0

    def test_add_message(self):
        """Test adding messages to session."""
        session = ChatSession(session_id="sess-1", project_name="test")
        msg1 = ChatMessage(content="User question", role=CHAT_ROLE_USER)
        msg2 = ChatMessage(content="Assistant answer", role=CHAT_ROLE_ASSISTANT)
        
        session.add_message(msg1)
        session.add_message(msg2)
        
        assert session.message_count == 2
        assert not session.is_empty
        assert msg1.session_id == "sess-1"
        assert msg1.sequence == 1
        assert msg2.sequence == 2

    def test_timestamps_updated(self):
        """Test that timestamps are updated when adding messages."""
        session = ChatSession(session_id="sess-1", project_name="test")
        
        t1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)
        
        msg1 = ChatMessage(content="First", timestamp=t1)
        msg2 = ChatMessage(content="Second", timestamp=t2)
        
        session.add_message(msg1)
        session.add_message(msg2)
        
        assert session.created_at == t1
        assert session.last_message_at == t2
        assert session.duration_minutes == 30

    def test_factory_function(self):
        """Test create_chat_session factory."""
        session = create_chat_session(
            session_id="s1",
            project_name="my-project",
            source_file="/path/to/session.json",
        )
        assert session.session_id == "s1"
        assert session.project_name == "my-project"
        assert session.source_file == "/path/to/session.json"


class TestChatWorkspace:
    """Tests for ChatWorkspace."""

    def test_create_basic_workspace(self):
        """Test creating a basic workspace."""
        ws = ChatWorkspace(
            workspace_id="hash123",
            workspace_path="C:/projects/test",
            project_name="test",
        )
        assert ws.workspace_id == "hash123"
        assert ws.project_name == "test"
        assert ws.session_count == 0

    def test_add_session(self):
        """Test adding sessions to workspace."""
        ws = ChatWorkspace(
            workspace_id="hash123",
            workspace_path="C:/projects/test",
            project_name="test",
        )
        
        session = ChatSession(session_id="s1", project_name="test")
        msg = ChatMessage(content="Test", timestamp=datetime.now(timezone.utc))
        session.add_message(msg)
        
        ws.add_session(session)
        
        assert ws.session_count == 1
        assert ws.total_messages == 1
        assert session.workspace_id == "hash123"

    def test_sessions_chronological(self):
        """Test getting sessions in chronological order."""
        ws = ChatWorkspace(workspace_id="h1", workspace_path="/test", project_name="test")
        
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 1, 2, tzinfo=timezone.utc)
        t3 = datetime(2024, 1, 3, tzinfo=timezone.utc)
        
        s1 = ChatSession(session_id="s1", created_at=t2)
        s2 = ChatSession(session_id="s2", created_at=t1)
        s3 = ChatSession(session_id="s3", created_at=t3)
        
        ws.add_session(s1)
        ws.add_session(s2)
        ws.add_session(s3)
        
        chrono = ws.sessions_chronological
        assert [s.session_id for s in chrono] == ["s2", "s1", "s3"]
        
        reverse = ws.sessions_reverse
        assert [s.session_id for s in reverse] == ["s3", "s1", "s2"]

    def test_factory_function_extracts_name(self):
        """Test that factory extracts project name from path."""
        ws = create_chat_workspace(
            workspace_id="abc",
            workspace_path="C:/projects/my-awesome-project",
        )
        assert ws.project_name == "my-awesome-project"


class TestIntegration:
    """Integration tests for the full hierarchy."""

    def test_full_hierarchy(self):
        """Test building a complete workspace → session → message hierarchy."""
        # Create workspace
        ws = create_chat_workspace("hash123", "C:/projects/py-sec-edgar")
        
        # Create session 1
        s1 = create_chat_session("session-1", "py-sec-edgar")
        s1.add_message(create_chat_message("How do I parse SEC filings?", CHAT_ROLE_USER))
        s1.add_message(create_chat_message("You can use the SEC EDGAR API...", CHAT_ROLE_ASSISTANT))
        
        # Create session 2
        s2 = create_chat_session("session-2", "py-sec-edgar")
        s2.add_message(create_chat_message("What's a 10-K?", CHAT_ROLE_USER))
        s2.add_message(create_chat_message("A 10-K is an annual report...", CHAT_ROLE_ASSISTANT))
        
        # Add to workspace
        ws.add_session(s1)
        ws.add_session(s2)
        
        # Verify hierarchy
        assert ws.session_count == 2
        assert ws.total_messages == 4
        assert ws.project_name == "py-sec-edgar"
        
        # Verify sessions
        assert s1.message_count == 2
        assert s1.workspace_id == "hash123"
        
        # Verify messages
        assert s1.messages[0].is_user
        assert s1.messages[1].is_assistant
        assert s1.messages[0].sequence == 1
        assert s1.messages[1].sequence == 2
