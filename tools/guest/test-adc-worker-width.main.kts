// Offline replay on independent copies. Original guest records remain immutable.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 3) { "Usage: test-adc-worker-width.main.kts SEED NEW_OUTPUT LLVM_OBJDUMP" }
val seed = Path.of(args[0]).toAbsolutePath().normalize()
val out = Path.of(args[1]).toAbsolutePath().normalize()
val checker = Path.of("tools/guest/VerifyAdcSequence.main.kts").toAbsolutePath()
require(!Files.exists(out)); Files.createDirectories(out)
fun hash(p: Path) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
val index = seed.resolve("evidence-sha256.txt")
val indexed = Files.readAllLines(index).map { line -> Path.of(line.substring(66)) to line.take(64) }
fun preserved() = indexed.forEach { (p, digest) -> require(hash(p) == digest) { "original changed: ${p.fileName}" } }
preserved()
val binary = seed.resolve("group-control.elf")
require(hash(binary) == "960b91e1b3cd7de8f49d47833c6e13ec43afcc597bb0d205c379f471a2bcda37")
val disassembly = out.resolve("worker-disassembly.txt")
val process = ProcessBuilder(args[2], "-d", "--disassemble-symbols=gm_worker_pc", binary.toString())
    .redirectOutput(disassembly.toFile()).redirectError(out.resolve("worker-disassembly.stderr").toFile()).start()
require(process.waitFor() == 0)
val decoded = Files.readString(disassembly)
require(Regex("238900: +b9400109\\s+ldr\\s+w9, \\[x8]").containsMatchIn(decoded)) { "compiled worker instruction" }
fun field(block: String, name: String): String = Regex("(?m)^$name = \"([^\"]+)\"$").findAll(block).toList().single().groupValues[1]
fun changeEvent(source: String, kind: String, name: String, replacement: String): String {
    val parts = source.split("[[events]]").toMutableList()
    val target = parts.indices.filter { parts[it].startsWith("\nkind = \"$kind\"\n") }.single()
    val old = field(parts[target], name)
    require(old != replacement)
    parts[target] = parts[target].replace("$name = \"$old\"", "$name = \"$replacement\"")
    return parts.joinToString("[[events]]")
}
val report = StringBuilder("schema_version = \"mho900-lab.adc-worker-width-controls/1\"\nclassification = \"offline-replay-and-targeted-corruption\"\nguest_launched = false\nchecker_sha256 = \"${hash(checker)}\"\nseed_index_sha256 = \"${hash(index)}\"\nnative_sha256 = \"${hash(binary)}\"\nworker_pc = \"0x238900\"\nworker_opcode = \"0xb9400109\"\n")
val cases = (101..108).map { "replay-$it" to it } + listOf("changed-opcode", "leader-substitution", "changed-address", "cleanup-count").map { it to 108 }
for ((case, arm) in cases) {
    val dir = out.resolve(case); Files.createDirectory(dir)
    val common = listOf("group-control.elf", "reference.tsv", "spu-private.bin", "adc-sequence/profile.toml", "source/adc-sequence-profile.h")
    val armFiles = Files.list(seed).use { paths -> paths.filter { Files.isRegularFile(it) && it.fileName.toString().startsWith("adcseq-$arm") }.toList() }
    val sources = common.map(seed::resolve) + armFiles
    for (from in sources) {
        val to = dir.resolve(seed.relativize(from)); Files.createDirectories(to.parent); Files.copy(from, to)
        require(!Files.isSameFile(from, to) && hash(from) == hash(to))
    }
    val trace = dir.resolve("adcseq-$arm.toml")
    val original = Files.readString(trace)
    val altered = when(case) {
        "changed-opcode" -> changeEvent(original, "adc-sequence-access", "opcode", "0x00000000f9400109")
        "leader-substitution" -> changeEvent(original, "adc-sequence-access", "tid", field(original.split("[[events]]").single { it.startsWith("\nkind = \"model-mode\"\n") }, "pid"))
        "changed-address" -> changeEvent(original, "adc-sequence-access", "address", "0x0000000000003004")
        "cleanup-count" -> changeEvent(original, "group-cleanup", "reaped_count", "0x0000000000000002")
        else -> original
    }
    if (altered != original) Files.writeString(trace, altered)
    val pb = ProcessBuilder("kotlinc", "-script", checker.toString(), "--", dir.toString(), arm.toString())
    pb.environment().remove("KOTLIN_RUNNER")
    pb.redirectOutput(out.resolve("$case.stdout").toFile()); pb.redirectError(out.resolve("$case.stderr").toFile())
    val rc = pb.start().waitFor()
    require((rc == 0) == case.startsWith("replay-")) { "unexpected $case exit $rc" }
    report.append("\n[[cases]]\nname = \"$case\"\narm = $arm\nexit_code = $rc\nexpected_outcome = true\n")
    Files.writeString(out.resolve("results.toml"), report)
}
preserved()
Files.writeString(out.resolve("preservation.toml"), "indexed_originals_unchanged = ${indexed.size}\n")
println("Offline replay: eight positives and four targeted negatives matched; original index unchanged")
