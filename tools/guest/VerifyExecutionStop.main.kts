import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size in 1..2) { "Usage: VerifyExecutionStop.main.kts RUN_DIRECTORY [success|readback-mismatch]" }
val verificationMode = args.getOrNull(1) ?: "success"
require(verificationMode == "success" || verificationMode == "readback-mismatch") { "Unknown verification mode: $verificationMode" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
fun text(name: String): String = Files.readString(run.resolve(name))
fun sha256(path: Path): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)))
fun number(value: String): ULong = value.removePrefix("0x").toULong(16)

for (line in Files.readAllLines(run.resolve("evidence-sha256.txt"))) {
    require(line.length > 66)
    val path = Path.of(line.substring(66)).normalize()
    require(path.startsWith(run)) { "Evidence escaped run directory" }
    require(sha256(path) == line.take(64)) { "Evidence hash mismatch: ${path.fileName}" }
}
val result = text("result.toml")
for (expected in listOf("mode = \"execution\"", "boot = \"completed\"", "inspection = \"completed\"",
    "install = \"not_reached\"", "launch = \"not_reached\"")) {
    if (expected == "inspection = \"completed\"" && verificationMode == "readback-mismatch") continue
    require(expected in result) { "Missing result: $expected" }
}
if (verificationMode == "readback-mismatch") require("inspection = \"failed\"" in result)
require(text("guest-kernel.txt").contains("3.18.91+"))
val enforcing = text("execution-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()
require(enforcing.size == 2 && enforcing.all { it.trim() == "Enforcing" })
require(text("execution-packages.txt").isBlank())
val processes = text("execution-processes.txt")
require(!processes.contains("sparrow", ignoreCase = true))
require(!processes.contains("frida", ignoreCase = true))
require(!processes.contains("com.rigol.scope", ignoreCase = true))

val control = run.resolve("execution-control.elf")
require(Files.isRegularFile(control))
val controlHash = sha256(control)
require(text("binary-sha256.txt").take(64) == controlHash)
val expectedArmCount = if (verificationMode == "success") 5 else 2
for (index in 0 until expectedArmCount) {
    require(sha256(run.resolve("execution-$index.elf")) == controlHash) { "Arm ELF changed: $index" }
    val expectedExit = if (verificationMode == "readback-mismatch" && index == 1) 82 else 0
    require(text("execution-$index-status.toml").trim() == "exit_code = $expectedExit")
}
if (verificationMode == "readback-mismatch") {
    for (index in 2..4) {
        require(!Files.exists(run.resolve("execution-$index.toml")))
        require(!Files.exists(run.resolve("execution-$index-status.toml")))
        require(!Files.exists(run.resolve("execution-$index.elf")))
        require(!Files.exists(run.resolve("execution-$index-pull.txt")))
    }
}
val server = text("execution-system-server.toml").lineSequence().filter { it.isNotBlank() }.map {
    val p = it.split(" = ", limit = 2); require(p.size == 2); p[0] to p[1].toInt()
}.toMap()
val expectedServerKeys = if (verificationMode == "success")
    setOf("before", "after_root", "after_arm_0", "after_arm_1", "after_arm_2", "after_arm_3", "after_arm_4")
else setOf("before", "after_root", "after_arm_0", "after_arm_1")
require(server.keys == expectedServerKeys)
require(server.values.distinct().size == 1)

data class Snapshot(val pc: ULong, val sp: ULong, val pstate: ULong, val x: List<ULong>)
data class Setup(val pid: ULong, val useBreak: Boolean, val miss: Boolean, val cloneFlags: ULong,
    val word: ULong, val log: ULong, val loop: ULong, val terminal: ULong, val target: ULong,
    val attemptLimit: ULong, val initialWord: ULong, val initialLogs: List<ULong>)
data class DebugState(val result: ULong, val size: ULong, val info: ULong, val addresses: List<ULong>, val controls: List<ULong>)
data class Stop(val signal: ULong, val code: ULong, val address: ULong, val opcode: ULong, val snapshot: Snapshot)
data class Terminal(val word: ULong, val attempts: ULong, val status: ULong, val loaded: ULong, val logs: List<ULong>)
sealed interface Event
data class SetupEvent(val value: Setup) : Event
data class InitialEvent(val value: Snapshot) : Event
data class DebugEvent(val name: String, val value: DebugState) : Event
data class DebugSetEvent(val result: ULong) : Event
data class StopEvent(val value: Stop) : Event
data class TerminalEvent(val value: Terminal) : Event
data class ExpectedStopEvent(val value: String) : Event
data class ReadbackMismatchEvent(val marker: Boolean = true) : Event
data class TerminatedEvent(val status: ULong) : Event

fun fields(section: String): Map<String, String> {
    val pairs = section.lineSequence().filter { it.isNotBlank() }.map {
        val p = it.split(" = ", limit = 2); require(p.size == 2); p[0] to p[1].removeSurrounding("\"")
    }.toList()
    require(pairs.map { it.first }.toSet().size == pairs.size) { "Duplicate event field" }
    return pairs.toMap()
}
fun snapshot(f: Map<String, String>): Snapshot = Snapshot(number(f.getValue("pc")), number(f.getValue("sp")),
    number(f.getValue("pstate")), (0..30).map { number(f.getValue("x" + it.toString().padStart(2, '0'))) })
fun debugState(f: Map<String, String>): DebugState = DebugState(number(f.getValue("result")), number(f.getValue("size")),
    number(f.getValue("info")), (0..15).map { number(f.getValue("a" + it.toString().padStart(2, '0'))) },
    (0..15).map { number(f.getValue("c" + it.toString().padStart(2, '0'))) })
fun parseEvents(path: String): List<Event> = text(path).split("[[events]]").drop(1).map { section ->
    val f = fields(section)
    when (f.getValue("kind")) {
        "setup" -> SetupEvent(Setup(number(f.getValue("pid")), number(f.getValue("use_break")) != 0uL,
            number(f.getValue("miss")) != 0uL, number(f.getValue("clone_flags")), number(f.getValue("word_address")),
            number(f.getValue("log_address")), number(f.getValue("loop_pc")), number(f.getValue("terminal_pc")),
            number(f.getValue("target_pc")), number(f.getValue("attempt_limit")), number(f.getValue("initial_word")),
            (0..7).map { number(f.getValue("s$it")) }))
        "initial" -> InitialEvent(snapshot(f))
        "debug-before", "debug-request", "debug-after" -> DebugEvent(f.getValue("kind"), debugState(f))
        "debug-set" -> DebugSetEvent(number(f.getValue("result")))
        "stop" -> StopEvent(Stop(number(f.getValue("signal")), number(f.getValue("si_code")), number(f.getValue("address")),
            number(f.getValue("opcode")), snapshot(f)))
        "terminal" -> TerminalEvent(Terminal(number(f.getValue("word")), number(f.getValue("attempts")),
            number(f.getValue("store_status")), number(f.getValue("loaded")), (0..7).map { number(f.getValue("s$it")) }))
        "expected-stop", "unexpected-stop" -> ExpectedStopEvent(f.getValue("kind"))
        "debug-readback-mismatch" -> ReadbackMismatchEvent()
        "terminated" -> TerminatedEvent(number(f.getValue("status")))
        else -> error("Unexpected event: ${f.getValue("kind")}")
    }
}

val elf = Files.readAllBytes(control)
require(elf.size >= 64 && elf[0] == 0x7f.toByte() && elf[1] == 'E'.code.toByte() && elf[2] == 'L'.code.toByte() && elf[3] == 'F'.code.toByte())
require(elf[4].toInt() == 2 && elf[5].toInt() == 1)
fun u16(o: Int) = ByteBuffer.wrap(elf, o, 2).order(ByteOrder.LITTLE_ENDIAN).short.toInt() and 0xffff
fun u64(o: Int) = ByteBuffer.wrap(elf, o, 8).order(ByteOrder.LITTLE_ENDIAN).long.toULong()
require(u16(16) == 2 && u16(18) == 183)
val phoff = u64(32).toInt(); val phentsize = u16(54); val phnum = u16(56)
fun u32(o: Int): ULong = ByteBuffer.wrap(elf, o, 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
fun elfWord(address: ULong): ULong {
    for (i in 0 until phnum) {
        val p = phoff + i * phentsize
        if (u32(p) != 1uL) continue
        val offset = u64(p + 8); val vaddr = u64(p + 16); val filesz = u64(p + 32)
        if (address >= vaddr && address + 4uL <= vaddr + filesz) {
            val at = (offset + address - vaddr).toInt()
            return ByteBuffer.wrap(elf, at, 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
        }
    }
    error("ELF address is not file-backed: 0x${address.toString(16)}")
}
val expectedLoop = listOf(0x485f7e6auL, 0x480bfe68uL, 0xb82c7a8buL, 0x1100058cuL, 0x3400006buL, 0x6b0d019fuL, 0x54ffff43uL)
val expectedBrk = 0xd4202460uL
val expectedControl = 0x1e5uL

fun requireDebug(event: DebugEvent, expectedName: String, expectedSize: ULong, expectedResult: ULong,
    expectedInfo: ULong? = null, expectedAddress: ULong? = null, expectedControlValue: ULong? = null) {
    require(event.name == expectedName && event.value.result == expectedResult && event.value.size == expectedSize)
    expectedInfo?.let { require(event.value.info == it) }
    if (expectedAddress != null) {
        require(event.value.addresses[0] == expectedAddress && event.value.controls[0] == expectedControlValue)
        require(event.value.addresses.drop(1).all { it == 0uL } && event.value.controls.drop(1).all { it == 0uL })
    } else {
        require(event.value.addresses.all { it == 0uL } && event.value.controls.all { it == 0uL })
    }
}
fun verifyArm(index: Int): Setup {
    val records = parseEvents("execution-$index.toml")
    val setup = records.filterIsInstance<SetupEvent>().single().value
    require(setup.cloneFlags == 17uL && setup.attemptLimit == 8uL && setup.initialWord == 1uL)
    require(setup.initialLogs.all { it == 0xffffffffuL })
    require(setup.terminal == setup.loop + 28uL && setup.target == setup.terminal + if (setup.miss) 4uL else 0uL)
    require(expectedLoop.mapIndexed { offset, opcode -> elfWord(setup.loop + offset.toULong() * 4uL) == opcode }.all { it })
    require(elfWord(setup.terminal) == expectedBrk)
    val initial = records.filterIsInstance<InitialEvent>().single().value
    require(records.first() is SetupEvent && records[1] is InitialEvent)
    val debugBefore = records.filterIsInstance<DebugEvent>().filter { it.name == "debug-before" }
    val debugRequest = records.filterIsInstance<DebugEvent>().filter { it.name == "debug-request" }
    val debugAfter = records.filterIsInstance<DebugEvent>().filter { it.name == "debug-after" }
    val debugSet = records.filterIsInstance<DebugSetEvent>()
    require(debugBefore.size == (if (setup.useBreak) 1 else 0) && debugRequest.size == debugBefore.size &&
        debugAfter.size == debugBefore.size && debugSet.size == debugBefore.size)
    if (setup.useBreak) {
        requireDebug(debugBefore.single(), "debug-before", 264uL, 0uL)
        require(debugBefore.single().value.info and 0xffuL != 0uL)
        requireDebug(debugRequest.single(), "debug-request", 24uL, 0uL, debugBefore.single().value.info, setup.target, expectedControl)
        require(debugSet.single().result == 0uL)
        requireDebug(debugAfter.single(), "debug-after", 264uL, 0uL, debugBefore.single().value.info, setup.target, expectedControl)
    }
    val stops = records.filterIsInstance<StopEvent>().map { it.value }
    require(stops.size == 1)
    val stop = stops.single()
    val terminal = records.filterIsInstance<TerminalEvent>().single().value
    require(records.filterIsInstance<TerminatedEvent>().size == 1)
    require(records.filterIsInstance<ExpectedStopEvent>().size == 1)
    val expected = records.filterIsInstance<ExpectedStopEvent>().single().value
    require(expected == "expected-stop")
    require(stop.signal == 5uL && stop.address == stop.snapshot.pc && stop.opcode == elfWord(stop.snapshot.pc))
    require(stop.opcode == expectedBrk && stop.snapshot.pc == setup.terminal)
    val expectedCode = if (setup.useBreak && !setup.miss) 4uL else 1uL
    require(stop.code == expectedCode)
    require(terminal.word == if (terminal.status == 0uL) 0uL else 1uL)
    require(terminal.attempts in 1uL..setup.attemptLimit && terminal.status in 0uL..1uL && terminal.loaded == 1uL)
    require(terminal.logs.drop(terminal.attempts.toInt()).all { it == 0xffffffffuL })
    require(terminal.logs.take(terminal.attempts.toInt()).dropLast(1).all { it == 1uL })
    require(terminal.logs[terminal.attempts.toInt() - 1] == terminal.status)
    require(stop.snapshot.x[8] == 0uL && stop.snapshot.x[10] == terminal.loaded && stop.snapshot.x[11] == terminal.status &&
        stop.snapshot.x[12] == terminal.attempts && stop.snapshot.x[13] == setup.attemptLimit &&
        stop.snapshot.x[19] == setup.word && stop.snapshot.x[20] == setup.log)
    require(terminal.status == 0uL || terminal.attempts == setup.attemptLimit)
    require(records.filterIsInstance<TerminatedEvent>().single().status == 9uL)
    val terminalEvent = records.filterIsInstance<TerminalEvent>().single()
    val expectedEvent = records.filterIsInstance<ExpectedStopEvent>().single()
    val terminatedEvent = records.filterIsInstance<TerminatedEvent>().single()
    val ordered: List<Event> = if (setup.useBreak) {
        listOf(records[0], records[1], debugBefore.single(), debugRequest.single(), debugSet.single(), debugAfter.single(),
            StopEvent(stop), terminalEvent, expectedEvent, terminatedEvent)
    } else listOf(records[0], records[1], StopEvent(stop), terminalEvent, expectedEvent, terminatedEvent)
    require(records == ordered) { "Unexpected event order or extra event" }
    require(initial.pc != setup.terminal)
    return setup
}

fun verifyReadbackMismatch(index: Int): Setup {
    val records = parseEvents("execution-$index.toml")
    val setup = records.filterIsInstance<SetupEvent>().single().value
    require(setup.useBreak && !setup.miss && setup.cloneFlags == 17uL && setup.attemptLimit == 8uL && setup.initialWord == 1uL)
    require(setup.target == setup.terminal && setup.terminal == setup.loop + 28uL)
    require(setup.initialLogs.all { it == 0xffffffffuL })
    require(expectedLoop.mapIndexed { offset, opcode -> elfWord(setup.loop + offset.toULong() * 4uL) == opcode }.all { it })
    require(elfWord(setup.terminal) == expectedBrk)
    require(records.first() is SetupEvent && records[1] is InitialEvent)
    val before = records.filterIsInstance<DebugEvent>().single { it.name == "debug-before" }
    val request = records.filterIsInstance<DebugEvent>().single { it.name == "debug-request" }
    val after = records.filterIsInstance<DebugEvent>().single { it.name == "debug-after" }
    requireDebug(before, "debug-before", 264uL, 0uL)
    require(before.value.info and 0xffuL != 0uL)
    requireDebug(request, "debug-request", 24uL, 0uL, before.value.info, setup.target, expectedControl)
    require(records.filterIsInstance<DebugSetEvent>().single().result == 0uL)
    requireDebug(after, "debug-after", 264uL, 0uL, before.value.info, setup.target, 0x1e4uL)
    require(records.none { it is StopEvent || it is TerminalEvent || it is ExpectedStopEvent })
    require(records.filterIsInstance<ReadbackMismatchEvent>().size == 1)
    require(records.filterIsInstance<TerminatedEvent>().single().status == 9uL)
    val ordered: List<Event> = listOf(records[0], records[1], before, request,
        records.filterIsInstance<DebugSetEvent>().single(), after,
        records.filterIsInstance<ReadbackMismatchEvent>().single(), records.filterIsInstance<TerminatedEvent>().single())
    require(records == ordered) { "Unexpected partial-arm event order or extra event" }
    return setup
}

if (verificationMode == "success") {
    val setups = (0..4).map { verifyArm(it) }
    require(setups.map { it.useBreak to it.miss } == listOf(false to false, true to false, true to true, true to false, false to false))
    require(setups.map { it.word }.distinct().size == 1 && setups.map { it.log }.distinct().size == 1 &&
        setups.map { it.loop }.distinct().size == 1 && setups.map { it.terminal }.distinct().size == 1)
    println("mode = \"execution\"")
    println("arms = 5")
    for ((i, setup) in setups.withIndex()) {
        val terminal = parseEvents("execution-$i.toml").filterIsInstance<TerminalEvent>().single().value
        println("[[outcomes]]")
        println("index = $i")
        println("mode = \"${if (!setup.useBreak) "cont" else if (setup.miss) "miss" else "break"}\"")
        println("attempts = ${terminal.attempts}")
        println("store_status = ${terminal.status}")
        println("word = \"0x${terminal.word.toString(16)}\"")
        println("stop_code = ${if (!setup.useBreak || setup.miss) 1 else 4}")
    }
} else {
    val baseline = verifyArm(0)
    val partial = verifyReadbackMismatch(1)
    require(!baseline.useBreak && !baseline.miss && partial.useBreak && !partial.miss)
    require(baseline.word == partial.word && baseline.log == partial.log && baseline.loop == partial.loop && baseline.terminal == partial.terminal)
    println("mode = \"execution\"")
    println("inspection = \"readback_mismatch\"")
    println("baseline_arm = 0")
    println("partial_arm = 1")
    println("partial_exit = 82")
    println("continued_to_breakpoint = false")
}
