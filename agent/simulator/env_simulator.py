# Environment Simulator – injects faults and simulates abnormal scenarios
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FaultConfig:
  """Configuration for a single injected fault."""

  fault_type: str
  enabled: bool = True
  params: Dict[str, Any] = field(default_factory=dict)
  injected_at: float = field(default_factory=time.time)

  def to_dict(self) -> Dict[str, Any]:
    """Serialize to dict for API responses."""
    return {
      "fault_type": self.fault_type,
      "enabled": self.enabled,
      "params": self.params,
      "injected_at": self.injected_at,
    }


@dataclass
class ScenarioResult:
  """Result of running a simulated scenario."""

  scenario_name: str
  description: str
  faults_injected: List[str]
  environment_state: Dict[str, Any]

  def to_dict(self) -> Dict[str, Any]:
    """Serialize to dict for API responses."""
    return {
      "scenario_name": self.scenario_name,
      "description": self.description,
      "faults_injected": self.faults_injected,
      "environment_state": self.environment_state,
    }


# Valid fault types
VALID_FAULT_TYPES = [
  "tool_timeout",
  "tool_error",
  "price_change",
  "stock_change",
  "api_rate_limit",
]

# Pre-defined scenario configurations
SCENARIO_DEFINITIONS: Dict[str, Dict[str, Any]] = {
  "peak_season": {
    "description": (
      "Peak season scenario: prices surge 30-80%, hotel availability "
      "drops significantly, flight seats become scarce"
    ),
    "faults": [
      {
        "fault_type": "price_change",
        "params": {
          "direction": "up",
          "percent_min": 30,
          "percent_max": 80,
          "affected_categories": ["flight", "hotel", "attraction"],
        },
      },
      {
        "fault_type": "stock_change",
        "params": {
          "availability": "low",
          "sold_out_probability": 0.4,
          "affected_categories": ["hotel", "flight"],
        },
      },
    ],
    "environment_state": {
      "season": "peak",
      "demand_level": "very_high",
      "price_multiplier": 1.5,
      "availability_factor": 0.3,
    },
  },
  "bad_weather": {
    "description": (
      "Bad weather scenario: storms cause flight delays/cancellations, "
      "outdoor attractions may close, travel warnings issued"
    ),
    "faults": [
      {
        "fault_type": "tool_timeout",
        "params": {
          "timeout_ms": 10000,
          "affected_tools": ["flight_search", "weather_api"],
          "timeout_probability": 0.3,
        },
      },
      {
        "fault_type": "tool_error",
        "params": {
          "error_type": "weather_disruption",
          "error_message": "Flight cancelled due to severe weather",
          "affected_tools": ["flight_search"],
          "error_probability": 0.5,
        },
      },
    ],
    "environment_state": {
      "weather_condition": "severe_storm",
      "flight_disruption_risk": "high",
      "outdoor_activity_available": False,
      "travel_advisory": "warning",
    },
  },
  "budget_crisis": {
    "description": (
      "Budget crisis scenario: all prices exceed expectations, "
      "currency exchange unfavorable, no discounts available"
    ),
    "faults": [
      {
        "fault_type": "price_change",
        "params": {
          "direction": "up",
          "percent_min": 50,
          "percent_max": 120,
          "affected_categories": ["flight", "hotel", "dining", "attraction"],
        },
      },
      {
        "fault_type": "tool_error",
        "params": {
          "error_type": "no_discount",
          "error_message": "No discounts or promotions currently available",
          "affected_tools": ["budget_allocator"],
          "error_probability": 1.0,
        },
      },
    ],
    "environment_state": {
      "price_level": "inflated",
      "currency_rate": "unfavorable",
      "discount_available": False,
      "budget_feasibility": "challenging",
    },
  },
}


class EnvironmentSimulator:
  """Simulates environmental faults and abnormal conditions for testing."""

  def __init__(self) -> None:
    self._active_faults: Dict[str, FaultConfig] = {}
    self._environment_state: Dict[str, Any] = {}
    self._active_scenario: Optional[str] = None

  def inject_fault(self, fault_type: str, **params: Any) -> Dict[str, Any]:
    """Inject a fault into the simulated environment.

    Args:
      fault_type: One of the valid fault types
      **params: Additional parameters for the fault

    Returns:
      Dict describing the injected fault

    Raises:
      ValueError: if fault_type is not recognized
    """
    if fault_type not in VALID_FAULT_TYPES:
      raise ValueError(
        f"Invalid fault type '{fault_type}'. "
        f"Valid types: {VALID_FAULT_TYPES}"
      )

    # Build default params based on fault type
    default_params = self._get_default_fault_params(fault_type)
    default_params.update(params)

    config = FaultConfig(
      fault_type=fault_type,
      enabled=True,
      params=default_params,
    )
    self._active_faults[fault_type] = config

    return {
      "status": "injected",
      "fault": config.to_dict(),
      "active_fault_count": len(self._active_faults),
    }

  def get_fault_config(self) -> Dict[str, Any]:
    """Get the current fault configuration."""
    return {
      "active_faults": {
        k: v.to_dict() for k, v in self._active_faults.items()
      },
      "active_scenario": self._active_scenario,
      "environment_state": self._environment_state,
      "fault_count": len(self._active_faults),
    }

  def reset(self) -> Dict[str, Any]:
    """Reset all faults and environment state."""
    count = len(self._active_faults)
    self._active_faults.clear()
    self._environment_state.clear()
    self._active_scenario = None
    return {
      "status": "reset",
      "faults_cleared": count,
    }

  def simulate_scenario(self, scenario_name: str) -> ScenarioResult:
    """Run a pre-defined scenario by injecting its faults.

    Args:
      scenario_name: Name of the scenario to run

    Returns:
      ScenarioResult with details of what was applied

    Raises:
      ValueError: if scenario_name is not recognized
    """
    if scenario_name not in SCENARIO_DEFINITIONS:
      raise ValueError(
        f"Unknown scenario '{scenario_name}'. "
        f"Available: {list(SCENARIO_DEFINITIONS.keys())}"
      )

    # Reset first
    self.reset()

    definition = SCENARIO_DEFINITIONS[scenario_name]
    injected_faults: List[str] = []

    # Inject each fault defined in the scenario
    for fault_def in definition["faults"]:
      fault_type = fault_def["fault_type"]
      params = fault_def.get("params", {})
      self.inject_fault(fault_type, **params)
      injected_faults.append(fault_type)

    # Apply environment state
    self._environment_state = dict(definition["environment_state"])
    self._active_scenario = scenario_name

    return ScenarioResult(
      scenario_name=scenario_name,
      description=definition["description"],
      faults_injected=injected_faults,
      environment_state=self._environment_state,
    )

  def list_scenarios(self) -> List[Dict[str, Any]]:
    """List all available pre-defined scenarios."""
    result: List[Dict[str, Any]] = []
    for name, definition in SCENARIO_DEFINITIONS.items():
      result.append({
        "name": name,
        "description": definition["description"],
        "fault_count": len(definition["faults"]),
        "fault_types": [
          f["fault_type"] for f in definition["faults"]
        ],
      })
    return result

  def is_fault_active(self, fault_type: str) -> bool:
    """Check if a specific fault type is currently active."""
    config = self._active_faults.get(fault_type)
    return config is not None and config.enabled

  def should_trigger_fault(self, fault_type: str) -> bool:
    """Probabilistically determine if a fault should trigger.

    Uses the probability parameter in the fault config. Defaults to
    100% if no probability is set.
    """
    config = self._active_faults.get(fault_type)
    if config is None or not config.enabled:
      return False

    probability = config.params.get(
      "timeout_probability",
      config.params.get("error_probability", 1.0),
    )
    return random.random() < probability

  def get_price_modifier(self) -> float:
    """Get the current price modification factor.

    Returns:
      A multiplier (1.0 = no change, 1.5 = 50% increase)
    """
    config = self._active_faults.get("price_change")
    if config is None or not config.enabled:
      return 1.0

    direction = config.params.get("direction", "up")
    pmin = config.params.get("percent_min", 10)
    pmax = config.params.get("percent_max", 30)
    percent = random.uniform(pmin, pmax)

    if direction == "up":
      return 1.0 + percent / 100.0
    else:
      return max(0.1, 1.0 - percent / 100.0)

  def _get_default_fault_params(
    self,
    fault_type: str,
  ) -> Dict[str, Any]:
    """Return sensible default params for each fault type."""
    defaults: Dict[str, Dict[str, Any]] = {
      "tool_timeout": {
        "timeout_ms": 5000,
        "affected_tools": ["all"],
        "timeout_probability": 0.5,
      },
      "tool_error": {
        "error_type": "internal_error",
        "error_message": "Simulated tool error",
        "affected_tools": ["all"],
        "error_probability": 0.5,
      },
      "price_change": {
        "direction": "up",
        "percent_min": 10,
        "percent_max": 30,
        "affected_categories": ["flight", "hotel"],
      },
      "stock_change": {
        "availability": "low",
        "sold_out_probability": 0.3,
        "affected_categories": ["hotel"],
      },
      "api_rate_limit": {
        "requests_per_minute": 5,
        "retry_after_seconds": 30,
        "affected_tools": ["all"],
      },
    }
    return dict(defaults.get(fault_type, {}))
