import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 1) { "Usage: VerifyExclusive.main.kts RUN_DIRECTORY" }
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
for (expected in listOf("mode = \"exclusive\"", "boot = \"completed\"", "inspection = \"completed\"",
    "install = \"not_reached\"", "launch = \"not_reached\"")) require(expected in result) { "Missing result: $expected" }
require(text("guest-kernel.txt").contains("3.18.91+"))
val enforcing = text("exclusive-enforcing.txt").lineSequence().filter { it.isNotBlank() }.toList()
require(enforcing.size == 2 && enforcing.all { it.trim() == "Enforcing" })
require(text("exclusive-packages.txt").isBlank())
require(!text("exclusive-processes.txt").contains("sparrow", ignoreCase = true))
require(!text("exclusive-processes.txt").contains("frida", ignoreCase = true))
require(!text("exclusive-processes.txt").contains("com.rigol.scope", ignoreCase = true))

val control = run.resolve("exclusive-control.elf")
require(Files.isRegularFile(control))
val controlHash = sha256(control)
require(text("binary-sha256.txt").take(64) == controlHash)
for (index in 0..3) {
    require(sha256(run.resolve("exclusive-$index.elf")) == controlHash) { "Arm ELF changed: $index" }
    require(text("exclusive-$index-status.toml").trim() == "exit_code = 0")
}
val server = text("exclusive-system-server.toml").lineSequence().filter { it.isNotBlank() }.map {
    val p = it.split(" = ", limit = 2); require(p.size == 2); p[0] to p[1].toInt()
}.toMap()
require(server.keys == setOf("before", "after_root", "after_arm_0", "after_arm_1", "after_arm_2", "after_arm_3"))
require(server.values.distinct().size == 1)

data class Snapshot(val pc: ULong, val sp: ULong, val pstate: ULong, val x: List<ULong>)
data class Setup(val pid: ULong, val stepped: Boolean, val cloneFlags: ULong, val word: ULong, val log: ULong,
    val loop: ULong, val terminal: ULong, val attemptLimit: ULong, val stepLimit: ULong,
    val initialWord: ULong, val initialLogs: List<ULong>)
data class Instruction(val index: ULong, val pc: ULong, val opcode: ULong)
data class Stop(val index: ULong, val signal: ULong, val code: ULong, val address: ULong, val snapshot: Snapshot)
data class Terminal(val word: ULong, val attempts: ULong, val status: ULong, val loaded: ULong, val observerSteps: ULong, val logs: List<ULong>)
sealed interface Event
data class SetupEvent(val value: Setup) : Event
data class InitialEvent(val value: Snapshot) : Event
data class InstructionEvent(val value: Instruction) : Event
data class StopEvent(val value: Stop) : Event
data class TerminalEvent(val value: Terminal) : Event
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
fun parseEvents(path: String): List<Event> = text(path).split("[[events]]").drop(1).map { section ->
    val f = fields(section)
    when (f.getValue("kind")) {
        "setup" -> SetupEvent(Setup(number(f.getValue("pid")), number(f.getValue("stepped")) != 0uL, number(f.getValue("clone_flags")),
            number(f.getValue("word_address")), number(f.getValue("log_address")), number(f.getValue("loop_pc")), number(f.getValue("terminal_pc")),
            number(f.getValue("attempt_limit")), number(f.getValue("step_limit")), number(f.getValue("initial_word")),
            (0..7).map { number(f.getValue("s$it")) }))
        "initial" -> InitialEvent(snapshot(f))
        "instruction" -> InstructionEvent(Instruction(number(f.getValue("index")), number(f.getValue("pc")), number(f.getValue("opcode"))))
        "stop" -> StopEvent(Stop(number(f.getValue("index")), number(f.getValue("signal")), number(f.getValue("si_code")), number(f.getValue("address")), snapshot(f)))
        "terminal" -> TerminalEvent(Terminal(number(f.getValue("word")), number(f.getValue("attempts")), number(f.getValue("store_status")),
            number(f.getValue("loaded")), number(f.getValue("observer_steps")), (0..7).map { number(f.getValue("s$it")) }))
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
fun u32(o: Int): ULong = ByteBuffer.wrap(elf, o, 4).order(ByteOrder.LITTLE_ENDIAN).int.toUInt().toULong()
val expectedLoop = listOf(0x485f7e6auL, 0x480bfe68uL, 0xb82c7a8buL, 0x1100058cuL, 0x3400006buL, 0x6b0d019fuL, 0x54ffff43uL)
val expectedBrk = 0xd4202460uL

data class ArmOutcome(val setup: Setup, val terminal: Terminal, val stepped: Boolean, val attempts: ULong, val finalWord: ULong)
fun requireRegs(s: Snapshot, setup: Setup) {
    require(s.x[8] == 0uL && s.x[13] == setup.attemptLimit && s.x[19] == setup.word && s.x[20] == setup.log)
}
fun verifyArm(index: Int): ArmOutcome {
    val records = parseEvents("exclusive-$index.toml")
    val setup = (records.filterIsInstance<SetupEvent>().single()).value
    require(setup.cloneFlags == 17uL && setup.attemptLimit == 8uL && setup.stepLimit == 128uL && setup.initialWord == 1uL)
    require(setup.initialLogs.all { it == 0xffffffffuL })
    require(expectedLoop.mapIndexed { offset, opcode -> elfWord(setup.loop + offset.toULong() * 4uL) == opcode }.all { it })
    require(elfWord(setup.terminal) == expectedBrk)
    require(setup.terminal == setup.loop + 28uL && setup.word % 2uL == 0uL && setup.log % 4uL == 0uL)
    val initial = records.filterIsInstance<InitialEvent>().single().value
    require(records.first() is SetupEvent && records[1] is InitialEvent)
    val instructions = records.filterIsInstance<InstructionEvent>().map { it.value }
    val stops = records.filterIsInstance<StopEvent>().map { it.value }
    if (setup.stepped) require(instructions.size == stops.size && instructions.size <= setup.stepLimit.toInt())
    else require(instructions.isEmpty() && stops.size == 1)
    require(records.filterIsInstance<TerminalEvent>().size == 1 && records.filterIsInstance<TerminatedEvent>().size == 1)
    val terminal = records.filterIsInstance<TerminalEvent>().single().value
    val terminated = records.filterIsInstance<TerminatedEvent>().single().status
    require(terminated == 9uL && terminal.observerSteps == if (setup.stepped) instructions.size.toULong() else 0uL)
    require(terminal.attempts in 1uL..setup.attemptLimit && terminal.status in 0uL..1uL && terminal.loaded == 1uL)
    require(terminal.logs.drop(terminal.attempts.toInt()).all { it == 0xffffffffuL })
    require(terminal.logs.take(terminal.attempts.toInt()).dropLast(1).all { it == 1uL })
    require(terminal.logs[terminal.attempts.toInt() - 1] == terminal.status)
    require(terminal.word == if (terminal.status == 0uL) 0uL else 1uL)
    require(terminal.status == 0uL || terminal.attempts == setup.attemptLimit)
    requireRegs(stops.last().snapshot, setup)
    if (!setup.stepped) {
        val stop = stops.single(); require(stop.signal == 5uL && stop.code == 1uL && stop.address == stop.snapshot.pc && stop.snapshot.pc == setup.terminal)
        require(elfWord(stop.snapshot.pc) == expectedBrk)
        require(stop.snapshot.x[10] == terminal.loaded && stop.snapshot.x[11] == terminal.status && stop.snapshot.x[12] == terminal.attempts)
    } else {
        require(instructions.isNotEmpty())
        require(instructions.first().pc == initial.pc)
        require(instructions.map { it.index } == instructions.indices.map { it.toULong() })
        require(stops.map { it.index } == instructions.map { it.index })
        require(instructions.all { elfWord(it.pc) == it.opcode })
        require(instructions.zip(stops).all { (i, s) -> s.address == s.snapshot.pc &&
            if (i.opcode == expectedBrk) s.signal == 5uL && s.code == 1uL else s.signal == 5uL && s.code == 4uL })
        require(instructions.drop(1).zip(stops.dropLast(1)).all { (next, prior) -> next.pc == prior.snapshot.pc })
        val loopStart = instructions.indexOfFirst { it.pc == setup.loop }
        require(loopStart >= 0)
        var cursor = loopStart; var attempt = 1uL; var counter = 0uL; val statuses = mutableListOf<ULong>()
        while (cursor < instructions.size && attempt <= setup.attemptLimit) {
            fun op(expected: ULong): Stop {
                require(cursor < instructions.size && instructions[cursor].opcode == expected)
                val position = expectedLoop.indexOf(expected)
                require(position >= 0 && instructions[cursor].pc == setup.loop + position.toULong() * 4uL)
                val stop = stops[cursor]; requireRegs(stop.snapshot, setup)
                if(position != 4 && position != 6) require(stop.snapshot.pc == instructions[cursor].pc + 4uL)
                cursor++; return stop
            }
            val load = op(expectedLoop[0]); require(load.snapshot.x[10] == 1uL && load.snapshot.x[12] == counter)
            val store = op(expectedLoop[1]); require(store.snapshot.x[10] == 1uL && store.snapshot.x[12] == counter); require(store.snapshot.x[11] in 0uL..1uL); statuses.add(store.snapshot.x[11])
            op(expectedLoop[2]); val add = op(expectedLoop[3]); counter++; require(add.snapshot.x[12] == counter)
            val cbz = op(expectedLoop[4])
            if (store.snapshot.x[11] == 0uL) { require(cbz.snapshot.pc == setup.terminal); break }
            require(cbz.snapshot.pc == instructions[cursor].pc); val cmp = op(expectedLoop[5]); require(cmp.snapshot.pc == instructions[cursor].pc)
            val branch = op(expectedLoop[6]); attempt++
            if (attempt < setup.attemptLimit + 1uL) require(branch.snapshot.pc == setup.loop) else require(branch.snapshot.pc == setup.terminal)
        }
        require(cursor < instructions.size && instructions[cursor].opcode == expectedBrk && instructions[cursor].pc == setup.terminal)
        require(cursor + 1 == instructions.size)
        val brk = stops[cursor]; require(brk.signal == 5uL && brk.code == 1uL && brk.address == brk.snapshot.pc && brk.snapshot.pc == setup.terminal)
        require(brk.snapshot.x[10] == terminal.loaded && brk.snapshot.x[11] == terminal.status && brk.snapshot.x[12] == terminal.attempts)
        require(statuses == terminal.logs.take(terminal.attempts.toInt()))
    }
    val terminalEvent = records.filterIsInstance<TerminalEvent>().single()
    val terminatedEvent = records.filterIsInstance<TerminatedEvent>().single()
    val ordered: List<Event> = if (setup.stepped) {
        listOf(records[0], records[1]) + instructions.zip(stops).flatMap { (instruction, stop) ->
            listOf(InstructionEvent(instruction), StopEvent(stop))
        } + listOf(terminalEvent, terminatedEvent)
    } else listOf(records[0], records[1], StopEvent(stops.single()), terminalEvent, terminatedEvent)
    require(records == ordered) { "Unexpected event order or extra event" }
    return ArmOutcome(setup, terminal, setup.stepped, terminal.attempts, terminal.word)
}

val outcomes = (0..3).map { verifyArm(it) }
require(outcomes.map { it.setup.word }.distinct().size == 1 && outcomes.map { it.setup.log }.distinct().size == 1 &&
    outcomes.map { it.setup.loop }.distinct().size == 1 && outcomes.map { it.setup.terminal }.distinct().size == 1)
require(outcomes.map { it.stepped } == listOf(false, true, true, false))
require(outcomes.map { it.attempts }.all { it in 1uL..8uL })
val differential = outcomes[0].finalWord != outcomes[1].finalWord || outcomes[2].finalWord != outcomes[3].finalWord
println("differential_observed = $differential")
println("replicated_outcome_difference = ${outcomes[0].finalWord == outcomes[3].finalWord &&
    outcomes[1].finalWord == outcomes[2].finalWord && outcomes[0].finalWord != outcomes[1].finalWord}")
for ((i, outcome) in outcomes.withIndex()) {
    println("[[arms]]")
    println("index = $i")
    println("mode = \"${if (outcome.stepped) "step" else "cont"}\"")
    println("attempts = ${outcome.attempts}")
    println("status = ${outcome.terminal.status}")
    println("word = \"0x${outcome.finalWord.toString(16)}\"")
}
