import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1);val out=Path.of(args[0]);require(!Files.exists(out));Files.createDirectories(out)
fun sha(p:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
val data=ByteArray(65536){(it*17).toByte()};val overlayData=byteArrayOf(1,7,3,9)
data class Fixture(val root:Path,val raw:Path,val overlay:Path,val rawHash:String,val overlayHash:String)
fun fixture(name:String):Fixture {val dir=out.resolve(name);Files.createDirectory(dir);val raw=dir.resolve("userdata.img");val overlay=dir.resolve("userdata.img.qcow2");Files.write(raw,data);Files.write(overlay,overlayData);return Fixture(dir,raw,overlay,sha(raw),sha(overlay))}
val results=StringBuilder("schema_version = \"mho900-lab.guest-backing-archive-controls/1\"\n")
fun invoke(label:String,arguments:List<String>,success:Boolean){val pb=ProcessBuilder(listOf("kotlinc","-script","tools/research/ArchiveGuestBacking.main.kts","--")+arguments);pb.environment().remove("KOTLIN_RUNNER");pb.redirectOutput(out.resolve("$label.stdout").toFile());pb.redirectError(out.resolve("$label.stderr").toFile());val rc=pb.start().waitFor();check((rc==0)==success){"$label exit $rc"};results.append("\n[[cases]]\nname = \"$label\"\nexpected_success = $success\nexit_code = $rc\nmatched = true\n");println("$label: $rc")}
fun prepare(f:Fixture,success:Boolean=true,label:String="${f.root.fileName}-prepare")=invoke(label,listOf("prepare",f.raw.toString(),f.overlay.toString(),f.rawHash,f.overlayHash,f.root.resolve("archive").toString()),success)
val positive=fixture("positive");prepare(positive)
val m=positive.root.resolve("archive/prepared.toml").toString();invoke("positive-retire",listOf("retire",m),true)
check(!Files.exists(positive.raw));invoke("positive-restore",listOf("restore",m,positive.raw.toString()),true)
check(sha(positive.raw)==positive.rawHash&&sha(positive.overlay)==positive.overlayHash)
val changed=fixture("changed-source");Files.write(changed.raw,byteArrayOf(0));prepare(changed,false)
check(Files.exists(changed.raw)&&sha(changed.overlay)==changed.overlayHash)
val late=fixture("changed-after-prepare");prepare(late);Files.write(late.raw,byteArrayOf(0))
invoke("changed-after-prepare-retire",listOf("retire",late.root.resolve("archive/prepared.toml").toString()),false)
check(Files.exists(late.raw)&&sha(late.overlay)==late.overlayHash)
val corrupt=fixture("corrupt-archive");prepare(corrupt);Files.write(corrupt.root.resolve("archive/userdata.img.gz"),byteArrayOf(0))
invoke("corrupt-archive-retire",listOf("retire",corrupt.root.resolve("archive/prepared.toml").toString()),false);check(sha(corrupt.raw)==corrupt.rawHash)
val active=fixture("active-user");val holder=ProcessBuilder("sleep","60").redirectInput(active.raw.toFile()).start()
try {prepare(active,false)} finally {holder.destroy();holder.waitFor()}
check(sha(active.raw)==active.rawHash&&sha(active.overlay)==active.overlayHash)
Files.writeString(out.resolve("results.toml"),results)
