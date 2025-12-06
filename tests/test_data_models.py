"""Unit tests for Luma data models."""

import pytest
from datetime import datetime
from luma_cog.data_models import Subscription, ChannelGroup, LumaConfig


class TestSubscription:
    """Test the Subscription data model."""

    def test_subscription_creation(self):
        """Test creating a subscription instance."""
        subscription = Subscription(
            api_id="test-api-id",
            slug="test-slug",
            name="Test Calendar",
            added_by=123456789,
            added_at="2025-12-06T18:00:00Z",
        )

        assert subscription.api_id == "test-api-id"
        assert subscription.slug == "test-slug"
        assert subscription.name == "Test Calendar"
        assert subscription.added_by == 123456789
        assert subscription.added_at == "2025-12-06T18:00:00Z"

    def test_subscription_from_dict(self):
        """Test creating subscription from dictionary."""
        data = {
            "api_id": "test-api-id",
            "slug": "test-slug",
            "name": "Test Calendar",
            "added_by": 123456789,
            "added_at": "2025-12-06T18:00:00Z",
        }

        subscription = Subscription.from_dict(data)

        assert subscription.api_id == "test-api-id"
        assert subscription.slug == "test-slug"
        assert subscription.name == "Test Calendar"
        assert subscription.added_by == 123456789
        assert subscription.added_at == "2025-12-06T18:00:00Z"

    def test_subscription_to_dict(self):
        """Test converting subscription to dictionary."""
        subscription = Subscription(
            api_id="test-api-id",
            slug="test-slug",
            name="Test Calendar",
            added_by=123456789,
            added_at="2025-12-06T18:00:00Z",
        )

        data = subscription.to_dict()

        assert data == {
            "api_id": "test-api-id",
            "slug": "test-slug",
            "name": "Test Calendar",
            "added_by": 123456789,
            "added_at": "2025-12-06T18:00:00Z",
        }

    def test_subscription_round_trip(self):
        """Test subscription serialization round trip."""
        original = Subscription(
            api_id="test-api-id",
            slug="test-slug",
            name="Test Calendar",
            added_by=123456789,
            added_at="2025-12-06T18:00:00Z",
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = Subscription.from_dict(data)

        assert restored.api_id == original.api_id
        assert restored.slug == original.slug
        assert restored.name == original.name
        assert restored.added_by == original.added_by
        assert restored.added_at == original.added_at

    def test_subscription_required_fields(self):
        """Test that all required fields are present."""
        with pytest.raises(TypeError):
            Subscription()  # Missing required fields

        with pytest.raises(TypeError):
            Subscription(api_id="test")  # Missing other required fields


class TestChannelGroup:
    """Test the ChannelGroup data model."""

    def test_channel_group_creation(self):
        """Test creating a channel group instance."""
        group = ChannelGroup(
            name="test-group",
            channel_id=987654321,
            subscription_ids=["sub1", "sub2"],
            max_events=10,
            created_by=123456789,
            created_at="2025-12-06T18:00:00Z",
        )

        assert group.name == "test-group"
        assert group.channel_id == 987654321
        assert group.subscription_ids == ["sub1", "sub2"]
        assert group.max_events == 10
        assert group.created_by == 123456789
        assert group.created_at == "2025-12-06T18:00:00Z"

    def test_channel_group_from_dict(self):
        """Test creating channel group from dictionary."""
        data = {
            "name": "test-group",
            "channel_id": 987654321,
            "subscription_ids": ["sub1", "sub2"],
            "max_events": 10,
            "created_by": 123456789,
            "created_at": "2025-12-06T18:00:00Z",
        }

        group = ChannelGroup.from_dict(data)

        assert group.name == "test-group"
        assert group.channel_id == 987654321
        assert group.subscription_ids == ["sub1", "sub2"]
        assert group.max_events == 10
        assert group.created_by == 123456789
        assert group.created_at == "2025-12-06T18:00:00Z"

    def test_channel_group_to_dict(self):
        """Test converting channel group to dictionary."""
        group = ChannelGroup(
            name="test-group",
            channel_id=987654321,
            subscription_ids=["sub1", "sub2"],
            max_events=10,
            created_by=123456789,
            created_at="2025-12-06T18:00:00Z",
        )

        data = group.to_dict()

        assert data == {
            "name": "test-group",
            "channel_id": 987654321,
            "subscription_ids": ["sub1", "sub2"],
            "max_events": 10,
            "created_by": 123456789,
            "created_at": "2025-12-06T18:00:00Z",
        }

    def test_channel_group_round_trip(self):
        """Test channel group serialization round trip."""
        original = ChannelGroup(
            name="test-group",
            channel_id=987654321,
            subscription_ids=["sub1", "sub2"],
            max_events=10,
            created_by=123456789,
            created_at="2025-12-06T18:00:00Z",
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = ChannelGroup.from_dict(data)

        assert restored.name == original.name
        assert restored.channel_id == original.channel_id
        assert restored.subscription_ids == original.subscription_ids
        assert restored.max_events == original.max_events
        assert restored.created_by == original.created_by
        assert restored.created_at == original.created_at

    def test_channel_group_empty_subscription_ids(self):
        """Test channel group with empty subscription list."""
        group = ChannelGroup(
            name="empty-group",
            channel_id=987654321,
            subscription_ids=[],  # Empty list
            max_events=5,
            created_by=123456789,
            created_at="2025-12-06T18:00:00Z",
        )

        assert group.subscription_ids == []
        data = group.to_dict()
        assert data["subscription_ids"] == []

    def test_channel_group_multiple_subscriptions(self):
        """Test channel group with multiple subscriptions."""
        subscriptions = [f"sub{i}" for i in range(10)]
        group = ChannelGroup(
            name="multi-group",
            channel_id=987654321,
            subscription_ids=subscriptions,
            max_events=20,
            created_by=123456789,
            created_at="2025-12-06T18:00:00Z",
        )

        assert len(group.subscription_ids) == 10
        assert group.subscription_ids == subscriptions

    def test_channel_group_required_fields(self):
        """Test that all required fields are present."""
        with pytest.raises(TypeError):
            ChannelGroup()  # Missing required fields

        with pytest.raises(TypeError):
            ChannelGroup(name="test")  # Missing other required fields


class TestLumaConfig:
    """Test the LumaConfig data model."""

    def test_luma_config_creation(self):
        """Test creating a Luma config instance."""
        config = LumaConfig(
            subscriptions={"test": {"api_id": "test"}},
            channel_groups={"group1": {"name": "group1"}},
            update_interval_hours=24,
            last_update="2025-12-06T18:00:00Z",
            enabled=True,
        )

        assert config.subscriptions == {"test": {"api_id": "test"}}
        assert config.channel_groups == {"group1": {"name": "group1"}}
        assert config.update_interval_hours == 24
        assert config.last_update == "2025-12-06T18:00:00Z"
        assert config.enabled is True

    def test_luma_config_from_dict(self):
        """Test creating Luma config from dictionary."""
        data = {
            "subscriptions": {"test": {"api_id": "test"}},
            "channel_groups": {"group1": {"name": "group1"}},
            "update_interval_hours": 24,
            "last_update": "2025-12-06T18:00:00Z",
            "enabled": True,
        }

        config = LumaConfig.from_dict(data)

        assert config.subscriptions == {"test": {"api_id": "test"}}
        assert config.channel_groups == {"group1": {"name": "group1"}}
        assert config.update_interval_hours == 24
        assert config.last_update == "2025-12-06T18:00:00Z"
        assert config.enabled is True

    def test_luma_config_to_dict(self):
        """Test converting Luma config to dictionary."""
        config = LumaConfig(
            subscriptions={"test": {"api_id": "test"}},
            channel_groups={"group1": {"name": "group1"}},
            update_interval_hours=24,
            last_update="2025-12-06T18:00:00Z",
            enabled=True,
        )

        data = config.to_dict()

        assert data == {
            "subscriptions": {"test": {"api_id": "test"}},
            "channel_groups": {"group1": {"name": "group1"}},
            "update_interval_hours": 24,
            "last_update": "2025-12-06T18:00:00Z",
            "enabled": True,
        }

    def test_luma_config_round_trip(self):
        """Test Luma config serialization round trip."""
        original = LumaConfig(
            subscriptions={"test": {"api_id": "test"}},
            channel_groups={"group1": {"name": "group1"}},
            update_interval_hours=24,
            last_update="2025-12-06T18:00:00Z",
            enabled=True,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = LumaConfig.from_dict(data)

        assert restored.subscriptions == original.subscriptions
        assert restored.channel_groups == original.channel_groups
        assert restored.update_interval_hours == original.update_interval_hours
        assert restored.last_update == original.last_update
        assert restored.enabled == original.enabled

    def test_luma_config_empty_subscriptions(self):
        """Test Luma config with empty subscriptions."""
        config = LumaConfig(
            subscriptions={},  # Empty
            channel_groups={"group1": {"name": "group1"}},
            update_interval_hours=24,
            last_update="2025-12-06T18:00:00Z",
            enabled=True,
        )

        assert config.subscriptions == {}
        data = config.to_dict()
        assert data["subscriptions"] == {}

    def test_luma_config_none_last_update(self):
        """Test Luma config with None last_update."""
        config = LumaConfig(
            subscriptions={"test": {"api_id": "test"}},
            channel_groups={},
            update_interval_hours=12,
            last_update=None,  # None value
            enabled=False,
        )

        assert config.last_update is None
        data = config.to_dict()
        assert data["last_update"] is None

    def test_luma_config_required_fields(self):
        """Test that all required fields are present."""
        with pytest.raises(TypeError):
            LumaConfig()  # Missing required fields

        with pytest.raises(TypeError):
            LumaConfig(subscriptions={})  # Missing other required fields

    def test_luma_config_different_intervals(self):
        """Test Luma config with different update intervals."""
        intervals = [1, 6, 12, 24, 48, 168]  # 1 hour to 1 week

        for interval in intervals:
            config = LumaConfig(
                subscriptions={},
                channel_groups={},
                update_interval_hours=interval,
                last_update="2025-12-06T18:00:00Z",
                enabled=True,
            )
            assert config.update_interval_hours == interval
