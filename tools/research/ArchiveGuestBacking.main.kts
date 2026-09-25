// Lossless preservation for finalized generated raw backings. No overlay rewriting.
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.LinkOption.NOFOLLOW_LINKS
import java.nio.file.StandardOpenOption.*
import java.nio.file.attribute.PosixFilePermissions
import java.nio.channels.FileChannel
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.GZIPInputStream
import java.time.Instant
val root=Path.of("").toAbsolutePath().normalize()
fun inside(text:String):Path {
    val p=Path.of(text);require(!p.isAbsolute){"project-relative paths required"}
    val resolved=root.resolve(p).normalize();require(resolved.startsWith(root.resolve("out"))) { "generated output only" }
    var cursor=resolved
    while(cursor!=root){require(!Files.isSymbolicLink(cursor)){"symlink path"};cursor=cursor.parent}
    return resolved
}
fun relative(p:Path)=root.relativize(p).toString()
fun sha(p:Path):String=Files.newInputStream(p).use {s->
    val md=MessageDigest.getInstance("SHA-256");val b=ByteArray(1048576)
    while(true){val n=s.read(b);if(n<0)break;md.update(b,0,n)};HexFormat.of().formatHex(md.digest())
}
fun regular(p:Path){require(Files.isRegularFile(p,NOFOLLOW_LINKS)){"regular file required"};require(Files.getAttribute(p,"unix:nlink",NOFOLLOW_LINKS).toString().toInt()==1){"independent single-link file required"}}
fun mode(p:Path)=PosixFilePermissions.toString(Files.getPosixFilePermissions(p,NOFOLLOW_LINKS))
fun force(p:Path){FileChannel.open(p,WRITE).use{it.force(true)}}
fun active(raw:Path,overlay:Path){
    require(Files.exists(overlay,NOFOLLOW_LINKS)){"dependent overlay missing"}
    // During restoration the raw is intentionally absent; lsof treats a missing path as an error.
    val existing=listOf(raw,overlay).filter{Files.exists(it,NOFOLLOW_LINKS)}
    val pb=ProcessBuilder(listOf("lsof","-F","p","--")+existing.map{it.toString()}).redirectErrorStream(true)
    val process=pb.start();val output=process.inputStream.bufferedReader().readText();val rc=process.waitFor()
    require(rc==1 && output.isBlank()){"active image user or indeterminate open-file check"}
}
data class Manifest(val raw:Path,val overlay:Path,val rawHash:String,val overlayHash:String,val size:Long,val permissions:String,val archive:Path,val archiveHash:String)
fun writeManifest(p:Path,m:Manifest,phase:String,removed:Boolean){
    val text="""schema_version = "mho900-lab.guest-backing-archive/1"
phase = "$phase"
recorded_at = "${Instant.now()}"
raw_path = "${relative(m.raw)}"
raw_sha256 = "${m.rawHash}"
raw_bytes = ${m.size}
raw_mode = "${m.permissions}"
overlay_path = "${relative(m.overlay)}"
overlay_sha256 = "${m.overlayHash}"
archive_path = "${relative(m.archive)}"
archive_sha256 = "${m.archiveHash}"
restore_to_original_location_before_overlay_use = true
restoration_to_independent_file_verified = true
raw_removed = $removed
"""
    Files.writeString(p,text,CREATE_NEW,WRITE);force(p)
}
fun readManifest(p:Path):Manifest {
    regular(p);val text=Files.readString(p)
    fun field(key:String):String{val a=Regex("(?m)^$key = (.+)$").findAll(text).toList();require(a.size==1);return a.single().groupValues[1].removeSurrounding("\"")}
    require(field("schema_version")=="mho900-lab.guest-backing-archive/1")
    return Manifest(inside(field("raw_path")),inside(field("overlay_path")),field("raw_sha256"),field("overlay_sha256"),field("raw_bytes").toLong(),field("raw_mode"),inside(field("archive_path")),field("archive_sha256"))
}
fun archiveValid(m:Manifest){regular(m.archive);require(sha(m.archive)==m.archiveHash){"archive changed"};require(sha(m.overlay)==m.overlayHash){"overlay changed"}}
fun restore(m:Manifest,destination:Path){
    archiveValid(m);require(!Files.exists(destination,NOFOLLOW_LINKS)){"restore destination exists"}
    GZIPInputStream(Files.newInputStream(m.archive)).use{input->Files.newOutputStream(destination,CREATE_NEW,WRITE).use{output->input.copyTo(output,1048576)}}
    Files.setPosixFilePermissions(destination,PosixFilePermissions.fromString(m.permissions));force(destination);regular(destination)
    require(Files.size(destination)==m.size&&sha(destination)==m.rawHash&&mode(destination)==m.permissions){"restored identity mismatch"}
    archiveValid(m)
}
fun sourceValid(m:Manifest){regular(m.raw);regular(m.overlay);require(Files.size(m.raw)==m.size&&mode(m.raw)==m.permissions&&sha(m.raw)==m.rawHash){"source changed"};require(sha(m.overlay)==m.overlayHash){"overlay changed"};active(m.raw,m.overlay)}
require(args.isNotEmpty()){"Usage: ArchiveGuestBacking.main.kts prepare RAW OVERLAY RAW_SHA OVERLAY_SHA NEW_DIR | retire MANIFEST | restore MANIFEST NEW_DESTINATION"}
when(args[0]){
    "prepare"->{
        require(args.size==6);val raw=inside(args[1]);val overlay=inside(args[2]);val out=inside(args[5])
        require(raw!=overlay && !out.startsWith(raw) && !out.startsWith(overlay) && !Files.exists(out,NOFOLLOW_LINKS))
        regular(raw);regular(overlay);require(sha(raw)==args[3]&&sha(overlay)==args[4]){"source changed"};active(raw,overlay)
        val permissions=mode(raw);val size=Files.size(raw);Files.createDirectories(out)
        val archive=out.resolve("userdata.img.gz")
        val process=ProcessBuilder("gzip","-n","-c",raw.toString()).redirectOutput(archive.toFile()).redirectError(out.resolve("compression.stderr").toFile()).start()
        require(process.waitFor()==0){"compression failed"};force(archive)
        val m=Manifest(raw,overlay,args[3],args[4],size,permissions,archive,sha(archive))
        val restored=out.resolve("prepare-restored.img");restore(m,restored);sourceValid(m)
        writeManifest(out.resolve("prepared.toml"),m,"prepared-and-restored",false)
        // This is our newly created round-trip test file; source and archive are still present.
        Files.delete(restored)
        println("prepared = \"${relative(out.resolve("prepared.toml"))}\"")
    }
    "retire"->{
        require(args.size==2);val manifestPath=inside(args[1]);val m=readManifest(manifestPath)
        require(manifestPath.fileName.toString()=="prepared.toml")
        val out=manifestPath.parent;require(!Files.exists(out.resolve("retirement-ready.toml"))) {"retirement already attempted; inspect recovery state"}
        sourceValid(m);archiveValid(m)
        val restored=out.resolve("retirement-restored.img");restore(m,restored)
        sourceValid(m);archiveValid(m)
        writeManifest(out.resolve("retirement-ready.toml"),m,"restoration-verified-before-removal",false)
        // Repeat identity and open-user checks immediately before retiring this exact raw.
        sourceValid(m);Files.delete(m.raw)
        writeManifest(out.resolve("original-removed.toml"),m,"original-removed-archive-and-restored-copy-retained",true)
        require(sha(restored)==m.rawHash);archiveValid(m);Files.delete(restored)
        writeManifest(out.resolve("complete.toml"),m,"complete",true)
        println("complete = \"${relative(out.resolve("complete.toml"))}\"")
    }
    "restore"->{require(args.size==3);val m=readManifest(inside(args[1]));val destination=inside(args[2]);active(m.raw,m.overlay);restore(m,destination);println("restored_sha256 = \"${sha(destination)}\"")}
    else->error("unknown command")
}
