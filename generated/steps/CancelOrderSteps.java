 ```java
package steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;

public class CancelOrderSteps {

    @Given("User is logged in")
    public void user_is_logged_in() {
        // Implementation not required as it's a precondition
    }

    @Given("User has at least one cancellable order")
    public void user_has_at_least_one_cancellable_order() {
        // Implementation not required as it's a precondition
    }

    @Given("Order payment status is Pending or Authorized")
    public void order_payment_status_is_pending_or_authorized() {
        // Implementation not required as it's a precondition
    }

    @When("User navigates to Order History")
    public void user_navigates_to_order_history() {
        // Navigation logic
    }

    @When("User opens Order Details page")
    public void user_opens_order_details_page() {
        // Navigation logic
    }

    @When("User initiates order cancellation")
    public void user_initiates_order_cancellation() {
        // Cancellation logic
    }

    @When("User confirms cancellation")
    public void user_confirms_cancellation() {
        // Confirmation logic
    }

    @Then("Order status is updated to Cancelled")
    public void order_status_is_updated_to_cancelled() {
        // Verification logic
    }

    @Then("Cancellation confirmation dialog is displayed")
    public void cancellation_confirmation_dialog_is_displayed() {
        // Verification logic
    }
}
```