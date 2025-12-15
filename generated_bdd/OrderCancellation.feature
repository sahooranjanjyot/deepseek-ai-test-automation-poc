Feature: Order Cancellation

  Background:
    Given the user is logged in

  Scenario Outline: Cancellable order
    Given an order is placed in a <status> state
    When the user cancels the order
    Then the order status should be "Cancelled"
    And the payment should not be captured
    Examples:
      | status    |
      | Pending   |
      | Processing|

  Scenario Outline: Non-cancellable order
    Given an order is placed in a <status> state
    When the user tries to cancel the order
    Then the order status should not change
    And the user should see an error message
    Examples:
      | status    |
      | Shipped   |
      | Delivered |

  Scenario: Payment authorized but not captured
    Given an order with authorized payment is placed in a <status> state
    When the user cancels the order
    Then the order status should be "Cancelled"
    And the payment should be voided/released
    And the payment should not be captured
    Examples:
      | status    |
      | Pending   |
      | Processing|

  Scenario Outline: Payment already captured
    Given an order with captured payment is placed in a <status> state
    When the user cancels the order
    Then the order status should be "Cancelled"
    And the payment should not be captured
    And (TODO: mark refund check as TODO)
    Examples:
      | status    |
      | Pending   |
      | Processing|
