from tools.rga_agent import RgaAgent


def test_agent_generates_plan_and_summary():
    agent = RgaAgent()
    plan = agent.generate_plan("Recommend a song for a casual player")

    assert isinstance(plan, list)
    assert plan
    assert any("request" in step.lower() for step in plan)

    result = agent.run("Recommend a song for a casual player")
    assert result["status"] == "ready"
    assert result["task"] == "Recommend a song for a casual player"
    assert isinstance(result["plan"], list)
    assert result["summary"].startswith("Agent ready")
