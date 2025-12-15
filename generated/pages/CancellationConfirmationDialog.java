 ```java
package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class CancellationConfirmationDialog {
    private WebDriver driver;
    private By confirmCancellationButton = By.xpath("//button[text()='Confirm Cancellation']");

    public CancellationConfirmationDialog(WebDriver driver) {
        this.driver = driver;
    }

    public void confirmCancellation() {
        WebDriverWait wait = new WebDriverWait(driver, 10);
        WebElement confirmButton = wait.until(ExpectedConditions.elementToBeClickable(confirmCancellationButton));
        confirmButton.click();
    }
}
```