Feature: Catálogo de Productos answers questions about products
  Sales staff ask questions through the API and the single agent answers
  using read-only tools over the product catalog.

  Scenario: Ask about an existing product
    When I ask "¿Quién es PRD-0004?"
    Then the response status is 200
    And the answer mentions "Audífonos Studio"
    And the tools used are "get_product"
    And the agent took 2 steps

  Scenario: Ask about an unknown product
    When I ask "¿Quién es PRD-9999?"
    Then the response status is 200
    And the tools used are "get_product"
    And the answer does not mention "Audífonos Studio"

  Scenario: Ask about a category
    When I ask "¿Qué productos hay en Electrónica?"
    Then the response status is 200
    And the answer mentions "Laptop Pro 14"
    And the tools used are "search_by_category"

  Scenario: Ask something with no product id and no category
    When I ask "Hola, ¿cómo estás?"
    Then the response status is 200
    And the answer is "Pregúntame por un producto (PRD-0001) o una categoría."
    And no tools were used

  Scenario: The step cap stops the loop
    Given the agent is limited to 1 step
    When I ask "¿Quién es PRD-0004?"
    Then the answer is "No pude completar la respuesta. Intenta con una pregunta más concreta."
    And the agent took 1 steps

  Scenario: An empty question is rejected
    When I ask an empty question
    Then the response status is 422

  Scenario: A question longer than the limit is rejected
    When I ask a question of 2001 characters
    Then the response status is 422

  Scenario: The health check reports the process
    When I request the health check
    Then the response status is 200
    And the health status is "ok"
    And the health check includes a process id
