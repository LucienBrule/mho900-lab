package lab.mho900.loader;

import android.app.Activity;
import android.os.Bundle;
import dalvik.system.BaseDexClassLoader;
import java.io.*;

/** Normal APK class-loader probe; no class-loader or native path overrides. */
public final class ProbeActivity extends Activity {
    private static native int marker();
    private static String quote(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\"";
    }
    private void save(String name, byte[] bytes) throws IOException {
        FileOutputStream out = openFileOutput(name, MODE_PRIVATE);
        try { out.write(bytes); out.getFD().sync(); } finally { out.close(); }
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            ClassLoader loader = getClassLoader();
            String found = ((BaseDexClassLoader) loader).findLibrary("scope-auklet");
            System.loadLibrary("scope-auklet");
            int value = marker();
            String result = "schema = \"mho900-lab.normal-apk-native-loader/1\"\n"
                + "pid = " + android.os.Process.myPid() + "\n"
                + "marker = " + value + "\n"
                + "found_library = " + quote(found) + "\n"
                + "native_library_dir = " + quote(getApplicationInfo().nativeLibraryDir) + "\n"
                + "source_dir = " + quote(getApplicationInfo().sourceDir) + "\n"
                + "class_loader = " + quote(loader.toString()) + "\n";
            FileInputStream in = new FileInputStream("/proc/self/maps");
            ByteArrayOutputStream maps = new ByteArrayOutputStream();
            byte[] buf = new byte[4096]; int count;
            try { while ((count = in.read(buf)) != -1) maps.write(buf, 0, count); }
            finally { in.close(); }
            save("maps.txt", maps.toByteArray());
            save("result.toml", result.getBytes("UTF-8"));
        } catch (Throwable failure) {
            try {
                StringWriter text = new StringWriter(); failure.printStackTrace(new PrintWriter(text));
                save("failure.txt", text.toString().getBytes("UTF-8"));
            } catch (IOException ignored) { android.util.Log.e("LoaderControl", "Evidence write failed", ignored); }
            android.util.Log.e("LoaderControl", "Probe failed", failure);
        }
    }
}
