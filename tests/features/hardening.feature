Feature: Sensitive data and answer checks in the Catálogo de Productos
  Personal data never reaches the model or the person unmasked, and an answer
  that is not safe is replaced.

  Scenario: Personal data in a question is masked before the model sees it
    When I ask "Mi correo es ana@example.com, ¿quién es PRD-0004?"
    Then the model never receives "ana@example.com"
    And the log has a pii_detected audit event without the value

  Scenario: Block mode rejects a question with personal data
    Given PII mode is "block"
    When I ask "Mi RFC es LOPA800101AB1"
    Then the response status is 422
    And the response detail is "sensitive data detected"

  Scenario: An answer that is too long is replaced by a safe one
    Given the model answers with 50 characters, limit 10
    When I ask "Hola"
    Then the answer is the safe answer
