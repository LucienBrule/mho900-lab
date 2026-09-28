// Independently reconstruct pinned instruction bytes from LLVM's disassembly.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==4){"Usage: VerifyAfeStatic.main.kts STOCK_ELF CONTRACT_DIRECTORY LLVM_OBJDUMP NEW_OUTPUT"}
val elf=Path.of(args[0]);val dir=Path.of(args[1]);val llvm=Path.of(args[2]);val out=Path.of(args[3]);require(!Files.exists(out));Files.createDirectories(out)
fun sha(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
require(sha(Files.readAllBytes(elf))=="4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e")
fun text(name:String)=Files.readString(dir.resolve(name))
fun field(body:String,key:String)=Regex("(?m)^"+Regex.escape(key)+" = (.+)$").findAll(body).toList().also{require(it.size==1){"field $key"}}.single().groupValues[1].removeSurrounding("\"")
fun num(value:String)=if(value.startsWith("0x"))value.drop(2).toLong(16)else value.toLong()
val inventory=text("inventory.toml");val ranges=inventory.substringBefore("[[calls]]").split("[[ranges]]").drop(1)
val words=mutableMapOf<Long,Long>()
for(range in ranges){val address=num(field(range,"address"));val size=num(field(range,"size"));val expected=field(range,"sha256")
 val p=ProcessBuilder(llvm.toString(),"-d","--start-address=0x${address.toString(16)}","--stop-address=0x${(address+size).toString(16)}",elf.toString()).redirectErrorStream(true).start()
 val asm=p.inputStream.bufferedReader().readText();require(p.waitFor()==0){asm};Files.writeString(out.resolve("range-${address.toString(16)}.asm"),asm)
 val rows=Regex("(?m)^\\s*([0-9a-f]+):\\s+([0-9a-f]{8})\\s").findAll(asm).map{it.groupValues[1].toLong(16) to it.groupValues[2].toLong(16)}.toList()
 require(rows.map{it.first}==(0 until size/4).map{address+it*4}){"LLVM range $address"}
 val bytes=rows.flatMap{(_,word)->(0..3).map{(word ushr(it*8)).toByte()}}.toByteArray();require(sha(bytes)==expected){"range digest ${address.toString(16)}"};rows.forEach{(pc,w)->require(words.put(pc,w)==null)}
}
val callRows=inventory.split("[[calls]]").drop(1)
for(row in callRows){val pc=num(field(row,"pc"));val w=words.getValue(pc);require(w==num(field(row,"opcode")));val target=num(field(row,"branch_target"));val immediate=(w and 0x3ffffffL);val signed=(immediate shl 38)shr 38;require(pc+signed*4==target){"branch target"}}
fun word(pc:Long)=words.getValue(pc)
fun mov(pc:Long,reg:Int):Long {val w=word(pc);require(w and 0xffe0001fL==0x52800000L+reg);return(w ushr 5)and 65535}
val constants=text("constants.toml").substringBefore("[[patches]]")
for((key,value)in listOf("zero_payload_bytes" to mov(0x35067c,3),"bandwidth_payload_bytes" to mov(0x350eac,3),"patch_value" to mov(0x350f24,8),"save_rfile_mode" to mov(0x3dcd7c,1),"save_open_flags" to mov(0x25710c,9),"save_create_mode" to mov(0x257114,9)))require(num(field(constants,key))==value){"constant $key"}
val contract=text("contract.toml");val header=contract.substringBefore("[layout]");val layout=contract.substringAfter("[layout]").substringBefore("[[operations]]")
require(num(field(header,"entry_pc"))==0x333bacL&&word(0x333bac)==0x5285070aL){"entry checkpoint"}
require(num(field(header,"proposed_exit_pc"))==0x333bdcL&&word(0x333bdc)==0xb90077e0L){"exit checkpoint"}
require(num(field(layout,"zero_payload_bytes"))==mov(0x35067c,3)&&num(field(layout,"bandwidth_payload_bytes"))==mov(0x350eac,3)){"payload length"}
require(num(field(layout,"afe_from_parent"))+num(field(layout,"bandwidth_from_afe"))==num(field(layout,"save_from_global_calibration"))){"object offset arithmetic"}
require(num(field(layout,"scope_global_va"))+num(field(layout,"calibration_from_scope"))+num(field(layout,"save_from_global_calibration"))==num(field(layout,"save_global_va"))){"global source arithmetic"}
val operations=contract.substringBefore("[[unknowns]]").split("[[operations]]").drop(1).associateBy{field(it,"id")}
val patch=operations.getValue("bandwidth-patch");require(num(field(patch,"value"))==mov(0x350f24,8)){"patch value"}
val offsets=Regex("0x[0-9a-f]+").findAll(field(patch,"offsets")).map{num(it.value)}.toList()
require(offsets==(0..11).map{((word(0x350f2c+4L*it) ushr 10)and 0xfff)*4}){"patch offsets"}
val open=operations.getValue("save-open");require(num(field(open,"open_flags"))==mov(0x25710c,9)){"open flags"};require(num(field(open,"create_mode"))==mov(0x257114,9))
require(field(open,"truncates")=="false"&&field(open,"restores_umask")=="false")
for((pc,expected)in listOf(0x350698L to 0x36f802e9L,0x350ec8L to 0x36f802e9L,0x351048L to 0x12800108L,0x25709cL to 0x2a1f03e8L,0x2570a8L to 0x97fee086L,0x3dcf44L to 0x97f8b0e3L))require(word(pc)==expected){"branch/side effect anchor"}
val result="schema_version = \"mho900-lab.afe-static-verification/1\"\nresult = \"accepted\"\nranges = ${ranges.size}\ncalls = ${callRows.size}\ncontract_sha256 = \"${sha(contract.toByteArray())}\"\nllvm_sha256 = \"${sha(Files.readAllBytes(llvm))}\"\nsemantic_scope = \"instruction identities, branch destinations, selected operands and reviewed contract arithmetic; not a whole-program proof\"\n"
Files.writeString(out.resolve("results.toml"),result);print(result)
