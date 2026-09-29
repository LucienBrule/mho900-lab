import java.io.BufferedInputStream
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import java.nio.file.attribute.BasicFileAttributes
import java.security.MessageDigest

require(args.size == 3) { "Usage: CompareRawReads.main.kts FIRST_IMAGE SECOND_IMAGE NEW_REPORT.toml" }
val first = Path.of(args[0])
val second = Path.of(args[1])
val report = Path.of(args[2])
require(!Files.isSameFile(first, second)) { "Two distinct input files are required" }
require(!Files.exists(report)) { "Refusing to replace an existing report" }
fun attributes(path: Path) = Files.readAttributes(path, BasicFileAttributes::class.java)
val before = listOf(attributes(first), attributes(second))
require(before.all { it.isRegularFile && it.size() > 0 }) { "Inputs must be nonempty regular files" }
require(before[0].size() == before[1].size()) { "Image lengths differ; retain both and investigate the short read" }
val size = before[0].size()
val firstDigest = MessageDigest.getInstance("SHA-256")
val secondDigest = MessageDigest.getInstance("SHA-256")
data class Difference(val start: Long, var endExclusive: Long)
val differences = mutableListOf<Difference>()
var changedBytes = 0L
var offset = 0L
val buffers = listOf(ByteArray(1024 * 1024), ByteArray(1024 * 1024))
BufferedInputStream(Files.newInputStream(first)).use { a ->
    BufferedInputStream(Files.newInputStream(second)).use { b ->
        while (offset < size) {
            val count = minOf(buffers[0].size.toLong(), size - offset).toInt()
            check(a.readNBytes(buffers[0], 0, count) == count && b.readNBytes(buffers[1], 0, count) == count)
            firstDigest.update(buffers[0], 0, count)
            secondDigest.update(buffers[1], 0, count)
            if (!java.util.Arrays.equals(buffers[0], 0, count, buffers[1], 0, count)) for (i in 0 until count) {
                if (buffers[0][i] != buffers[1][i]) {
                    changedBytes++
                    // Coalesce differing 4 KiB granules, not individual changed-byte runs.
                    val start = (offset + i) / 4096L * 4096L
                    val end = minOf(start + 4096L, size)
                    val last = differences.lastOrNull()
                    if (last != null && start <= last.endExclusive) last.endExclusive = maxOf(last.endExclusive, end)
                    else differences.add(Difference(start, end))
                }
            }
            offset += count
        }
        check(a.read() == -1 && b.read() == -1) { "Input grew during comparison" }
    }
}
listOf(first, second).forEachIndexed { i, path ->
    val after = attributes(path)
    check(after.size() == before[i].size() && after.lastModifiedTime() == before[i].lastModifiedTime()
        && after.fileKey() == before[i].fileKey()) { "Input changed during comparison" }
}
fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it.toInt() and 255) }
val text = buildString {
    appendLine("schema_version = 1")
    appendLine("bytes_per_image = $size")
    appendLine("first_sha256 = \"${hex(firstDigest.digest())}\"")
    appendLine("second_sha256 = \"${hex(secondDigest.digest())}\"")
    appendLine("identical = ${changedBytes == 0L}")
    appendLine("differing_bytes = $changedBytes")
    appendLine("range_granularity_bytes = 4096")
    for (difference in differences) {
        appendLine("[[differing_ranges]]")
        appendLine("start_byte = ${difference.start}")
        appendLine("end_byte_exclusive = ${difference.endExclusive}")
    }
}
Files.writeString(report, text, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)
println("Compared $size bytes per image; $changedBytes changed bytes in ${differences.size} coalesced ranges.")
