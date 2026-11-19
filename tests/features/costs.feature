Feature: Cost levers of the Catálogo de Productos
  Each answer reports which model served it, why, and what it cost.

  Scenario: A short simple question uses the small model
    When I ask "Who is PRD-0001?"
    Then the response status is 200
    And the model used is the small model
    And the route is reported

  Scenario: A comparison question uses the large model
    When I ask "Compara las categorías de Hogar y Deportes"
    Then the response status is 200
    And the model used is the large model

  Scenario: Disabling routing always uses the large model
    Given routing is disabled
    When I ask "Who is PRD-0001?"
    Then the model used is the large model

  Scenario: The response reports its cost
    When I ask "Who is PRD-0001?"
    Then the response reports a positive cost and no cached calls

  Scenario: A gateway failure is reported as model unavailable
    Given the gateway is down
    When I ask "Who is PRD-0001?"
    Then the response status is 502
    And the detail is "model unavailable"
    And the response carries a request id
