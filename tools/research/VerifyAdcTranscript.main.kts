// Independent fixed-protocol validation against stock ELF bytes and prior static evidence.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 4) { "Usage: VerifyAdcTranscript.main.kts STOCK_ELF PRIOR_TSV TRANSCRIPT PROFILE" }
val elfBytes = Files.readAllBytes(Path.of(args[0]))
val priorBytes = Files.readAllBytes(Path.of(args[1]))
val transcript = Path.of(args[2])
val expectedProfile = args[3].toInt().also { require(it in 1..2) }
fun hash(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
require(hash(elfBytes) == "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
require(hash(priorBytes) == "6b9f7b8cdfba8d99fa720b2771cd741f285a05d5f9a77f0aa7173fbf5a2e39c9")
val elf = ByteBuffer.wrap(elfBytes).order(ByteOrder.LITTLE_ENDIAN)
data class Segment(val offset: Long, val address: Long, val size: Long)
val segments = (0 until (elf.getShort(56).toInt() and 0xffff)).map {
    elf.getLong(32).toInt() + it * (elf.getShort(54).toInt() and 0xffff)
}.filter { elf.getInt(it) == 1 }.map { Segment(elf.getLong(it + 8), elf.getLong(it + 16), elf.getLong(it + 32)) }
fun stockWord(address: Long): Long {
    val segment = segments.single { address >= it.address && address + 4 <= it.address + it.size }
    return elf.getInt((segment.offset + address - segment.address).toInt()).toLong() and 0xffffffffL
}
// Bound the read before allocation, including a possible byte past the maximum.
val bytes = Files.newInputStream(transcript).use { it.readNBytes(5393) }
require(bytes.size in 1304..5392) { "Input length out of bounds" }
val data = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
fun u32(at: Int) = data.getInt(at).toLong() and 0xffffffffL
fun u64(at: Int) = data.getLong(at)
require(bytes.copyOfRange(0, 8).contentEquals("MHOADCT1".toByteArray(Charsets.US_ASCII))) { "Magic mismatch" }
require(u32(8) == 1L && u32(12) == 64L && u32(16) == bytes.size.toLong()) { "Version or size mismatch" }
require(u32(20) == expectedProfile.toLong()) { "Profile mismatch" }
val count = u32(24).toInt()
require(count in 1..512 && (expectedProfile != 1 || count == 452)) { "Write count mismatch" }
require(bytes.size == 1296 + count * 8) { "Trailing or truncated input" }
require(u32(28) == 111L && u32(32) == 11L && u32(36) == 2L)
require(u32(40) == 0x3000L && u32(44) == 4L && (48..60 step 4).all { u32(it) == 0L })
data class Binding(val kind: Long, val slot: Long, val target: Long)
val bindings = listOf(
    Binding(1, 0xb8ddd0, 0x27ed3c), Binding(1, 0xb78d30, 0x27e9b0),
    Binding(1, 0xb82d20, 0x2717c8), Binding(1, 0xb88fd0, 0x27e8a8),
    Binding(1, 0xb79db8, 0x2703c8), Binding(2, 0xb8cfa0, 0x994a5c),
    Binding(2, 0xb8d0c8, 0x994c18), Binding(2, 0xb8e7a8, 0x99471c),
    Binding(2, 0xb8eea8, 0x9948bc), Binding(2, 0xb8cb08, 0x3cb45bc),
    Binding(2, 0xb8d1b8, 0x3cb45c8))
for ((i, expected) in bindings.withIndex()) {
    val at = 64 + 24 * i
    require(u32(at + 4) == 0L && Binding(u32(at), u64(at + 8), u64(at + 16)) == expected) { "Binding $i differs" }
}
val addresses = (0 until 111).map { stockWord(0x994a5c + it * 4L) }
val values = (0 until 111).map { stockWord(0x994c18 + it * 4L) }
require((0 until 111).all { u32(328 + 4 * it) == addresses[it] && u32(772 + 4 * it) == values[it] }) { "Table differs" }
val sourceAddresses = listOf(0x994740L, 0x99473cL, 0x9948e0L, 0x9948dcL)
val sources = sourceAddresses.map(::stockWord)
require(sources == listOf(0x6721L, 0xbL, 0x2720L, 0L))
require((0..3).all { u32(1216 + it * 4) == sources[it] }) { "Source word differs" }
data class Shadow(val slot: Long, val objectAddress: Long, val width: Long, val initial: Long, val final: Long)
val shadows = listOf(Shadow(0xb8cb08, 0x3cb45bc, 4, 0x67216721, 0x47215721), Shadow(0xb8d1b8, 0x3cb45c8, 2, 0xb, 0))
for ((i, expected) in shadows.withIndex()) {
    val at = 1232 + 32 * i
    require(u32(at + 28) == 0L && Shadow(u64(at), u64(at + 8), u32(at + 16), u32(at + 20), u32(at + 24)) == expected) { "Shadow $i differs" }
}
// Use the prior independent static derivation as the sequence oracle, including the complete tail.
val prior = priorBytes.toString(Charsets.UTF_8).lineSequence().filter { it.isNotBlank() }.drop(1).mapIndexed { i, line ->
    val fields = line.split('\t')
    require(fields.size == 7 && fields[0].toInt() == i)
    fields[6].removePrefix("0x").toLong(16)
}.toList()
require(prior.size == 452)
require(count <= prior.size) { "This verifier accepts only a prefix of the pinned 452-write derivation" }
for (i in 0 until count) {
    val at = 1296 + 8 * i
    require(u32(at) == 0x3000L && u32(at + 4) == prior[i]) { "Write $i differs from independent static evidence" }
}
println("schema_version = \"mho900-lab.adc-transcript-verification/1\"")
println("verified = true")
println("profile = $expectedProfile")
println("write_count = $count")
println("input_bytes = ${bytes.size}")
println("input_sha256 = \"${hash(bytes)}\"")
println("bindings_checked = 11\ntable_words_checked = 222\nsource_words_checked = 4\nshadow_records_checked = 2")
println("oracle = \"Pinned prior static derivation; not hardware evidence\"")
