package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class CancellationConfirmationDialog {
    private WebDriver driver;
    private WebDriverWait wait;

    // Locators
    private By confirmCancellationButtonLocator = By.xpath("TODO"); // Define the actual locator

    // Constructor
    public CancellationConfirmationDialog(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, 10);
    }

    // Method to confirm cancellation
    public void confirmCancellation() {
        WebElement confirmCancellationButton = wait.until(ExpectedConditions.elementToBeClickable(confirmCancellationButtonLocator));
        confirmCancellationButton.click();
    }
}
