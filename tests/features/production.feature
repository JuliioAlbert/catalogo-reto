Feature: Production safety of the Catálogo de Productos
  Clients need a key, are rate limited, and a badly configured production
  deployment refuses to start.

  Scenario: Asking without a key is rejected
    Given no API key is sent
    When I ask "Who is PRD-0004?"
    Then the response status is 401
    And the response detail is "invalid or missing API key"

  Scenario: Metrics with a wrong key are rejected
    Given the API key "not-a-real-key" is sent
    When I request "/metrics"
    Then the response status is 401
    And the response detail is "invalid or missing API key"

  Scenario: Public pages do not need a key
    Given no API key is sent
    When I request "/health"
    And I request "/"
    Then every response status is 200

  Scenario: The log names the client and never the key
    When "alice" asks "Who is PRD-0004?"
    Then the agent run and audit events name the client "alice"
    And the log and the response do not contain the key of "alice"

  Scenario: A client over the rate limit waits while others are not affected
    Given the rate limit is 2 requests per minute
    When "alice" asks "Who is PRD-0004?" 3 times
    Then the response status is 429
    And the response detail is "rate limit exceeded"
    And the response has a positive Retry-After header
    And "bob" can still ask a question
    And "alice" can ask again after 61 seconds

  Scenario: Production refuses to start with the fake model
    When I start production with MODEL_PROVIDER "fake"
    Then the startup is refused

  Scenario: Production refuses to start with a short key
    When I start production with API_KEYS "alice:abcdefghijklmno"
    Then the startup is refused
    And the refusal does not show the key
