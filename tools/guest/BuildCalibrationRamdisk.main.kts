// Produce the pinned API 25 ramdisk derivative containing only an empty /rigol.
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.CRC32
import java.util.zip.GZIPInputStream

require(args.size == 2) { "Usage: BuildCalibrationRamdisk.main.kts BASE_RAMDISK NEW_OUTPUT_DIRECTORY" }
val input = Path.of(args[0])
val output = Path.of(args[1])
require(!Files.exists(output)) { "Output directory already exists" }

val expectedInputHash = "100d85ff3ddfd78d04830f0c9508ca387c36baf4a612fa9ba2d9c41fd6327300"
val maximumCompressedBytes = 4 * 1024 * 1024
val maximumArchiveBytes = 8 * 1024 * 1024
val expectedRecords = 47
val expectedMaximumInode = 0x4940eL

fun sha256(bytes: ByteArray): String = HexFormat.of().formatHex(
    MessageDigest.getInstance("SHA-256").digest(bytes)
)
fun putLe16(out: ByteArrayOutputStream, value: Int) {
    out.write(value and 0xff)
    out.write((value ushr 8) and 0xff)
}
fun putLe32(out: ByteArrayOutputStream, value: Long) {
    repeat(4) { shift -> out.write(((value ushr (shift * 8)) and 0xff).toInt()) }
}
fun align4(value: Int): Int = Math.addExact(value, 3) and -4
fun hex8(value: Long): String {
    require(value in 0..0xffffffffL)
    return value.toString(16).padStart(8, '0')
}
fun tomlString(value: String): String = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

data class Entry(
    val start: Int,
    val end: Int,
    val inode: Long,
    val mode: Long,
    val uid: Long,
    val gid: Long,
    val nlink: Long,
    val mtime: Long,
    val size: Long,
    val devMajor: Long,
    val devMinor: Long,
    val rdevMajor: Long,
    val rdevMinor: Long,
    val nameSize: Long,
    val check: Long,
    val name: String,
)

fun parseHex(bytes: ByteArray, offset: Int): Long {
    require(offset >= 0 && offset + 8 <= bytes.size)
    var value = 0L
    repeat(8) { index ->
        val c = bytes[offset + index].toInt().toChar()
        val digit = c.digitToIntOrNull(16) ?: error("Non-hex newc field")
        value = (value shl 4) or digit.toLong()
    }
    return value
}

fun parseArchive(bytes: ByteArray): Pair<List<Entry>, Int> {
    val entries = mutableListOf<Entry>()
    val names = mutableSetOf<String>()
    var offset = 0
    var trailerEnd = -1
    while (trailerEnd < 0) {
        require(entries.size < 1024) { "Too many archive records" }
        require(offset + 110 <= bytes.size) { "Truncated newc header" }
        require(String(bytes, offset, 6, Charsets.US_ASCII) == "070701") { "Unsupported cpio format" }
        val fields = LongArray(13) { index -> parseHex(bytes, offset + 6 + index * 8) }
        require(fields[12] == 0L) { "Unexpected newc checksum field" }
        val nameSize = fields[11]
        val size = fields[6]
        require(nameSize in 1..4096 && size in 0..maximumArchiveBytes.toLong()) { "Unbounded newc record" }
        val nameEndLong = Math.addExact(offset.toLong() + 110L, nameSize)
        require(nameEndLong <= bytes.size.toLong()) { "Truncated newc name" }
        val nameEnd = nameEndLong.toInt()
        require(bytes[nameEnd - 1] == 0.toByte()) { "Unterminated newc name" }
        val name = String(bytes, offset + 110, nameSize.toInt() - 1, Charsets.UTF_8)
        require(name.isNotEmpty() && '\u0000' !in name && names.add(name)) { "Invalid or duplicate newc name" }
        val dataStart = align4(nameEnd)
        val dataEndLong = Math.addExact(dataStart.toLong(), size)
        require(dataEndLong <= bytes.size.toLong()) { "Truncated newc payload" }
        val end = align4(dataEndLong.toInt())
        require(end <= bytes.size) { "Truncated newc padding" }
        require((nameEnd until dataStart).all { bytes[it] == 0.toByte() }) { "Nonzero name padding" }
        require((dataEndLong.toInt() until end).all { bytes[it] == 0.toByte() }) { "Nonzero data padding" }
        val entry = Entry(offset, end, fields[0], fields[1], fields[2], fields[3], fields[4], fields[5],
            size, fields[7], fields[8], fields[9], fields[10], nameSize, fields[12], name)
        entries.add(entry)
        offset = end
        if (name == "TRAILER!!!") {
            require(size == 0L && entry == entries.last())
            trailerEnd = end
        }
    }
    require((trailerEnd until bytes.size).all { bytes[it] == 0.toByte() }) { "Nonzero bytes after trailer" }
    require(bytes.size % 512 == 0) { "Archive is not padded to 512 bytes" }
    return entries.toList() to trailerEnd
}

fun directoryRecord(inode: Long): ByteArray {
    val name = "rigol\u0000".toByteArray(Charsets.US_ASCII)
    val fields = listOf(inode, 0x41edL, 0L, 0L, 2L, 0L, 0L, 0L, 0L, 0L, 0L, name.size.toLong(), 0L)
    val raw = ("070701" + fields.joinToString("") { hex8(it) }).toByteArray(Charsets.US_ASCII)
    require(raw.size == 110 && name.size == 6)
    return ByteArrayOutputStream().also { out ->
        out.write(raw)
        out.write(name)
        repeat(align4(raw.size + name.size) - raw.size - name.size) { out.write(0) }
    }.toByteArray()
}

fun canonicalGzipStored(payload: ByteArray): ByteArray {
    val out = ByteArrayOutputStream(payload.size + payload.size / 65535 * 5 + 32)
    out.write(byteArrayOf(0x1f, 0x8b.toByte(), 8, 0, 0, 0, 0, 0, 0, 255.toByte()))
    var offset = 0
    while (offset < payload.size) {
        val count = minOf(65535, payload.size - offset)
        val final = offset + count == payload.size
        out.write(if (final) 1 else 0) // BFINAL followed by BTYPE=00 and byte alignment.
        putLe16(out, count)
        putLe16(out, count xor 0xffff)
        out.write(payload, offset, count)
        offset += count
    }
    val crc = CRC32().apply { update(payload) }.value
    putLe32(out, crc)
    putLe32(out, payload.size.toLong() and 0xffffffffL)
    return out.toByteArray()
}

val compressed = Files.readAllBytes(input)
require(compressed.size <= maximumCompressedBytes) { "Compressed input exceeds bound" }
require(sha256(compressed) == expectedInputHash) { "Unexpected base ramdisk" }
val archive = GZIPInputStream(ByteArrayInputStream(compressed)).use { stream ->
    val out = ByteArrayOutputStream()
    val buffer = ByteArray(65536)
    while (true) {
        val count = stream.read(buffer)
        if (count < 0) break
        require(out.size() + count <= maximumArchiveBytes) { "Expanded archive exceeds bound" }
        out.write(buffer, 0, count)
    }
    out.toByteArray()
}
val parsed = parseArchive(archive)
val entries = parsed.first
val trailerEnd = parsed.second
require(entries.size == expectedRecords) { "Unexpected base record count" }
require(entries.maxOf { it.inode } == expectedMaximumInode) { "Unexpected base inode inventory" }
require(entries.last().name == "TRAILER!!!" && entries.none { it.name == "rigol" }) { "Unexpected base paths" }

val trailer = entries.last()
val inserted = directoryRecord(expectedMaximumInode + 1)
val unpaddedSize = Math.addExact(Math.addExact(trailer.start, inserted.size), trailer.end - trailer.start)
val derivedArchive = ByteArray(align4(unpaddedSize).let { (it + 511) and -512 })
System.arraycopy(archive, 0, derivedArchive, 0, trailer.start)
System.arraycopy(inserted, 0, derivedArchive, trailer.start, inserted.size)
System.arraycopy(archive, trailer.start, derivedArchive, trailer.start + inserted.size, trailer.end - trailer.start)
val derivedParsed = parseArchive(derivedArchive).first
require(derivedParsed.size == expectedRecords + 1)
derivedParsed.dropLast(2).zip(entries.dropLast(1)).forEach { pair ->
    val derivedEntry = pair.first
    val baseEntry = pair.second
    require(derivedArchive.copyOfRange(derivedEntry.start, derivedEntry.end)
        .contentEquals(archive.copyOfRange(baseEntry.start, baseEntry.end))) { "Original record changed" }
}
val derivedTrailer = derivedParsed.last()
require(derivedArchive.copyOfRange(derivedTrailer.start, derivedTrailer.end)
    .contentEquals(archive.copyOfRange(trailer.start, trailer.end))) { "Trailer record changed" }
val added = derivedParsed[derivedParsed.lastIndex - 1]
require(added.name == "rigol" && added.inode == expectedMaximumInode + 1 && added.mode == 0x41edL)
require(added.uid == 0L && added.gid == 0L && added.nlink == 2L && added.mtime == 0L && added.size == 0L)
require(derivedParsed.last().name == "TRAILER!!!")

val derivative = canonicalGzipStored(derivedArchive)
Files.createDirectory(output)
val imagePath = output.resolve("ramdisk.img")
Files.write(imagePath, derivative)
val manifestPath = output.resolve("manifest.toml")
Files.newBufferedWriter(manifestPath).use { writer ->
    writer.appendLine("schema_version = \"mho900-lab.calibration-ramdisk/1\"")
    writer.appendLine("base_sha256 = ${tomlString(expectedInputHash)}")
    writer.appendLine("base_compressed_size = ${compressed.size}")
    writer.appendLine("base_uncompressed_size = ${archive.size}")
    writer.appendLine("base_uncompressed_sha256 = ${tomlString(sha256(archive))}")
    writer.appendLine("base_record_count = ${entries.size}")
    writer.appendLine("base_trailer_end = $trailerEnd")
    writer.appendLine("derivative_sha256 = ${tomlString(sha256(derivative))}")
    writer.appendLine("derivative_compressed_size = ${derivative.size}")
    writer.appendLine("derivative_uncompressed_size = ${derivedArchive.size}")
    writer.appendLine("derivative_uncompressed_sha256 = ${tomlString(sha256(derivedArchive))}")
    writer.appendLine("derivative_record_count = ${derivedParsed.size}")
    writer.appendLine("compression = \"gzip-stored-deflate-v1\"")
    writer.appendLine("original_records_byte_preserved = true")
    writer.appendLine("added_path = \"rigol\"")
    writer.appendLine("added_inode = ${added.inode}")
    writer.appendLine("added_mode = \"040755\"")
    writer.appendLine("added_uid = 0")
    writer.appendLine("added_gid = 0")
    writer.appendLine("added_nlink = 2")
    writer.appendLine("added_mtime = 0")
    writer.appendLine("added_size = 0")
}
println("result = \"derived\"")
println("ramdisk_sha256 = ${tomlString(sha256(derivative))}")
println("ramdisk_size = ${derivative.size}")
