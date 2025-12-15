 ```java
package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class OrderDetailsPage {
    private WebDriver driver;
    private By cancelOrderButton = By.cssSelector("button.cancel-order");
    private By confirmationDialog = By.id("confirmation-dialog");
    private By confirmCancellationButton = By.cssSelector("button.confirm-cancel");

    public OrderDetailsPage(WebDriver driver) {
        this.driver = driver;
    }

    public void cancelOrder() {
        WebDriverWait wait = new WebDriverWait(driver, 10);
        WebElement cancelOrderBtn = wait.until(ExpectedConditions.elementToBeClickable(cancelOrderButton));
        cancelOrderBtn.click();

        WebElement confirmCancellationBtn = wait.until(ExpectedConditions.elementToBeClickable(confirmCancellationButton));
        confirmCancellationBtn.click();
    }
}
```