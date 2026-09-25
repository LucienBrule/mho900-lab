// Exercise calibration-loader verification against isolated semantic alterations.
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat

require(args.size in 2..3){"Usage: CheckCalibrationLoaderEvidence.main.kts RUN_DIRECTORY OUTPUT_DIRECTORY [VERIFIER_FILE]"}
val run=Path.of(args[0]).toAbsolutePath().normalize();val out=Path.of(args[1]).toAbsolutePath().normalize()
require(Files.isDirectory(run)&&!Files.exists(out));Files.createDirectories(out)
val verifier=if(args.size==3)Path.of(args[2]).toAbsolutePath().normalize() else listOf(run.resolve("source/VerifyCalibrationLoaders.main.kts"),Path.of("tools/guest/VerifyCalibrationLoaders.main.kts").toAbsolutePath()).first{Files.isRegularFile(it)}
require(Files.isRegularFile(verifier))
val source=Files.readString(run.resolve("loader-76.toml"))
fun blocks(s:String)=s.split("[[events]]").toMutableList()
fun change(s:String,kind:String,ordinal:Int,key:String,value:String):String{val p=blocks(s);val at=p.indices.filter{p[it].startsWith("\nkind = \"$kind\"\n")}[ordinal];val rx=Regex("(?m)^${Regex.escape(key)} = \"[^\"]+\"$");require(rx.findAll(p[at]).count()==1);p[at]=p[at].replace(rx){"$key = \"$value\""};return p.joinToString("[[events]]")}
fun flip(s:String,kind:String,ordinal:Int,key:String):String{val b=blocks(s).filter{it.startsWith("\nkind = \"$kind\"\n")}[ordinal];val v=Regex("(?m)^${Regex.escape(key)} = \\\"0x([0-9a-f]+)\\\"$").find(b)!!.groupValues[1].toULong(16);return change(s,kind,ordinal,key,"0x${(v xor 1uL).toString(16)}")}
fun remove(s:String,kind:String,ordinal:Int):String{val p=blocks(s);p.removeAt(p.indices.filter{p[it].startsWith("\nkind = \"$kind\"\n")}[ordinal]);return p.joinToString("[[events]]")}
data class Case(val name:String,val events:String=source,val damage:String?=null,val overrideFile:String?=null,val overrideText:String?=null,val pass:Boolean=false)
val cases=listOf(Case("accepted",pass=true),Case("changed-reference-header",overrideFile="reference.tsv",overrideText=Files.readString(run.resolve("reference.tsv")).replaceFirst("ordinal", "ORDINAL")),Case("failed-final-health",overrideFile="final-health-status.toml",overrideText=Files.readString(run.resolve("final-health-status.toml")).let{v->v.replace("pid_exit = 0","pid_exit = 1").also{require(it!=v)}}),Case("wrong-signed-status",flip(source,"loader-status",0,"actual")),Case("missing-debug-ready",remove(source,"loader-debug-ready",1)),Case("changed-checkpoint-register",flip(source,"loader-checkpoint-registers",2,"x15")),Case("missing-reap",remove(source,"group-reaped",0)),Case("wrong-prefix-write",flip(source,"modeled-write",100,"value")),Case("damaged-vertical-file",damage="loader-76-terminal-vertical.bin"))
fun hash(p:Path)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(p)))
fun q(s:String)="\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\""
var all=true;Files.newBufferedWriter(out.resolve("results.toml")).use{w->w.appendLine("schema_version = \"mho900-lab.calibration-loader-verifier-controls/1\"");w.appendLine("verifier_sha256 = ${q(hash(verifier))}")
 for(c in cases){val d=out.resolve(c.name);Files.createDirectory(d);Files.list(run).use{xs->xs.forEach{Files.createSymbolicLink(d.resolve(it.fileName),it)}};Files.delete(d.resolve("loader-76.toml"));Files.writeString(d.resolve("loader-76.toml"),c.events)
  if(c.overrideFile!=null){Files.delete(d.resolve(c.overrideFile));Files.writeString(d.resolve(c.overrideFile),requireNotNull(c.overrideText))}
  if(c.damage!=null){Files.delete(d.resolve(c.damage));val b=Files.readAllBytes(run.resolve(c.damage));b[b.size/2]=(b[b.size/2].toInt() xor 1).toByte();Files.write(d.resolve(c.damage),b)}
  val idx=d.resolve("evidence-sha256.txt");if(Files.exists(idx)){Files.delete(idx);val lines=Files.readAllLines(run.resolve("evidence-sha256.txt")).map{line->val rel=run.relativize(Path.of(line.substring(66)));val f=d.resolve(rel);hash(f)+"  "+f};Files.write(idx,lines)}
  val cmd=listOf("kotlin",verifier.toString(),d.toString());Files.writeString(d.resolve("command.txt"),cmd.joinToString("\n")+"\n");val pb=ProcessBuilder(cmd);pb.environment().remove("KOTLIN_RUNNER");val pr=pb.redirectOutput(d.resolve("stdout.toml").toFile()).redirectError(d.resolve("stderr.txt").toFile()).start();val exit=pr.waitFor();Files.writeString(d.resolve("exit.toml"),"exit_code = $exit\n");val ok=(exit==0)==c.pass;all=all&&ok;w.appendLine("\n[[cases]]");w.appendLine("name = ${q(c.name)}");w.appendLine("expected_accept = ${c.pass}");w.appendLine("exit_code = $exit");w.appendLine("expected_result = $ok");w.flush()}}
require(all){"altered evidence result mismatch"};println("result = \"accepted\"\ncases = ${cases.size}\nnegative_cases = ${cases.size-1}")
