import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==4){"Usage: test-afe-static.main.kts STOCK_ELF CONTRACT_DIRECTORY LLVM_OBJDUMP NEW_OUTPUT"}
val out=Path.of(args[3]);require(!Files.exists(out));Files.createDirectories(out)
val source=Path.of(args[1]);val checker=Path.of("tools/research/VerifyAfeStatic.main.kts").toAbsolutePath()
fun hash(p:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
data class Case(val name:String,val file:String?,val before:String,val after:String,val diagnostic:String)
val cases=listOf(Case("complete",null,"","",""),Case("patch-value","contract.toml","value = 115","value = 116","patch value"),Case("open-flags","contract.toml","open_flags = 0x42","open_flags = 0x242","open flags"),Case("checkpoint","contract.toml","proposed_exit_pc = 0x333bdc","proposed_exit_pc = 0x333be0","exit checkpoint"),Case("range-hash","inventory.toml","\nsha256 = \"","\nsha256 = \"0","range digest"))
val sourceHashes=Files.list(source).use{it.filter{p->p.toString().endsWith(".toml")}.toList()}.associateWith(::hash)
val checkerHash=hash(checker)
val rows=cases.map{c->val case=out.resolve(c.name);val data=case.resolve("contract");Files.createDirectories(data)
 sourceHashes.keys.forEach{Files.copy(it,data.resolve(it.fileName))}
 if(c.file!=null){val p=data.resolve(c.file);val text=Files.readString(p);require(text.contains(c.before));Files.writeString(p,text.replaceFirst(c.before,c.after))}
 val builder=ProcessBuilder("kotlin",checker.toString(),args[0],data.toString(),args[2],case.resolve("verification").toString()).redirectOutput(case.resolve("stdout.txt").toFile()).redirectError(case.resolve("stderr.txt").toFile());builder.environment().remove("KOTLIN_RUNNER");val exit=builder.start().waitFor()
 require(if(c.file==null)exit==0 else exit!=0&&Files.readString(case.resolve("stderr.txt")).contains(c.diagnostic)){"unexpected ${c.name} exit=$exit"}
 "\n[[cases]]\nname = \"${c.name}\"\nexit_code = $exit\nexpected_outcome = true\n"
}
require(sourceHashes.all{(p,h)->hash(p)==h});require(hash(checker)==checkerHash)
val result="schema_version = \"mho900-lab.afe-static-controls/1\"\npositive = 1\nnegative = 4\nguest_runs = 0\nchecker_sha256 = \"$checkerHash\"\nsource_preserved = true\n"+rows.joinToString("")
Files.writeString(out.resolve("results.toml"),result);print(result)
