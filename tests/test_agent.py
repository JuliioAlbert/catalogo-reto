"""Unit tests for app.agent with a scripted model."""

from conftest import ScriptedModel, field, final_answer, tool_call

from app.agent import Agent

CAP_MESSAGE = "No pude completar la respuesta. Intenta con una pregunta más concreta."


def build_agent(catalog, model, max_steps=3):
    return Agent(model=model, catalog=catalog, max_steps=max_steps)


def test_direct_answer_takes_one_step_and_no_tools(catalog):
    agent = build_agent(catalog, ScriptedModel(final_answer("Hola")))
    result = agent.run("Hola")
    assert field(result, "answer") == "Hola"
    assert field(result, "steps") == 1
    assert not field(result, "tools_used")


def test_tool_result_is_fed_back_as_a_user_message(catalog):
    model = ScriptedModel(
        tool_call("get_product", product_id="PRD-0004"), final_answer("listo")
    )
    result = build_agent(catalog, model).run("¿Quién es PRD-0004?")
    assert list(field(result, "tools_used")) == ["get_product"]
    assert field(result, "steps") == 2
    last = model.calls[1][-1]
    assert last["role"] == "user"
    assert last["content"].startswith("Resultado de la herramienta:")


def test_unknown_tool_and_invalid_json_do_not_crash_the_agent(catalog):
    for reply in (tool_call("delete_everything"), "this is not json"):
        result = build_agent(catalog, ScriptedModel(reply)).run("Hola")
        assert isinstance(field(result, "answer"), str)
        assert field(result, "steps") <= 3


def test_reaching_the_step_cap_returns_the_exact_message(catalog):
    model = ScriptedModel(tool_call("get_product", product_id="PRD-0001"))
    result = build_agent(catalog, model, max_steps=2).run("PRD-0001")
    assert field(result, "answer") == CAP_MESSAGE
    assert field(result, "steps") == 2
    assert len(model.calls) == 2
