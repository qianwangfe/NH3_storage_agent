from .base import SkillRegistry
from .computational_design import ComputationalDesignSkill
from .conductivity_loading import ConductivityLoadingSkill
from .dual_axis import DualAxisCrossDatabaseSkill
from .h2_release_loading import H2ReleaseLoadingSkill
from .mechanism_synthesis import MechanismSynthesisSkill
from .state_complexity import StateComplexitySkill
from .state_sequence_lookup import StateSequenceLookupSkill


def build_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(StateComplexitySkill())
    registry.register(StateSequenceLookupSkill())
    registry.register(ConductivityLoadingSkill())
    registry.register(H2ReleaseLoadingSkill())
    registry.register(DualAxisCrossDatabaseSkill())
    registry.register(MechanismSynthesisSkill())
    registry.register(ComputationalDesignSkill())
    return registry
