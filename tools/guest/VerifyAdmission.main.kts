// Independent checks of captured experiment evidence; does not control a guest.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import javax.xml.parsers.DocumentBuilderFactory
import org.w3c.dom.Element

require(args.size == 1) { "Usage: VerifyAdmission.main.kts RUN_DIRECTORY" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
fun text(name: String): String = Files.readString(run.resolve(name))
fun sha256(path: Path): String {
    val digest = MessageDigest.getInstance("SHA-256")
    Files.newInputStream(path).use { stream ->
        val buffer = ByteArray(65536)
        while (true) {
            val size = stream.read(buffer)
            if (size < 0) break
            digest.update(buffer, 0, size)
        }
    }
    return HexFormat.of().formatHex(digest.digest())
}
val stockHash = "6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b"
val stockSigner = "f48e7189aac174df7fd19acf58b6d15832760fcf25ac0a6d4bcd5fc1974d4c03"
val platformSigner = "c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8"
for (line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) {
    require(line.length > 66)
    val artifact = Path.of(line.substring(66)).normalize()
    require(artifact.startsWith(run)) { "Evidence escaped run directory" }
    require(sha256(artifact) == line.take(64)) { "Evidence hash mismatch: ${artifact.fileName}" }
}
val result = text("result.toml")
for (expected in listOf("boot = \"completed\"", "install = \"admitted\"", "launch = \"attempted\"",
    "inspection = \"completed\"")) require(expected in result) { "Incomplete run" }
val hook = text("admission-hook.txt").lineSequence().filter { it.isNotBlank() }.toList()
require(hook == listOf("admission-exception-ready",
    "REJECT lab.mho900.admission.control reason=package",
    "REJECT com.rigol.scope reason=signer",
    "REJECT com.rigol.scope reason=digest",
    "ADMIT exact-stock shared-user-error=-8")) { "Unexpected hook decisions" }
for (name in listOf("control-unrelated.txt", "control-different-signer.txt", "control-changed-bytes.txt",
    "unhooked-stock.txt", "detached-stock-update.txt")) {
    require("INSTALL_FAILED_SHARED_USER_INCOMPATIBLE" in text(name)) { "Expected rejection absent: $name" }
    require(!text(name).lineSequence().contains("Success"))
}
require(text("install.txt").lineSequence().contains("Success"))
require(sha256(run.resolve("installed.apk")) == stockHash) { "Installed bytes changed" }
require(stockSigner in text("installed-signature.txt"))
require(stockSigner in text("control-changed-bytes-signature.txt"))
require("Verified using v2 scheme (APK Signature Scheme v2): true" in text("control-changed-bytes-signature.txt"))
require(!text("zygote-maps.txt").contains("frida", ignoreCase = true))
require(text("zygote-maps.txt").contains("/system/bin/app_process64"))
require(text("app-pid.txt").isBlank()) { "Unexpected surviving application process" }
val log = text("application-logcat.txt")
require("No match for app with uid 1000, seinfo default, name com.rigol.scope" in log)
require("selinux_android_setcontext(1000, 0, \"default\", \"com.rigol.scope\") failed" in log)
require("Fatal signal 6 (SIGABRT)" in text("crash-logcat.txt"))
require(!text("crash-logcat.txt").contains("frida-agent"))
require(!text("crash-logcat.txt").contains(">>> system_server <<<"))
require(text("frida-detach-status.toml").trim() == "exit_code = 0")
val serverPids = text("system-server-pid.toml").lineSequence().filter { it.isNotBlank() }
    .map { it.substringAfter("= ").toInt() }.toList()
require(serverPids.size == 3 && serverPids.distinct().size == 1) { "system_server restarted" }
require(Files.list(run.resolve("tombstones")).use { paths ->
    paths.filter { Files.isRegularFile(it) }.anyMatch {
        Files.readString(it).contains("selinux_android_setcontext failed")
    }
}) { "No matching native tombstone" }

val factory = DocumentBuilderFactory.newInstance()
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
factory.isExpandEntityReferences = false
val document = factory.newDocumentBuilder().parse(run.resolve("packages.xml").toFile())
fun elements(tag: String): List<Element> {
    val nodes = document.getElementsByTagName(tag)
    return (0 until nodes.length).map { nodes.item(it) as Element }
}
fun certificate(parent: Element): String {
    val reference = parent.getElementsByTagName("cert").item(0) as Element
    val index = reference.getAttribute("index")
    val encoded = elements("cert").first {
        it.getAttribute("index") == index && it.hasAttribute("key")
    }.getAttribute("key")
    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(HexFormat.of().parseHex(encoded)))
}
val stock = elements("package").single { it.getAttribute("name") == "com.rigol.scope" }
val shared = elements("shared-user").single { it.getAttribute("name") == "android.uid.system" }
require(stock.getAttribute("sharedUserId") == "1000")
require(shared.getAttribute("userId") == "1000")
require(certificate(stock) == stockSigner) { "Stored APK certificate changed" }
require(certificate(shared) == platformSigner) { "Shared UID certificate changed" }
println("verified_run = \"${run.fileName}\"")
println("negative_controls_rejected = 3")
println("installed_apk_sha256 = \"$stockHash\"")
println("uid = 1000")
println("shared_uid_signer_preserved = true")
println("first_launch_failure = \"SELinux context lookup before application initialization\"")
