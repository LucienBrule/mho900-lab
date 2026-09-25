// Independent checks of captured experiment evidence; does not control a guest.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import javax.xml.parsers.DocumentBuilderFactory
import org.w3c.dom.Element
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.zip.ZipFile

require(args.size == 1) { "Usage: VerifySyscall.main.kts RUN_DIRECTORY" }
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
    "LABEL exact-stock uid=1000 before=default after=platform",
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
val appPid = text("syscall-app-pid.toml").trim().substringAfter("= ").toInt()
require(text("process-labels.txt").lineSequence().any {
    it.startsWith("u:r:system_app:s0") && it.endsWith("com.rigol.scope") &&
        it.trim().split(Regex("\\s+")).getOrNull(2) == appPid.toString()
}) { "No matching system_app process label" }
val log = text("application-logcat.txt")
require("No match for app with uid 1000" !in log)
require("am_on_resume_called: [0,com.rigol.scope.SplashActivity,LAUNCH_ACTIVITY]" in log)
require("Displayed com.rigol.scope/.SplashActivity" in log)
require("com.rigol.scope/.MainActivity" !in text("activities.txt"))
require(!text("crash-logcat.txt").contains("frida-agent"))
require(!text("crash-logcat.txt").contains(">>> system_server <<<"))
require(text("frida-detach-status.toml").trim() == "exit_code = 0")
val serverPids = text("system-server-pid.toml").lineSequence().filter { it.isNotBlank() }
    .map { it.substringAfter("= ").toInt() }.toList()
require(serverPids.size == 3 && serverPids.distinct().size == 1) { "system_server restarted" }
require("android.content.pm.ApplicationInfo.seinfo" in text("frida-inspection.txt"))
val scan = text("scan-package-oatdump.txt")
val assign = scan.indexOf("SELinuxMMAC.assignSeinfoValue")
val verify = scan.indexOf("PackageManagerService.verifySignaturesLP")
require(assign >= 0 && verify > assign) { "Unexpected framework assignment ordering" }

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
require(text("syscall-helper-status.toml").trim() == "exit_code = 0")
require(!text("syscall-before.txt").contains("frida", ignoreCase = true))
val outcome = text("syscall-outcome.toml").trim()
println(outcome)
when (outcome) {
    "outcome = \"observer unavailable\"" -> {
        require(text("syscall-tool-inventory.txt").contains("No such file"))
        require(text("app-pid.txt").trim() == appPid.toString())
    }
    "outcome = \"observer attach failed\"" -> {
        require(Regex("TracerPid:\\s+0").containsMatchIn(text("syscall-attached-status.txt")))
        require(text("syscall-status.txt").isNotBlank())
    }
    "outcome = \"observation completed\"" -> {
        require(text("syscall-control.txt").contains("/dev/null"))
        require(text("syscall-control.txt").contains("exited with 0"))
        require(text("syscall-enforcing.txt").trim() == "Enforcing")
        val trace = text("syscall-stock.txt")
        val open = Regex("openat\\(AT_FDCWD, \"/dev/xdma0_bypass\", O_RDWR\\|O_SYNC\\) = ([0-9]+)")
            .find(trace) ?: error("No successful bypass open")
        val fd = open.groupValues[1].toInt()
        val mapping = "mmap(NULL, 16777216, PROT_READ|PROT_WRITE, MAP_SHARED, $fd, 0) = -1 ENODEV"
        val mappingAt = trace.indexOf(mapping, open.range.last)
        require(mappingAt > open.range.last)
        // Android maps this stored ELF directly from the APK. Derive its ZIP data offset.
        val bytes = Files.readAllBytes(run.resolve("installed.apk"))
        val zip = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val end = (bytes.size - 22 downTo maxOf(0, bytes.size - 65557)).first {
            zip.getInt(it) == 0x06054b50
        }
        var entry = zip.getInt(end + 16)
        var nativeOffset = -1
        repeat(zip.getShort(end + 10).toInt() and 65535) {
            require(zip.getInt(entry) == 0x02014b50)
            val nameSize = zip.getShort(entry + 28).toInt() and 65535
            val extraSize = zip.getShort(entry + 30).toInt() and 65535
            val commentSize = zip.getShort(entry + 32).toInt() and 65535
            val name = String(bytes, entry + 46, nameSize, Charsets.UTF_8)
            if (name == "lib/arm64-v8a/libscope-auklet.so") {
                require(zip.getShort(entry + 10).toInt() == 0) { "Compressed native ELF" }
                val local = zip.getInt(entry + 42)
                require(zip.getInt(local) == 0x04034b50)
                nativeOffset = local + 30 + (zip.getShort(local + 26).toInt() and 65535) +
                    (zip.getShort(local + 28).toInt() and 65535)
            }
            entry += 46 + nameSize + extraSize + commentSize
        }
        require(nativeOffset > 0 && nativeOffset % 4096 == 0)
        val native = ZipFile(run.resolve("installed.apk").toFile()).use {
            it.getInputStream(it.getEntry("lib/arm64-v8a/libscope-auklet.so")).readBytes()
        }
        require(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(native)) ==
            "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
        val offsetText = nativeOffset.toString(16).padStart(8, '0')
        val base = text("syscall-before.txt").lineSequence().single {
            "/com.rigol.scope-" in it && " r-xp $offsetText " in it
        }.substringBefore('-').toULong(16)
        val faultPc = (base + 0x270604uL).toString(16).padStart(16, '0')
        val fault = "[$faultPc] --- SIGSEGV {si_signo=SIGSEGV, si_code=SEGV_MAPERR, si_addr=0x4047}"
        require(trace.indexOf(fault, mappingAt) > mappingAt)
        require(text("app-pid.txt").isBlank())
        println("mmap_errno = \"ENODEV\"")
        println("fault_pc = \"libscope-auklet.so+0x270604\"")
        println("fault_address = \"0x4047\"")
    }
    else -> error("Unreviewed outcome")
}
