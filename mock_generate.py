import json
from pathlib import Path

FEATURE_OUT = Path("generated/features/cancel_order.feature")
STEPS_OUT = Path("generated/steps/CancelOrderSteps.java")
PAGES_DIR = Path("generated/pages")

TESTCASE = Path("testcases/cancel_order.json")

def ensure_dirs():
    FEATURE_OUT.parent.mkdir(parents=True, exist_ok=True)
    STEPS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

def read_testcase():
    if TESTCASE.exists():
        return json.loads(TESTCASE.read_text(encoding="utf-8"))
    return {}

def write_feature(tc: dict):
    # Business-centric 3-liner scenario. No And/But.
    content = """Feature: Cancel order

  Scenario: Cancel a paid order
    Given the customer is logged in and has a paid order
    When the customer cancels the order from order history
    Then the order is cancelled and a confirmation message is shown
"""
    FEATURE_OUT.write_text(content, encoding="utf-8")

def write_steps(tc: dict):
    # Exactly 1 Given, 1 When, 1 Then. Granular helpers inside.
    content = """package steps;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

import pages.OrderHistoryPage;
import pages.OrderDetailsPage;
import pages.CancellationConfirmationDialog;

public class CancelOrderSteps {

    private final OrderHistoryPage orderHistoryPage = new OrderHistoryPage();
    private final OrderDetailsPage orderDetailsPage = new OrderDetailsPage();
    private final CancellationConfirmationDialog confirmationDialog = new CancellationConfirmationDialog();

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
        clickCancelOrder();
        clickConfirmCancellation();
    }

    @Then("the order is cancelled and a confirmation message is shown")
    public void order_is_cancelled_and_confirmation_is_shown() {
        verifyConfirmationShown();
        verifyOrderStatusIsCancelled();
    }

    /* ---------- Granular helper methods (internal orchestration) ---------- */

    private void loginUser() {
        // TODO: Implement login
    }

    private void ensureUserHasCancellableOrder() {
        // TODO: Ensure at least one cancellable order exists
    }

    private void ensureOrderPaymentStatusIsPaidOrAuthorized() {
        // TODO: Verify payment status is paid/authorized
    }

    private void navigateToOrderHistory() {
        orderHistoryPage.openOrderHistory();
    }

    private void openOrderDetails() {
        orderHistoryPage.openMostRecentOrderDetails();
    }

    private void clickCancelOrder() {
        orderDetailsPage.clickCancelOrder();
    }

    private void clickConfirmCancellation() {
        // Either confirm from details page or dialog depending on your UI.
        // Keep atomic calls only:
        confirmationDialog.clickConfirmCancellation();
    }

    private void verifyConfirmationShown() {
        confirmationDialog.verifyConfirmationMessageShown();
    }

    private void verifyOrderStatusIsCancelled() {
        orderDetailsPage.verifyOrderStatusCancelled();
    }
}
"""
    STEPS_OUT.write_text(content, encoding="utf-8")

def write_pages(tc: dict):
    # Atomic public methods only (as per validator prefixes)
    order_history = """package pages;

public class OrderHistoryPage {

    public void openOrderHistory() {
        // TODO: Navigate to Order History page
    }

    public void openMostRecentOrderDetails() {
        // TODO: Open details of the most recent order
    }
}
"""
    order_details = """package pages;

public class OrderDetailsPage {

    public void clickCancelOrder() {
        // TODO: Click Cancel Order button
    }

    public void verifyOrderStatusCancelled() {
        // TODO: Assert order status is Cancelled
    }
}
"""
    dialog = """package pages;

public class CancellationConfirmationDialog {

    public void clickConfirmCancellation() {
        // TODO: Click Confirm button in cancellation dialog
    }

    public void verifyConfirmationMessageShown() {
        // TODO: Verify cancellation confirmation message is displayed
    }
}
"""
    (PAGES_DIR / "OrderHistoryPage.java").write_text(order_history, encoding="utf-8")
    (PAGES_DIR / "OrderDetailsPage.java").write_text(order_details, encoding="utf-8")
    (PAGES_DIR / "CancellationConfirmationDialog.java").write_text(dialog, encoding="utf-8")

def main():
    ensure_dirs()
    tc = read_testcase()
    write_feature(tc)
    write_steps(tc)
    write_pages(tc)
    print("✅ Mock artifacts generated into /generated")

if __name__ == "__main__":
    main()