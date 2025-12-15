package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.util.List;

public class OrderHistoryPage {
    private WebDriver driver;
    private WebDriverWait wait;

    // TODO: Define locators
    private By orderHistoryTable = By.id("order-history-table");
    private By orderIdLinks = By.cssSelector("#order-history-table a[href*='/order/']");

    public OrderHistoryPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, 10);
    }

    public void navigateToOrderDetails(int orderIndex) {
        List<WebElement> orderLinks = driver.findElements(orderIdLinks);
        if (orderLinks.size() > orderIndex) {
            orderLinks.get(orderIndex).click();
        } else {
            throw new IndexOutOfBoundsException("Order index out of bounds");
        }
    }

    public boolean isOrderHistoryDisplayed() {
        return driver.findElement(orderHistoryTable).isDisplayed();
    }
}
