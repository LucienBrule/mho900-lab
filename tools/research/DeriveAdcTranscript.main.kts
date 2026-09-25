// Derive a bounded ADC initialization transcript from the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 3) {
    "Usage: DeriveAdcTranscript.main.kts STOCK_ELF INDEPENDENT_TRANSCRIPT_TSV NEW_OUTPUT_DIRECTORY"
}
val input = Path.of(args[0])
val independent = Path.of(args[1])
val output = Path.of(args[2])
require(!Files.exists(output)) { "Output directory already exists" }

fun sha256(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun sha256(path: Path): String = Files.newInputStream(path).use { stream ->
    val digest = MessageDigest.getInstance("SHA-256")
    val buffer = ByteArray(65536)
    while (true) { val count = stream.read(buffer); if (count < 0) break; digest.update(buffer, 0, count) }
    HexFormat.of().formatHex(digest.digest())
}
fun hex(value: Long, width: Int = 0): String = "0x" + value.toString(16).padStart(width, '0')
fun quote(value: String) = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

data class Segment(val fileOffset: Long, val address: Long, val fileSize: Long)
data class Section(val type: Int, val offset: Long, val size: Long, val link: Int, val entrySize: Long)
data class Symbol(val name: String, val address: Long, val size: Long, val section: Int)
data class Relocation(val address: Long, val type: Long, val symbol: Symbol)

class Elf(private val bytes: ByteArray) {
    private val data = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
    private fun u16(at: Int) = data.getShort(at).toInt() and 0xffff
    private fun u32(at: Int) = data.getInt(at).toLong() and 0xffffffffL
    private fun u64(at: Int) = data.getLong(at)
    private val segments: List<Segment>
    private val sections: List<Section>
    val symbols: Map<String, Symbol>
    val relocations: Map<Long, Relocation>

    init {
        require(bytes.size >= 64 && bytes.sliceArray(0 until 6).contentEquals(byteArrayOf(0x7f, 0x45, 0x4c, 0x46, 2, 1)))
        require(u16(18) == 183) { "Expected AArch64 ELF" }
        segments = (0 until u16(56)).map { u64(32).toInt() + it * u16(54) }
            .filter { u32(it) == 1L }
            .map { Segment(u64(it + 8), u64(it + 16), u64(it + 32)) }
        sections = (0 until u16(60)).map { u64(40).toInt() + it * u16(58) }
            .map { Section(u32(it + 4).toInt(), u64(it + 24), u64(it + 32), u32(it + 40).toInt(), u64(it + 56)) }
        fun sectionSymbols(section: Section): List<Symbol> {
            require(section.entrySize == 24L)
            val strings = sections[section.link]
            return (0 until (section.size / section.entrySize).toInt()).map { index ->
                val at = (section.offset + index * section.entrySize).toInt()
                val start = (strings.offset + u32(at)).toInt()
                var end = start
                while (bytes[end] != 0.toByte()) end++
                Symbol(String(bytes, start, end - start, Charsets.UTF_8), u64(at + 8), u64(at + 16), u16(at + 6))
            }
        }
        val dynamic = sections.filter { it.type == 11 }.flatMap(::sectionSymbols)
        symbols = dynamic.filter { it.name.isNotEmpty() }.groupBy { it.name }.mapValues { (name, matches) ->
            val defined = matches.filter { it.section != 0 }
            require(defined.map { it.address to it.size }.distinct().size <= 1) { "Conflicting symbol $name" }
            defined.singleOrNull() ?: matches.single()
        }
        relocations = sections.filter { it.type == 4 }.flatMap { section ->
            val linked = sectionSymbols(sections[section.link])
            (0 until (section.size / section.entrySize).toInt()).map { index ->
                val at = (section.offset + index * section.entrySize).toInt()
                val info = u64(at + 8)
                Relocation(u64(at), info and 0xffffffffL, linked[(info ushr 32).toInt()])
            }
        }.associateBy { it.address }
    }

    private fun fileOffset(address: Long, count: Int): Int {
        val matches = segments.filter { address >= it.address && address + count <= it.address + it.fileSize }
        require(matches.size == 1) { "Address ${hex(address)} is not uniquely file-backed" }
        return (matches.single().fileOffset + address - matches.single().address).toInt()
    }
    fun word(address: Long) = u32(fileOffset(address, 4))
    fun words(address: Long, count: Int) = (0 until count).map { word(address + it * 4L) }
    fun region(address: Long, count: Int) = bytes.copyOfRange(fileOffset(address, count), fileOffset(address, count) + count)
}

data class Binding(val kind: Int, val relocationType: Long, val name: String, val slot: Long, val expected: Long)
data class Shadow(val name: String, val slot: Long, val objectAddress: Long, val width: Int,
                  val initial: Long, val final: Long, val source: String)
data class Write(val region: String, val entry: Int, val mode: Int, val phase: String,
                 val offset: Long, val value: Long, val dependency: String)

val bytes = Files.readAllBytes(input)
val stockHash = sha256(bytes)
require(stockHash == "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e") {
    "Unexpected stock ELF"
}
val elf = Elf(bytes)
fun symbol(name: String, address: Long, size: Long) {
    val actual = requireNotNull(elf.symbols[name]) { "Missing symbol $name" }
    require(actual.address == address && actual.size == size && actual.section != 0) { "Symbol mismatch $name" }
}
fun relocation(slot: Long, type: Long, name: String, expected: Long) {
    val actual = requireNotNull(elf.relocations[slot]) { "Missing relocation ${hex(slot)}" }
    require(actual.type == type && actual.symbol.name == name && actual.symbol.address == expected) {
        "Relocation mismatch ${hex(slot)}"
    }
}
fun opcode(address: Long, expected: Long) = require(elf.word(address) == expected) {
    "Opcode mismatch ${hex(address)}: ${hex(elf.word(address), 8)}"
}

symbol("addrValue", 0x994a5c, 444)
symbol("regValue", 0x994c18, 444)
symbol("regInitValue", 0x99471c, 416)
symbol("maskValue", 0x9948bc, 416)
symbol("gInt16DevAcquireADCRT8847IQ_0x09", 0x3cb45bc, 4)
symbol("gInt16DevAcquireADCRT8847IQ_0x08", 0x3cb45c8, 2)
symbol("DevAcquireADC_Init", 0x27ed3c, 468)
symbol("DevAcquireADC_InitGlobalVariable", 0x27e9b0, 908)
symbol("Dev_AdcWrite", 0x2717c8, 240)
symbol("DevAcquireADC_SetADCReg", 0x27e8a8, 120)
symbol("Dev_WriteRegister", 0x2703c8, 156)

val bindings = listOf(
    Binding(1, 0x401, "DevAcquireADC_Init", 0xb8ddd0, 0x27ed3c),
    Binding(1, 0x402, "DevAcquireADC_InitGlobalVariable", 0xb78d30, 0x27e9b0),
    Binding(1, 0x402, "Dev_AdcWrite", 0xb82d20, 0x2717c8),
    Binding(1, 0x402, "DevAcquireADC_SetADCReg", 0xb88fd0, 0x27e8a8),
    Binding(1, 0x402, "Dev_WriteRegister", 0xb79db8, 0x2703c8),
    Binding(2, 0x401, "addrValue", 0xb8cfa0, 0x994a5c),
    Binding(2, 0x401, "regValue", 0xb8d0c8, 0x994c18),
    Binding(2, 0x401, "regInitValue", 0xb8e7a8, 0x99471c),
    Binding(2, 0x401, "maskValue", 0xb8eea8, 0x9948bc),
    Binding(2, 0x401, "gInt16DevAcquireADCRT8847IQ_0x09", 0xb8cb08, 0x3cb45bc),
    Binding(2, 0x401, "gInt16DevAcquireADCRT8847IQ_0x08", 0xb8d1b8, 0x3cb45c8)
)
bindings.forEach { relocation(it.slot, it.relocationType, it.name, it.expected) }

listOf(
    Triple(0x27e9b0L, 908, "38908c0508de266a33fb3d438ecf1be5acc302b5f23c5365e93cfb1732714905"),
    Triple(0x27ed3cL, 468, "8fdb461aa8335c286e21b5e7de260a613adfa6eceda9e0887b3cbedd3fd197f5"),
    Triple(0x2717c8L, 240, "9d10959082b86d08be81f4450b7a3b24175d3a1c83f7be3a6137a988777b254d"),
    Triple(0x27e8a8L, 120, "c9b47fa7dad0eef62046c6d2a72145997e9a41faa1b430a330d15292d3eeac9f"),
    Triple(0x2703c8L, 156, "3cbc8ab721e7c4fa684e44d6e3e55ac42e6d082a02f81450a4df79bcc133c877")
).forEach { (address, size, expected) -> require(sha256(elf.region(address, size)) == expected) { "Code range mismatch ${hex(address)}" } }

// Loop, command construction, direct tail, shadow mutations, and tail calls.
listOf(
    0x27ed60L to 0x97fde7d4L, 0x27ed6cL to 0x7101b91fL,
    0x27edc4L to 0x97fe37b3L, 0x27ee00L to 0x97fe37a4L, 0x27ee10L to 0x17ffffd6L,
    0x2717d4L to 0x781fa3a0L, 0x2717d8L to 0x781f83a1L,
    0x271810L to 0x52a02008L, 0x27181cL to 0x52a04008L,
    0x271840L to 0x52a08009L, 0x27184cL to 0x53103d29L,
    0x271870L to 0x97fe2554L, 0x271878L to 0x12bf8009L,
    0x271884L to 0x52800c88L, 0x27189cL to 0x97fe2549L,
    0x27ee30L to 0x97fe3798L, 0x27ee4cL to 0x97fe3791L,
    0x27ee54L to 0x79400148L, 0x27ee68L to 0x79000148L,
    0x27ee7cL to 0x79000548L, 0x27eebcL to 0x128001e9L,
    0x27e8ecL to 0xb940010bL, 0x27e8f0L to 0x4a0b014aL, 0x27e908L to 0x97fe38e2L,
    0x27043cL to 0xb9000109L
).forEach { opcode(it.first, it.second) }

val addresses = elf.words(0x994a5c, 111)
val registers = elf.words(0x994c18, 111)
val mask8 = elf.word(0x9948bc + 8 * 4)
val mask9 = elf.word(0x9948bc + 9 * 4)
val init8 = elf.word(0x99471c + 0x20)
val init9 = elf.word(0x99471c + 0x24)
require(mask8 == 0L && mask9 == 0x2720L && init8 == 0xbL && init9 == 0x6721L)
val final9Low = (init9 and 0x8fff) or 0x5000
val final9High = (init9 and 0x8fff) or 0x4000
val final9 = final9Low or (final9High shl 16)
val final8 = init8 and 0xfff0
require(final9Low == 0x5721L && final9High == 0x4721L && final9 == 0x47215721L && final8 == 0L)

val shadows = listOf(
    Shadow("index9", 0xb8cb08, 0x3cb45bc, 4, init9 or (init9 shl 16), final9, "regInitValue+0x24 replicated twice"),
    Shadow("index8", 0xb8d1b8, 0x3cb45c8, 2, init8, final8, "regInitValue+0x20")
)
val writes = mutableListOf<Write>()
fun addCommand(region: String, entry: Int, mode: Int, address: Long, value: Long, dependency: String) {
    val command = 0x04000000L or ((mode + 1L) shl 24) or ((address and 0xffff) shl 16) or (value and 0xffff)
    writes += Write(region, entry, mode, "assert", 0x3000, command, dependency)
    writes += Write(region, entry, mode, "clear", 0x3000, command and 0x03ffffff, dependency)
}
for (entry in 0 until 110) for (mode in 0..1) {
    addCommand("table", entry, mode, addresses[entry], registers[entry], "immutable-table")
}
addCommand("constant-tail", -1, 0, 0, 13, "constant")
addCommand("constant-tail", -1, 1, 0, 5, "constant")
addCommand("shadow-tail-index9", -1, 0, 9L, final9Low xor mask9, "writable-shadow")
addCommand("shadow-tail-index9", -1, 1, 9L, final9High xor mask9, "writable-shadow")
addCommand("shadow-tail-index8", -1, 0, 8L, final8 xor mask8, "writable-shadow")
addCommand("shadow-tail-index8", -1, 1, 8L, final8 xor mask8, "writable-shadow")
require(writes.size == 452 && writes.take(440).all { it.dependency == "immutable-table" })

val independentLines = Files.readAllLines(independent)
require(sha256(independent) == "6b9f7b8cdfba8d99fa720b2771cd741f285a05d5f9a77f0aa7173fbf5a2e39c9") {
    "Unexpected independent transcript"
}
require(independentLines.size == 453) { "Independent transcript must contain header plus 452 rows" }
val independentValues = independentLines.drop(1).mapIndexed { index, line ->
    val fields = line.split('\t')
    require(fields.size == 7 && fields[0].toInt() == index) { "Independent row $index malformed" }
    fields[6].removePrefix("0x").toLong(16)
}
require(independentValues == writes.map { it.value }) { "Independent transcript differs" }

Files.createDirectories(output)
val tsv = output.resolve("adc-transcript.tsv")
Files.newBufferedWriter(tsv).use { writer ->
    writer.appendLine("ordinal\tregion\ttable_index\tmode\tphase\toffset\tvalue\tdependency")
    writes.forEachIndexed { index, write ->
        writer.appendLine("$index\t${write.region}\t${write.entry}\t${write.mode}\t${write.phase}\t${hex(write.offset, 4)}\t${hex(write.value, 8)}\t${write.dependency}")
    }
}

val headerSize = 64
val bindingOffset = headerSize
val addressTableOffset = bindingOffset + bindings.size * 24
val registerTableOffset = addressTableOffset + 111 * 4
val sourceWordsOffset = registerTableOffset + 111 * 4
val shadowOffset = sourceWordsOffset + 4 * 4
val writesOffset = shadowOffset + shadows.size * 32
val fullSize = writesOffset + writes.size * 8
val maximumSize = writesOffset + 512 * 8
require(bindings.size == 11 && fullSize == 4912 && maximumSize == 5392)

fun fixture(flags: Int, fixtureWrites: List<Write>): ByteArray {
    require(flags == 1 || flags == 2)
    require(fixtureWrites.isNotEmpty() && fixtureWrites.size <= 512)
    if (flags == 1) require(fixtureWrites.size == 452)
    val totalSize = writesOffset + fixtureWrites.size * 8
    val result = ByteBuffer.allocate(totalSize).order(ByteOrder.LITTLE_ENDIAN)
    result.put("MHOADCT1".toByteArray(Charsets.US_ASCII))
    result.putInt(1).putInt(headerSize).putInt(totalSize).putInt(flags)
    result.putInt(fixtureWrites.size).putInt(111).putInt(bindings.size).putInt(shadows.size)
    result.putInt(0x3000).putInt(4)
    repeat(4) { result.putInt(0) }
    bindings.forEach { result.putInt(it.kind).putInt(0).putLong(it.slot).putLong(it.expected) }
    addresses.forEach { result.putInt(it.toInt()) }
    registers.forEach { result.putInt(it.toInt()) }
    listOf(init9, init8, mask9, mask8).forEach { result.putInt(it.toInt()) }
    shadows.forEach { result.putLong(it.slot).putLong(it.objectAddress).putInt(it.width).putInt(it.initial.toInt()).putInt(it.final.toInt()).putInt(0) }
    fixtureWrites.forEach { result.putInt(it.offset.toInt()).putInt(it.value.toInt()) }
    require(result.position() == totalSize)
    return result.array()
}
val stockFixture = output.resolve("adc-stock.bin")
val privateFixture = output.resolve("adc-private.bin")
val privateOneFixture = output.resolve("adc-private-one.bin")
Files.write(stockFixture, fixture(1, writes))
Files.write(privateFixture, fixture(2, writes))
Files.write(privateOneFixture, fixture(2, writes.take(1)))

val manifest = output.resolve("manifest.toml")
Files.newBufferedWriter(manifest).use { writer ->
    writer.appendLine("schema_version = \"mho900-lab.adc-transcript-derivation/1\"")
    writer.appendLine("stock_library_sha256 = ${quote(stockHash)}")
    writer.appendLine("independent_transcript_sha256 = ${quote(sha256(independent))}")
    writer.appendLine("agreement = \"all-452-values\"")
    writer.appendLine("write_count = 452")
    writer.appendLine("immutable_table_write_count = 440")
    writer.appendLine("constant_tail_write_count = 4")
    writer.appendLine("writable_shadow_write_count = 8")
    writer.appendLine("table_entries = 111")
    writer.appendLine("table_entries_used = 110")
    writer.appendLine("max_protocol_writes = 512")
    writer.appendLine("\n[protocol]")
    writer.appendLine("magic = \"MHOADCT1\"")
    writer.appendLine("version = 1")
    writer.appendLine("byte_order = \"little-endian\"")
    writer.appendLine("full_size = $fullSize")
    writer.appendLine("maximum_size = $maximumSize")
    writer.appendLine("header_offset = 0")
    writer.appendLine("header_size = $headerSize")
    writer.appendLine("bindings_offset = $bindingOffset")
    writer.appendLine("binding_count = ${bindings.size}")
    writer.appendLine("binding_size = 24")
    writer.appendLine("address_table_offset = $addressTableOffset")
    writer.appendLine("register_table_offset = $registerTableOffset")
    writer.appendLine("source_words_offset = $sourceWordsOffset")
    writer.appendLine("source_words_order = [\"init9\", \"init8\", \"mask9\", \"mask8\"]")
    writer.appendLine("shadows_offset = $shadowOffset")
    writer.appendLine("shadow_count = ${shadows.size}")
    writer.appendLine("shadow_size = 32")
    writer.appendLine("writes_offset = $writesOffset")
    writer.appendLine("write_size = 8")
    writer.appendLine("write_offset = \"0x3000\"")
    writer.appendLine("write_width = 4")
    writer.appendLine("validation = \"exact-size-counts-flags-reserved-bindings-tables-source-shadows-order-no-trailing-bytes\"")
    bindings.forEach { binding ->
        writer.appendLine("\n[[bindings]]")
        writer.appendLine("name = ${quote(binding.name)}")
        writer.appendLine("kind = ${binding.kind}")
        writer.appendLine("relocation_type = ${quote(hex(binding.relocationType))}")
        writer.appendLine("slot_relative = ${quote(hex(binding.slot))}")
        writer.appendLine("expected_relative = ${quote(hex(binding.expected))}")
    }
    shadows.forEach { shadow ->
        writer.appendLine("\n[[shadows]]")
        writer.appendLine("name = ${quote(shadow.name)}")
        writer.appendLine("slot_relative = ${quote(hex(shadow.slot))}")
        writer.appendLine("object_relative = ${quote(hex(shadow.objectAddress))}")
        writer.appendLine("width = ${shadow.width}")
        writer.appendLine("initial = ${quote(hex(shadow.initial, shadow.width * 2))}")
        writer.appendLine("final = ${quote(hex(shadow.final, shadow.width * 2))}")
        writer.appendLine("source = ${quote(shadow.source)}")
    }
    listOf(tsv, stockFixture, privateFixture, privateOneFixture).forEach { file ->
        writer.appendLine("\n[[files]]")
        writer.appendLine("path = ${quote(file.fileName.toString())}")
        writer.appendLine("size = ${Files.size(file)}")
        writer.appendLine("sha256 = ${quote(sha256(file))}")
    }
    writer.appendLine("\n[limits]")
    writer.appendLine("classification = \"conditional-static-software-transcript\"")
    writer.appendLine("runtime_bindings_verified = false")
    writer.appendLine("concurrent_shadow_mutation_excluded = false")
    writer.appendLine("hardware_effects_inferred = false")
    writer.appendLine("timing_completion_dma_interrupts_inferred = false")
}
println("derived_writes=452 full_size=$fullSize stock_fixture_sha256=${sha256(stockFixture)}")
