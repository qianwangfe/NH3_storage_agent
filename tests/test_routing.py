from hydride_agent.orchestration import deterministic_plan


def test_representative_routes():
    cases = [
        ("Compare state diversity across material families", "state_complexity"),
        ("Trace the LiBH4 state sequence from x = 1 to 3", "state_sequence_lookup"),
        ("Plot DigBat conductivity against NH3/BH4", "conductivity_loading"),
        ("Compare DigHyd H2 release", "h2_release_loading"),
        ("Compare DigBat conductivity and DigHyd H2 release", "dual_axis_cross_database"),
        ("Generate an evidence-to-hypothesis mechanism map", "mechanism_synthesis"),
        ("Design a molecular dynamics and metadynamics workflow", "computational_design"),
    ]
    for query, expected in cases:
        assert deterministic_plan(query).skill == expected


def test_conductivity_and_h2_have_independent_routes():
    assert deterministic_plan("DigBat conductivity plot").databases == ["digbat"]
    assert deterministic_plan("DigHyd H2 release plot").databases == ["dighyd"]
