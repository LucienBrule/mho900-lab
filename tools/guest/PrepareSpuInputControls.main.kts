// Generate malformed fixed SPU transcript inputs for pre-target rejection checks.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: PrepareSpuInputControls.main.kts PRIVATE_INPUT NEW_OUTPUT_DIRECTORY" }
val input = Files.readAllBytes(Path.of(args[0]))
val output = Path.of(args[1])
fun hash(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
require(input.size == 1064)
require(hash(input) == "d55b7d70b4bcd1e3e95cd48fc7a7e791c2a16fc52cea32398b3799b94fb7aac6")
require(!Files.exists(output))
fun word(at: Int, value: Int) = input.copyOf().also { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(at, value) }
fun long(at: Int, value: Long) = input.copyOf().also { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putLong(at, value) }
data class Case(val name: String, val bytes: ByteArray)
val cases = listOf(
    Case("magic", input.copyOf().also { it[0] = 0 }),
    Case("version", word(8, 2)),
    Case("profile", word(20, 3)),
    Case("count", word(24, 9)),
    Case("reserved", word(52, 1)),
    Case("binding", word(64, 0)),
    Case("global", word(424 + 8, 0)),
    Case("derived", word(472, 0)),
    Case("series-pointer", long(488 + 8, 1)),
    Case("series-config-pointer", long(488 + 24, 1)),
    Case("sample", long(776 + 8, 1)),
    Case("shadow", long(872 + 8, 1)),
    Case("terminal-shadow", word(872 + 24, 1)),
    Case("offset", word(1000, 0x1004)),
    Case("operand", word(1004, 0xdeadbeef.toInt())),
    Case("truncated", input.copyOf(input.size - 1)),
    Case("trailing", input + byteArrayOf(0))
)
Files.createDirectories(output)
val manifest = StringBuilder("schema_version = \"mho900-lab.spu-parser-controls/1\"\n")
for (case in cases) {
    require(!case.bytes.contentEquals(input)) { "Mutation did not change input: ${case.name}" }
    Files.write(output.resolve("${case.name}.bin"), case.bytes)
    manifest.append("\n[[cases]]\nname = \"${case.name}\"\nsha256 = \"${hash(case.bytes)}\"\nexpected_exit = 2\n")
}
Files.writeString(output.resolve("manifest.toml"), manifest)
println("malformed_inputs = ${cases.size}")
