import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

require(args.size == 1) { "Usage: test-raw-comparison.main.kts NEW_OUTPUT_DIRECTORY" }
val out = Path.of(args[0])
require(!Files.exists(out))
Files.createDirectories(out)
val original = ByteArray(1048583) { (it % 251).toByte() }
val modified = original.copyOf()
for (offset in listOf(4095, 4096, 1048576, 1048582)) modified[offset] = (modified[offset].toInt() xor 1).toByte()
for ((name, bytes) in listOf("a" to original, "same" to original, "different" to modified,
                           "short" to original.copyOf(original.size - 1))) {
    Files.write(out.resolve("$name.img"), bytes)
}
data class Case(val name: String, val second: String, val success: Boolean)
val cases = listOf(Case("equal", "same", true), Case("changed", "different", true),
                   Case("short", "short", false), Case("same-file", "a", false))
val results = StringBuilder("schema_version = 1\n")
for (case in cases) {
    val process = ProcessBuilder("kotlinc", "-script", "tools/bench/CompareRawReads.main.kts", "--",
        out.resolve("a.img").toString(), out.resolve("${case.second}.img").toString(),
        out.resolve("${case.name}.toml").toString())
    process.environment().remove("KOTLIN_RUNNER")
    process.redirectOutput(out.resolve("${case.name}.stdout").toFile())
    process.redirectError(out.resolve("${case.name}.stderr").toFile())
    val code = process.start().waitFor()
    check((code == 0) == case.success) { "${case.name}: unexpected exit $code" }
    if (!case.success) check(!Files.exists(out.resolve("${case.name}.toml")))
    results.append("[[cases]]\nname = \"${case.name}\"\nexit_code = $code\nmatched = true\n")
}
val changed = Files.readString(out.resolve("changed.toml"))
check("differing_bytes = 4\n" in changed)
check("start_byte = 0\nend_byte_exclusive = 8192\n" in changed)
check("start_byte = 1048576\nend_byte_exclusive = 1048583\n" in changed)
check("identical = true\n" in Files.readString(out.resolve("equal.toml")))
fun sha(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {
    "%02x".format(it.toInt() and 255)
}
check("first_sha256 = \"${sha(original)}\"" in changed)
check("second_sha256 = \"${sha(modified)}\"" in changed)
check(Files.readAllBytes(out.resolve("a.img")).contentEquals(original))
Files.writeString(out.resolve("results.toml"), results)
println("Equal, changed-boundary, partial-tail, short-read, same-file, and digest controls passed.")
