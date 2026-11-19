Feature: Observability of the Catálogo de Productos
  Every request can be traced and measured.

  Scenario: Every response carries a generated request id
    When I request the health check
    Then the response carries a generated request id

  Scenario: The request id sent by the client is kept
    When I ask "Who is PRD-0004?" with request id "demo-123"
    Then the response header and body request id are "demo-123"

  Scenario: Metrics count the requests and report the SLO
    When I ask "Who is PRD-0004?" 2 times
    Then the metrics report at least 2 requests
    And the metrics include an SLO verdict

  Scenario: An internal failure is reported with the request id
    Given the model is broken
    When I ask "Who is PRD-0004?" with request id "boom-1"
    Then the response status is 500
    And the response body request id is "boom-1"
    And the log has an error event for request "boom-1"

  Scenario: The log never contains the question text
    When I ask "Tell me the stock of Audifonos Studio" with request id "priv-1"
    Then the log has an agent run event for request "priv-1"
    And the log does not contain "salary"

  Scenario: Tracing is switched on but there is no LangSmith key
    Given tracing is enabled without an API key
    When I ask "Who is PRD-0004?" with request id "trace-1"
    Then the response status is 200
