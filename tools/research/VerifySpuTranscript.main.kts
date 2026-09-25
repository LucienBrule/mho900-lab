// Independent fixed SPU fixture decoder and stock ELF comparison.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 3) { "Usage: VerifySpuTranscript.main.kts STOCK_ELF FIXTURE PROFILE" }
fun hash(bytes: ByteArray) = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
val raw = Files.readAllBytes(Path.of(args[0]))
require(hash(raw) == "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
val elf = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN)
fun eu32(at: Int) = elf.getInt(at).toLong() and 0xffffffffL
fun eu16(at: Int) = elf.getShort(at).toInt() and 0xffff
data class Segment(val offset: Long, val address: Long, val fileSize: Long, val memorySize: Long)
val segments = (0 until eu16(56)).map { elf.getLong(32).toInt() + it * eu16(54) }
    .filter { eu32(it) == 1L }
    .map { Segment(elf.getLong(it+8), elf.getLong(it+16), elf.getLong(it+32), elf.getLong(it+40)) }
fun stockBytes(address: Long, count: Int): ByteArray {
    val segment = segments.single { address >= it.address && address + count <= it.address + it.memorySize }
    return ByteArray(count) { i ->
        val relative = address + i - segment.address
        if (relative >= segment.fileSize) 0 else raw[(segment.offset + relative).toInt()]
    }
}
fun stockWord(address: Long) = ByteBuffer.wrap(stockBytes(address,4)).order(ByteOrder.LITTLE_ENDIAN).int.toLong() and 0xffffffffL
data class Section(val type: Long, val offset: Long, val size: Long, val link: Int, val entry: Long)
val sections = (0 until eu16(60)).map { elf.getLong(40).toInt() + it * eu16(58) }.map {
    Section(eu32(it+4),elf.getLong(it+24),elf.getLong(it+32),elf.getInt(it+40),elf.getLong(it+56))
}
data class Relocation(val type: Long, val value: Long)
val relocations = mutableMapOf<Long,Relocation>()
for (section in sections.filter { it.type == 4L }) {
    require(section.entry == 24L)
    val symbols = sections[section.link]
    for (i in 0 until (section.size/24).toInt()) {
        val at = (section.offset+24*i).toInt()
        val info = elf.getLong(at+8)
        val type = info and 0xffffffffL
        val addend = elf.getLong(at+16)
        val symbol = (info ushr 32).toInt()
        val target = if(type == 0x403L) addend else elf.getLong((symbols.offset+symbols.entry*symbol+8).toInt())+addend
        require(relocations.put(elf.getLong(at),Relocation(type,target)) == null)
    }
}
val bytes = Files.newInputStream(Path.of(args[1])).use { it.readNBytes(1065) }
require(bytes.size == 1064) { "Exact fixed length required" }
val input = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
fun u32(at: Int) = input.getInt(at).toLong() and 0xffffffffL
fun u64(at: Int) = input.getLong(at)
require(bytes.copyOfRange(0,8).contentEquals("MHOSPUT1".toByteArray(Charsets.US_ASCII)))
val profile = args[2].toInt().also { require(it in 1..2) }
val header = listOf(1,64,1064,profile,8,15,9,3,4,4,2,0,0,0)
require(header.indices.all { u32(8+4*it) == header[it].toLong() }) { "Header mismatch" }
data class Binding(val slot: Long, val target: Long)
val bindings = listOf(
    Binding(0xb8cb50,0x272f40), Binding(0xb7ca38,0x272c8c), Binding(0xb78630,0x272da8),
    Binding(0xb85af0,0x273018), Binding(0xb785a8,0x2732d0), Binding(0xb820f8,0x274f04),
    Binding(0xb8ab80,0x27254c), Binding(0xb7a568,0x272490), Binding(0xb7bb08,0x272244),
    Binding(0xb86690,0x272c2c), Binding(0xb79db8,0x2703c8), Binding(0xb8d288,0x3cb44fc),
    Binding(0xb8bb48,0x3cb44a0), Binding(0xb8d060,0x3cb44f0), Binding(0xb8be90,0x3cb44b0))
for((i,binding) in bindings.withIndex()) {
    val at = 64+24*i
    require(u32(at)==(if(i<11) 1L else 2L) && u32(at+4)==0L)
    require(Binding(u64(at+8),u64(at+16))==binding) { "Binding $i mismatch" }
    val relocation = relocations.getValue(binding.slot)
    require(relocation.value==binding.target && relocation.type==(if(i==0 || i>=11) 0x401L else 0x402L))
}
val globals = listOf(0xb8f4e4L to 8L,0xb8f4e8L to 900L,0xbe1134L to 0L)
for((i,entry) in globals.withIndex()) {
    val at=424+16*i
    require(u64(at)==entry.first && u32(at+8)==entry.second && u32(at+12)==0L)
    require(stockWord(entry.first)==entry.second)
}
// The nine records contain two relocatable pointer fields. Resolve ELF relocations
// independently; never compare raw on-disk pointer placeholders to loaded pointers.
val samplePointers=listOf(0xb8f808L,0xb8f808L,0xb8f808L,0xb8f908L,0xb8fa08L,0xb8fb08L,0xb8fc08L,0xb8fc08L,0xb8fc08L)
val configPointers=listOf(0xb8f40cL,0xb8f40cL,0xb8f478L,0xb8f2c8L,0xb8f3a0L,0xb8f40cL,0L,0L,0L)
val normalizedRecords = (0 until 9).map { index ->
    val address=0xb8f4f0L+32*index
    val record=stockBytes(address,32)
    val data=ByteBuffer.wrap(record).order(ByteOrder.LITTLE_ENDIAN)
    for(offset in listOf(8,24)) {
        val relocation=relocations[address+offset]
        val expectedPointer=if(offset==8) samplePointers[index] else configPointers[index]
        if(relocation!=null) {
            require(expectedPointer!=0L && relocation.type==(if(offset==8) 0x403L else 0x101L))
            require(relocation.value==expectedPointer)
            data.putLong(offset,relocation.value)
        } else require(expectedPointer==0L && data.getLong(offset)==0L)
    }
    require(bytes.copyOfRange(488+32*index,520+32*index).contentEquals(record)) { "Selection record $index mismatch" }
    data
}
val domain=u32(432)
val selector=u32(448)
val power=u32(464)
val effective=if(selector==4000L && power==1L) 2000L else selector
val selected=normalizedRecords.indexOfFirst { it.getInt(0).toLong()==domain && it.getInt(4).toLong()==effective }.let { if(it<0) 0 else it }
val chosen=normalizedRecords[selected]
require(selected==2 && chosen.getLong(8)==0xb8f808L && chosen.getInt(16)==16)
val modes=mutableListOf<Long>()
for((i,index) in listOf(0,1,15).withIndex()) {
    val at=776+32*i
    val address=chosen.getLong(8)+16*index
    require(u32(at)==index.toLong() && u32(at+4)==0L && u64(at+8)==address)
    require(bytes.copyOfRange(at+16,at+32).contentEquals(stockBytes(address,16))) { "Sample $index mismatch" }
    modes += stockWord(address+4)
}
require(modes==listOf(1L,1L,4L))
require((0..3).map { u32(472+4*it) }==listOf(effective,selected.toLong(),modes[1],modes[2]))
val checkpoints=listOf(1L,0L,0L,0L)
val gainByte=(1L and 3L)*0x55
val gain=gainByte*0x01010101
val rangeBits=listOf(1L,1L,1L,1L).foldIndexed(0L) { bit,acc,value -> acc or ((value and 1L) shl bit) }
val finals=listOf(0L,gain,1L shl 29,(rangeBits shl 20) or 1)
for(i in 0..3) {
    val at=872+32*i
    require(Binding(u64(at),u64(at+8))==bindings[11+i])
    require(u32(at+16)==4L && u32(at+20)==checkpoints[i] && u32(at+24)==finals[i] && u32(at+28)==0L)
}
val writes=listOf(0x1000L to 1L,0x1000L to 0L,0x1000L to 0L,0x1000L to 0x10L,0x1000L to 0L,
    0x105cL to gain,0x1010L to finals[2],0x1014L to finals[3])
for((i,entry) in writes.withIndex()) require(u32(1000+8*i)==entry.first && u32(1004+8*i)==entry.second) { "Write $i mismatch" }
println("schema_version = \"mho900-lab.spu-transcript-verification/1\"")
println("verified = true\nprofile = $profile\ninput_bytes = ${bytes.size}\nwrite_count = 8")
println("input_sha256 = \"${hash(bytes)}\"")
println("bindings_checked = 15\nselection_records_checked = 9\nsample_records_checked = 3\nshadow_records_checked = 4")
println("gain_mode = ${modes[1]}\nrange_mode = ${modes[2]}\nselected_record = $selected")
println("oracle = \"Independent ELF relocation and data decoding plus reviewed stock instruction formulas; no hardware claim\"")
