// Verify the ADC-parameter static grammar against the pinned stock ELF.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size == 2) { "Usage: VerifyAdcParameter.main.kts STOCK_ELF CONTRACT_DIR" }
val elfPath = Path.of(args[0]); val dir = Path.of(args[1])
fun sha(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
fun num(s0:String):Long { val s=s0.trim(); require(s.matches(Regex("(?:-?[0-9]+|0x[0-9a-fA-F]+)"))){"bad integer $s"}; return if(s.startsWith("0x"))s.drop(2).toLong(16) else s.toLong() }
fun bool(s:String)=when(s.trim()){ "true"->true;"false"->false;else->error("bad boolean $s") }
fun str(s0:String):String { val s=s0.trim();require(s.length>=2&&s.first()=='\"'&&s.last()=='\"'){"bad string $s"};val o=StringBuilder();var i=1;while(i<s.lastIndex){val c=s[i++];if(c!='\\')o.append(c)else when(val e=s[i++]){'\\'->o.append('\\');'\"'->o.append('\"');'n'->o.append('\n');'t'->o.append('\t');else->error("bad escape $e")}};return o.toString() }
fun arr(s0:String):List<String>{val s=s0.trim();require(s.startsWith("[")&&s.endsWith("]"));val body=s.substring(1,s.lastIndex);if(body.isBlank())return emptyList();val out=mutableListOf<String>();var q=false;var esc=false;var begin=0;for(i in body.indices){val c=body[i];if(esc){esc=false;continue};if(q&&c=='\\'){esc=true;continue};if(c=='\"')q=!q;if(c==','&&!q){out+=body.substring(begin,i).trim();begin=i+1}};require(!q&&!esc);out+=body.substring(begin).trim();return out}
data class Tab(val kind:String,val array:Boolean,val v:LinkedHashMap<String,String> = linkedMapOf())
data class Doc(val root:LinkedHashMap<String,String>,val tabs:List<Tab>)
fun parse(p:Path):Doc{val root=linkedMapOf<String,String>();val ts=mutableListOf<Tab>();var cur:Tab?=null;Files.readAllLines(p).forEachIndexed{ix,src->val line=src.trim();if(line.isEmpty()||line.startsWith("#"))return@forEachIndexed;if(line.startsWith("[[")){require(line.endsWith("]]")){"bad table ${ix+1}"};cur=Tab(line.substring(2,line.length-2).trim(),true);ts+=cur!!;return@forEachIndexed};if(line.startsWith("[")){require(line.endsWith("]"));val k=line.substring(1,line.lastIndex).trim();require(ts.none{!it.array&&it.kind==k}){"duplicate table $k"};cur=Tab(k,false);ts+=cur!!;return@forEachIndexed};val eq=line.indexOf('=');require(eq>0){"bad assignment ${ix+1}"};val k=line.substring(0,eq).trim();val value=line.substring(eq+1).trim();require(k.matches(Regex("[a-z_][a-z0-9_.-]*"))&&value.isNotEmpty());require((cur?.v?:root).put(k,value)==null){"duplicate $k"}};return Doc(root,ts)}
fun tabs(d:Doc,k:String)=d.tabs.filter{it.array&&it.kind==k};fun tab(d:Doc,k:String)=d.tabs.single{!it.array&&it.kind==k}
fun sv(t:Tab,k:String)=str(t.v.getValue(k));fun nv(t:Tab,k:String)=num(t.v.getValue(k));fun bv(t:Tab,k:String)=bool(t.v.getValue(k));fun na(t:Tab,k:String)=arr(t.v.getValue(k)).map(::num)
data class Seg(val file:Long,val va:Long,val fileSize:Long,val memSize:Long)
data class Sec(val type:Int,val file:Long,val size:Long,val link:Int,val entry:Long)
data class Sym(val name:String,val value:Long,val size:Long,val section:Int)
data class Rel(val slot:Long,val type:Long,val symbol:Sym?)
class Elf(val raw:ByteArray){private val b=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);private fun u16(p:Int)=b.getShort(p).toInt()and 0xffff;private fun u32(p:Int)=b.getInt(p).toLong()and 0xffffffffL;private fun u64(p:Int)=b.getLong(p);private val segs:List<Seg>;val symbols:Map<String,Sym>;val rels:Map<Long,Rel>
 init{require(raw.size>=64&&raw[0]==0x7f.toByte()&&String(raw,1,3)=="ELF"&&raw[4]==2.toByte()&&raw[5]==1.toByte()&&u16(18)==183){"not AArch64 ELF64 LE"};segs=(0 until u16(56)).map{u64(32).toInt()+it*u16(54)}.filter{u32(it)==1L}.map{Seg(u64(it+8),u64(it+16),u64(it+32),u64(it+40))};val ss=(0 until u16(60)).map{u64(40).toInt()+it*u16(58)}.map{Sec(u32(it+4).toInt(),u64(it+24),u64(it+32),u32(it+40).toInt(),u64(it+56))};fun syms(s:Sec):List<Sym>{require(s.entry==24L);val strings=ss[s.link];return(0 until(s.size/s.entry).toInt()).map{i->val p=(s.file+i*s.entry).toInt();val st=(strings.file+u32(p)).toInt();var en=st;while(raw[en]!=0.toByte())en++;Sym(String(raw,st,en-st),u64(p+8),u64(p+16),u16(p+6))}};val all=ss.filter{it.type==11}.flatMap(::syms);symbols=all.filter{it.name.isNotEmpty()}.groupBy{it.name}.mapValues{(_,l)->l.firstOrNull{it.section!=0}?:l.first()};val rm=mutableMapOf<Long,Rel>();ss.filter{it.type==4}.forEach{s->val ls=syms(ss[s.link]);repeat((s.size/s.entry).toInt()){i->val p=(s.file+i*s.entry).toInt();val info=u64(p+8);val si=(info ushr 32).toInt();val r=Rel(u64(p),info and 0xffffffffL,if(si==0)null else ls[si]);require(rm.put(r.slot,r)==null)}};rels=rm}
 private fun off(va:Long,n:Int):Int{val s=segs.single{va>=it.va&&va+n<=it.va+it.fileSize};return(s.file+va-s.va).toInt()};fun bytes(va:Long,n:Int)=raw.copyOfRange(off(va,n),off(va,n)+n);fun word(va:Long)=ByteBuffer.wrap(bytes(va,4)).order(ByteOrder.LITTLE_ENDIAN).int.toLong()and 0xffffffffL
}
val pin="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e";val raw=Files.readAllBytes(elfPath);require(sha(raw)==pin){"stock ELF hash"};val elf=Elf(raw)
fun load(n:String)=parse(dir.resolve(n).also{require(Files.isRegularFile(it)){"missing $n"}})
fun root(d:Doc,k:String)=d.root.getValue(k);fun checkPin(d:Doc){require(str(root(d,"stock_elf_sha256"))==pin)}
fun branch(pc:Long,op:Long):Long{require((op ushr 26)==0x25L){"not BL 0x${pc.toString(16)}"};var imm=op and 0x3ffffff;if((imm and 0x2000000)!=0L)imm=imm or -0x4000000;return pc+(imm shl 2)}
fun pltSlot(pc:Long):Long{val a=elf.word(pc);val l=elf.word(pc+4);require((a and 0x9f00001fL)==0x90000010L&&(l and 0xffc003ffL)==0xf9400211L){"PLT encoding 0x${pc.toString(16)}"};var imm=((a ushr 29)and 3)or(((a ushr 5)and 0x7ffff)shl 2);if((imm and 0x100000)!=0L)imm=imm or -0x200000;return(pc and -4096L)+(imm shl 12)+(((l ushr 10)and 0xfff)shl 3)}

val inv=load("call-inventory.toml");checkPin(inv);require(str(root(inv,"schema_version"))=="mho900-lab.adc-parameter-inventory/1")
data class Range(val name:String,val start:Long,val end:Long)
val ranges=linkedMapOf<String,Range>();for(t in tabs(inv,"ranges")){val n=sv(t,"name");val a=nv(t,"address");val z=a+nv(t,"size");require(ranges.put(n,Range(n,a,z))==null){"duplicate range $n"};val s=requireNotNull(elf.symbols[n]){"missing symbol $n"};require(s.section!=0&&s.value==a&&s.size==z-a){"symbol range $n"};require(sha(elf.bytes(a,(z-a).toInt()))==sv(t,"sha256")){"range hash $n"}}
require(ranges.size==35){"range count"}
val calls=tabs(inv,"calls");val callKeys=mutableSetOf<Pair<String,Long>>();for(t in calls){val owner=sv(t,"owner");val pc=nv(t,"pc");val op=nv(t,"opcode");require(callKeys.add(owner to pc)){"duplicate call"};val rr=requireNotNull(ranges[owner]);require(pc in rr.start until rr.end&&elf.word(pc)==op){"call bytes $owner 0x${pc.toString(16)}"};val bt=branch(pc,op);require(bt==nv(t,"branch_target"));val symbol=sv(t,"symbol");val resolved=nv(t,"resolved_target");if("relocation_slot" in t.v){val slot=nv(t,"relocation_slot");require(pltSlot(bt)==slot);val rel=requireNotNull(elf.rels[slot]);require(rel.symbol?.name==symbol){"relocation 0x${slot.toString(16)}"};if(rel.symbol?.section!=0)require(rel.symbol?.value==resolved){"resolved target $symbol"}}else if(symbol!="UNRESOLVED"){val s=requireNotNull(elf.symbols[symbol]);require(s.section!=0&&s.value==resolved&&bt==resolved){"direct target $symbol"}}else require(bt==resolved)}
for(t in tabs(inv,"branches")){val owner=sv(t,"owner");val pc=nv(t,"pc");require(pc in ranges.getValue(owner).start until ranges.getValue(owner).end){"branch range $owner 0x${pc.toString(16)}"};require(elf.word(pc)==nv(t,"opcode")){"branch bytes $owner 0x${pc.toString(16)}"};if(sv(t,"kind")=="return")require(na(t,"successors").isEmpty())else require(na(t,"successors").isNotEmpty()){"branch successors $owner 0x${pc.toString(16)}"}}
for(t in tabs(inv,"tables")){val a=nv(t,"address");val n=nv(t,"bytes").toInt();require(n>0&&sha(elf.bytes(a,n))==sv(t,"sha256")){"inventory table ${sv(t,"id")}"}}

// Independently walk byte-decoded successors, so omitted calls/branches and
// altered successors cannot pass merely by retaining the original range hash.
fun sx(value:Long,bits:Int)=(value shl (64-bits)) shr (64-bits)
val prune=mapOf(0x33f074L to 0x3500042bL,0x33f794L to 0x35000768L,0x33ee24L to 0x540006ecL)
require(prune.all{(pc,op)->elf.word(pc)==op})
val jumpSpecs=mapOf(0x281a8cL to (0x9945ccL to 8),0x281f60L to (0x99460cL to 8),0x284500L to (0x9946fcL to 8),0x347ac0L to (0x99c558L to 4))
val allBranches=tabs(inv,"branches")
for(rr in ranges.values){
 val pending=ArrayDeque<Long>();pending.add(rr.start);val seen=mutableSetOf<Long>()
 val branchPcs=mutableSetOf<Long>();val callPcs=mutableSetOf<Long>()
 while(pending.isNotEmpty()){
  val pc=pending.removeFirst();if(!seen.add(pc))continue
  require(pc%4==0L&&pc in rr.start until rr.end)
  val op=elf.word(pc);var kind="fallthrough"
  val next=when{
   pc in prune->{kind="mode-zero-fallthrough";listOf(pc+4)}
   op and 0xfffffc1fL==0xd65f0000L->{kind="return";emptyList()}
   op and 0xfffffc1fL==0xd61f0000L->{kind="table-branch";val (a,n)=requireNotNull(jumpSpecs[pc]){"unresolved BR"};(0 until n).map{a+sx(elf.word(a+4L*it),32)}}
   op and 0xfc000000L==0x14000000L->{kind="branch";listOf(pc+(sx(op and 0x3ffffff,26) shl 2))}
   op and 0xff000010L==0x54000000L->{kind="conditional";listOf(pc+4,pc+(sx((op ushr 5)and 0x7ffff,19) shl 2))}
   op and 0x7e000000L==0x34000000L->{kind="compare-branch";listOf(pc+4,pc+(sx((op ushr 5)and 0x7ffff,19) shl 2))}
   op and 0x7e000000L==0x36000000L->{kind="test-bit-branch";listOf(pc+4,pc+(sx((op ushr 5)and 0x3fff,14) shl 2))}
   else->listOf(pc+4)
  }
  if(kind!="fallthrough"){
   branchPcs+=pc;val supplied=allBranches.single{sv(it,"owner")==rr.name&&nv(it,"pc")==pc}
   require(sv(supplied,"kind")==kind&&na(supplied,"successors")==next){"decoded branch successors"}
  }
  if(op and 0xfc000000L==0x94000000L)callPcs+=pc
  require(op and 0xfffffc1fL!=0xd63f0000L){"unresolved indirect call"}
  next.filter{it in rr.start until rr.end}.forEach(pending::addLast)
 }
 require(allBranches.filter{sv(it,"owner")==rr.name}.map{nv(it,"pc")}.toSet()==branchPcs){"branch coverage"}
 require(calls.filter{sv(it,"owner")==rr.name}.map{nv(it,"pc")}.toSet()==callPcs){"call coverage"}
 val rt=tabs(inv,"ranges").single{sv(it,"name")==rr.name}
 require(nv(rt,"reachable_instruction_count")==seen.size.toLong()){"reachable instruction count"}
}
for(t in calls){
 val dest=nv(t,"branch_target");val name=sv(t,"symbol")
 if("relocation_slot" in t.v){val s=requireNotNull(elf.rels[nv(t,"relocation_slot")]?.symbol);require(nv(t,"resolved_target")==s.value&&bv(t,"defined")== (s.section!=0))}
 else if(name=="UNRESOLVED")require(nv(t,"resolved_target")==dest&&!bv(t,"defined"))
 else{val s=elf.symbols.getValue(name);require(s.value==dest&&nv(t,"resolved_target")==dest&&bv(t,"defined"))}
 require(bv(t,"expanded")==ranges.containsKey(name)){"expanded target"}
}
for(t in tabs(inv,"tables")){val a=nv(t,"address");val n=nv(t,"bytes").toInt();require(nv(t,"element_width")==4L&&bv(t,"signed"));require(na(t,"values")== (0 until n/4).map{sx(elf.word(a+4L*it),32)}){"decoded table values"}}

val main=load("main-grammar.toml");checkPin(main);require(str(root(main,"schema_version"))=="mho900-lab.adc-parameter-main-grammar/1");require(num(root(main,"function_start"))==0x33efe0L&&num(root(main,"function_end_exclusive"))==0x33fc80L&&num(root(main,"mode"))==0L);require(num(root(main,"mode_zero_main_call_sites"))==13L&&num(root(main,"mode_zero_main_call_invocations"))==35L&&num(root(main,"record_reads_described_here"))==62L)
val nodes=tabs(main,"nodes");val ids=listOf("reference","spu-gain","quad-gain","stary","core-offset","sample-clock-delay","clock-delay","synchronize","return");require(nodes.map{sv(it,"id")}==ids&&nodes.map{nv(it,"order")}==(0L..8L).toList()){"main node order"}
data class Field(val base:Long,val stride:Long,val width:Long,val count:Long,val signed:Boolean)
val fields=mapOf("reference" to Field(0x8854,2,2,2,true),"spu-gain" to Field(0x8cd4,4,4,16,false),"quad-gain" to Field(0x8824,2,2,16,true),"core-offset" to Field(0x8804,2,2,16,true),"sample-clock-delay" to Field(0x8844,2,2,8,true),"clock-delay" to Field(0x8a04,2,2,4,true))
for(t in nodes.filter{sv(it,"id") in fields}){val f=fields.getValue(sv(t,"id"));require(nv(t,"field_base")==f.base&&nv(t,"field_stride")==f.stride&&nv(t,"field_width")==f.width&&nv(t,"field_count")==f.count&&bv(t,"signed")==f.signed){"field ${sv(t,"id")}"};na(t,"load_pcs").forEach{elf.word(it)}}
val loadOpcodes=mapOf(0x33f024L to 0x78ea6901L,0x33f048L to 0x78e86921L,0x33ec68L to 0x79c001a2L,0x33ecd8L to 0x79c001a2L,0x33ed30L to 0x79c001a2L,0x33ed88L to 0x79c001a2L,0x33ee74L to 0xb86c690bL,0x33eedcL to 0xb86c690bL,0x33f774L to 0x78ea6902L,0x33f7fcL to 0x78e96902L,0x33f838L to 0x78e96941L,0x33f844L to 0x78e96942L,0x33f85cL to 0x78e96941L,0x33f868L to 0x78e96942L);require(loadOpcodes.all{(p,o)->elf.word(p)==o}){"field load opcode/width/signedness"}
val loopOpcodes=mapOf(0x33ee3cL to 0x71001d08L,0x33eea4L to 0x71003d08L,0x33f730L to 0x71003d08L,0x33f734L to 0x540002ecL,0x33f7acL to 0x71000508L,0x33f7b0L to 0x540003ecL,0x33f7c8L to 0x71000d08L,0x33f7ccL to 0x5400026cL);require(loopOpcodes.all{(p,o)->elf.word(p)==o}){"main loop compare/branch opcodes"}
require(nv(nodes[4],"iteration_first")==0L&&nv(nodes[4],"iteration_last_inclusive")==15L&&nv(nodes[4],"iteration_stride")==1L);require(na(nodes[5],"sample_clock_order")==listOf(0L,2L,1L,3L));require(na(nodes[1],"loop_bounds_inclusive")==listOf(7L,15L))
val expectedCalls=listOf(0x33f038L,0x33f058L,0x33f06cL,0x33f094L,0x33f0acL,0x33f0c4L,0x33f0dcL,0x33f0f0L,0x33f778L,0x33f800L,0x33f84cL,0x33f878L,0x33fc4cL);require(nodes.flatMap{if("call_pcs" in it.v)na(it,"call_pcs")else emptyList()}.toSet()==expectedCalls.toSet());require(expectedCalls.all{p->calls.any{nv(it,"pc")==p}}){"main call inventory"}
val flow=tab(main,"control_flow");na(flow,"forced_fallthrough_pcs").forEach{elf.word(it)}

val stary=load("stary-grammar.toml");checkPin(stary);require(num(root(stary,"start"))==0x33fc80L&&num(root(stary,"end_exclusive"))==0x341840L&&sha(elf.bytes(0x33fc80,0x1bc0))==str(root(stary,"range_sha256")))
val expectedTables=mapOf("delay-map" to listOf(0L,4L,2L,6L,1L,5L,3L,7L),"lane-permutation" to listOf(3L,2L,1L,0L,7L,6L,5L,4L,11L,10L,9L,8L,15L,14L,13L,12L));for(t in tabs(stary,"tables")){val a=nv(t,"address");val n=nv(t,"length").toInt();require(sha(elf.bytes(a,n))==sv(t,"sha256")){"stary table hash"};expectedTables[sv(t,"id")]?.let{require(na(t,"values")==it){"stary table values"}}}
val sel=tab(stary,"selection");require(na(sel,"supported_rates")==listOf(1000000000L,2000000000L,4000000000L)&&na(sel,"factor_by_rate")==listOf(4L,2L,1L)&&na(sel,"outer_count_by_rate")==listOf(4L,8L,16L)&&na(sel,"inner_count_by_rate")==listOf(4L,2L,1L))
val paths=tab(stary,"path_counts");require(nv(paths,"supported_rate_writes")==148L&&nv(paths,"sample_rate_le_500mhz_writes")==1L&&nv(paths,"unsupported_rate_above_500mhz_writes")==4L)
val friendly=mapOf("GetVerticalScale" to "_Z16GetVerticalScalei","Drv_GetSetting" to "_Z14Drv_GetSettingj","CChannel::getImpedance" to "_ZN8CChannel12getImpedanceEv","Drv_GetScope" to "_Z12Drv_GetScopev","CDrvScope::GetDrvParam" to "_ZN9CDrvScope11GetDrvParamEj","CDrvParam::GetSampleRate" to "_ZN9CDrvParam13GetSampleRateEv","CCalibration_ADC::DrvCalibration_GetChDly" to "_ZN16CCalibration_ADC23DrvCalibration_GetChDlyEPj")
for(t in tabs(stary,"bindings")){val r=requireNotNull(elf.rels[nv(t,"slot")]);require(r.symbol?.name==sv(t,"name")&&r.symbol?.value==nv(t,"target")){"stary data binding ${sv(t,"name")}"}}
for(t in tabs(stary,"call_bindings")){val name=sv(t,"name");val r=requireNotNull(elf.rels[nv(t,"slot")]);require(r.symbol?.name==friendly.getOrDefault(name,name)&&r.symbol?.value==nv(t,"target")){"stary call binding $name"}}

val sr=load("stary-refinements.toml");checkPin(sr);require(str(root(sr,"schema_version"))=="mho900-lab.adc-stary-static-refinements/1");require(num(root(sr,"function_start"))==0x33fc80L&&num(root(sr,"function_end_exclusive"))==0x341840L&&str(root(sr,"function_sha256"))==sha(elf.bytes(0x33fc80,0x1bc0)))
val acc=tabs(sr,"adc_state_accesses");require(acc.map{nv(it,"pc")}==listOf(0x33ffd4L,0x34001cL,0x340028L,0x34002cL)&&acc.all{nv(it,"width")==4L});val sample=tab(sr,"sample_rate");require(sv(sample,"representation").contains("signed int64")&&listOf("gate","rate4","rate2","rate1").all{p->elf.word(nv(sample,"${p}_load_pc"));elf.word(nv(sample,"${p}_convert_pc"));elf.word(nv(sample,"${p}_compare_pc"));elf.word(nv(sample,"${p}_branch_pc"));true})
val matrix=tab(sr,"matrix_window");require(nv(matrix,"root_offset")==0x4eb4L&&nv(matrix,"mode_stride")==0xe40L&&nv(matrix,"scale_stride")==0xc0L&&nv(matrix,"cell_width")==4L&&nv(matrix,"cell_min")==0L&&nv(matrix,"cell_max")==15L&&nv(matrix,"conservative_end_exclusive")==0x5cf4L&&bv(matrix,"disjoint"))
val loops=tabs(sr,"loop_witnesses");require(loops.map{nv(it,"rate")}==listOf(4000000000L,2000000000L,1000000000L)&&loops.map{nv(it,"factor")}==listOf(1L,2L,4L)&&loops.map{nv(it,"outer_count")*nv(it,"inner_count")}==listOf(16L,16L,16L));for(t in loops)t.v.filterKeys{it.endsWith("_pc")}.values.map(::num).forEach{elf.word(it)}
for(t in tabs(sr,"call_witnesses")){val pc=nv(t,"pc");require(calls.any{nv(it,"pc")==pc}){"stary witness 0x${pc.toString(16)}"}}

val helper=load("helper-grammar.toml");checkPin(helper);require(str(root(helper,"schema_version"))=="mho900-lab.adc-parameter-helper-grammar/1");require(!bool(root(helper,"asynchronous_boundary"))&&bool(root(helper,"hardware_read_present"))&&!bool(root(helper,"hardware_read_control_use"))&&!bool(root(helper,"shadows_assumed_zero")))
for(t in tabs(helper,"shadow")){val r=requireNotNull(elf.rels[nv(t,"got_slot")]);require(r.symbol?.name==sv(t,"name")){"helper shadow ${sv(t,"name")}"};require(nv(t,"element_width") in setOf(2L,4L))}
for(kind in listOf("function","delay_child","transport"))for(t in tabs(helper,kind)){val a=nv(t,"start");val z=nv(t,"end");require(z>a&&sha(elf.bytes(a,(z-a).toInt()))==sv(t,"sha256")){"helper range ${sv(t,"name")}"}}
val adj=tab(helper,"adjustment_write_count");require(nv(adj,"reset")==2L&&nv(adj,"offset_mode")==1L&&nv(adj,"offset_bypass")==1L&&nv(adj,"supported_path_lanes")==16L&&nv(adj,"per_lane_gain")==3L&&nv(adj,"per_lane_offset1")==3L&&nv(adj,"per_lane_offset2")==3L&&nv(adj,"total")==148L)
for(t in tabs(helper,"function").filter{"jump_table" in it.v}){val a=nv(t,"jump_table");val n=if(sv(t,"name")=="DevAcquireADC_SetDlySmpClk")32 else 32;require(sha(elf.bytes(a,n))==sv(t,"jump_table_sha256")){"jump table ${sv(t,"name")}"}}

val hr=load("helper-refinements.toml");checkPin(hr);require(str(root(hr,"schema_version"))=="mho900-lab.adc-parameter-helper-refinements/1"&&num(root(hr,"binding_count"))==16L&&num(root(hr,"mutable_object_count"))==15L&&bool(root(hr,"hardware_read_control_use_inside_protocol"))&&!bool(root(hr,"hardware_read_control_use_after_getter")));val hbindings=tabs(hr,"binding");require(hbindings.size==16&&hbindings.map{nv(it,"index")}==(0L..15L).toList());for(t in hbindings){val r=requireNotNull(elf.rels[nv(t,"got_slot")]);require(r.symbol?.name==sv(t,"name")&&r.symbol?.value==nv(t,"expected_target")){"helper binding ${sv(t,"name")}"}}
val mask=tab(hr,"mask_table");require(nv(mask,"address")==0x9948bcL&&nv(mask,"entry_width")==4L&&nv(mask,"entry_count")==104L&&sha(elf.bytes(0x9948bc,416))==sv(mask,"full_sha256"))
val getter=load("getter-inputs.toml");checkPin(getter);require(str(root(getter,"schema_version"))=="mho900-lab.adc-parameter-getter-inputs/1"&&!bool(root(getter,"asynchronous_boundary"))&&!bool(root(getter,"direct_mmio"))&&num(root(getter,"opaque_defined_getter_count"))==0L);val getters=tabs(getter,"getter");require(getters.size==17);for(t in getters){val a=nv(t,"start");val z=nv(t,"end");require(z>a&&sha(elf.bytes(a,(z-a).toInt()))==sv(t,"sha256")){"getter ${sv(t,"name")}"}}
val scope=load("scope.toml");checkPin(scope);require(str(root(scope,"schema_version"))=="mho900-lab.adc-parameter-scope/1"&&!bool(root(scope,"semantic_prose_automatically_proven"))&&!bool(root(scope,"fpga_semantics_recovered")));val predicted=tab(scope,"predicted_counts");require(nv(predicted,"non_stary_writes")==96L&&nv(predicted,"total_writes_bypass")==96L+nv(paths,"sample_rate_le_500mhz_writes")&&nv(predicted,"total_writes_unsupported_rate")==96L+nv(paths,"unsupported_rate_above_500mhz_writes")&&nv(predicted,"total_writes_supported_rate")==96L+nv(paths,"supported_rate_writes")&&nv(predicted,"total_reads")==2L&&nv(predicted,"non_stary_requested_delay_us")==5200L&&nv(predicted,"bypass_requested_delay_us")==25200L&&nv(predicted,"other_requested_delay_us")==45200L)

val integer=load("integer-refinements.toml");checkPin(integer)
for(t in tabs(integer,"getter")){val a=nv(t,"start");val z=nv(t,"end");require(sha(elf.bytes(a,(z-a).toInt()))==sv(t,"sha256")){"integer getter range"}}
for(t in integer.tabs)for((key,value) in t.v.filterKeys{it.endsWith("_opcode")}){
 val pc=nv(t,key.removeSuffix("_opcode")+"_pc")
 require(elf.word(pc)==num(value)){"integer instruction ${t.kind} $key"}
}

println("schema_version = \"mho900-lab.verify-adc-parameter/1\"")
println("result = \"accepted\"")
println("stock_elf_sha256 = \"$pin\"")
println("ranges_verified = ${ranges.size}")
println("calls_verified = ${calls.size}")
println("main_nodes_verified = ${nodes.size}")
println("stary_tables_verified = ${tabs(stary,"tables").size}")
println("helper_ranges_verified = ${listOf("function","delay_child","transport").sumOf{tabs(helper,it).size}}")
println("getter_ranges_verified = ${getters.size}")
println("relocations_verified = ${tabs(stary,"bindings").size+tabs(stary,"call_bindings").size+hbindings.size}")
println("structural_limit = \"ELF bytes, symbols, relocations, tables, and selected instruction witnesses are bound; semantic prose is not automatically proved.\"")
