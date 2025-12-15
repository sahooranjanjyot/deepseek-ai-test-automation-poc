package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

public class OrderDetailsPage {
    private WebDriver driver;

    // Locators
    private By cancelOrderButtonLocator = By.id("cancel-order-button");
    private By confirmCancellationButtonLocator = By.id("confirm-cancellation-button");

    // Constructor
    public OrderDetailsPage(WebDriver driver) {
        this.driver = driver;
    }

    // Methods
    public void cancelOrder() {
        WebElement cancelOrderButton = driver.findElement(cancelOrderButtonLocator);
        cancelOrderButton.click();
    }

    public void confirmCancellation() {
        WebElement confirmCancellationButton = driver.findElement(confirmCancellationButtonLocator);
        confirmCancellationButton.click();
    }
}
