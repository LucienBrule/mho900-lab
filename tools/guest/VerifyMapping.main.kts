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

require(args.size in 1..2) { "Usage: VerifyMapping.main.kts RUN_DIRECTORY [capture|negative]" }
enum class ExpectedOutcome { CAPTURE, NEGATIVE }
val expectedOutcome = ExpectedOutcome.valueOf(args.getOrElse(1) { "capture" }.uppercase())
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
val appPid = text("mapping-app-pid.toml").trim().substringAfter("= ").toInt()
require(text("process-labels.txt").lineSequence().any {
    it.startsWith("u:r:system_app:s0") && it.endsWith("com.rigol.scope") &&
        it.trim().split(Regex("\\s+")).getOrNull(2) == appPid.toString()
}) { "No matching system_app process label" }
val log = text("application-logcat.txt")
require("No match for app with uid 1000" !in log)
require("am_on_resume_called: [0,com.rigol.scope.SplashActivity,LAUNCH_ACTIVITY]" in log)
require("Displayed com.rigol.scope/.SplashActivity" in log)
require("com.rigol.scope/.MainActivity" !in text("activities.txt"))
require(text("app-pid.txt").isBlank()) { "App still running" }
val signalExit = Regex("Zygote\\s*:\\s*Process $appPid exited due to signal \\(11\\)").containsMatchIn(log)
require("SIGSEGV" in text("crash-logcat.txt") ||
    (expectedOutcome == ExpectedOutcome.NEGATIVE && signalExit)) { "No signal-11 death witness" }
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
val nativeBytes = ZipFile(run.resolve("installed.apk").toFile()).use { zip ->
    zip.getInputStream(zip.getEntry("lib/arm64-v8a/libscope-auklet.so")).use { it.readBytes() }
}
require(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(nativeBytes)) ==
    "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
enum class Operation { READ, WRITE }
sealed interface Event { val sequence: Int }
data class ControlFault(override val sequence: Int, val operation: Operation, val width: Int, val source: ULong) : Event
data class ControlsPassed(override val sequence: Int, val faults: Int, val ordinary: Boolean) : Event
data class AdapterReady(override val sequence: Int, val pid: Int, val module: String, val preserved: Boolean) : Event
data class OpenRequest(override val sequence: Int, val path: String, val flags: ULong, val caller: ULong) : Event
data class OpenResult(override val sequence: Int, val fd: Int, val backing: String) : Event
data class MapRequest(override val sequence: Int, val address: ULong, val length: ULong, val protection: Int,
    val flags: Int, val fd: Int, val offset: ULong, val caller: ULong) : Event
data class MappingReady(override val sequence: Int, val base: ULong, val length: Int,
    val protection: String, val supplied: Boolean) : Event
data class UnsupportedAccess(override val sequence: Int, val operation: Operation, val offset: ULong,
    val width: Int, val pc: ULong, val instruction: String, val opcode: ULong,
    val register: Int, val valueBefore: ULong, val thread: Int, val completed: Boolean) : Event
data class UnhandledFault(override val sequence: Int, val type: String, val operation: Operation,
    val address: ULong, val region: ULong?) : Event
fun parseEvent(section: String): Event {
    // Raw fields exist only at this constrained TOML parsing boundary.
    val pairs = section.lineSequence().filter { it.isNotBlank() }.map { line ->
        val pair = line.split(" = ", limit = 2)
        require(pair.size == 2)
        pair[0] to pair[1]
    }.toList()
    val fields = pairs.toMap()
    require(fields.size == pairs.size) { "Duplicate event field" }
    fun value(key: String) = fields.getValue(key).removeSurrounding("\"")
    fun integer(key: String) = value(key).toInt()
    fun hex(key: String) = value(key).removePrefix("0x").toULong(16)
    fun bool(key: String) = value(key).toBooleanStrict()
    fun operation() = Operation.valueOf(value("operation").uppercase())
    val sequence = integer("sequence")
    return when (value("kind")) {
        "control-fault" -> ControlFault(sequence, operation(), integer("width"), hex("source"))
        "controls-passed" -> ControlsPassed(sequence, integer("faults"), bool("ordinary_memory"))
        "adapter-ready" -> AdapterReady(sequence, integer("pid"), value("stock_module"), bool("native_instructions_preserved"))
        "open-request" -> OpenRequest(sequence, value("path"), hex("flags"), hex("caller"))
        "open-result" -> OpenResult(sequence, integer("fd"), value("backing"))
        "mmap-request" -> MapRequest(sequence, hex("address"), hex("length"), integer("protection"),
            integer("flags"), integer("fd"), hex("offset"), hex("caller"))
        "mapping-ready" -> MappingReady(sequence, hex("base"), integer("length"),
            value("backing_protection"), bool("hardware_values_supplied"))
        "unsupported-mmio" -> UnsupportedAccess(sequence, operation(), hex("offset"), integer("width"),
            hex("pc"), value("instruction"), hex("opcode"), integer("register"), hex("value_before"),
            integer("thread"), bool("completed"))
        "unhandled-fault" -> UnhandledFault(sequence, value("type"), operation(), hex("address"),
            if (value("region") == "none") null else hex("region"))
        else -> error("Unexpected event: ${value("kind")}")
    }
}
val records = text("mapping-events.toml").split("[[events]]").drop(1).map(::parseEvent)
require(records.map { it.sequence } == (1..records.size).toList()) { "Reordered or missing events" }
val faults = records.filterIsInstance<ControlFault>()
require(faults.map { it.operation to it.width } ==
    listOf(Operation.WRITE to 4, Operation.READ to 4, Operation.WRITE to 8, Operation.READ to 8))
require(faults.all { it.source == 0x1122334455667788uL })
val controls = records.filterIsInstance<ControlsPassed>().single()
require(controls.faults == 4 && controls.ordinary)
val ready = records.filterIsInstance<AdapterReady>().single()
require(ready.pid == appPid && ready.preserved && ready.module == "libscope-auklet.so")
val opened = records.filterIsInstance<OpenRequest>().single()
require(opened.path == "/dev/xdma0_bypass" && opened.flags == 0x101002uL && opened.caller == 0x270200uL)
require(ready.sequence < opened.sequence) { "Open admitted before adapter readiness" }
val openedResult = records.filterIsInstance<OpenResult>().single()
require(openedResult.fd >= 0 && openedResult.backing == "/dev/null")
for (mapped in records.filterIsInstance<MapRequest>()) {
    require(mapped.fd == openedResult.fd && mapped.length == 0x1000000uL)
    require(mapped.address == 0uL && mapped.offset == 0uL && mapped.protection == 3 && mapped.flags == 1)
    require(mapped.caller == 0x270284uL)
}
for (mapping in records.filterIsInstance<MappingReady>()) {
    require(mapping.base != 0uL && mapping.length == 16777216 && mapping.protection == "---" && !mapping.supplied)
}
require(text("mapping-final-pid.txt").isBlank())
require(text("mapping-helper-status.toml").trim() == "exit_code = 0")
require(!text("mapping-zygote-maps.txt").contains("frida", ignoreCase = true))
if (expectedOutcome == ExpectedOutcome.NEGATIVE) {
    require(records.none { it is UnsupportedAccess }) { "A complete capture exists; evaluate it separately" }
    val mappings = records.filterIsInstance<MappingReady>()
    val negativeStage: String
    if (mappings.isEmpty()) {
        val fault = records.filterIsInstance<UnhandledFault>().single()
        require(fault == records.last() && fault.type == "access-violation" && fault.region == null)
        require(fault.operation == Operation.READ && fault.address == 0x4047uL)
        require(records.none { it is MapRequest })
        require("fault addr 0x4047" in text("crash-logcat.txt"))
        negativeStage = "mapping interception absent"
    } else {
        val mapping = mappings.single()
        require(records.filterIsInstance<MapRequest>().size == 1 && mapping == records.last())
        require(records.none { it is UnhandledFault })
        require(signalExit && text("crash-logcat.txt").isBlank())
        Files.walk(run.resolve("tombstones")).use { artifacts ->
            require(artifacts.noneMatch { Files.isRegularFile(it) }) { "Unreviewed tombstone present" }
        }
        // Process death is witnessed, but its fault address and instruction are unknown.
        negativeStage = "mapping captured; signal-11 exit; fault metadata absent"
    }
    println("verified_evidence_run = \"${run.fileName}\"")
    println("hypothesis_supported = false")
    println("outcome = \"$negativeStage\"")
    println("private_access_controls_passed = 4")
    println("negative_admission_controls_rejected = 3")
    println("system_server_stable = true")
    println("hardware_values_supplied = false")
} else {
require(records.filterIsInstance<MapRequest>().size == 1 && records.filterIsInstance<MappingReady>().size == 1)
val stop = records.filterIsInstance<UnsupportedAccess>().singleOrNull()
    ?: error("No unique complete unsupported-access witness; do not classify this as a validated capture")
require(stop == records.last() && !stop.completed && stop.width in listOf(4, 8))
require(stop.offset + stop.width.toULong() <= 16777216uL)
// These call-site semantics were independently disassembled in stock/accessors.txt.
data class InstructionWitness(val pc: ULong, val operation: Operation, val width: Int, val opcode: ULong)
val instructions = listOf(InstructionWitness(0x27043cuL, Operation.WRITE, 4, 0xb9000109uL),
    InstructionWitness(0x270604uL, Operation.READ, 4, 0xb9400109uL),
    InstructionWitness(0x27056cuL, Operation.WRITE, 8, 0xf9000128uL))
val instruction = instructions.singleOrNull { it.pc == stop.pc } ?: error("New instruction requires static review")
require(stop.operation == instruction.operation && stop.width == instruction.width && stop.opcode == instruction.opcode)
// All three sites lie in the captured first PT_LOAD, whose file offset equals virtual address.
require(ByteBuffer.wrap(nativeBytes, stop.pc.toInt(), 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong() == stop.opcode)
println("verified_run = \"${run.fileName}\"")
println("negative_controls_rejected = 3")
println("installed_apk_sha256 = \"$stockHash\"")
println("uid = 1000")
println("shared_uid_signer_preserved = true")
println("operation = \"${stop.operation.name.lowercase()}\"")
println("offset = \"0x${stop.offset.toString(16)}\"")
println("width = ${stop.width}")
println("pc = \"0x${stop.pc.toString(16)}\"")
println("hardware_values_supplied = false")
}
