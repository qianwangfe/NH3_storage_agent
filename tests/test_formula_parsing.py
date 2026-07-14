import math

from hydride_agent.skills.common import host_system_base, nh3_per_bh4, pure_parent_or_ammine


def test_formula_parsing_for_common_notations():
    assert host_system_base("LiBH4(NH3)2(s)") == "LiBH4"
    assert math.isclose(nh3_per_bh4("LiBH4(NH3)2"), 2.0)
    assert math.isclose(nh3_per_bh4("Mg(BH4)2·1.8NH3"), 0.9)
    assert pure_parent_or_ammine("Mg(BH4)2·4NH3")
    assert not pure_parent_or_ammine("Mg(BH4)2·1.5NH3@MgO")
