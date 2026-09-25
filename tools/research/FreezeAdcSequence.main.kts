// Freeze one private suite. Refuses to overwrite an existing experiment contract.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.time.Instant
import java.util.HexFormat
require(args.size == 1) { "Usage: FreezeAdcSequence.main.kts NEW_MANIFEST" }
val destination = Path.of(args[0]); require(!Files.exists(destination))
fun hash(p: Path) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
data class Artifact(val path: String, val runPath: String)
val artifacts = mutableListOf<Artifact>()
Files.list(Path.of("tools/guest")).use { paths -> paths.sorted().filter { Files.isRegularFile(it) }.forEach {
    artifacts.add(Artifact(it.toString(), "source/${it.fileName}"))
} }
for (name in listOf("BuildAdcSequenceProfile.main.kts", "VerifyAdcSequenceImage.main.kts", "test-adc-sequence-image.main.kts",
    "FreezeAdcSequence.main.kts", "InstantiateAdcCandidate.main.kts", "VerifyAdcCandidate.main.kts", "ReviewAdcInputEvidence.main.kts")) {
    artifacts.add(Artifact("tools/research/$name", "source/$name"))
}
Files.list(Path.of("experiments/adc-parameter-static")).use { paths -> paths.sorted().filter { it.toString().endsWith(".toml") }.forEach {
    artifacts.add(Artifact(it.toString(), "adc-parameter-static/${it.fileName}"))
} }
for (name in listOf("candidate.toml", "sequence.tsv")) artifacts.add(Artifact("experiments/adc-candidate/$name", "adc-candidate/$name"))
artifacts.add(Artifact("experiments/adc-sequence/profile.toml", "adc-sequence/profile.toml"))
artifacts.add(Artifact("experiments/guest-admission/inputs.toml", "source/admission-inputs.toml"))
artifacts.add(Artifact("experiments/guest-baseline/inputs.toml", "source/baseline-inputs.toml"))
artifacts.add(Artifact("experiments/adc-transcript/reference.tsv", "reference.tsv"))
artifacts.add(Artifact("experiments/calibration-static/loader-candidate.toml", "calibration-loader-candidate.toml"))
for (kind in listOf("adc", "spu")) {
    artifacts.add(Artifact("out/$kind-transcript/derived-01/$kind-private.bin", "$kind-private.bin"))
    artifacts.add(Artifact("experiments/$kind-transcript/derivation.toml", "source/$kind-transcript-derivation.toml"))
}
val nativeDirectory = "out/adc-sequence-profile/native-build02"
val native = "$nativeDirectory/group-observer"
require(hash(Path.of(native)) == "960b91e1b3cd7de8f49d47833c6e13ec43afcc597bb0d205c379f471a2bcda37")
artifacts.add(Artifact(native, "group-control.elf"))
for (name in listOf("build-inputs.txt", "adc-sequence-inputs.txt", "compiler.txt", "linker.txt", "binary-sha256.txt")) {
    artifacts.add(Artifact("$nativeDirectory/$name", name))
}
require(artifacts.map { it.runPath }.distinct().size == artifacts.size)
artifacts.forEach { a ->
    for (s in listOf(a.path, a.runPath)) require(!Path.of(s).isAbsolute && !s.split('/').contains(".."))
    require(Files.isRegularFile(Path.of(a.path)) && !Files.isSymbolicLink(Path.of(a.path)))
}
val arms = listOf("complete sequence and worker/read-protocol/atomic/precise-stop controls", "changed first operand",
    "reordered first two accesses", "omitted first access", "unknown read", "wrong terminal PC", "entry config mismatch",
    "second-thread mapped read", "clone coverage", "deadline", "missing atomic completion", "wrong final shadow")
val manifest = buildString {
    append("schema_version = \"mho900-lab.adc-sequence-controls/1\"\nfrozen_at = \"${Instant.now()}\"\n")
    append("task = \"TASK.guest.adc-sequence-private-run\"\ntask_contract = \"sha256:0e64756e6b6e8de319960b59666850fee0f6e9ec853a4239a675fe38a591546d\"\n")
    append("mode = \"adcsequencecontrol\"\nrun_id = \"private-adc-sequence-01\"\nstock_application_launched = false\nexpected_native_exit = 78\nstop_suite_on_unexpected_result = true\nadaptive_retry = false\nphysical_access = false\n")
    append("\n[native]\npath = \"$native\"\nsha256 = \"${hash(Path.of(native))}\"\nprofile = 2\n")
    arms.forEachIndexed { i, question -> append("\n[[arms]]\narm = ${101 + i}\nquestion = \"$question\"\n") }
    artifacts.forEach { a -> append("\n[[artifacts]]\npath = \"${a.path}\"\nrun_path = \"${a.runPath}\"\nsha256 = \"${hash(Path.of(a.path))}\"\n") }
}
Files.createDirectories(destination.toAbsolutePath().parent)
Files.writeString(destination, manifest)
println("manifest_sha256 = \"${hash(destination)}\"\nartifacts = ${artifacts.size}")
