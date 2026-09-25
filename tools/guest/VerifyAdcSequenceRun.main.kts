// Final private-suite integrity and health audit. Per-arm semantics are checked independently.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: VerifyAdcSequenceRun.main.kts RUN_DIRECTORY FROZEN_MANIFEST_SHA256" }
val run = Path.of(args[0]).toAbsolutePath().normalize()
val frozenManifest = args[1]
require(frozenManifest.matches(Regex("[0-9a-f]{64}")))
val consumed = linkedSetOf<Path>()
fun path(name: String): Path {
    val p = run.resolve(name).normalize()
    require(p.startsWith(run) && Files.isRegularFile(p) && !Files.isSymbolicLink(p)) { "artifact: $name" }
    return p
}
fun bytes(name: String): ByteArray { val p = path(name); consumed.add(p); return Files.readAllBytes(p) }
fun text(name: String) = bytes(name).toString(Charsets.UTF_8)
fun hash(b: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
fun field(body: String, key: String): String {
    val rows = Regex("(?m)^${Regex.escape(key)} = (.+)$").findAll(body).toList()
    require(rows.size == 1) { "field $key" }
    return rows.single().groupValues[1].removeSurrounding("\"")
}
fun expect(body: String, fields: Map<String, String>) {
    fields.forEach { (key, value) -> require(field(body, key) == value) { "contract $key" } }
}
val manifestName = "source/adc-sequence-control-inputs.toml"
val manifest = text(manifestName)
require(hash(bytes(manifestName)) == frozenManifest) { "external freeze pin" }
val runId = field(manifest.substringBefore("\n["), "run_id")
require(runId.matches(Regex("private-adc-sequence-[0-9]{2}")))
expect(manifest.substringBefore("\n["), mapOf(
    "schema_version" to "mho900-lab.adc-sequence-controls/1",
    "mode" to "adcsequencecontrol", "run_id" to runId,
    "stock_application_launched" to "false", "expected_native_exit" to "78",
    "stop_suite_on_unexpected_result" to "true", "adaptive_retry" to "false", "physical_access" to "false"))
val arms = manifest.split("[[arms]]").drop(1).map { field(it.substringBefore("\n["), "arm").toInt() }
require(arms == (101..112).toList())
val artifactBlocks = manifest.split("[[artifacts]]").drop(1).map { it.substringBefore("\n[") }
require(artifactBlocks.isNotEmpty())
val frozenPaths = artifactBlocks.map { field(it, "run_path") }
require(frozenPaths.distinct().size == frozenPaths.size)
artifactBlocks.forEach { b -> require(hash(bytes(field(b, "run_path"))) == field(b, "sha256")) { "frozen input ${field(b, "run_path")}" } }
require(listOf("group-control.elf", "source/VerifyAdcSequence.main.kts", "source/VerifyAdcSequenceRun.main.kts",
    "source/run-admission.sh", "source/admission-runtime.sh", "source/admission-adcsequencecontrol.sh",
    "adc-sequence/profile.toml", "adc-candidate/candidate.toml", "adc-candidate/sequence.tsv").all { it in frozenPaths })

val captureNames = listOf("loader-entry-lsb.bin", "loader-entry-adc.bin", "loader-terminal-lsb.bin",
    "loader-terminal-adc.bin", "loader-terminal-vertical.bin", "adc-input-matrix.bin", "adc-input-setting.bin",
    "adc-input-drvparam.bin", "adc-input-series.bin", "adc-input-config.bin", "adc-input-sample-entry.bin",
    "adc-input-shadow-low.bin", "adc-input-shadow-high.bin", "adc-input-global-inputs.bin", "adc-input-maps.txt")
// The helper invokes the frozen full verifier immediately after each arm. Its outputs
// and every consumed witness must be in the final index; this audit does not replace it.
for (arm in arms) {
    val prefix = "adcseq-$arm"
    require(text("$prefix-status.toml").trim() == "exit_code = 78")
    require(bytes("$prefix.elf").contentEquals(bytes("group-control.elf")))
    expect(text("$prefix-verification.toml"), mapOf("schema_version" to "mho900-lab.adc-sequence-verification/1",
        "result" to "accepted", "arm" to arm.toString()))
    text("$prefix-verification.stderr")
    text("$prefix.toml")
    val pulls = text("$prefix-pulls.toml").lineSequence().filter { it.isNotBlank() }.map { line ->
        val p = line.split(" = ", limit = 2); require(p.size == 2 && p[1] == "0"); p[0].removeSurrounding("\"")
    }.toList()
    require(pulls == captureNames)
    captureNames.forEach { bytes("$prefix-$it") }
}
val result = text("result.toml")
expect(result, mapOf("run_id" to runId, "mode" to "adcsequencecontrol", "boot" to "completed",
    "inspection" to "completed", "install" to "not_reached", "launch" to "not_reached", "runner_exit" to "0",
    "stopped_phase" to "finished", "final_health_attempted" to "true", "initial_index_exit" to "0"))
expect(text("frida-prerequisite.toml"), mapOf("schema_version" to "mho900-lab.frida-prerequisite/1",
    "mode" to "adcsequencecontrol", "required" to "false", "reason" to "private native control suite"))
val finalPid = text("final-system-server.txt").trim().toULong()
require(finalPid > 0uL)
val pidLines = text("adcseq-system-server.toml").lineSequence().filter { it.isNotBlank() }.map { line ->
    val p = line.split(" = ", limit = 2); require(p.size == 2); p[0] to p[1].toULong()
}.toList()
require(pidLines.map { it.first } == listOf("before", "after_root") + arms.map { "after_arm_$it" } + "after")
require(pidLines.all { it.second == finalPid }) { "system_server continuity" }
for (name in listOf("adcseq-enforcing.txt", "adcseq-final-enforcing.txt", "final-enforcing.txt")) require(text(name).trim() == "Enforcing")
for (name in listOf("adcseq-packages.txt", "adcseq-final-packages.txt", "final-packages.txt")) require(text(name).isBlank())
for (name in listOf("adcseq-processes-before.txt", "adcseq-processes-after.txt", "final-processes.txt")) {
    val processes = text(name); require(processes.contains("system_server") && !Regex("Sparrow|frida|group-observer").containsMatchIn(processes))
}
expect(text("final-health-status.toml"), listOf("pid", "enforcing", "processes", "packages", "final_health_helper").associate { "${it}_exit" to "0" })
expect(text("cleanup-status.toml"), mapOf("emulator_console_exit" to "0", "adb_server_exit" to "0"))
expect(text("runner-command-status.toml"), mapOf("boot_getprop_exit" to "0", "boot_kernel_exit" to "0", "final_logcat_exit" to "0"))
val staging = text("userdata-staging.toml")
expect(staging, mapOf("source_sha256" to "effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2",
    "staged_sha256" to "effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2",
    "independent_inode" to "true", "staged_link_count" to "1", "minimum_free_kib" to "2097152"))
require(field(staging, "free_kib_before").toLong() >= 2097152 && field(staging, "free_kib_after").toLong() >= 2097152)
require(field(staging, "source_identity").substringBeforeLast(':') != field(staging, "staged_identity").substringBeforeLast(':'))

val indexBytes = Files.readAllBytes(path("evidence-sha256.txt"))
val indexed = indexBytes.toString(Charsets.UTF_8).lineSequence().filter { it.isNotBlank() }.map { line ->
    require(line.length > 66 && line.substring(64, 66) == "  " && line.take(64).matches(Regex("[0-9a-f]{64}")))
    val p = Path.of(line.substring(66)).toAbsolutePath().normalize()
    require(p.startsWith(run) && Files.isRegularFile(p) && !Files.isSymbolicLink(p))
    require(hash(Files.readAllBytes(p)) == line.take(64)) { "index hash ${run.relativize(p)}" }; p
}.toList()
require(indexed.size == indexed.distinct().size) { "duplicate index path" }
require(consumed.all { it in indexed }) { "consumed input missing from final index: ${consumed.filter { it !in indexed }.map { run.relativize(it) }}" }
println("schema_version = \"mho900-lab.adc-sequence-suite-audit/1\"\nresult = \"accepted\"\nmanifest_sha256 = \"$frozenManifest\"\nindex_sha256 = \"${hash(indexBytes)}\"\narms = ${arms.size}\nindexed_artifacts = ${indexed.size}\nconsumed_artifacts = ${consumed.size}\nstock_application_launched = false\nphysical_access = false")
