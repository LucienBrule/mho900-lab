// Correlate independent stock static evidence with captured live thread state.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.ZipFile

require(args.size == 2) { "Usage: VerifyStartup.main.kts RUN_DIRECTORY STATIC_DIRECTORY" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
val static = Path.of(args[1]).toAbsolutePath().normalize()
fun text(root: Path, name: String): String = Files.readString(root.resolve(name))
fun digest(bytes: ByteArray): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun verifyIndex(root: Path, name: String) {
    for (line in Files.readAllLines(root.resolve(name))) {
        val artifact = Path.of(line.substring(66)).normalize()
        require(artifact.startsWith(root) && artifact != root.resolve(name))
        require(digest(Files.readAllBytes(artifact)) == line.take(64)) { "Hash mismatch: $artifact" }
    }
}
verifyIndex(run, "evidence-sha256.txt")
verifyIndex(static, "checksums.txt")
val libraryHash = "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e"
ZipFile(run.resolve("installed.apk").toFile()).use { zip ->
    val entry = zip.getEntry("lib/arm64-v8a/libscope-auklet.so")
    require(digest(zip.getInputStream(entry).use { it.readBytes() }) == libraryHash)
}
require(libraryHash in text(static, "input-sha256.txt"))
val java = text(run, "startup-java.txt")
val main = java.substringAfter("\"main\" prio=").substringBefore("\n\"Jit thread")
for (expected in listOf("nanosleep", "usleep", "000000000027022c", "0000000000239110",
    "0000000000232558", "API.UI_StartBusiness(Native method)", "SplashActivity")) {
    require(expected in main) { "Missing main-thread frame: $expected" }
}
require("libscope-auklet.so" in java)
require("/data/app/com.rigol.scope-1/base.apk" in text(run, "startup-maps.txt"))
require("/dev/xdma*: No such file or directory" in text(run, "startup-files.txt"))
for (sample in 1..2) {
    val threads = text(run, "startup-threads-$sample.txt")
    require("com.rigol.scope\nhrtimer_nanosleep" in threads)
    // Preserve the known failed optional collector; SIGQUIT supplied the successful stack witness.
    require(text(run, "startup-native-$sample.toml").trim() == "exit_code = 127")
    require("debuggerd: not found" in text(run, "startup-native-$sample.txt"))
}
require(text(run, "startup-final-pid.txt").trim() == text(run, "app-pid.txt").trim())
val native = text(static, "native-startup.txt")
for (expected in listOf("2701fc:", "__open_2@plt", "27022c:", "usleep@plt", "#0x7530",
    "#0x3e8", "270280:", "mmap@plt", "#0x1000000", "232558:")) require(expected in native)
require("239110:" in text(static, "factory-init.txt"))
require("Dev_PCIeInit@plt" in text(static, "factory-init.txt"))
require("2f  64  65  76  2f  78  64  6d  61  30  5f  62  79  70  61  73" in
    text(static, "pcie-device-string.txt"))
val splash = text(static, "SplashActivity.java")
val start = splash.indexOf("API.getInstance().UI_StartBusiness")
val read = splash.indexOf("viewModelManager.readAll")
val next = splash.indexOf("SplashActivity.this.gotoMainActivity()")
require(start >= 0 && read > start && next > read)
require("System.loadLibrary(\"scope-auklet\")" in text(static, "cil.API.java"))
println("verified_run = \"${run.fileName}\"")
println("corroborated_boundary = \"Stock JNI main thread in PCIe device-open retry\"")
println("hardware_behavior_supplied = false")
