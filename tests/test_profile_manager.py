# ProfileManager unit tests – pure in-memory, no LLM calls
from __future__ import annotations

import pytest

from agent.memory.profile import ProfileManager, UserProfile


class TestProfileManager:
    """Tests for ProfileManager long-term preference storage."""

    def setup_method(self):
        self.pm = ProfileManager()

    # --- get_profile ---

    @pytest.mark.asyncio
    async def test_get_default_profile(self):
        """New user gets a blank UserProfile with empty defaults."""
        profile = await self.pm.get_profile("user-1")
        assert isinstance(profile, UserProfile)
        assert profile.travel_style == []
        assert profile.budget_preference is None
        assert profile.accommodation_pref is None
        assert profile.transport_pref is None
        assert profile.dietary_restrictions == []
        assert profile.visited_destinations == []

    @pytest.mark.asyncio
    async def test_get_profile_returns_same_instance(self):
        """Repeated get for the same user returns the same object."""
        p1 = await self.pm.get_profile("user-1")
        p2 = await self.pm.get_profile("user-1")
        assert p1 is p2

    # --- update_profile ---

    @pytest.mark.asyncio
    async def test_update_profile_scalar(self):
        """Scalar fields are overwritten by update."""
        await self.pm.update_profile("u1", {"budget_preference": "luxury"})
        profile = await self.pm.get_profile("u1")
        assert profile.budget_preference == "luxury"

    @pytest.mark.asyncio
    async def test_update_profile_list_append(self):
        """List fields are appended (not overwritten) and deduplicated."""
        await self.pm.update_profile("u1", {"travel_style": ["adventure"]})
        await self.pm.update_profile("u1", {"travel_style": ["adventure", "foodie"]})

        profile = await self.pm.get_profile("u1")
        assert profile.travel_style == ["adventure", "foodie"]

    @pytest.mark.asyncio
    async def test_update_profile_list_with_string(self):
        """A string value for a list field is appended as a single item."""
        await self.pm.update_profile("u1", {"dietary_restrictions": "vegetarian"})
        profile = await self.pm.get_profile("u1")
        assert "vegetarian" in profile.dietary_restrictions

    @pytest.mark.asyncio
    async def test_update_profile_ignores_none_values(self):
        """None values in updates dict are skipped."""
        await self.pm.update_profile("u1", {"budget_preference": "budget"})
        await self.pm.update_profile("u1", {"budget_preference": None})
        profile = await self.pm.get_profile("u1")
        assert profile.budget_preference == "budget"

    def test_update_profile_ignores_unknown_fields(self):
        """Unknown field names are silently ignored (via hasattr check)."""
        # Validate that UserProfile doesn't have an arbitrary field
        profile = UserProfile()
        assert not hasattr(profile, "unknown_field")

    # --- learn_from_session ---

    @pytest.mark.asyncio
    async def test_learn_from_session_style(self):
        """Detects travel style keywords from user messages."""
        messages = [
            {"role": "user", "content": "我想去冒险，体验刺激的活动"},
            {"role": "assistant", "content": "好的，推荐攀岩"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert "adventure" in profile.travel_style

    @pytest.mark.asyncio
    async def test_learn_from_session_budget(self):
        """Detects budget preference keywords."""
        messages = [
            {"role": "user", "content": "预算有限，想穷游"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert profile.budget_preference == "budget"

    @pytest.mark.asyncio
    async def test_learn_from_session_accommodation(self):
        """Detects accommodation preference keywords."""
        messages = [
            {"role": "user", "content": "我喜欢住民宿，有当地特色"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert profile.accommodation_pref == "minsu"

    @pytest.mark.asyncio
    async def test_learn_from_session_transport(self):
        """Detects transport preference keywords."""
        messages = [
            {"role": "user", "content": "最好是直飞，不要转机"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert profile.transport_pref == "direct_flight"

    @pytest.mark.asyncio
    async def test_learn_from_session_dietary(self):
        """Detects dietary restrictions from user messages."""
        messages = [
            {"role": "user", "content": "我是素食主义者，不吃辣"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert "vegetarian" in profile.dietary_restrictions
        assert "no_spicy" in profile.dietary_restrictions

    @pytest.mark.asyncio
    async def test_learn_from_session_brands(self):
        """Detects brand preferences from user messages."""
        messages = [
            {"role": "user", "content": "我喜欢住希尔顿，飞全日空"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert "希尔顿" in profile.favorite_brands
        assert "全日空" in profile.favorite_brands

    @pytest.mark.asyncio
    async def test_learn_from_session_destinations(self):
        """Detects visited destinations from user messages."""
        messages = [
            {"role": "user", "content": "我之前去过日本和泰国"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert "日本" in profile.visited_destinations
        assert "泰国" in profile.visited_destinations

    @pytest.mark.asyncio
    async def test_learn_from_session_empty_messages(self):
        """Empty messages produce no changes."""
        await self.pm.learn_from_session("u1", [])
        profile = await self.pm.get_profile("u1")
        assert profile.travel_style == []
        assert profile.budget_preference is None

    @pytest.mark.asyncio
    async def test_learn_from_session_no_user_messages(self):
        """Only assistant messages — no user text to parse."""
        messages = [
            {"role": "assistant", "content": "冒险旅行推荐"},
        ]
        await self.pm.learn_from_session("u1", messages)
        profile = await self.pm.get_profile("u1")
        assert profile.travel_style == []

    # --- delete_profile ---

    @pytest.mark.asyncio
    async def test_delete_profile(self):
        """Deleted profile returns a fresh blank on next get."""
        await self.pm.update_profile("u1", {"budget_preference": "luxury"})
        self.pm.delete_profile("u1")
        profile = await self.pm.get_profile("u1")
        assert profile.budget_preference is None

    # --- get_personalization_context ---

    def test_personalization_context_empty(self):
        """Blank profile returns empty string."""
        ctx = self.pm.get_personalization_context("u1")
        assert ctx == ""

    @pytest.mark.asyncio
    async def test_personalization_context_with_data(self):
        """Populated profile produces a human-readable context string."""
        await self.pm.update_profile("u1", {
            "travel_style": ["adventure", "foodie"],
            "budget_preference": "luxury",
        })
        ctx = self.pm.get_personalization_context("u1")
        assert "冒险探索" in ctx
        assert "美食体验" in ctx
        assert "奢华型" in ctx
