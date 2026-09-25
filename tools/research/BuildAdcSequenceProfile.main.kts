// Compile the pinned software candidate into a bounded observer data contract.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1){"Usage: BuildAdcSequenceProfile.main.kts NEW_OUTPUT_DIRECTORY"}
val out=Path.of(args[0]);require(!Files.exists(out))
fun sha(p:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
val candidate=Path.of("experiments/adc-candidate/candidate.toml")
val sequence=Path.of("experiments/adc-candidate/sequence.tsv")
require(sha(candidate)=="5339cbe2af98ce52f99776f9eeba3b5dc391d8f1269b094123a3eec4caf19d70")
require(sha(sequence)=="d43f2f307125cd70b11c0164412ad846abc51b6b30ad092497b5ae103f8741cd")
val text=Files.readString(candidate)
fun field(block:String,key:String):String {val a=Regex("(?m)^${Regex.escape(key)} = (.+)$").findAll(block).toList();require(a.size==1);return a.single().groupValues[1].removeSurrounding("\"")}
fun num(s:String)=if(s.startsWith("0x"))s.drop(2).toLong(16)else s.toLong()
fun blocks(name:String)=text.split("[[$name]]").drop(1).map{it.substringBefore("\n[")}
fun hex(v:Long)="0x"+v.toULong().toString(16)
enum class Source(val file:String) {
    ADC_RECORD("native-loader-terminal-adc.bin"),SETTING("adc-input-setting.bin"),DRV("adc-input-drvparam.bin"),
    CONFIG("adc-input-config.bin"),SAMPLE("adc-input-sample-entry.bin"),LOW("adc-input-shadow-low.bin"),
    HIGH("adc-input-shadow-high.bin"),GLOBAL("adc-input-global-inputs.bin"),SERIES("adc-input-series.bin"),MASK("maskValue")
}
data class Guard(val name:String,val source:Source,val offset:Int,val width:Int,val expected:Long)
data class FinalShadow(val name:String,val source:Source,val offset:Int,val width:Int,val expected:Long)
sealed interface Operation {val sequenceIndex:Int;val phase:String}
data class Write(override val sequenceIndex:Int,override val phase:String,val offset:Long,val value:Long):Operation
data class Read(override val sequenceIndex:Int,override val phase:String,val offset:Long,val syntheticValue:Long):Operation
val guards=mutableListOf<Guard>();val finals=mutableListOf<FinalShadow>()
for(b in blocks("calibration_fields")+blocks("runtime_fields")){
    val type=field(b,"type");val width=when(type){"s16"->2;"u32","s32"->4;"s64"->8;"u8-bit0"->1;else->error("type $type")}
    val value=num(field(b,"value"));val bits=if(width==8)value else value and ((1L shl (width*8))-1)
    guards+=Guard(field(b,"name"),Source.entries.single{it.file==field(b,"source")},num(field(b,"offset")).toInt(),width,bits)
}
for(b in blocks("shadows")){
    val address=num(field(b,"address"));val width=num(field(b,"width")).toInt();val name=field(b,"name")
    val (source,base)=when(address){in 0x3cb44fcL..0x3cb4534L->Source.LOW to 0x3cb44fcL
        in 0x3cb457cL..0x3cb45ecL->Source.HIGH to 0x3cb457cL
        in 0xbe1138L..0xbe1150L->Source.GLOBAL to 0xbe1128L
        else->error("shadow address")}
    fun values(key:String)=field(b,key).removeSurrounding("[","]").split(',').map{num(it.trim())}
    val initial=values("initial");val final=values("final");require(initial.size==final.size)
    initial.forEachIndexed{i,v->guards+=Guard("$name[$i]",source,(address-base).toInt()+width*i,width,v)}
    final.forEachIndexed{i,v->finals+=FinalShadow("$name[$i]",source,(address-base).toInt()+width*i,width,v)}
}
for(b in blocks("mask_words")){val reg=num(field(b,"register")).toInt();guards+=Guard("mask[$reg]",Source.MASK,reg*4,4,num(field(b,"value")))}
guards+=listOf(Guard("selector0",Source.SERIES,0,4,8),Guard("selector1",Source.SERIES,4,4,900),
    Guard("specialFlag",Source.GLOBAL,12,4,0),Guard("selectedRow.selector0",Source.SERIES,0x4c,4,8),
    Guard("selectedRow.selector1",Source.SERIES,0x50,4,900),Guard("tableBound",Source.SERIES,0x5c,4,16))
require(guards.map{Triple(it.source,it.offset,it.width)}.distinct().size==guards.size)
val lengths=listOf(1936,0x1c71,0x10,0x3c,8,0x3c,0x74,0x2c,0x12c,312)
guards.forEach{require(it.width in listOf(1,2,4,8)&&it.offset>=0&&it.offset+it.width<=lengths[it.source.ordinal])}
var readIndex=0
val ops=blocks("operations").mapNotNull{b->val i=num(field(b,"index")).toInt();val phase=field(b,"phase");when(field(b,"kind")){
    "SLEEP"->null // Requests remain in stock code. This boundary does not observe elapsed/requested sleeps.
    "W32"->Write(i,phase,num(field(b,"offset")),num(field(b,"value")))
    "R32"->{require(field(b,"value_class")=="HARDWARE-RETURNED-UNOBSERVED");Read(i,phase,num(field(b,"offset")),listOf(0x11234L,0L)[readIndex++])}
    else->error("operation kind")}}
require(ops.size==99&&ops.filterIsInstance<Write>().size==97&&readIndex==2)
Files.createDirectories(out)
val header=buildString{
    append("/* Generated from the pinned software prediction; read responses are explicitly synthetic. */\n#ifndef MHO_ADC_SEQUENCE_PROFILE_H\n#define MHO_ADC_SEQUENCE_PROFILE_H\n")
    append("#define AP_OPERATIONS ${ops.size}U\n#define AP_GUARDS ${guards.size}U\n#define AP_FINAL_SHADOWS ${finals.size}U\n#define AP_SOURCES ${Source.entries.size}U\n")
    append("#define AP_RETURN_PC 0x333bacUL\n#define AP_RETURN_OPCODE 0x5285070aU\n")
    for(s in Source.entries)append("#define AP_SOURCE_${s.name} ${s.ordinal}U\n")
    append("struct ApOperation { unsigned sequence_index,read,offset,value; };\nstatic const struct ApOperation ap_operations[AP_OPERATIONS]={\n")
    for(op in ops){val(offset,value,read)=when(op){is Write->Triple(op.offset,op.value,0);is Read->Triple(op.offset,op.syntheticValue,1)};append("{${op.sequenceIndex}U,${read}U,${hex(offset)}U,${hex(value)}U},\n")}
    append("};\nstruct ApGuard { unsigned source,offset,width; U expected; };\nstatic const struct ApGuard ap_guards[AP_GUARDS]={\n")
    for(g in guards)append("{${g.source.ordinal}U,${hex(g.offset.toLong())}U,${g.width}U,${hex(g.expected)}UL},\n")
    append("};\nstatic const struct ApGuard ap_final_shadows[AP_FINAL_SHADOWS]={\n")
    for(g in finals)append("{${g.source.ordinal}U,${hex(g.offset.toLong())}U,${g.width}U,${hex(g.expected)}UL},\n")
    append("};\n#endif\n")
}
Files.writeString(out.resolve("adc-sequence-profile.h"),header)
val manifest=buildString{
    append("schema_version = \"mho900-lab.adc-sequence-profile/1\"\nclassification = \"synthetic-observer-contract\"\n")
    append("candidate_sha256 = \"${sha(candidate)}\"\nsequence_sha256 = \"${sha(sequence)}\"\nheader_sha256 = \"${sha(out.resolve("adc-sequence-profile.h"))}\"\n")
    append("bus_operations = 99\nwrites = 97\nreads = 2\nsynthetic_read_values = [0x11234, 0]\nsleep_requests_observed_at_this_boundary = false\n")
    append("entry_guards = ${guards.size}\nfinal_shadow_values = ${finals.size}\nrelocated_pointer_bytes_compared = false\n")
    append("additional_guards_required = [\"selected row equals two without fallback\", \"normalized mask zero\", \"16 relocated bindings\", \"selected config and table addresses\", \"mapped base equals observed mapping\", \"entry call arguments\"]\n")
    for((i,g)in guards.withIndex())append("\n[[guards]]\nindex = $i\nname = \"${g.name}\"\nsource = \"${g.source}\"\noffset = ${hex(g.offset.toLong())}\nwidth = ${g.width}\nexpected_bits = ${hex(g.expected)}\n")
    for((i,op)in ops.withIndex()){append("\n[[operations]]\nindex = $i\nsequence_index = ${op.sequenceIndex}\nphase = \"${op.phase}\"\n");when(op){
        is Write->append("kind = \"W32\"\noffset = ${hex(op.offset)}\nvalue = ${hex(op.value)}\n")
        is Read->append("kind = \"R32\"\noffset = ${hex(op.offset)}\nsynthetic_value = ${hex(op.syntheticValue)}\nclassification = \"MODELED-SOFTWARE-PROTOCOL-CONTROL\"\n")}}
}
Files.writeString(out.resolve("profile.toml"),manifest)
println("Compiled99 bus operations,${guards.size} typed entry guards,${finals.size} final shadow values; sleeps remain ordinary stock code")
