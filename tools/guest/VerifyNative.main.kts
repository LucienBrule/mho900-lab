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

require(args.size in 1..2) { "Usage: VerifyNative.main.kts RUN_DIRECTORY [single-read|two-word|two-word-budget|admission-only|admission-next-access]" }
val admissionNext = args.getOrNull(1) == "admission-next-access"
val admissionOnly = args.getOrNull(1) == "admission-only" || admissionNext
val singleRead = args.size == 2 && args[1] == "single-read"
val stepBudget = args.size == 2 && args[1] == "two-word-budget"
val twoWord = args.size == 2 && args[1] in listOf("two-word", "two-word-budget")
require(args.size == 1 || singleRead || twoWord || admissionOnly) { "Unknown verification mode" }
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
require(text("native-status.toml").trim() == "exit_code = ${if(stepBudget) 72 else if(admissionNext) 78 else 0}")
require(text("app-pid.txt").isBlank())
require(text("native-enforcing.txt").trim() == "Enforcing")
require(!text("native-before.txt").contains("frida", ignoreCase = true))
if (admissionOnly) {
    println("admission_preservation = \"verified\"")
    kotlin.system.exitProcess(0)
}
sealed interface Event
data class Ready(val pid: ULong) : Event
data class Binding(val base: ULong, val got: ULong) : Event
data class Opened(val fd: ULong) : Event
data class Request(val address: ULong, val length: ULong, val protection: ULong, val flags: ULong,
    val fd: ULong, val offset: ULong, val pc: ULong, val lr: ULong) : Event
data class Mapped(val base: ULong, val protection: ULong) : Event
data class Response(val value: ULong, val pcBefore: ULong, val pcAfter: ULong,
    val before: ULong, val after: ULong, val unchanged: ULong, val output: ULong) : Event
data class Output(val address: ULong, val raw: ULong, val completed: ULong) : Event
data class StepBefore(val index: ULong, val pc: ULong, val opcode: ULong) : Event
data class StepAfter(val index: ULong, val pc: ULong, val signal: ULong, val code: ULong, val address: ULong) : Event
data class Boundary(val pc: ULong, val opcode: ULong, val objectAddress: ULong, val gotSlot: ULong,
    val value: ULong, val completed: ULong, val steps: ULong, val limit: ULong) : Event
data class GlobalStore(val phase: String, val pc: ULong, val objectAddress: ULong, val value: ULong) : Event
data class Terminated(val status: ULong) : Event
data class Rejected(val reason: String) : Event
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
        "synthetic-response" -> Response(number("value"), number("pc_before"), number("pc_after"),
            number("destination_before"), number("destination_after"), number("other_registers_unchanged"),
            number("output_address"))
        "consumer-output" -> Output(number("address"), number("raw_word"), number("completed_reads"))
        "step-before" -> StepBefore(number("index"), number("pc"), number("opcode"))
        "step-after" -> StepAfter(number("index"), number("pc"), number("signal"), number("si_code"), number("address"))
        "composition-boundary" -> Boundary(number("pc"), number("opcode"), number("object"), number("got_slot"),
            number("value"), number("completed_reads"), number("steps"), number("step_limit"))
        "global-store-before" -> GlobalStore("before", number("pc"), number("object"), number("value"))
        "global-store-after" -> GlobalStore("after", number("pc"), number("object"), number("value"))
        "terminated" -> Terminated(number("status"))
        "response-guard-rejected", "step-rejected", "step-budget-exhausted" -> Rejected(fields.getValue("kind"))
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
fun checkCapture(records: List<Event>, index: Int = 0): Pair<Fault, Access> {
    val opened = records.filterIsInstance<Opened>().single()
    val request = records.filterIsInstance<Request>().single()
    require(request.address == 0uL && request.length == 0x1000000uL && request.protection == 3uL &&
        request.flags == 1uL && request.fd == opened.fd && request.offset == 0uL)
    val mapped = records.filterIsInstance<Mapped>().single()
    require(mapped.base != 0uL && mapped.protection == 0uL)
    val fault = records.filterIsInstance<Fault>()[index]
    require(fault.signal == 11uL && fault.code == 2uL)
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
    require(events("native-control-$which.toml").filterIsInstance<Fault>().size == 1)
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
fun nativeWord(offset: ULong): ULong =
    ByteBuffer.wrap(native, offset.toInt(), 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
data class ExecMap(val start: ULong, val end: ULong, val fileOffset: ULong, val path: String)
fun executableMaps(): List<ExecMap> = text("native-before.txt").lineSequence().mapNotNull { line ->
    val fields = line.trim().split(Regex("\\s+"))
    if (fields.size < 6 || !fields[1].contains('x')) null else {
        val range = fields[0].split("-", limit = 2)
        ExecMap(range[0].toULong(16), range[1].toULong(16), fields[2].toULong(16), fields.drop(5).joinToString(" "))
    }
}.toList()
fun sha256Hex(path: Path): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)))
require(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(native)) ==
    "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
require(fault.relativePc == 0x270604uL && access.operation == Operation.READ && access.width == 4)
require(ByteBuffer.wrap(native, fault.relativePc.toInt(), 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong() ==
    fault.opcode)
require(fault.offset == 0x4048uL)
if(singleRead) {
    val expected = text("native-test-word.toml").trim().substringAfter("\"0x").substringBefore('"').toULong(16)
    require(expected in listOf(0uL, 0x11223344uL))
    for((name, isStock) in listOf("native-step-control.toml" to false, "native-events.toml" to true)) {
        val records = events(name)
        val faults = records.filterIsInstance<Fault>()
        require(faults.size == 2)
        val response = records.filterIsInstance<Response>().single()
        val output = records.filterIsInstance<Output>().single()
        val (first, firstAccess) = checkCapture(records)
        val (second, secondAccess) = checkCapture(records, 1)
        require(first.offset == 0x4048uL && second.offset == 0x4044uL)
        require(listOf(firstAccess,secondAccess).all { it.operation == Operation.READ && it.width == 4 })
        require(response.value == expected && response.after == expected && response.unchanged == 1uL)
        require(response.pcBefore == first.pc && response.pcAfter == first.pc + 4uL)
        require(response.before == first.registers[9] && firstAccess.register == 9)
        require(records.indexOf(first) < records.indexOf(response) && records.indexOf(response) < records.indexOf(second))
        require(records.last() == output && output.address == response.output && output.completed == 1uL)
        require(output.raw and 0xffffffffuL == expected)
        if(isStock) require(second.pc == first.pc && second.opcode == first.opcode)
        else {
            require(response.before == ULong.MAX_VALUE && output.raw == expected) { "W-register zero extension failed" }
        }
    }
    println("synthetic_response = \"0x${expected.toString(16)}\"")
    println("next_offset = \"0x4044\"")
    println("completed_reads = 1")
} else if(twoWord) {
    val records = captured
    val faults = records.filterIsInstance<Fault>()
    require(faults.size == 2) { "two-word fault count" }
    require(faults[0].offset == 0x4048uL && faults[1].offset == 0x4044uL)
    require(faults.all { it.signal == 11uL && it.code == 2uL && it.opcode == 0xb9400109uL })
    val (firstFault, firstAccess) = checkCapture(records)
    val (secondFault, secondAccess) = checkCapture(records, 1)
    require(firstAccess.operation == Operation.READ && firstAccess.width == 4 && firstAccess.register == 9)
    require(secondAccess.operation == Operation.READ && secondAccess.width == 4 && secondAccess.register == 9)
    require(firstFault.address == firstFault.registers[firstAccess.baseRegister] + firstAccess.immediate)
    require(secondFault.address == secondFault.registers[secondAccess.baseRegister] + secondAccess.immediate)
    require(secondFault.pc == firstFault.pc && secondFault.relativePc == firstFault.relativePc)
    val responses = records.filterIsInstance<Response>()
    require(responses.size == 2) { "two-word response count" }
    require(responses[0].value == 0xe1234567uL && responses[1].value == 0x89abcdefuL)
    require(responses[0].pcBefore == faults[0].pc && responses[0].pcAfter == faults[0].pc + 4uL)
    require(responses[1].pcBefore == faults[1].pc && responses[1].pcAfter == faults[1].pc + 4uL)
    require(responses.all { it.after == it.value && it.unchanged == 1uL })
    require(responses[0].before == firstFault.registers[9] && responses[1].before == secondFault.registers[9])
    val before = records.filterIsInstance<StepBefore>()
    val after = records.filterIsInstance<StepAfter>()
    require(before.size == after.size && before.size <= 256 && before.isNotEmpty())
    require(before.map { it.index } == after.map { it.index })
    require(before.map { it.index } == before.indices.map { it.toULong() })
    require(before.first().pc == responses.last().pcAfter)
    require(before.drop(1).map { it.pc } == after.dropLast(1).map { it.pc })
    require(after.all { it.signal == 5uL && it.code == 4uL && it.address == it.pc })
    val libc = run.resolve("native-libc.so")
    require(Files.isRegularFile(libc))
    val libcManifest = text("native-libc-sha256.txt").lineSequence().first { it.isNotBlank() }
    require(libcManifest.length >= 64 && sha256Hex(libc) == libcManifest.take(64))
    val maps = executableMaps()
    require(maps.any { it.path.contains("base.apk") } && maps.any { it.path.endsWith("/libc.so") })
    for (step in before) {
        val mapping = maps.singleOrNull { step.pc >= it.start && step.pc + 4uL <= it.end }
            ?: error("step outside executable mapping")
        val expected = when {
            mapping.path.contains("base.apk") -> {
                require(mapping.start == binding.base)
                nativeWord(step.pc - binding.base)
            }
            mapping.path.endsWith("/libc.so") -> {
                val offset = step.pc - mapping.start + mapping.fileOffset
                require(offset + 4uL <= Files.size(libc).toULong())
                ByteBuffer.wrap(Files.readAllBytes(libc), offset.toInt(), 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
            }
            else -> error("unknown executable mapping ${mapping.path}")
        }
        require(step.opcode == expected) { "step opcode mismatch at 0x${(step.pc - mapping.start).toString(16)}" }
    }
    require(before.none { it.pc == binding.base + 0x42a2b4uL })
    if(stepBudget) {
        require(before.size == 256 && records.none { it is Boundary || it is GlobalStore || it is Output })
        val rejected = records.filterIsInstance<Rejected>().single()
        val terminated = records.filterIsInstance<Terminated>().single()
        require(rejected.reason == "step-budget-exhausted" && terminated.status == 9uL)
        val sequence: List<Event> = listOf(binding, records.filterIsInstance<Ready>().single(),
            records.filterIsInstance<Opened>().single(), records.filterIsInstance<Request>().single(),
            records.filterIsInstance<Mapped>().single(), faults[0], responses[0], faults[1], responses[1]) +
            before.zip(after).flatMap { (pre, post) -> listOf(pre, post) } + listOf(rejected, terminated)
        require(records == sequence) { "Budget outcome event order or extra event" }
        val libcMap = maps.single { it.path == "/system/lib64/libc.so" }
        val loop = libcMap.start + 0x68cb0uL - libcMap.fileOffset
        val firstLoop = before.indexOfFirst { it.pc == loop }
        require(firstLoop >= 0 && before.size - firstLoop > 6)
        val loopOpcodes = listOf(0x485f7e6auL, 0x480bfe68uL, 0x35ffffcbuL)
        for(index in firstLoop until before.size) {
            val phase = (index - firstLoop) % 3
            require(before[index].pc == loop + phase.toULong() * 4uL)
            require(before[index].opcode == loopOpcodes[phase])
            require(after[index].pc == loop + ((phase + 1) % 3).toULong() * 4uL)
        }
        println("completed_reads = 2")
        println("single_steps = 256")
        println("exclusive_retry_loop_first_step = $firstLoop")
        println("exclusive_retry_loop_steps = ${before.size - firstLoop}")
        println("stop_reason = \"step-budget-exhausted\"")
        println("stock_global_store_observed = false")
        println("pre_converter_boundary = false")
    } else {
    val boundary = records.filterIsInstance<Boundary>().single()
    require(boundary.pc == binding.base + 0x42a2b4uL && boundary.opcode == 0x97f7331fuL)
    require(boundary.gotSlot == binding.base + 0xb8d758uL && boundary.objectAddress == binding.base + 0xbbccf0uL)
    require(boundary.value == 0x0123456789abcdefuL && boundary.completed == 2uL && boundary.steps == before.size.toULong())
    require(boundary.limit == 256uL && boundary.pc == after.last().pc)
    val stores = records.filterIsInstance<GlobalStore>()
    require(stores.size == 2)
    val storeBefore = stores.single { it.phase == "before" }
    val storeAfter = stores.single { it.phase == "after" }
    require(storeBefore.pc == binding.base + 0x42a8ecuL && storeAfter.pc == binding.base + 0x42a8f0uL)
    require(storeBefore.objectAddress == binding.base + 0xbbccf0uL && storeAfter.objectAddress == storeBefore.objectAddress)
    require(storeBefore.value == 0x0123456789abcdefuL && storeAfter.value == storeBefore.value)
    require(records.indexOf(storeBefore) < records.indexOf(storeAfter) && records.indexOf(storeAfter) < records.indexOf(boundary))
    val terminated = records.filterIsInstance<Terminated>().single()
    require(terminated.status and 0x7fuL == 9uL)
    require(records.none { it is Rejected || it is Output })
    val sequence: List<Event> = listOf(binding, records.filterIsInstance<Ready>().single(),
        records.filterIsInstance<Opened>().single(), records.filterIsInstance<Request>().single(),
        records.filterIsInstance<Mapped>().single(), faults[0], responses[0], faults[1], responses[1]) +
        before.zip(after).flatMap { (pre, post) ->
            if(pre.pc == storeBefore.pc) listOf(pre, storeBefore, post, storeAfter) else listOf(pre, post)
        } + listOf(boundary, terminated)
    require(records == sequence) { "Stock event order or extra event" }
    println("two_word_value = \"0x0123456789abcdef\"")
    println("two_word_steps = ${before.size}")
    println("pre_converter_boundary = true")
    }
} else {
    require(captured.filterIsInstance<Fault>().size == 1 && captured.last() == fault)
    require(captured.none { it is Response || it is Output })
}
println("control_accesses_verified = 4")
println("stock_operation = \"read\"")
println("stock_width = 4")
println("stock_offset = \"0x4048\"")
println("stock_pc = \"0x270604\"")
println("synthetic_values_supplied = ${singleRead || twoWord}")
