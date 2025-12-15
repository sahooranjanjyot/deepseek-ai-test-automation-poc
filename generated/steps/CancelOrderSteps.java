package steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

public class CancelOrderSteps {

    @Given("the customer is logged in and has a paid order")
    public void customer_is_logged_in_and_has_paid_order() {
        loginUser();
        ensureUserHasCancellableOrder();
        ensureOrderPaymentStatusIsPaidOrAuthorized();
    }

    @When("the customer cancels the order from order history")
    public void customer_cancels_order_from_order_history() {
        navigateToOrderHistory();
        openOrderDetails();
        initiateOrderCancellation();
        confirmCancellation();
    }

    @Then("the order is cancelled and a confirmation message is shown")
    public void order_is_cancelled_and_confirmation_is_shown() {
        verifyCancellationConfirmationDialog();
        verifyOrderStatusIsCancelled();
    }

    /* ---------- Granular helper methods (internal orchestration) ---------- */

    private void loginUser() {
        // TODO: Implement user login
    }

    private void ensureUserHasCancellableOrder() {
        // TODO: Ensure at least one cancellable order exists
    }

    private void ensureOrderPaymentStatusIsPaidOrAuthorized() {
        // TODO: Verify payment status
    }

    private void navigateToOrderHistory() {
        // TODO: Navigate to order history page
    }

    private void openOrderDetails() {
        // TODO: Open specific order details
    }

    private void initiateOrderCancellation() {
        // TODO: Click cancel order
    }

    private void confirmCancellation() {
        // TODO: Confirm cancellation
    }

    private void verifyCancellationConfirmationDialog() {
        // TODO: Verify confirmation dialog
    }

    private void verifyOrderStatusIsCancelled() {
        // TODO: Verify order status is cancelled
    }
}
