"""
Test component version specifications and version registry.
"""

from agent.versioning import ComponentVersionSpec, VersionRegistry

def test_component_version_spec() -> None:
    spec = ComponentVersionSpec(
        component_type="planner",
        name="planner-v1",
        version="1.0.0",
        metadata={"strategy": "reactive"},
    )

    assert spec.get_full_identifier() == "planner:planner-v1@1.0.0"

def test_version_registry() -> None:
    registry = VersionRegistry()
    spec = ComponentVersionSpec(
        component_type="memory",
        name="memory-v1",
        version="1.0.0",
    )

    registry.register(spec)
    retrieved = registry.get("memory:memory-v1@1.0.0")

    assert retrieved is not None
    assert retrieved.name == "memory-v1"
    assert len(registry.list_components()) == 1
