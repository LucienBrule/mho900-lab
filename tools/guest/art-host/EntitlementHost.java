package lab.mho900.guest;

/** Real ART process host. Stock class initialization is left to the observer. */
public final class EntitlementHost {
    public static volatile boolean ready = false;

    private EntitlementHost() {}

    public static void main(String[] args) throws InterruptedException {
        ready = true;
        System.out.println("ART_HOST_READY lab.mho900.guest.EntitlementHost");
        System.out.flush();
        Thread.sleep(120000L);
        System.err.println("ART_HOST_TIMEOUT");
        System.err.flush();
        System.exit(79);
    }
}
