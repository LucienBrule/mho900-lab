// Insert an ignored APK Signing Block entry. The signed ZIP contents remain intact.
// This creates a negative-control copy; the input is never written.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

require(args.size == 2) { "Usage: ChangedApkControl.main.kts INPUT OUTPUT" }
val source = Path.of(args[0])
val target = Path.of(args[1])
require(!Files.exists(target)) { "Refusing to overwrite output" }
val input = Files.readAllBytes(source)
fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
    .digest(bytes).joinToString("") { "%02x".format(it) }
require(sha256(input) == "6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b")
val view = ByteBuffer.wrap(input).order(ByteOrder.LITTLE_ENDIAN)
val eocd = (input.size - 22 downTo maxOf(0, input.size - 65557)).first {
    view.getInt(it) == 0x06054b50 && it + 22 + (view.getShort(it + 20).toInt() and 65535) == input.size
}
val directory = view.getInt(eocd + 16)
require(directory > 32 && directory < eocd)
val magic = "APK Sig Block 42".toByteArray(Charsets.US_ASCII)
require(input.copyOfRange(directory - 16, directory).contentEquals(magic))
val oldSize = view.getLong(directory - 24)
require(oldSize in 24..Int.MAX_VALUE.toLong())
val blockStart = directory - oldSize.toInt() - 8
require(blockStart >= 0 && view.getLong(blockStart) == oldSize)
val payload = "mho900-lab digest negative control".toByteArray(Charsets.US_ASCII)
// Keep the signing block page-aligned, as required by this APK's verity digest.
val entry = ByteBuffer.allocate(4096).order(ByteOrder.LITTLE_ENDIAN)
    .putLong(4088).putInt(0x6d686f39).put(payload).array()
val insertAt = directory - 24
val output = input.copyOfRange(0, insertAt) + entry + input.copyOfRange(insertAt, input.size)
val changed = ByteBuffer.wrap(output).order(ByteOrder.LITTLE_ENDIAN)
changed.putLong(blockStart, oldSize + entry.size)
changed.putLong(directory + entry.size - 24, oldSize + entry.size)
changed.putInt(eocd + entry.size + 16, directory + entry.size)
Files.write(target, output)
println("input_sha256 = \"${sha256(input)}\"")
println("output_sha256 = \"${sha256(output)}\"")
println("added_bytes = ${entry.size}")
