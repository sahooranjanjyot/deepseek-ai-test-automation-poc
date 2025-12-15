 ```java
package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.util.List;

public class OrderHistoryPage {
    private WebDriver driver;
    private By orderHistoryTable = By.id("orderHistoryTable");
    private By orderRows = By.cssSelector("#orderHistoryTable tbody tr");
    private By orderIdLinks = By.cssSelector("#orderHistoryTable tbody tr td:first-child a");

    public OrderHistoryPage(WebDriver driver) {
        this.driver = driver;
    }

    public void navigateToOrderHistory() {
        // TODO: Click on Account menu and then click on Order History
    }

    public void openOrderDetailsPage(int orderIndex) {
        List<WebElement> rows = driver.findElements(orderRows);
        if (orderIndex < 0 || orderIndex >= rows.size()) {
            throw new IndexOutOfBoundsException("Order index out of bounds");
        }
        rows.get(orderIndex).findElements(orderIdLinks).get(0).click();
    }
}
```