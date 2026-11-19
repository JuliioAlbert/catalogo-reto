"""End-to-end tests of the catalog view (cards, filters and the ask button)."""
import os

from playwright.sync_api import Page, expect


def open_catalog(page: Page, api_key: str = None) -> None:
    """Open the page and type the API key so the catalog loads."""
    key = os.environ["E2E_API_KEY"] if api_key is None else api_key
    page.goto("/")
    page.get_by_test_id("api-key").fill(key)


def test_without_a_key_the_page_asks_for_it(page: Page):
    page.goto("/")
    expect(page.get_by_test_id("catalog-status")).to_contain_text("Escribe tu clave")


def test_a_wrong_key_shows_invalid_key_in_the_catalog(page: Page):
    open_catalog(page, api_key="wrong-key-0000000000")
    expect(page.get_by_test_id("catalog-status")).to_contain_text("Clave inválida")
    expect(page.get_by_test_id("product-card")).to_have_count(0)


def test_a_valid_key_shows_every_product_as_a_card(page: Page):
    open_catalog(page)
    expect(page.get_by_test_id("product-card")).to_have_count(12)
    expect(page.get_by_test_id("catalog-grid")).to_contain_text("Laptop Pro 14")
    expect(page.get_by_test_id("catalog-grid")).to_contain_text("$18,999")


def test_choosing_a_category_filters_the_cards(page: Page):
    open_catalog(page)
    expect(page.get_by_test_id("product-card")).to_have_count(12)
    page.get_by_test_id("category-filter").get_by_role("button", name="Oficina").click()
    expect(page.get_by_test_id("product-card")).to_have_count(3)
    expect(page.get_by_test_id("catalog-grid")).to_contain_text("Silla Ergonómica")


def test_the_ask_button_fills_the_question_with_the_product_id(page: Page):
    open_catalog(page)
    expect(page.get_by_test_id("product-card")).to_have_count(12)
    page.get_by_test_id("product-card").first.get_by_role("button").click()
    expect(page.get_by_test_id("question")).to_have_value("¿Qué sabes de PRD-0001?")
