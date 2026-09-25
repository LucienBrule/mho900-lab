// Check the actual compiled data layout and private post-atomic stop; no guest execution.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1){"Usage: VerifyAdcSequenceImage.main.kts NATIVE_ELF"}
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
val profile=Files.readString(Path.of("experiments/adc-sequence/profile.toml"))
val candidate=Files.readAllBytes(Path.of("experiments/adc-candidate/candidate.toml"))
require(hash(candidate)=="5339cbe2af98ce52f99776f9eeba3b5dc391d8f1269b094123a3eec4caf19d70")
fun field(b:String,k:String):String{val m=Regex("(?m)^${Regex.escape(k)} = (.+)$").findAll(b).toList();require(m.size==1);return m.single().groupValues[1].removeSurrounding("\"")}
fun num(s:String)=if(s.startsWith("0x"))s.drop(2).toULong(16) else s.toULong()
fun blocks(s:String,name:String)=s.split("[[$name]]").drop(1).map{it.substringBefore("\n[")}
val bytes=Files.readAllBytes(Path.of(args[0]));val b=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
fun u16(p:Int)=b.getShort(p).toUShort().toInt()
fun u32(p:Int)=b.getInt(p).toUInt().toULong()
fun u64(p:Int)=b.getLong(p).toULong()
require(bytes.take(6)==listOf(127,69,76,70,2,1).map{it.toByte()}&&u16(18)==183)
data class Symbol(val name:String,val address:ULong,val size:ULong)
data class Segment(val offset:ULong,val address:ULong,val size:ULong)
val segments=(0 until u16(56)).map{u64(32).toInt()+it*u16(54)}.filter{u32(it)==1uL}.map{Segment(u64(it+8),u64(it+16),u64(it+32))}
fun fileOffset(address:ULong,length:Int):Int {val s=segments.single{address>=it.address&&address+length.toULong()<=it.address+it.size};return (s.offset+address-s.address).toInt()}
val sections=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)}
val symtab=sections.single{u32(it+4)==2uL};val strings=sections[u32(symtab+40).toInt()]
val symbols=(0 until (u64(symtab+32)/24u).toInt()).map{i->val p=u64(symtab+24).toInt()+24*i;val start=u64(strings+24).toInt()+u32(p).toInt();var end=start;while(bytes[end]!=0.toByte())end++;Symbol(String(bytes,start,end-start),u64(p+8),u64(p+16))}
fun symbol(name:String)=symbols.single{it.name==name}
fun word(address:ULong)=u32(fileOffset(address,4))
val ops=blocks(profile,"operations");require(ops.size==99)
val table=symbol("ap_operations");require(table.size==99uL*16u)
ops.forEachIndexed{i,o->val p=fileOffset(table.address+i.toULong()*16u,16);val read=field(o,"kind")=="R32"
    require(u32(p)==num(field(o,"sequence_index"))&&u32(p+4)==if(read)1uL else 0uL)
    require(u32(p+8)==num(field(o,"offset"))&&u32(p+12)==num(field(o,if(read)"synthetic_value" else "value"))){"compiled operation $i"}
}
val sources=listOf("ADC_RECORD","SETTING","DRV","CONFIG","SAMPLE","LOW","HIGH","GLOBAL","SERIES","MASK")
val guards=blocks(profile,"guards");require(guards.size==175)
val guardTable=symbol("ap_guards");require(guardTable.size==175uL*24u)
guards.forEachIndexed{i,g->val p=fileOffset(guardTable.address+i.toULong()*24u,24)
    require(u32(p)==sources.indexOf(field(g,"source")).toULong()&&u32(p+4)==num(field(g,"offset"))&&u32(p+8)==num(field(g,"width"))&&u64(p+16)==num(field(g,"expected_bits"))){"compiled entry guard $i"}
}
val finals=symbol("ap_final_shadows");require(finals.size==33uL*24u)
data class Final(val source:ULong,val offset:ULong,val width:ULong,val value:ULong)
val expectedFinal=blocks(String(candidate),"shadows").flatMap{s->val address=num(field(s,"address"));val width=num(field(s,"width"))
    val (source,base)=when(address){in 0x3cb44fcuL..0x3cb4534uL->5uL to 0x3cb44fcuL;in 0x3cb457cuL..0x3cb45ecuL->6uL to 0x3cb457cuL;else->7uL to 0xbe1128uL}
    field(s,"final").removeSurrounding("[","]").split(',').mapIndexed{i,v->Final(source,address-base+i.toULong()*width,width,num(v.trim()))}}
expectedFinal.forEachIndexed{i,f->val p=fileOffset(finals.address+i.toULong()*24u,24);require(Final(u32(p),u32(p+4),u32(p+8),u64(p+16))==f)}
val site=symbol("gm_ap_site");val stop=symbol("gm_ap_cp");val wrong=symbol("gm_ap_wrong_cp")
require(word(site.address)==0x52800000uL&&wrong.address==site.address+4u&&stop.address==site.address+8u&&word(stop.address)==0xd503201fuL&&word(stop.address+4u)==0xd65f03c0uL)
val loader=symbol("gm_loader_private")
val loopOffsets=(0 until loader.size.toInt()-20 step 4).filter{i->val address=loader.address+i.toULong()
    if(word(address)!=0x885ffd09uL||word(address+4u)!=0x11000529uL||word(address+8u)!=0x880afd09uL||word(address+12u)!=0x35ffffaauL)false
    else {val branch=word(address+16u);val imm=(branch and 0x03ffffffuL).toLong();val signed=if(imm and 0x02000000L!=0L)imm-0x04000000L else imm
        branch and 0xfc000000uL==0x94000000uL&&(address+16u).toLong()+4*signed==site.address.toLong()}}
require(loopOffsets.size==1){"missing contiguous final exclusive loop followed by call to stop site"}
println("schema_version = \"mho900-lab.adc-sequence-image-check/1\"\naccepted = true\nnative_sha256 = \"${hash(bytes)}\"\nbus_operations = 99\nentry_guards = 175\nfinal_shadow_values = 33\nprivate_final_atomic_loop_verified_statically = true\nprivate_stop_after_atomic_loop = true\nguest_executed = false\noperations_file_offset = ${fileOffset(table.address,16)}\nguards_file_offset = ${fileOffset(guardTable.address,24)}\natomic_loop_file_offset = ${fileOffset(loader.address+loopOffsets.single().toULong(),20)}")
