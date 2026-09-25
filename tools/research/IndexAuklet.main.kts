// Read-only call inventory. LLVM labels are checked against pinned ELF instruction bytes.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 3) { "Usage: IndexAuklet.main.kts STOCK_ELF LLVM_DISASSEMBLY OUTPUT_DIRECTORY" }
val input = Path.of(args[0])
val listing = Path.of(args[1])
val output = Path.of(args[2])
require(!Files.exists(output)) { "Use a new output directory; evidence is not overwritten" }
fun digest(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun digestFile(file: Path): String {
    val hash = MessageDigest.getInstance("SHA-256")
    Files.newInputStream(file).use { stream ->
        val buffer = ByteArray(65536)
        while (true) { val count = stream.read(buffer); if (count < 0) break; hash.update(buffer, 0, count) }
    }
    return HexFormat.of().formatHex(hash.digest())
}
fun hx(value: Long) = "0x" + value.toString(16)
fun quote(value: String) = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\t", "\\t") + "\""
data class Segment(val offset: Long, val address: Long, val size: Long)
data class Section(val type: Int, val offset: Long, val size: Long, val link: Int, val entrySize: Long)
data class Symbol(val name: String, val address: Long, val size: Long, val section: Int)
data class Relocation(val address: Long, val type: Long, val symbol: Symbol)
class Elf(val bytes: ByteArray) {
    val data = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
    fun u16(at: Int) = data.getShort(at).toInt() and 0xffff
    fun u32(at: Int) = data.getInt(at).toLong() and 0xffffffffL
    fun u64(at: Int) = data.getLong(at)
    val segments: List<Segment>
    val sections: List<Section>
    val relocations: Map<Long, Relocation>
    val dynamicSymbols: List<Symbol>
    init {
        require(bytes.take(6) == listOf<Byte>(0x7f, 0x45, 0x4c, 0x46, 2, 1))
        require(u16(18) == 183) { "Expected AArch64 ELF" }
        segments = (0 until u16(56)).map { u64(32).toInt() + it * u16(54) }.filter { u32(it) == 1L }
            .map { Segment(u64(it + 8), u64(it + 16), u64(it + 32)) }
        sections = (0 until u16(60)).map { u64(40).toInt() + it * u16(58) }
            .map { Section(u32(it + 4).toInt(), u64(it + 24), u64(it + 32), u32(it + 40).toInt(), u64(it + 56)) }
        fun symbols(section: Section): List<Symbol> {
            val strings = sections[section.link]
            return (0 until (section.size / section.entrySize).toInt()).map { index ->
                val at = (section.offset + index * section.entrySize).toInt()
                val start = (strings.offset + u32(at)).toInt()
                var end = start
                while (bytes[end] != 0.toByte()) end++
                Symbol(String(bytes, start, end - start, Charsets.UTF_8), u64(at + 8), u64(at + 16), u16(at + 6))
            }
        }
        dynamicSymbols = sections.filter { it.type == 11 }.flatMap(::symbols)
        relocations = sections.filter { it.type == 4 }.flatMap { section ->
            val symbols = symbols(sections[section.link])
            (0 until (section.size / section.entrySize).toInt()).map { index ->
                val at = (section.offset + index * section.entrySize).toInt()
                val info = u64(at + 8)
                Relocation(u64(at), info and 0xffffffffL, symbols[(info ushr 32).toInt()])
            }
        }.associateBy { it.address }
    }
    fun offset(address: Long, count: Int): Int {
        val segment = segments.single { address >= it.address && address + count <= it.address + it.size }
        return (segment.offset + address - segment.address).toInt()
    }
    fun word(address: Long) = u32(offset(address, 4))
    fun words(address: Long, count: Int) = (0 until count).map { word(address + it * 4L) }
}
data class Instruction(val pc: Long, val word: Long, val mnemonic: String, val operands: String)
data class Function(val address: Long, val name: String, val instructions: List<Instruction>)
enum class EdgeKind { DIRECT, PLT, GOT_CONDITIONAL, INDIRECT_UNKNOWN, SYMBOL_BRANCH_CANDIDATE }
data class Edge(val owner: Function, val instruction: Instruction, val kind: EdgeKind,
                val target: String?, val address: Long?, val slot: Long?)
val bytes = Files.readAllBytes(input)
val stockHash = digest(bytes)
require(stockHash == "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e") { "Unexpected stock ELF" }
val elf = Elf(bytes)
val header = Regex("^([0-9a-f]{16}) <(.+)>:$")
val instruction = Regex("^\\s+([0-9a-f]+): ([0-9a-f]{8})\\s+([a-z0-9.]+)\\s*(.*)$")
val functions = mutableListOf<Function>()
var name = ""
var address = 0L
var instructions = mutableListOf<Instruction>()
var checked = 0
Files.newBufferedReader(listing).useLines { lines -> lines.forEach { line ->
    val h = header.matchEntire(line)
    if (h != null) {
        if (name.isNotEmpty()) functions += Function(address, name, instructions.toList())
        address = h.groupValues[1].toLong(16); name = h.groupValues[2]; instructions = mutableListOf()
    } else {
        val m = instruction.matchEntire(line)
        if (m != null) {
            val insn = Instruction(m.groupValues[1].toLong(16), m.groupValues[2].toLong(16), m.groupValues[3], m.groupValues[4])
            require(elf.word(insn.pc) == insn.word) { "Disassembly differs from ELF at ${hx(insn.pc)}" }
            checked++; instructions += insn
        }
    }
} }
if (name.isNotEmpty()) functions += Function(address, name, instructions.toList())
val byAddress = functions.associateBy { it.address }
val symbolsByName = elf.dynamicSymbols.associateBy { it.name }
val edges = mutableListOf<Edge>()
for (function in functions.filterNot { it.name.endsWith("@plt") || it.name == ".plt" }) {
    for ((index, insn) in function.instructions.withIndex()) {
        if (insn.mnemonic == "bl" || insn.mnemonic == "b") {
            val target = Regex("^0x([0-9a-f]+)").find(insn.operands)?.groupValues?.get(1)?.toLong(16) ?: continue
            if (insn.mnemonic == "b" && (target == function.address || target !in byAddress)) continue
            val targetName = byAddress[target]?.name
            val rawName = targetName?.removeSuffix("@plt")
            val resolvedName = rawName?.let { symbolsByName[it] }?.let { byAddress[it.address]?.name } ?: rawName
            val kind = when { insn.mnemonic == "b" -> EdgeKind.SYMBOL_BRANCH_CANDIDATE
                targetName?.endsWith("@plt") == true -> EdgeKind.PLT
                else -> EdgeKind.DIRECT }
            edges += Edge(function, insn, kind, resolvedName, target, null)
        } else if (insn.mnemonic == "blr" || insn.mnemonic == "br") {
            // Only the exact adjacent ADRP/LDR/BLR form is resolved. No general data-flow inference.
            val previous = function.instructions.getOrNull(index - 1)
            val earlier = function.instructions.getOrNull(index - 2)
            var slot: Long? = null
            if (previous != null && earlier != null && previous.pc + 4 == insn.pc && earlier.pc + 4 == previous.pc &&
                previous.word and 0xffc00000L == 0xf9400000L && earlier.word and 0x9f000000L == 0x90000000L) {
                val destination = previous.word and 31
                val base = (previous.word shr 5) and 31
                val called = (insn.word shr 5) and 31
                if (destination == called && earlier.word and 31 == base) {
                    val encoded = ((earlier.word shr 5) and 0x7ffffL) * 4 + ((earlier.word shr 29) and 3)
                    val signed = if (encoded and 0x100000 != 0L) encoded - 0x200000 else encoded
                    slot = (earlier.pc and -4096L) + signed * 4096 + ((previous.word shr 10) and 4095) * 8
                }
            }
            val relocation = slot?.let { elf.relocations[it] }?.takeIf { it.type == 0x401L || it.type == 0x402L }
            val symbol = relocation?.symbol
            val targetName = symbol?.let { byAddress[it.address]?.name ?: it.name }
            edges += Edge(function, insn, if (symbol == null) EdgeKind.INDIRECT_UNKNOWN else EdgeKind.GOT_CONDITIONAL,
                targetName, symbol?.address?.takeIf { it != 0L }, slot)
        }
    }
}
Files.createDirectories(output)
Files.newBufferedWriter(output.resolve("calls.tsv")).use { writer ->
    writer.appendLine("preceding_label\tlabel_address\tpc\tkind\ttarget_name\tbranch_or_symbol_address\tgot_slot")
    for (edge in edges) writer.appendLine(listOf(edge.owner.name, hx(edge.owner.address), hx(edge.instruction.pc), edge.kind.name,
        edge.target ?: "?", edge.address?.let(::hx) ?: "?", edge.slot?.let(::hx) ?: "?").joinToString("\t"))
}
val boundaryNames = setOf("Dev_ReadRegister", "Dev_WriteRegister", "Dev_WriteAfgRegister", "Dev_WriteWaveDataRegister", "open", "open64", "__open_2", "mmap", "mmap64", "ioctl", "read", "write", "__read_chk", "__write_chk", "pread", "pread64", "pwrite", "pwrite64", "munmap", "close", "pthread_create")
val boundary = edges.filter { it.target in boundaryNames || it.target?.contains("DMA", ignoreCase = true) == true }
Files.newBufferedWriter(output.resolve("hardware-callers.toml")).use { writer ->
    writer.appendLine("schema_version = \"mho900-lab.static-call-inventory/1\"")
    writer.appendLine("stock_library_sha256 = ${quote(stockHash)}")
    writer.appendLine("scope = \"Named register wrappers, POSIX device primitives and DMA-named functions; includes non-device file users\"")
    writer.appendLine("runtime_binding_verified = false")
    writer.appendLine("owner_confidence = \"Nearest preceding LLVM label; not a proven function extent\"")
    for (edge in boundary) {
        writer.appendLine("\n[[calls]]")
        writer.appendLine("owner = ${quote(edge.owner.name)}")
        writer.appendLine("pc = ${quote(hx(edge.instruction.pc))}")
        writer.appendLine("target = ${quote(edge.target!!)}")
        writer.appendLine("edge_kind = ${quote(edge.kind.name)}")
        edge.slot?.let { writer.appendLine("got_slot = ${quote(hx(it))}") }
    }
}
val selected = functions.filter { it.name.startsWith("DevAcquireADC_") || it.name in setOf("Dev_Init", "Dev_AdcWrite", "Dev_AdcRead", "Dev_WriteRegister", "Dev_ReadRegister", "Dev_PCIeInit") }
Files.newBufferedWriter(output.resolve("adc-routines.txt")).use { writer ->
    for (function in selected) {
        writer.appendLine("${hx(function.address)} <${function.name}>:")
        function.instructions.forEach { writer.appendLine("${hx(it.pc)}: ${it.word.toString(16).padStart(8, '0')} ${it.mnemonic} ${it.operands}") }
    }
}
val addressWords = elf.words(0x994a5c, 111)
val valueWords = elf.words(0x994c18, 111)
require(elf.word(0x27ed6c) == 0x7101b91fL && elf.word(0x27ee10) == 0x17ffffd6L)
Files.newBufferedWriter(output.resolve("adc-loop.tsv")).use { writer ->
    writer.appendLine("index\tentry\tmode\toffset\tvalue")
    var index = 0
    for (entry in 0 until 110) for (mode in 0..1) {
        val command = 0x04000000L or ((mode + 1L) shl 24) or ((addressWords[entry] and 0xffff) shl 16) or (valueWords[entry] and 0xffff)
        for (value in listOf(command, command and 0x03ffffff)) writer.appendLine("${index++}\t$entry\t$mode\t0x3000\t${hx(value)}")
    }
}
val summary = """
schema_version = "mho900-lab.static-index/1"
stock_library_sha256 = "$stockHash"
disassembly_sha256 = "${digestFile(listing)}"
instruction_words_checked = $checked
function_labels = ${functions.size}
call_edges = ${edges.size}
conditional_got_edges = ${edges.count { it.kind == EdgeKind.GOT_CONDITIONAL }}
unresolved_indirect_edges = ${edges.count { it.kind == EdgeKind.INDIRECT_UNKNOWN }}
unnamed_direct_edges = ${edges.count { it.kind == EdgeKind.DIRECT && it.target == null }}
boundary_call_sites = ${boundary.size}
register_read_sites = ${edges.count { it.target == "Dev_ReadRegister" }}
register_write_sites = ${edges.count { it.target == "Dev_WriteRegister" }}
adc_loop_writes = 440
limits = ["Owner is preceding LLVM label, not proven function extent", "Symbol branches may be fragments or aliases, not tail calls", "PLT edge address is stub address; GOT edge address is static symbol value", "Only adjacent ADRP/LDR indirect calls resolved", "No runtime selector or binding proof", "No general constant propagation", "No FPGA behavior inferred", "No claim of reachability for inventory edges"]
""".trimIndent() + "\n"
Files.writeString(output.resolve("summary.toml"), summary)
print(summary)

// Reviewed semantic annotations, scoped to the pinned image. This is not an automatic decompiler.
enum class Classification(val wire: String) {
    STATIC_DETERMINED("STATIC-DETERMINED"), RUNTIME_SELECTED("RUNTIME-SELECTED"),
    HARDWARE_RETURNED("HARDWARE-RETURNED"), ASYNCHRONOUS("ASYNCHRONOUS"), UNKNOWN("UNKNOWN")
}
enum class Operation { CALL_SEQUENCE, LOOP, WRITE_SEQUENCE, READ_BRANCH, SOFTWARE_STATE, DEVICE_ABI, DISPATCH }
data class Node(val id: String, val classification: Classification, val operation: Operation,
                val pcs: List<Long>, val semantics: String, val conditions: String, val children: List<String> = emptyList())
val nodes = listOf(
    Node("startup", Classification.RUNTIME_SELECTED, Operation.CALL_SEQUENCE,
        listOf(0x239110, 0x239114, 0x2392dc),
        "CApiFactory::Api_Init calls PCIeInit, InitVendor, application post loops, then Drv_Init(false).",
        "PLT bindings and application callbacks are runtime inputs; static order is not an observed call stack.",
        listOf("bypass", "dna", "driver-init")),
    Node("bypass", Classification.RUNTIME_SELECTED, Operation.DEVICE_ABI,
        listOf(0x2701fc, 0x270280),
        "Open /dev/xdma0_bypass; mmap offset 0, length 0x1000000, PROT_READ|PROT_WRITE, MAP_SHARED.",
        "Open and mapping return values select error paths. Existing guest witness confirms these requests."),
    Node("dna", Classification.HARDWARE_RETURNED, Operation.READ_BRANCH,
        listOf(0x270604, 0x42a8ec),
        "SCU offsets 0x4048 then 0x4044 feed masked 57-bit m_DNA composition.",
        "Two synthetic read values and resulting m_DNA have dynamic evidence; physical identity values are unknown."),
    Node("driver-init", Classification.RUNTIME_SELECTED, Operation.CALL_SEQUENCE,
        listOf(0x2e5254, 0x2e5268, 0x2e5278, 0x2e5288),
        "Drv_Init calls InitDrvFEM, Dev_Init(input bool), SCU version and hardware-version reads, then configuration-dependent DDR work.",
        "Other callers include low-power reinitialization with true. Do not flatten both branches into one transcript.",
        listOf("device-init", "scu-version", "ddr")),
    Node("device-init", Classification.RUNTIME_SELECTED, Operation.CALL_SEQUENCE,
        listOf(0x272890, 0x2728ac, 0x2728b8, 0x2728c4, 0x2728d8, 0x2728dc, 0x2728e4, 0x272980),
        "Four AFE initializers, ADC, SPU, WPU software globals, SCU, board-power notification, bool-selected reset branch, LA accumulator reset. Returns zero without propagating child results.",
        "ADC/SPU/WPU and LA calls use relocatable GOT slots; identities require live binding validation.",
        listOf("adc-globals", "adc-loop", "adc-tail-direct", "adc-tail-state", "spu", "wpu", "scu-init", "board-power", "reset-selector", "la-reset")),
    Node("adc-globals", Classification.STATIC_DETERMINED, Operation.SOFTWARE_STATE,
        listOf(0x27ed60, 0x27e9ec, 0x27ea78, 0x27eb44, 0x27ecb0),
        "InitGlobalVariable initializes software shadows from regInitValue; bounded copy loops have counts 8,2,2,8 with additional scalar copies and masks. No MMIO or child calls.",
        "ELF regInitValue=0x99471c; runtime GOT binding and absence of concurrent shadow mutations remain conditions."),
    Node("adc-loop", Classification.STATIC_DETERMINED, Operation.LOOP,
        listOf(0x27ed6c, 0x27edc4, 0x27ee00, 0x27ee10),
        "For i=0..109, call AdcWrite(regValue[i],addrValue[i],0), then mode1: 440 W32 at offset0x3000. Entry110 is unused.",
        "Arrays each have111 u32 elements at ELF0x994a5c and0x994c18; GOT and PLT self-binding assumed. Only first2 completed stores and third attempted store observed.",
        listOf("adc-write")),
    Node("adc-write", Classification.STATIC_DETERMINED, Operation.WRITE_SEQUENCE,
        listOf(0x2717d4, 0x2717d8, 0x271810, 0x27181c, 0x271828, 0x271870, 0x27188c, 0x27189c),
        "For mode0/1: command=0x04000000|((mode+1)<<24)|((addr&0xffff)<<16)|(value&0xffff); W32(0x3000,command), usleep(100), W32(0x3000,command&0x03ffffff). Invalid mode returns-1 without writes.",
        "Valid modes return0 regardless of Dev_WriteRegister/usleep results. Sleep request is not guaranteed elapsed hardware time or completion."),
    Node("adc-tail-direct", Classification.STATIC_DETERMINED, Operation.WRITE_SEQUENCE,
        listOf(0x27ee14, 0x27ee30, 0x27ee34, 0x27ee4c),
        "AdcWrite(13,0,0), AdcWrite(5,0,1): 0500000d,0100000d,06000005,02000005 at0x3000.",
        "Same stock bindings and writer as table loop.", listOf("adc-write")),
    Node("adc-tail-state", Classification.RUNTIME_SELECTED, Operation.SOFTWARE_STATE,
        listOf(0x27ee54, 0x27ee68, 0x27ee7c, 0x27ee98, 0x27eeb0, 0x27eec4, 0x27eee0, 0x27eef8),
        "Shadow09[0]=(old&0x8fff)|0x5000; shadow09[1]=(old&0x8fff)|0x4000; clear low nibble of shadow08; SetADCReg(mode0,9), (mode1,9), (mode0,8), (mode1,8). With initialized shadows: eight words05097001,01097001,06096001,02096001,05080000,01080000,06080000,02080000.",
        "Shadows are writable BSS, not device reads. Expected initial09=0x6721 and08=0x000b; concurrent callers or interposition can invalidate prediction.", listOf("adc-set")),
    Node("adc-set", Classification.STATIC_DETERMINED, Operation.WRITE_SEQUENCE,
        listOf(0x27e8d4, 0x27e8ec, 0x27e8f0, 0x27e908, 0x27e910),
        "SetADCReg(mode,index,value) calls AdcWrite((value&0xffff)^maskValue[index],index,mode), then returns0 regardless of child result.",
        "maskValue ELF0x9948bc; index is unchecked here; caller must bound it. Entries9=0x2720 and8=0.", listOf("adc-write")),
    Node("adc-read", Classification.HARDWARE_RETURNED, Operation.READ_BRANCH,
        listOf(0x271968, 0x271988, 0x27199c, 0x2719ac, 0x2719c0, 0x2719c8),
        "Mode0/1 selects base; write0x04800000|base|(addr16<<16), sleep100us, write command&0x03ffffff, sleep100us, R32(0x3004). If returned bit16 set, copy low16 to output and return0; otherwise return-1.",
        "No polling here; reset/readiness/latency semantics unknown. Invalid mode returns-1 before accesses."),
    Node("adc-get", Classification.HARDWARE_RETURNED, Operation.READ_BRANCH,
        listOf(0x27e948, 0x27e95c, 0x27e974, 0x27e978, 0x27e99c),
        "GetADCReg zero-initializes local16, invokes AdcRead, XORs local16 with maskValue[index], stores result, returns0. Child failure is discarded.",
        "A zero status from this wrapper is not proof of successful device response.", listOf("adc-read")),
    Node("adc-otp", Classification.HARDWARE_RETURNED, Operation.LOOP,
        listOf(0x27efc4, 0x27efe4, 0x27efec, 0x27f024),
        "GetOtpAll repeatedly invokes GetOtpByte; accepted-count increments only when returned bit4 is clear, until13 values accepted. Attempt index increments regardless; no fixed attempt bound is visible.",
        "Not called by ADC_Init. GetOtpByte is a separate write/read protocol; not admitted for modeling. Returned data controls liveness.", listOf("adc-get")),
    Node("spu", Classification.RUNTIME_SELECTED, Operation.WRITE_SEQUENCE,
        listOf(0x272f68, 0x272f70, 0x272f88, 0x272fb0, 0x272fc8),
        "Exactly8 W32: five at0x1000 (S|1,S&~1,S&~0x11,(S&~0x11)|0x10,S&~0x11), then0x105c gain,0x1010 T|0x20000000,0x1014 ADC bits. No device read in selected nested paths.",
        "Mutable S,G,T,A and separate software modes Mg=GetSampleMode(1), Mr=GetSampleMode(15) required. Gain=0x55555555 for Mg1, (G&0xffff0000)|0x5555 for Mg2, else (G&0xffffff00)|0x55. ADC=((A|1)&~0x00f00000)|(L<<20), L=0 for Mr1/2 else15. Return propagates only0x1010 write result."),
    Node("wpu", Classification.STATIC_DETERMINED, Operation.SOFTWARE_STATE,
        listOf(0x28f8a4, 0x28f8c8),
        "WPU_Init sets software globals including1000,480,0,1,50 and0.0f; no child call or MMIO wrapper.",
        "GOT symbols must resolve to expected software objects; WPU rendering is a later path."),
    Node("scu-init", Classification.RUNTIME_SELECTED, Operation.WRITE_SEQUENCE,
        listOf(0x285250, 0x285284),
        "W32(0x4004,shadow with bit31=input bool); then clear bit31 and bit2 in shadow and W32(0x4004,new shadow). Dev_Init passes true.",
        "Remaining shadow bits are software state; endpoint effects unknown."),
    Node("board-power", Classification.RUNTIME_SELECTED, Operation.DEVICE_ABI,
        listOf(0x2728dc, 0x297e44, 0x297e50, 0x297f20, 0x297f3c, 0x297f44),
        "UART_OPen failure returns-1; otherwise form five-byte FA,05,00,CRC,AF frame, call uartDataSeed and Uart_Close, return0. Dev_Init discards this result.",
        "UART helper semantics and actual FD/device response remain separate from mapped register writes."),
    Node("reset-selector", Classification.RUNTIME_SELECTED, Operation.DISPATCH,
        listOf(0x2728e4, 0x2728e8, 0x272904, 0x272928, 0x272934),
        "False calls Dev_SetGD32Reset. True writes1 then0 at0x2003c with usleep5000, then JESD init and DAC-sync operations. Both join at LA accumulator reset.",
        "Api_Init statically passes false; runtime binding/caller identity still unverified. Nested hardware semantics unresolved."),
    Node("la-reset", Classification.RUNTIME_SELECTED, Operation.WRITE_SEQUENCE,
        listOf(0x294e18, 0x294e3c, 0x294e60, 0x2949f0),
        "Set bit0 of software word at ELF0x106d4d8, W32(0x7034,shadow); clear bit0 and repeat W32. Wrapper adds0x7000 to selector0x34.",
        "Other shadow bits are runtime software state; endpoint reset behavior unproved."),
    Node("scu-version", Classification.HARDWARE_RETURNED, Operation.READ_BRANCH,
        listOf(0x285300, 0x285310, 0x285394),
        "GetVersion reads offsets0x4 then0x0; GetHardwareVersion reads0x401c. Drv_Init consumes these results after Dev_Init returns.",
        "Version encoding, physical values and downstream branch relevance need further recovery; no synthetic values admitted."),
    Node("ddr", Classification.HARDWARE_RETURNED, Operation.DISPATCH,
        listOf(0x2e5470, 0x2e54a0, 0x2e5590, 0x2e55a4),
        "Drv_Init uses DevConfig_GetDdrCalSkip, GetDdrSkipTap, SetMemReset and Spu_SelfTest call sites.",
        "Static inventory only for these nested routines; selectors, calibration/polling behavior remain unresolved."),
    Node("dma", Classification.UNKNOWN, Operation.DEVICE_ABI,
        listOf(0x37dedc, 0x37df30, 0x37df84),
        "DrvDMA_Init opens /dev/dma_auklet and maps256MiB; destination pointer is base+128MiB. Copy uses two ioctls. XDMA C2H is a distinct read path.",
        "Provider, completion, buffer ownership, sample content and whether operations block are unknown."),
    Node("thread-activity", Classification.ASYNCHRONOUS, Operation.DISPATCH,
        emptyList(), "Stock dynamic evidence contains multiple threads and runtime clones; any modeled-mapping access must be attributed across the observed group.",
        "Per-function static order does not establish global thread order, interrupt semantics or future schedules."),
    Node("unresolved-edges", Classification.UNKNOWN, Operation.DISPATCH,
        emptyList(), "Inventory retains ${edges.count { it.kind == EdgeKind.INDIRECT_UNKNOWN }} unresolved BR/BLR sites, including intraprocedural jump tables and virtual calls.",
        "Not all are hardware calls, and no absence of direct calls proves absence of an indirect caller.")
)
require(nodes.map { it.id }.distinct().size == nodes.size)
val nodeIds = nodes.map { it.id }.toSet()
require(nodes.flatMap { it.children }.all { it in nodeIds })
val allInstructions = functions.flatMap { it.instructions }.associateBy { it.pc }
require(nodes.flatMap { it.pcs }.all { it in allInstructions })
require(elf.word(0x99471c + 0x24) == 0x6721L && elf.word(0x99471c + 0x20) == 0xbL)
require(elf.word(0x9948bc + 9 * 4) == 0x2720L && elf.word(0x9948bc + 8 * 4) == 0L)
Files.newBufferedWriter(output.resolve("initialization-graph.toml")).use { writer ->
    writer.appendLine("schema_version = \"mho900-lab.initialization-graph/1\"")
    writer.appendLine("stock_library_sha256 = ${quote(stockHash)}")
    writer.appendLine("method = \"Reviewed static annotations plus byte-checked call inventory; not general symbolic execution\"")
    writer.appendLine("children_semantics = \"Decomposition and dependency, not unconditional dynamic reachability or cross-thread ordering\"")
    for (node in nodes) {
        writer.appendLine("\n[[nodes]]")
        writer.appendLine("id = ${quote(node.id)}")
        writer.appendLine("classification = ${quote(node.classification.wire)}")
        writer.appendLine("operation = ${quote(node.operation.name)}")
        writer.appendLine("pcs = [${node.pcs.joinToString(", ") { quote(hx(it)) }}]")
        writer.appendLine("opcodes = [${node.pcs.joinToString(", ") { quote("0x" + elf.word(it).toString(16).padStart(8, '0')) }}]")
        writer.appendLine("semantics = ${quote(node.semantics)}")
        writer.appendLine("conditions = ${quote(node.conditions)}")
        writer.appendLine("children = [${node.children.joinToString(", ", transform = ::quote)}]")
    }
}
println("semantic_nodes = ${nodes.size}")
Files.writeString(output.resolve("mapped-wrappers.toml"), """
schema_version = "mho900-lab.mapped-wrappers/1"
stock_library_sha256 = "$stockHash"
mapped_base_helper = "0x271ec4"
coverage = "Named access wrappers plus all decoded BL callers of the mapped-base helper; aliases and raw accesses through copied pointers are not exhaustively identified"

[[wrappers]]
name = "Dev_ReadRegister"
pc = "0x270604"
opcode = "${hx(elf.word(0x270604))}"
access = "R32"
address = "mapped_base + zero_extend_u32(argument0)"

[[wrappers]]
name = "Dev_WriteRegister"
pc = "0x27043c"
opcode = "${hx(elf.word(0x27043c))}"
access = "W32"
address = "mapped_base + zero_extend_u32(argument0)"

[[wrappers]]
name = "Dev_WriteAfgRegister"
pc = "0x27056c"
opcode = "${hx(elf.word(0x27056c))}"
access = "W64"
address = "mapped_base + argument0"

[[wrappers]]
name = "Dev_WriteWaveDataRegister"
entry = "0x270464"
access = "NONE-IN-DECODED-BODY"
address = "computes mapped_base + 8*argument0; no mapped store before return"
""".trimIndent() + "\n" + edges.filter { it.address == 0x271ec4L }.joinToString("\n") {
    "\n[[base_helper_callers]]\npreceding_label = ${quote(it.owner.name)}\npc = ${quote(hx(it.instruction.pc))}\n"
})
