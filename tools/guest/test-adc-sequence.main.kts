// Host-only synthetic controls for VerifyAdcSequence.main.kts.
// These fixtures are generated evidence-shape tests, not guest outcomes.
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.HexFormat

val repo = Path.of("").toAbsolutePath().normalize()
val seed = repo.resolve("out/guest-admission/private-adc-input-capture-01")
val native = repo.resolve("out/adc-sequence-profile/native-build02/group-observer")
val verifier = repo.resolve("tools/guest/VerifyAdcSequence.main.kts")
val profilePath = repo.resolve("experiments/adc-sequence/profile.toml")
val profileHeaderPath = repo.resolve("tools/guest/adc-sequence-profile.h")
require(args.size == 1) { "Usage: test-adc-sequence.main.kts NEW_OUTPUT" }
val root = Path.of(args[0]).toAbsolutePath().normalize()
require(!Files.exists(root)) { "NEW_OUTPUT must not exist" }
val nativeSymbols: Map<String, ULong> = ProcessBuilder("nm", "-n", native.toString()).start().let { process ->
    val rows = process.inputStream.bufferedReader().readLines(); require(process.waitFor() == 0); rows.mapNotNull { line ->
        val field = line.trim().split(Regex("\\s+")); if (field.size == 3) field[2] to field[0].toULong(16) else null
    }.toMap()
}
require(Files.isRegularFile(verifier) && Files.isRegularFile(native) && Files.isDirectory(seed))

data class Operation(val index: Int, val sequenceIndex: ULong, val read: Boolean, val offset: ULong, val value: ULong)
data class Guard(val index: Int, val source: String, val offset: ULong, val width: Int, val expected: ULong)
fun number(value: String): ULong = if (value.startsWith("0x")) value.drop(2).toULong(16) else value.toULong()
fun blocks(source: String, marker: String, until: String?): List<Map<String, String>> {
    val region = source.substringAfter(marker).let { if (until == null) it else it.substringBefore(until) }
    return region.split(marker).filter { it.isNotBlank() }.map { block ->
        block.lineSequence().takeWhile { !it.startsWith("[[") }.filter { " = " in it }.associate { line ->
            val pair = line.split(" = ", limit = 2); pair[0] to pair[1].removeSurrounding("\"")
        }
    }
}
val profileText = Files.readString(profilePath)
val operations = blocks(profileText, "[[operations]]", null).map { row ->
    val read = row.getValue("kind") == "R32"
    Operation(number(row.getValue("index")).toInt(), number(row.getValue("sequence_index")), read, number(row.getValue("offset")), number(row.getValue(if (read) "synthetic_value" else "value")))
}
fun guards(marker: String, until: String?): List<Guard> = blocks(profileText, marker, until).map { row ->
    Guard(number(row.getValue("index")).toInt(), row.getValue("source"), number(row.getValue("offset")), number(row.getValue("width")).toInt(), number(row.getValue("expected_bits")))
}
val entryGuards = guards("[[guards]]", "[[operations]]")
val finalHeader = Files.readString(profileHeaderPath).substringAfter("ap_final_shadows[AP_FINAL_SHADOWS]").substringAfter('{').substringBefore("};")
val finalGuards = Regex("\\{(\\d+)U,0x([0-9a-f]+)U(?:L)?,(\\d+)U,0x([0-9a-f]+)U(?:L)?}").findAll(finalHeader).mapIndexed { index, match ->
    val group = match.groupValues; Guard(index, group[1], group[2].toULong(16), group[3].toInt(), group[4].toULong(16))
}.toList()
require(operations.size == 99 && operations.count { it.read } == 2 && entryGuards.size == 175 && finalGuards.size == 33)

fun event(kind: String, fields: List<Pair<String, String>>): String = buildString {
    append("\n[[events]]\nkind = \"").append(kind).append("\"\n")
    fields.forEach { (key, value) -> append(key).append(" = ").append(value).append('\n') }
}
fun hex(value: ULong): String = "\"0x" + value.toString(16).padStart(16, '0') + "\""
fun numeric(key: String, value: ULong) = key to hex(value)
fun quoted(key: String, value: String) = key to "\"$value\""
fun registers(kind: String, pid: ULong, pc: ULong, x9: ULong, x8: ULong = 8uL): String {
    val fields = mutableListOf(numeric("tid", pid), numeric("pc", pc), numeric("sp", 0x200000uL), numeric("pstate", 0uL))
    (0..30).forEach { index -> fields += numeric("x" + index.toString().padStart(2, '0'), when(index) { 8 -> x8; 9 -> x9; else -> index.toULong() }) }
    return event(kind, fields)
}
fun registersFrom(kind: String, fields: Map<String, String>): String = event(kind, listOf("tid", "pc", "sp", "pstate").map { it to "\"${fields.getValue(it)}\"" } + (0..30).map { index -> val key = "x" + index.toString().padStart(2, '0'); key to "\"${fields.getValue(key)}\"" })
fun debug(kind: String, address: ULong, control: ULong, request: Boolean): String {
    val fields = mutableListOf(numeric("result", 0uL), numeric("size", if (request) 24uL else 264uL), numeric("info", 0x606uL))
    (0..15).forEach { index -> val n = index.toString().padStart(2, '0'); fields += numeric("a$n", if (index == 0) address else 0uL); fields += numeric("c$n", if (index == 0) control else 0uL) }
    return event(kind, fields)
}
fun patchLittleEndian(path: Path, offset: Int, width: Int, value: ULong) {
    val bytes = Files.readAllBytes(path); require(offset + width <= bytes.size)
    repeat(width) { bytes[offset + it] = (value shr (8 * it)).toByte() }; Files.write(path, bytes)
}
val sourceFiles = mapOf(
    "SETTING" to "adc-input-setting.bin", "DRV" to "adc-input-drvparam.bin",
    "CONFIG" to "adc-input-config.bin", "SAMPLE" to "adc-input-sample-entry.bin", "LOW" to "adc-input-shadow-low.bin",
    "HIGH" to "adc-input-shadow-high.bin", "GLOBAL" to "adc-input-global-inputs.bin", "SERIES" to "adc-input-series.bin"
)
fun copyFresh(from: Path, to: Path) { Files.createDirectories(to.parent); Files.copy(from, to, StandardCopyOption.REPLACE_EXISTING); require(!Files.isSameFile(from, to)) }
fun sha256(path: Path): String = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)))
fun fnv1a64(bytes: ByteArray): ULong { var hash=0xcbf29ce484222325uL; bytes.forEach { hash=(hash xor (it.toInt() and 255).toULong())*0x100000001b3uL }; return hash }
fun little(bytes: ByteArray, offset: Int, width: Int): ULong { var value=0uL; repeat(width) { value=value or ((bytes[offset+it].toInt() and 255).toULong() shl (8*it)) }; return value }

fun buildFixture(directory: Path) {
    Files.createDirectories(directory.resolve("adc-sequence")); Files.createDirectories(directory.resolve("source"))
    copyFresh(profilePath, directory.resolve("adc-sequence/profile.toml")); copyFresh(profileHeaderPath, directory.resolve("source/adc-sequence-profile.h"))
    copyFresh(native, directory.resolve("group-control.elf")); copyFresh(native, directory.resolve("adcseq-101.elf"))
    copyFresh(seed.resolve("reference.tsv"), directory.resolve("reference.tsv")); copyFresh(seed.resolve("spu-private.bin"), directory.resolve("spu-private.bin"))
    Files.writeString(directory.resolve("adcseq-101-status.toml"), "exit_code = 78\n")
    val captures = listOf("loader-entry-lsb.bin", "loader-entry-adc.bin", "loader-terminal-lsb.bin", "loader-terminal-adc.bin", "loader-terminal-vertical.bin") +
        listOf("adc-input-matrix.bin", "adc-input-setting.bin", "adc-input-drvparam.bin", "adc-input-series.bin", "adc-input-config.bin", "adc-input-sample-entry.bin", "adc-input-shadow-low.bin", "adc-input-shadow-high.bin", "adc-input-global-inputs.bin")
    captures.forEach { name -> copyFresh(seed.resolve("adcinput-90-$name"), directory.resolve("adcseq-101-$name")) }
    copyFresh(seed.resolve("adcinput-90-adc-input-maps.txt"), directory.resolve("adcseq-101-adc-input-maps.txt"))
    // The sequence fixture replaces the captured ADC record with the guarded zero-based record.
    Files.write(directory.resolve("adcseq-101-loader-terminal-adc.bin"), ByteArray(1936)); Files.write(directory.resolve("adcseq-101-loader-entry-adc.bin"), ByteArray(1936))
    entryGuards.filter { it.source == "ADC_RECORD" }.forEach { guard ->
        patchLittleEndian(directory.resolve("adcseq-101-loader-terminal-adc.bin"), guard.offset.toInt(), guard.width, guard.expected)
        patchLittleEndian(directory.resolve("adcseq-101-loader-entry-adc.bin"), guard.offset.toInt(), guard.width, guard.expected)
    }
    val samplePath = directory.resolve("adcseq-101-adc-input-sample-entry.bin")
    Files.write(samplePath, ByteArray(8) { (17 * it + 13).toByte() })
    entryGuards.filter { it.source in sourceFiles }.forEach { guard -> patchLittleEndian(directory.resolve("adcseq-101-${sourceFiles.getValue(guard.source)}"), guard.offset.toInt(), guard.width, guard.expected) }

    var inherited = Files.readString(seed.resolve("adcinput-90.toml"))
    inherited = inherited.replaceFirst("arm = \"0x000000000000005a\"", "arm = \"0x0000000000000065\"")
    inherited = mutateEvent(inherited, "adc-input-mode", 0, "arm", hex(101uL))
    val oldSampleAddress = number(inherited.split("[[events]]").drop(1).first { "kind = \"adc-input-capture\"" in it && "name = \"adc-input-sample-entry.bin\"" in it }.lineSequence().first { it.startsWith("address = ") }.substringAfter("= ").removeSurrounding("\""))
    inherited = mutateEvent(inherited, "adc-input-capture", 5, "address", hex(oldSampleAddress - 0x10uL))
    listOf("matrix", "setting", "drvparam", "series", "config", "sample-entry", "shadow-low", "shadow-high", "global-inputs").forEachIndexed { index, name ->
        inherited = mutateEvent(inherited, "adc-input-capture", index, "hash_fnv1a64", hex(fnv1a64(Files.readAllBytes(directory.resolve("adcseq-101-adc-input-$name.bin")))))
    }
    inherited = mutateEvent(inherited, "adc-input-map", 24, "address", hex(oldSampleAddress - 0x10uL))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "raw_mask", hex(0uL))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "normalized_mask", hex(0uL))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "mode", hex(little(Files.readAllBytes(samplePath), 4, 4)))
    val configBytes = Files.readAllBytes(directory.resolve("adcseq-101-adc-input-config.bin")); val drvBytes = Files.readAllBytes(directory.resolve("adcseq-101-adc-input-drvparam.bin"))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "config_adcs_delay", hex(little(configBytes, 0x20, 4)))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "config_point_time", hex(little(configBytes, 0x38, 4)))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "sample_rate", hex(little(drvBytes, 8, 8)))
    inherited = mutateEvent(inherited, "model-binding", 0, "first_pc", hex(nativeSymbols.getValue("gm_first_pc")))
    inherited = mutateEvent(inherited, "model-binding", 0, "second_pc", hex(nativeSymbols.getValue("gm_second_pc")))
    inherited = mutateEvent(inherited, "model-binding", 0, "write_pc", hex(nativeSymbols.getValue("gm_write_pc")))
    inherited = mutateEvent(inherited, "model-binding", 0, "store_pc", hex(nativeSymbols.getValue("gm_store_pc")))
    listOf("gm_tail_private", "gm_loader_private", "gm_private_leader", "gm_cl_cp0", "gm_cl_cp1", "gm_cl_cp2").forEachIndexed { index, symbol ->
        inherited = mutateEvent(inherited, "loader-binding", index, "actual_target", hex(nativeSymbols.getValue(symbol)))
        inherited = mutateEvent(inherited, "loader-binding", index, "expected_target", hex(nativeSymbols.getValue(symbol)))
    }
    listOf("gm_cl_cp0", "gm_cl_cp1", "gm_cl_cp2", "gm_cl_cp3").forEachIndexed { index, symbol ->
        val pc = hex(nativeSymbols.getValue(symbol))
        inherited = mutateEvent(inherited, "loader-debug-arm-request", index, "a00", pc)
        inherited = mutateEvent(inherited, "loader-debug-arm-after", index, "a00", pc)
        inherited = mutateEvent(inherited, "loader-debug-ready", index, "target", pc)
        inherited = mutateEvent(inherited, "loader-debug-before", index + 1, "a00", pc)
        inherited = mutateEvent(inherited, "loader-checkpoint", index, "pc", pc)
        inherited = mutateEvent(inherited, "loader-checkpoint", index, "address", pc)
        inherited = mutateEvent(inherited, "loader-checkpoint", index, "expected_pc", pc)
        inherited = mutateEvent(inherited, "loader-checkpoint-registers", index, "pc", pc)
        inherited = mutateEvent(inherited, "loader-debug-registers", index + 1, "pc", pc)
    }
    val modeLine = Regex("kind = \"model-mode\"[\\s\\S]*?pid = \"(0x[0-9a-f]+)\"").find(inherited) ?: error("seed pid")
    val pid = number(modeLine.groupValues[1])
    val mappingLine = Regex("kind = \"mapping-result\"[\\s\\S]*?base = \"(0x[0-9a-f]+)\"").find(inherited) ?: error("seed mapping")
    val mapping = number(mappingLine.groupValues[1]); val returnPc = nativeSymbols.getValue("gm_ap_cp")
    patchLittleEndian(directory.resolve("adcseq-101-adc-input-global-inputs.bin"), 0, 8, mapping)
    patchLittleEndian(directory.resolve("adcseq-101-adc-input-global-inputs.bin"), 12, 4, 0uL)
    inherited = mutateEvent(inherited, "adc-input-capture", 8, "hash_fnv1a64", hex(fnv1a64(Files.readAllBytes(directory.resolve("adcseq-101-adc-input-global-inputs.bin")))))
    inherited = mutateEvent(inherited, "adc-input-state", 0, "mapped_base_value", hex(mapping))
    val cut = inherited.indexOf("\n[[events]]\nkind = \"terminal-quiesce\""); require(cut > 0)
    val head = inherited.substring(0, cut); var cleanup = inherited.substring(cut)
    cleanup = mutateEvent(cleanup, "tail-summary", 0, "total_writes", hex(563uL))
    cleanup = mutateEvent(cleanup, "remaining-summary", 0, "total_writes", hex(563uL))
    cleanup = mutateEvent(cleanup, "terminal-state", 0, "modeled_writes", hex(563uL))
    val inheritedEvents = inherited.split("[[events]]").drop(1).map { block -> block.lineSequence().filter { " = " in it }.associate { line -> val pair = line.split(" = ", limit = 2); pair[0] to pair[1].removeSurrounding("\"") } }
    val captureAddresses = inheritedEvents.filter { it["kind"] == "adc-input-capture" }.associate { it.getValue("name").removePrefix("adc-input-").removeSuffix(".bin") to number(it.getValue("address")) }
    val loaderAdcAddress = number(inheritedEvents.filter { it["kind"] == "loader-capture" }[3].getValue("address"))
    val maskAddress = number(inheritedEvents.first { it["kind"] == "adc-input-binding" }.getValue("expected_target"))
    val loaderRegisters = inheritedEvents.last { it["kind"] == "loader-debug-registers" }
    val bindingEvent = inheritedEvents.single { it["kind"] == "model-binding" }
    val readPc = number(bindingEvent.getValue("first_pc")); val writePc = number(bindingEvent.getValue("write_pc"))
    val trackedThreads = inheritedEvents.filter { it["kind"] == "group-track" }.map { number(it.getValue("tid")) }.toSet()
    val sourceAddress = mapOf("ADC_RECORD" to loaderAdcAddress, "SETTING" to captureAddresses.getValue("setting"), "DRV" to captureAddresses.getValue("drvparam"), "CONFIG" to captureAddresses.getValue("config"), "SAMPLE" to captureAddresses.getValue("sample-entry"), "LOW" to captureAddresses.getValue("shadow-low"), "HIGH" to captureAddresses.getValue("shadow-high"), "GLOBAL" to captureAddresses.getValue("global-inputs"), "SERIES" to captureAddresses.getValue("series"), "MASK" to maskAddress)
    val sourceIndex = listOf("ADC_RECORD", "SETTING", "DRV", "CONFIG", "SAMPLE", "LOW", "HIGH", "GLOBAL", "SERIES", "MASK")
    val phase = buildString {
        append(event("adc-sequence-mode", listOf(quoted("scope", "private"), numeric("arm", 101uL), numeric("operations", 99uL), numeric("guards", 175uL), numeric("final_shadows", 33uL), numeric("synthetic0", 0x11234uL), numeric("synthetic1", 0uL), numeric("return_pc", returnPc), numeric("stock_return_relative", 0x333bacuL), numeric("sleep_observation", 0uL))))
        entryGuards.forEach { g -> append(event("adc-sequence-entry-guard", listOf(numeric("index", g.index.toULong()), numeric("source", sourceIndex.indexOf(g.source).toULong()), numeric("offset", g.offset), numeric("address", sourceAddress.getValue(g.source) + g.offset), numeric("width", g.width.toULong()), numeric("actual", g.expected), numeric("expected", g.expected), numeric("read_ok", 1uL), numeric("match", 1uL)))) }
        append(event("adc-sequence-entry-binding", listOf(numeric("selected_row", 2uL), numeric("expected_row", 2uL), numeric("mapped_base", mapping), numeric("expected_mapping", mapping))))
        append(debug("adc-sequence-debug-before", 0uL, 0x1e5uL, false)); append(debug("adc-sequence-debug-request", returnPc, 0x1e5uL, true)); append(event("adc-sequence-debug-set", listOf(numeric("result", 0uL)))); append(debug("adc-sequence-debug-after", returnPc, 0x1e4uL, false))
        append(registersFrom("adc-sequence-entry-registers", loaderRegisters)); append(event("adc-sequence-resume-group", listOf(numeric("threads", trackedThreads.size.toULong()), numeric("leader", pid))))
        trackedThreads.forEach { tid -> append(event("runtime-resume", listOf(numeric("tid", tid), numeric("operation", 7uL)))) }
        operations.forEach { op ->
            val pc = if (op.read) readPc else writePc
            append(event("adc-sequence-access", listOf(numeric("index", op.index.toULong()), numeric("tid", pid), numeric("signal", 11uL), numeric("si_code", 2uL), numeric("address", mapping + op.offset), numeric("offset", op.offset), numeric("pc", pc), numeric("opcode", if (op.read) 0xb9400109uL else 0xb9000109uL), numeric("operand", if (op.read) 0uL else op.value))))
            append(registers("adc-sequence-before-registers", pid, pc, if (op.read) 0uL else op.value, mapping + op.offset)); append(event(if (op.read) "adc-sequence-read" else "adc-sequence-write", listOf(numeric("index", op.index.toULong()), numeric("sequence_index", op.sequenceIndex), numeric("tid", pid), numeric("offset", op.offset), numeric("value", op.value), numeric("width", 4uL), numeric("synthetic_response", if (op.read) 1uL else 0uL)))); append(registers("adc-sequence-after-registers", pid, pc + 4uL, op.value, mapping + op.offset)); append(event("runtime-resume", listOf(numeric("tid", pid), numeric("operation", 7uL))))
        }
        append(event("adc-sequence-return", listOf(numeric("tid", pid), numeric("pc", returnPc), numeric("expected_pc", returnPc), numeric("si_code", 4uL), numeric("address", returnPc), numeric("opcode", 0xd503201fuL), numeric("status", 0uL), numeric("operations", 99uL))))
        append(registers("adc-sequence-return-registers", pid, returnPc, 9uL))
        append(event("loader-terminal-converge", listOf(numeric("stopping_tid", pid))))
        finalGuards.forEach { g -> val sourceName = sourceIndex[g.source.toInt()]; append(event("adc-sequence-final-shadow", listOf(numeric("index", g.index.toULong()), numeric("source", g.source.toULong()), numeric("offset", g.offset), numeric("address", sourceAddress.getValue(sourceName) + g.offset), numeric("width", g.width.toULong()), numeric("actual", g.expected), numeric("expected", g.expected), numeric("read_ok", 1uL), numeric("match", 1uL)))) }
        append(debug("adc-sequence-debug-before", returnPc, 0x1e4uL, false)); append(debug("adc-sequence-debug-request", 0uL, 0uL, true)); append(event("adc-sequence-debug-set", listOf(numeric("result", 0uL)))); append(debug("adc-sequence-debug-after", 0uL, 0x1e5uL, false))
        append(registers("adc-sequence-final-registers", pid, returnPc, 9uL)); append(event("adc-sequence-complete", listOf(numeric("return_instruction_executed", 0uL))))
        append(event("adc-sequence-summary", listOf(numeric("operations", 99uL), numeric("writes", 97uL), numeric("reads", 2uL), numeric("private_metrics", 1uL), numeric("worker_ack", 1uL), numeric("atomic", 1uL), numeric("raw0", 0x11234uL), numeric("raw1", 0uL), numeric("protocol0", 0x1234uL), numeric("protocol1", 0uL), numeric("private_reads", 2uL), numeric("old_executed", 0uL))))
    }
    Files.writeString(directory.resolve("adcseq-101.toml"), head + phase + cleanup)
}
fun invoke(directory: Path, label: String): Pair<Int, String> {
    val builder = ProcessBuilder("kotlinc", "-script", verifier.toString(), "--", directory.toString(), "101")
    builder.environment().remove("KOTLIN_RUNNER")
    val process = builder.start(); val stdout = process.inputStream.bufferedReader().readText(); val stderr = process.errorStream.bufferedReader().readText(); val code = process.waitFor()
    Files.writeString(directory.resolve("verifier-$label.stdout"), stdout); Files.writeString(directory.resolve("verifier-$label.stderr"), stderr)
    return code to (stdout + stderr)
}
fun mutateEvent(source: String, kind: String, occurrence: Int, field: String, replacement: String): String {
    val marker = "[[events]]"; val chunks = source.split(marker).toMutableList(); var seen = 0; var changed = 0
    for (index in 1 until chunks.size) if (chunks[index].lineSequence().any { it == "kind = \"$kind\"" }) {
        if (seen++ == occurrence) { val pattern = Regex("(?m)^${Regex.escape(field)} = .*$"); require(pattern.containsMatchIn(chunks[index])); chunks[index] = chunks[index].replace(pattern, "$field = $replacement"); changed++ }
    }
    require(changed == 1) { "mutation must change exactly one $kind.$field" }; return chunks.joinToString(marker)
}

Files.createDirectories(root)
val positive = root.resolve("positive-synthetic"); buildFixture(positive)
val (positiveCode, positiveOutput) = invoke(positive, "positive"); require(positiveCode == 0) { "positive synthetic fixture rejected:\n$positiveOutput" }
data class Corruption(val name: String, val kind: String, val occurrence: Int, val field: String, val replacement: String)
val corruptions = listOf(
    Corruption("changed-operation", "adc-sequence-write", 0, "value", hex(operations[0].value + 1uL)),
    Corruption("changed-register", "adc-sequence-before-registers", 0, "x09", hex(operations[0].value + 1uL)),
    Corruption("entry-guard", "adc-sequence-entry-guard", 0, "match", hex(0uL)),
    Corruption("terminal-atomic", "adc-sequence-summary", 0, "atomic", hex(0uL)),
    Corruption("missing-thread-cleanup", "group-cleanup", 0, "reaped_count", hex(2uL))
)
val positiveTranscript = Files.readString(positive.resolve("adcseq-101.toml"))
corruptions.forEach { corruption ->
    val directory = root.resolve("negative-${corruption.name}"); buildFixture(directory)
    val transcript = Files.readString(directory.resolve("adcseq-101.toml")); val changed = mutateEvent(transcript, corruption.kind, corruption.occurrence, corruption.field, corruption.replacement)
    require(changed != transcript); Files.writeString(directory.resolve("adcseq-101.toml"), changed)
    val (code, output) = invoke(directory, corruption.name); require(code != 0) { "negative ${corruption.name} was accepted:\n$output" }
}
Files.writeString(root.resolve("results.toml"), """schema_version = "mho900-lab.adc-sequence-verifier-controls/1"
classification = "fully-synthetic-host-fixtures-not-guest-outcomes"
result = "accepted"
positive_controls = 1
negative_controls = ${corruptions.size}
guest_runs = 0
verifier_sha256 = "${sha256(verifier)}"
seed_transcript_sha256 = "${sha256(seed.resolve("adcinput-90.toml"))}"
native_sha256 = "${sha256(native)}"
profile_sha256 = "${sha256(profilePath)}"
profile_header_sha256 = "${sha256(profileHeaderPath)}"
""")
println("synthetic ADC sequence verifier controls passed: 1 positive, ${corruptions.size} negative")
