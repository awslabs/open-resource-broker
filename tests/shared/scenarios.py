from dataclasses import dataclass, field


@dataclass(frozen=True)
class TestScenario:
    scenario_id: str  # stable ID used as pytest parametrize ID
    template_id: str  # e.g. "RunInstances-OnDemand"
    provider_api: str  # "RunInstances" | "EC2Fleet" | "SpotFleet" | "ASG"
    capacity: int  # machines to request
    overrides: dict = field(default_factory=dict)
    tags: frozenset = field(default_factory=frozenset)
    expected_status: str = "complete"


def get_smoke_scenarios() -> list[TestScenario]:
    """Minimal set exercising every provider API — used by onmoto."""
    return [
        TestScenario(
            "run-instances-ondemand",
            "RunInstances-OnDemand",
            "RunInstances",
            1,
            tags=frozenset({"smoke"}),
        ),
        TestScenario("asg-ondemand", "ASG-OnDemand", "ASG", 1, tags=frozenset({"smoke"})),
        TestScenario(
            "ec2fleet-request-ondemand",
            "EC2Fleet-Request-OnDemand",
            "EC2Fleet",
            1,
            tags=frozenset({"smoke"}),
        ),
        TestScenario(
            "spotfleet-request-lowest",
            "SpotFleet-Request-LowestPrice",
            "SpotFleet",
            1,
            tags=frozenset({"smoke"}),
        ),
    ]


def get_scenario_by_id(scenario_id: str) -> TestScenario:
    all_scenarios = get_smoke_scenarios()
    for s in all_scenarios:
        if s.scenario_id == scenario_id:
            return s
    raise KeyError(f"Unknown scenario: {scenario_id}")
