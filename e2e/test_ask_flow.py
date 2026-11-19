"""End-to-end tests of the question and answer page, run in a real browser."""
import os
import re

from playwright.sync_api import Page, expect


def ask(page: Page, question: str, api_key: str = None) -> None:
    """Type the API key and a question, then send it."""
    key = os.environ["E2E_API_KEY"] if api_key is None else api_key
    page.get_by_test_id("api-key").fill(key)
    page.get_by_test_id("question").fill(question)
    page.get_by_test_id("send").click()


def test_a_wrong_api_key_shows_invalid_key_message(page: Page):
    page.goto("/")
    ask(page, "Cuantos productos hay en ventas?", api_key="wrong-key-0000000000")
    answer = page.get_by_test_id("answer")
    expect(answer).to_contain_text("Clave inválida")
    expect(answer.locator(".assistant")).to_have_count(0)


def test_a_question_shows_the_answer_in_the_conversation(page: Page):
    page.goto("/")
    ask(page, "Quien es el jefe de la categoría de ventas?")
    answer = page.get_by_test_id("answer")
    expect(answer).to_contain_text("Quien es el jefe de la categoría de ventas?")
    expect(answer.locator(".assistant")).to_have_count(1)
    expect(answer.locator(".assistant")).not_to_be_empty()


def test_the_answer_comes_with_a_request_id(page: Page):
    page.goto("/")
    ask(page, "Cuantos productos hay en ventas?")
    request_id = page.get_by_test_id("request-id")
    expect(request_id).to_be_visible()
    expect(request_id).to_contain_text(re.compile(r"\S{6,}"))


def test_the_input_is_cleared_after_sending(page: Page):
    page.goto("/")
    ask(page, "Cuantos productos hay en ventas?")
    expect(page.get_by_test_id("answer").locator(".assistant")).to_have_count(1)
    expect(page.get_by_test_id("question")).to_have_value("")


def test_an_empty_question_shows_an_error_message_in_spanish(page: Page):
    page.goto("/")
    ask(page, "   ")
    answer = page.get_by_test_id("answer")
    expect(answer).to_contain_text("Escribe una pregunta")
    expect(answer.locator(".assistant")).to_have_count(0)


def test_a_second_question_keeps_the_previous_conversation(page: Page):
    page.goto("/")
    ask(page, "Cuantos productos hay en ventas?")
    answer = page.get_by_test_id("answer")
    expect(answer.locator(".assistant")).to_have_count(1)
    ask(page, "Y en ingenieria?")
    expect(answer.locator(".assistant")).to_have_count(2)
    expect(answer).to_contain_text("Cuantos productos hay en ventas?")
    expect(answer).to_contain_text("Y en ingenieria?")
    expect(answer.locator(".user")).to_have_count(2)
