from gemini_splunk_agent.agent import build_agent, _ADK_AVAILABLE


def test_adk_is_importable():
    assert _ADK_AVAILABLE, "google-adk must be installed for this test environment"


def test_agent_constructs_with_default_model():
    agent = build_agent(stub=True)
    assert agent is not None
    assert agent.name == "gemini_splunk_agent"


def test_agent_uses_requested_model():
    agent = build_agent(model="gemini-2.5-pro", stub=True)
    assert "gemini-2.5-pro" in str(agent.model) or agent.model == "gemini-2.5-pro"


def test_agent_has_mcp_toolset():
    agent = build_agent(stub=True)
    tools = list(getattr(agent, "tools", []) or [])
    assert len(tools) >= 1, "agent should have at least the Splunk MCP toolset wired"
