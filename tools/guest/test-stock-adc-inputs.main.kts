// Run only on an explicitly synthetic host fixture. Clone every case independently.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==2){"Usage: test-stock-adc-inputs.main.kts SYNTHETIC_BASE NEW_OUTPUT"}
val base=Path.of(args[0]).toAbsolutePath();val out=Path.of(args[1]).toAbsolutePath()
require(Files.readString(base.parent.resolve("preparation.toml")).contains("kind = \"synthetic-host-only\""))
require(!Files.exists(out));Files.createDirectories(out)
fun files(p:Path)=Files.walk(p).use{it.filter{f->Files.isRegularFile(f)}.sorted().toList()}
fun hash(p:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
fun own(p:Path){require(!Files.isSymbolicLink(p)&&Files.getAttribute(p,"unix:nlink").toString()=="1")}
fun change(p:Path,from:String,to:String){own(p);val text=Files.readString(p);require(from in text);Files.writeString(p,text.replaceFirst(from,to))}
val original=files(base).associateWith{hash(it)}
data class Case(val name:String,val mutate:(Path)->Unit)
val cases=listOf(
    Case("changed-matrix-reindexed"){r->val p=r.resolve("adc-input-matrix.bin");own(p);val b=Files.readAllBytes(p);b[5]=(b[5].toInt() xor 1).toByte();Files.write(p,b)},
    Case("failed-capture-pull"){r->change(r.resolve("adc-input-pulls.toml"),"matrix = 0","matrix = 1")},
    Case("actual-runtime-pin"){r->val p=r.resolve("source/group-probe.sh");own(p);Files.writeString(p,Files.readString(p)+"\n# changed fixture\n")},
    Case("staging-inode-alias"){r->change(r.resolve("userdata-staging.toml"),"staged_identity = \"1:2:1\"","staged_identity = \"1:1:1\"")},
    Case("terminal-resume"){r->change(r.resolve("native-events.toml"),"kind = \"adc-input-summary\"","kind = \"runtime-resume\"\ntid = \"0x1\"\n\n[[events]]\nkind = \"adc-input-summary\"")},
    Case("missing-health-result"){r->change(r.resolve("final-health-status.toml"),"processes_exit = 0\n","")},
    Case("duplicate-index"){_ ->},
    Case("unindexed-capture"){_ ->}
)
val report=StringBuilder("schema_version = \"mho900-lab.stock-adc-input-host-controls/1\"\nkind = \"synthetic-host-only\"\nguest_launched = false\n")
for(case in cases){
    val dir=out.resolve(case.name);Files.createDirectory(dir);val run=dir.resolve("run")
    val clone=ProcessBuilder("/bin/cp","-cR",base.toString(),run.toString()).start();require(clone.waitFor()==0)
    files(run).forEach{p->own(p);require(Files.getAttribute(p,"unix:ino")!=Files.getAttribute(base.resolve(run.relativize(p)),"unix:ino"))}
    case.mutate(run)
    val list=files(run).filter{it.fileName.toString()!="evidence-sha256.txt"&&(case.name!="unindexed-capture"||it.fileName.toString()!="adc-input-matrix.bin")}
    var index=list.joinToString(""){hash(it)+"  $it\n"};if(case.name=="duplicate-index")index+=index.substringBefore('\n')+"\n"
    Files.writeString(run.resolve("evidence-sha256.txt"),index)
    val pb=ProcessBuilder("kotlinc","-script",run.resolve("source/VerifyStockAdcInputs.main.kts").toString(),"--",run.toString());pb.environment().remove("KOTLIN_RUNNER");pb.redirectOutput(dir.resolve("verification.toml").toFile());pb.redirectError(dir.resolve("verification.stderr").toFile());val rc=pb.start().waitFor()
    report.append("\n[[cases]]\nname = \"${case.name}\"\nexit_code = $rc\nrejected = ${rc!=0}\nindex_regenerated = true\n")
    Files.writeString(out.resolve("results.toml"),report);require(rc!=0){"control accepted ${case.name}"}
}
original.forEach{(p,d)->require(hash(p)==d)}
Files.writeString(out.resolve("preservation.toml"),"base_unchanged = true\nindependent_copies = true\n")
println("All ${cases.size} full-profile negatives rejected.")
