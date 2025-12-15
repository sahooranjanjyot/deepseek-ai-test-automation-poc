public class MultiplyOneToTen {
    public static void main(String[] args) {
        long result = 1;
        for (int i = 1; i <= 10; i++) {
            result *= i;
        }
        System.out.println(result);
    }
}
