// Generate immutable malformed inputs for pre-target parser rejection controls.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size == 2) { "Usage: PrepareAdcInputControls.main.kts PRIVATE_INPUT NEW_OUTPUT_DIRECTORY" }
val input = Files.readAllBytes(Path.of(args[0]))
val output = Path.of(args[1])
fun hash(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
require(hash(input) == "28471720179d4bf0e41911c0a4d29e108c89bbb4279d264793efb5f8ff9e866d")
require(!Files.exists(output))
fun word(at: Int, value: Int) = input.copyOf().also { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(at, value) }
data class Case(val name: String, val bytes: ByteArray)
val cases = listOf(
    Case("magic", input.copyOf().also { it[0] = 0 }), Case("version", word(8, 2)),
    Case("profile", word(20, 1)), Case("count", word(24, 513)),
    Case("reference-count", (input + ByteArray(8)).also { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(16, it.size).putInt(24, 453) }),
    Case("reserved", word(48, 1)),
    Case("truncated", input.copyOf(input.size - 1)), Case("trailing", input + byteArrayOf(0)),
    Case("oversized", ByteArray(5393)), Case("binding", word(72, 0)), Case("table-count", word(28, 110)),
    Case("width", word(44, 8)), Case("offset", word(40, 0x3004)))
Files.createDirectories(output)
val manifest = StringBuilder("schema_version = \"mho900-lab.adc-parser-controls/1\"\n")
for (case in cases) {
    Files.write(output.resolve("${case.name}.bin"), case.bytes)
    manifest.append("\n[[cases]]\nname = \"${case.name}\"\nsha256 = \"${hash(case.bytes)}\"\nexpected_exit = 2\n")
}
Files.writeString(output.resolve("manifest.toml"), manifest)
println("malformed_inputs = ${cases.size}")
