Feature: Cancel an order and ensure customer is not charged

  Scenario: Cancel an order and verify no charge is applied
    Given User is logged in
    And User has at least one cancellable order
    And Order payment status is Pending or Authorized
    When Navigate to Order History
    And Open Order Details page
    And Initiate order cancellation
    And Confirm cancellation
    Then Order status is updated to Cancelled
    And Payment authorization is voided
    And No charge is applied to the customer
