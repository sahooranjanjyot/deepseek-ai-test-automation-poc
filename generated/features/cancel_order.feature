Feature: Cancel an order and ensure customer is not charged

Scenario: Cancel an order and verify no charge is applied
Given the customer is logged in and has a paid order
When the customer cancels the order from order history and confirms cancellation
Then the order is cancelled and a confirmation message is shown
