// Independent checks of captured experiment evidence; does not control a guest.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import javax.xml.parsers.DocumentBuilderFactory
import org.w3c.dom.Element
import java.util.zip.ZipFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

require(args.size == 1) { "Usage: VerifyNative.main.kts RUN_DIRECTORY" }
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
val appPid = text("native-app-pid.toml").trim().substringAfter("= ").toInt()
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
require(text("native-helper-status.toml").trim() == "exit_code = 0")
require(text("native-status.toml").trim() == "exit_code = 0")
require(text("app-pid.txt").isBlank())
require(text("native-enforcing.txt").trim() == "Enforcing")
require(!text("native-before.txt").contains("frida", ignoreCase = true))
sealed interface Event
data class Ready(val pid: ULong) : Event
data class Binding(val base: ULong, val got: ULong) : Event
data class Opened(val fd: ULong) : Event
data class Request(val address: ULong, val length: ULong, val protection: ULong, val flags: ULong,
    val fd: ULong, val offset: ULong, val pc: ULong, val lr: ULong) : Event
data class Mapped(val base: ULong, val protection: ULong) : Event
data class Fault(val signal: ULong, val code: ULong, val address: ULong, val mapping: ULong,
    val offset: ULong, val pc: ULong, val relativePc: ULong, val opcode: ULong,
    val registers: List<ULong>) : Event
fun events(name: String): List<Event> = text(name).split("[[events]]").drop(1).map { section ->
    // Constrained serialized-data boundary; domain objects below are typed.
    val pairs = section.lineSequence().filter { it.isNotBlank() }.map {
        val pair = it.split(" = ", limit = 2); require(pair.size == 2)
        pair[0] to pair[1].removeSurrounding("\"")
    }.toList()
    val fields = pairs.toMap(); require(fields.size == pairs.size)
    fun number(key: String) = fields.getValue(key).removePrefix("0x").toULong(16)
    when(fields.getValue("kind")) {
        "ready" -> Ready(number("pid"))
        "stock-binding" -> Binding(number("base"), number("mmap_got"))
        "open-result" -> Opened(number("fd"))
        "mmap-request" -> Request(number("a0"), number("a1"), number("a2"), number("a3"),
            number("a4"), number("a5"), number("pc"), number("lr"))
        "mapping-result" -> Mapped(number("base"), number("protection"))
        "fault" -> Fault(number("signal"), number("si_code"), number("address"), number("mapping"),
            number("offset"), number("pc"), number("relative_pc"), number("opcode"),
            (0..30).map { number("x" + it.toString().padStart(2, '0')) })
        else -> error("Unreviewed native event")
    }
}
enum class Operation { READ, WRITE }
data class Access(val operation: Operation, val width: Int, val register: Int, val baseRegister: Int, val immediate: ULong)
fun decode(word: ULong): Access {
    require(word and 0x3f800000uL == 0x39000000uL) { "Unreviewed ARM64 instruction" }
    val width = 1 shl (word shr 30).toInt()
    return Access(if(word and 0x00400000uL != 0uL) Operation.READ else Operation.WRITE,
        width, (word and 31uL).toInt(), ((word shr 5) and 31uL).toInt(),
        ((word shr 10) and 4095uL) * width.toULong())
}
fun checkCapture(records: List<Event>): Pair<Fault, Access> {
    val opened = records.filterIsInstance<Opened>().single()
    val request = records.filterIsInstance<Request>().single()
    require(request.address == 0uL && request.length == 0x1000000uL && request.protection == 3uL &&
        request.flags == 1uL && request.fd == opened.fd && request.offset == 0uL)
    val mapped = records.filterIsInstance<Mapped>().single()
    require(mapped.base != 0uL && mapped.protection == 0uL)
    val fault = records.filterIsInstance<Fault>().single()
    require(records.last() == fault && fault.signal == 11uL && fault.code == 2uL)
    require(fault.mapping == mapped.base && fault.address == mapped.base + fault.offset)
    val access = decode(fault.opcode)
    require(access.width in listOf(4, 8) && access.baseRegister < 31)
    require(fault.address == fault.registers[access.baseRegister] + access.immediate)
    require(fault.offset + access.width.toULong() <= 0x1000000uL)
    return fault to access
}
for (which in 0..3) {
    require(text("native-control-$which-status.toml").trim() == "exit_code = 0")
    val (fault, access) = checkCapture(events("native-control-$which.toml"))
    require(fault.offset == 0x4048uL && access.width == if(which < 2) 4 else 8)
    require(access.operation == if(which % 2 == 0) Operation.READ else Operation.WRITE)
    if(access.operation == Operation.WRITE) require(fault.registers[access.register] == 0x1122334455667788uL)
}
val captured = events("native-events.toml")
require(captured.filterIsInstance<Ready>().single().pid == appPid.toULong())
val binding = captured.filterIsInstance<Binding>().single()
val (fault, access) = checkCapture(captured)
require(fault.pc == binding.base + fault.relativePc)
require(captured.filterIsInstance<Request>().single().lr == binding.base + 0x270284uL)
val native = ZipFile(run.resolve("installed.apk").toFile()).use {
    it.getInputStream(it.getEntry("lib/arm64-v8a/libscope-auklet.so")).readBytes()
}
require(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(native)) ==
    "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
require(fault.relativePc == 0x270604uL && access.operation == Operation.READ && access.width == 4)
require(ByteBuffer.wrap(native, fault.relativePc.toInt(), 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong() ==
    fault.opcode)
require(fault.offset == 0x4048uL)
println("control_accesses_verified = 4")
println("stock_operation = \"read\"")
println("stock_width = 4")
println("stock_offset = \"0x4048\"")
println("stock_pc = \"0x270604\"")
println("hardware_values_supplied = false")
