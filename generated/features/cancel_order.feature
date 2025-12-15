 Scenario: Cancel an order and ensure customer is not charged
    Given User is logged in
    And User has at least one cancellable order
    And Order payment status is Pending or Authorized
    When User navigates to "Home Page" and clicks on "Account menu → Order History"
    Then User navigates to "Order History Page" and opens "Order ID link for a cancellable order"
    And User initiates order cancellation on "Order Details Page"
    Then User confirms cancellation on "Cancellation Confirmation Dialog"
    Then Order status is updated to Cancelled
    And Payment authorization is voided
    And No charge is applied to the customer