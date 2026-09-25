import java.nio.file.Files
import java.nio.file.Path

require(args.size in 1..2) { "Usage: VerifyPairControls.main.kts RUN_DIRECTORY [step-rejected]" }
val rejectedStep = args.size == 2
if(rejectedStep) require(args[1] == "step-rejected")
val run = Path.of(args[0]).toAbsolutePath().normalize()
fun text(name: String): String = Files.readString(run.resolve(name))
fun number(value: String): ULong = value.removePrefix("0x").toULong(16)

sealed interface Event
data class Fault(val signal: ULong, val code: ULong, val address: ULong, val mapping: ULong, val offset: ULong, val pc: ULong,
    val opcode: ULong, val registers: List<ULong>) : Event
data class Response(val value: ULong, val before: ULong, val after: ULong, val unchanged: ULong,
    val beforePc: ULong, val afterPc: ULong, val output: ULong) : Event
data class Boundary(val pc: ULong, val opcode: ULong, val value: ULong, val completed: ULong,
    val steps: ULong, val objectAddress: ULong, val got: ULong, val limit: ULong) : Event
data class StepBefore(val index: ULong, val pc: ULong, val opcode: ULong) : Event
data class StepAfter(val index: ULong, val pc: ULong, val signal: ULong, val code: ULong, val address: ULong) : Event
data class Rejected(val reason: String) : Event
data class Terminated(val status: ULong) : Event
data class Phase(val name: String) : Event

fun events(name: String): List<Event> = text(name).split("[[events]]").drop(1).map { section ->
    val pairs = section.lineSequence().filter { it.isNotBlank() }.map {
        val pair = it.split(" = ", limit = 2); require(pair.size == 2)
        pair[0] to pair[1].removeSurrounding("\"")
    }.toList()
    val fields = pairs.toMap(); require(fields.size == pairs.size)
    when (fields.getValue("kind")) {
        "ready", "open-result", "mmap-request", "mapping-result" -> Phase(fields.getValue("kind"))
        "fault" -> Fault(number(fields.getValue("signal")), number(fields.getValue("si_code")), number(fields.getValue("address")),
            number(fields.getValue("mapping")), number(fields.getValue("offset")), number(fields.getValue("pc")), number(fields.getValue("opcode")),
            (0..30).map { number(fields.getValue("x" + it.toString().padStart(2, '0'))) })
        "synthetic-response" -> Response(number(fields.getValue("value")), number(fields.getValue("destination_before")),
            number(fields.getValue("destination_after")), number(fields.getValue("other_registers_unchanged")),
            number(fields.getValue("pc_before")), number(fields.getValue("pc_after")), number(fields.getValue("output_address")))
        "step-before" -> StepBefore(number(fields.getValue("index")), number(fields.getValue("pc")), number(fields.getValue("opcode")))
        "step-after" -> StepAfter(number(fields.getValue("index")), number(fields.getValue("pc")),
            number(fields.getValue("signal")), number(fields.getValue("si_code")), number(fields.getValue("address")))
        "composition-boundary" -> Boundary(number(fields.getValue("pc")), number(fields.getValue("opcode")), number(fields.getValue("value")),
            number(fields.getValue("completed_reads")), number(fields.getValue("steps")), number(fields.getValue("object")),
            number(fields.getValue("got_slot")), number(fields.getValue("step_limit")))
        "response-guard-rejected" -> Rejected("response-guard-rejected")
        "step-rejected" -> Rejected("step-rejected")
        "terminated" -> Terminated(number(fields.getValue("status")))
        else -> error("Unexpected pair-control event: ${fields.getValue("kind")}")
    }
}
val phases = listOf("ready", "open-result", "mmap-request", "mapping-result").map { Phase(it) }

fun verifyPositive(): Unit {
    val records = events("native-pair-control.toml")
    val faults = records.filterIsInstance<Fault>()
    require(faults.size == 2) { "positive fault count" }
    require(faults[0].signal == 11uL && faults[0].code == 2uL && faults[0].offset == 0x4048uL)
    require(faults[1].signal == 11uL && faults[1].code == 2uL && faults[1].offset == 0x4044uL)
    require(faults[0].mapping != 0uL && faults[0].mapping == faults[1].mapping)
    require(faults.all { it.address == it.mapping + it.offset && (it.opcode and 0xffc0001fuL) == 0xb9400009uL })
    require(faults.all { it.address == it.registers[((it.opcode shr 5) and 31uL).toInt()] + ((it.opcode shr 10) and 4095uL) * 4uL })
    val responses = records.filterIsInstance<Response>()
    require(responses.size == 2) { "positive response count" }
    require(responses[0].value == 0xe1234567uL && responses[0].beforePc == faults[0].pc && responses[0].afterPc == faults[0].pc + 4uL)
    require(responses[1].value == 0x89abcdefuL && responses[1].beforePc == faults[1].pc && responses[1].afterPc == faults[1].pc + 4uL)
    require(responses.all { it.after == it.value && it.unchanged == 1uL })
    require(responses[0].before == faults[0].registers[9] && responses[1].before == faults[1].registers[9])
    val stepsBefore = records.filterIsInstance<StepBefore>()
    val stepsAfter = records.filterIsInstance<StepAfter>()
    if(rejectedStep) {
        val before = stepsBefore.single(); val after = stepsAfter.single()
        require(before.index == 0uL && after.index == 0uL && before.pc == responses.last().afterPc)
        require(before.opcode == 0xb3607d69uL && after.pc == before.pc + 4uL)
        require(after.signal == 5uL && after.code == 4uL && after.address == after.pc)
        val rejection = records.filterIsInstance<Rejected>().single()
        val terminated = records.filterIsInstance<Terminated>().single()
        require(rejection.reason == "step-rejected" && terminated.status == 9uL)
        require(records == phases + listOf(faults[0], responses[0], faults[1], responses[1],
            before, after, rejection, terminated))
        require(text("native-helper-status.toml").trim() == "exit_code = 73")
        for(name in listOf("native-events.toml", "native-before.txt", "native-pair-negative.toml")) {
            require(!Files.exists(run.resolve(name))) { "Unexpected later phase: $name" }
        }
        println("private_control_completed_reads = 2")
        println("single_step_pc_advance = 4")
        println("single_step_signal = 5")
        println("single_step_code = 4")
        println("stop_reason = \"step-code-mismatch\"")
        println("stock_device_responses = 0")
        return
    }
    require(stepsBefore.size == 3 && stepsAfter.size == 3) { "positive step count" }
    require(stepsBefore.map { it.index } == listOf(0uL, 1uL, 2uL))
    require(stepsAfter.map { it.index } == listOf(0uL, 1uL, 2uL))
    require(stepsAfter.all { it.signal == 5uL && it.code == 4uL && it.address == it.pc })
    require(stepsBefore[0].opcode == 0xb3607d69uL && stepsBefore[1].opcode == 0x9240e129uL)
    require(stepsBefore[2].opcode and 0xffc0001fuL == 0xf9000009uL)
    require(stepsBefore.first().pc == responses.last().afterPc)
    require(stepsBefore.zip(stepsAfter).all { (before, after) -> after.pc == before.pc + 4uL })
    require(stepsBefore.zipWithNext().all { (a, b) -> b.pc == records.filterIsInstance<StepAfter>().first { it.index == a.index }.pc })
    require(records.filterIsInstance<Boundary>().single().let { it.completed == 2uL && it.steps == 3uL && it.value == 0x0123456789abcdefuL })
    val boundary = records.filterIsInstance<Boundary>().single()
    require(boundary.limit == 256uL && boundary.got == 0uL && boundary.objectAddress != 0uL)
    require(responses.all { it.output == boundary.objectAddress })
    require(boundary.pc == stepsAfter.last().pc && boundary.opcode == 0xd503201fuL)
    require(records.indexOf(boundary) + 1 == records.indexOf(records.filterIsInstance<Terminated>().single()))
    require(records.filterIsInstance<Terminated>().single().status and 0x7fuL == 9uL)
    require(records.none { it is Rejected })
    val expected = phases + listOf(faults[0], responses[0], faults[1], responses[1]) +
        stepsBefore.zip(stepsAfter).flatMap { (before, after) -> listOf(before, after) } +
        listOf(boundary, records.filterIsInstance<Terminated>().single())
    require(records == expected) { "Positive event order or extra event" }
    println("positive_pair_control = \"verified\"")
}

fun verifyNegative(): Unit {
    val records = events("native-pair-negative.toml")
    val faults = records.filterIsInstance<Fault>()
    require(faults.size == 2) { "negative fault count" }
    require(faults[0].offset == 0x4048uL && faults[1].offset == 0x4040uL)
    require(faults.all { it.signal == 11uL && it.code == 2uL && it.mapping != 0uL })
    require(faults[0].mapping == faults[1].mapping)
    require(faults.all { it.address == it.mapping + it.offset && (it.opcode and 0xffc0001fuL) == 0xb9400009uL })
    require(faults.all { it.address == it.registers[((it.opcode shr 5) and 31uL).toInt()] + ((it.opcode shr 10) and 4095uL) * 4uL })
    require(records.filterIsInstance<Response>().size == 1) { "negative response count" }
    require(records.filterIsInstance<Response>().single().value == 0xe1234567uL)
    require(records.filterIsInstance<Response>().single().after == 0xe1234567uL && records.filterIsInstance<Response>().single().unchanged == 1uL)
    require(records.filterIsInstance<Rejected>().single().reason == "response-guard-rejected")
    require(records.none { it is StepBefore || it is StepAfter || it is Boundary })
    require(records.filterIsInstance<Terminated>().single().status and 0xffuL == 9uL)
    require(text("native-pair-negative-status.toml").trim() == "exit_code = 78")
    val response = records.filterIsInstance<Response>().single()
    require(response.before == faults[0].registers[9] && response.beforePc == faults[0].pc &&
        response.afterPc == faults[0].pc + 4uL)
    require(records == phases + listOf(faults[0], response, faults[1],
        records.filterIsInstance<Rejected>().single(), records.filterIsInstance<Terminated>().single()))
    println("negative_pair_control = \"verified\"")
}

for(which in 0..3) {
    require(text("native-control-$which-status.toml").trim() == "exit_code = 0")
    val records = events("native-control-$which.toml")
    val fault = records.filterIsInstance<Fault>().single()
    require(records == phases + fault)
    require(fault.signal == 11uL && fault.code == 2uL && fault.offset == 0x4048uL && fault.mapping != 0uL)
    require(fault.address == fault.mapping + fault.offset)
    require(fault.opcode and 0x3f800000uL == 0x39000000uL)
    val width = 1 shl (fault.opcode shr 30).toInt()
    require(width == if(which < 2) 4 else 8)
    val read = fault.opcode and 0x00400000uL != 0uL
    require(read == (which % 2 == 0))
    val register = (fault.opcode and 31uL).toInt()
    val base = ((fault.opcode shr 5) and 31uL).toInt()
    require(base < 31 && fault.address == fault.registers[base] +
        ((fault.opcode shr 10) and 4095uL) * width.toULong())
    if(!read) require(fault.registers[register] == 0x1122334455667788uL)
}
println("control_accesses_verified = 4")
verifyPositive()
if(!rejectedStep) verifyNegative()
