// Synthetic host records exercise only the suite integrity/health audit, not native behavior.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size == 1) { "Usage: test-adc-sequence-run.main.kts NEW_OUTPUT" }
val out = Path.of(args[0]).toAbsolutePath().normalize(); require(!Files.exists(out)); Files.createDirectories(out)
val checker = Path.of("tools/guest/VerifyAdcSequenceRun.main.kts").toAbsolutePath()
val runtime = Path.of("tools/guest/admission-runtime.sh").toAbsolutePath()
fun hash(b: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
val captures = listOf("loader-entry-lsb.bin", "loader-entry-adc.bin", "loader-terminal-lsb.bin", "loader-terminal-adc.bin",
    "loader-terminal-vertical.bin", "adc-input-matrix.bin", "adc-input-setting.bin", "adc-input-drvparam.bin", "adc-input-series.bin",
    "adc-input-config.bin", "adc-input-sample-entry.bin", "adc-input-shadow-low.bin", "adc-input-shadow-high.bin", "adc-input-global-inputs.bin", "adc-input-maps.txt")
val cases = listOf("complete", "missing-candidate", "changed-and-reindexed-profile", "changed-system-server", "not-enforcing",
    "leftover-observer", "health-command-failed", "missing-arm-capture", "native-exit-failed", "unindexed-consumed", "wrong-freeze-pin")
val report = StringBuilder("schema_version = \"mho900-lab.adc-sequence-suite-host-controls/1\"\nclassification = \"synthetic-integrity-and-health-only\"\nchecker_sha256 = \"${hash(Files.readAllBytes(checker))}\"\nruntime_sha256 = \"${hash(Files.readAllBytes(runtime))}\"\nguest_launched = false\nnative_semantics_tested = false\n")
for (case in cases) {
    val dir = out.resolve(case); Files.createDirectory(dir)
    fun put(name: String, text: String) { val p = dir.resolve(name); Files.createDirectories(p.parent); Files.writeString(p, text) }
    val frozen = listOf("group-control.elf", "source/VerifyAdcSequence.main.kts", "source/VerifyAdcSequenceRun.main.kts",
        "source/run-admission.sh", "source/admission-runtime.sh", "source/admission-adcsequencecontrol.sh",
        "adc-sequence/profile.toml", "adc-candidate/candidate.toml", "adc-candidate/sequence.tsv")
    frozen.forEach { put(it, "synthetic host artifact: $it\n") }
    val manifest = buildString {
        append("schema_version = \"mho900-lab.adc-sequence-controls/1\"\nmode = \"adcsequencecontrol\"\nrun_id = \"private-adc-sequence-01\"\nstock_application_launched = false\nexpected_native_exit = 78\nstop_suite_on_unexpected_result = true\nadaptive_retry = false\nphysical_access = false\n")
        for (arm in 101..112) append("\n[[arms]]\narm = $arm\n")
        for (name in frozen) append("\n[[artifacts]]\nrun_path = \"$name\"\nsha256 = \"${hash(Files.readAllBytes(dir.resolve(name)))}\"\n")
    }
    put("source/adc-sequence-control-inputs.toml", manifest)
    for (arm in 101..112) {
        val prefix = "adcseq-$arm"
        put("$prefix-status.toml", "exit_code = 78\n"); put("$prefix.elf", "synthetic host artifact: group-control.elf\n")
        put("$prefix-verification.toml", "schema_version = \"mho900-lab.adc-sequence-verification/1\"\nresult = \"accepted\"\narm = $arm\n"); put("$prefix-verification.stderr", "")
        put("$prefix.toml", "synthetic = true\n")
        put("$prefix-pulls.toml", captures.joinToString("") { "\"$it\" = 0\n" })
        captures.forEach { put("$prefix-$it", "synthetic host capture\n") }
    }
    put("result.toml", "run_id = \"private-adc-sequence-01\"\nmode = \"adcsequencecontrol\"\nboot = \"completed\"\ninspection = \"completed\"\ninstall = \"not_reached\"\nlaunch = \"not_reached\"\nrunner_exit = 0\nstopped_phase = \"finished\"\nfinal_health_attempted = true\ninitial_index_exit = 0\n")
    put("final-system-server.txt", "123\n")
    put("adcseq-system-server.toml", (listOf("before", "after_root") + (101..112).map { "after_arm_$it" } + "after").joinToString("") { "$it = 123\n" })
    for (name in listOf("adcseq-enforcing.txt", "adcseq-final-enforcing.txt", "final-enforcing.txt")) put(name, "Enforcing\n")
    for (name in listOf("adcseq-packages.txt", "adcseq-final-packages.txt", "final-packages.txt")) put(name, "")
    for (name in listOf("adcseq-processes-before.txt", "adcseq-processes-after.txt", "final-processes.txt")) put(name, "system_server\n")
    put("final-health-status.toml", listOf("pid", "enforcing", "processes", "packages", "final_health_helper").joinToString("") { "${it}_exit = 0\n" })
    put("cleanup-status.toml", "emulator_console_exit = 0\nadb_server_exit = 0\n")
    put("runner-command-status.toml", "boot_getprop_exit = 0\nboot_kernel_exit = 0\nfinal_logcat_exit = 0\n")
    val imageHash = "effba4cc839206b25dee05455f6c49b9fad0ca90d524812fd4bbc5d3c02636d2"
    put("userdata-staging.toml", "source_sha256 = \"$imageHash\"\nstaged_sha256 = \"$imageHash\"\nindependent_inode = true\nstaged_link_count = 1\nminimum_free_kib = 2097152\nfree_kib_before = 3000000\nfree_kib_after = 3000000\nsource_identity = \"1:2:1\"\nstaged_identity = \"1:3:1\"\n")
    when (case) {
        "missing-candidate" -> Files.delete(dir.resolve("adc-candidate/candidate.toml"))
        "changed-and-reindexed-profile" -> put("adc-sequence/profile.toml", "changed = true\n")
        "changed-system-server" -> put("final-system-server.txt", "124\n")
        "not-enforcing" -> put("final-enforcing.txt", "Permissive\n")
        "leftover-observer" -> put("final-processes.txt", "system_server\ngroup-observer\n")
        "health-command-failed" -> put("final-health-status.toml", "pid_exit = 1\n")
        "missing-arm-capture" -> Files.delete(dir.resolve("adcseq-112-adc-input-setting.bin"))
        "native-exit-failed" -> put("adcseq-111-status.toml", "exit_code = 1\n")
    }
    val index = ProcessBuilder("sh", "-c", "set -eu; . \"\$1\"; run=\$2; runner_index", "index", runtime.toString(), dir.toString())
        .redirectOutput(out.resolve("$case-index.stdout").toFile()).redirectError(out.resolve("$case-index.stderr").toFile()).start()
    require(index.waitFor() == 0)
    if (case == "unindexed-consumed") {
        val p = dir.resolve("evidence-sha256.txt")
        Files.write(p, Files.readAllLines(p).filterNot { it.endsWith("/adcseq-101-adc-input-maps.txt") })
    }
    val pin = if (case == "wrong-freeze-pin") "0".repeat(64) else hash(manifest.toByteArray())
    val pb = ProcessBuilder("kotlinc", "-script", checker.toString(), "--", dir.toString(), pin)
    pb.environment().remove("KOTLIN_RUNNER")
    pb.redirectOutput(out.resolve("$case.stdout").toFile()); pb.redirectError(out.resolve("$case.stderr").toFile())
    val rc = pb.start().waitFor(); require((rc == 0) == (case == "complete")) { "unexpected $case exit $rc" }
    if (case == "complete") require("result = \"accepted\"" in Files.readString(out.resolve("$case.stdout")))
    report.append("\n[[cases]]\nname = \"$case\"\nexit_code = $rc\nexpected_outcome = true\n")
    Files.writeString(out.resolve("results.toml"), report)
}
println("Suite audit controls: one positive and ten negatives matched")
