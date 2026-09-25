// Inspect extracted calibration records without changing or publishing their payloads.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.CRC32

require(args.size==2){"Usage: InspectCalibrationAssets.main.kts EXTRACTED_STOCK_ROOT NEW_OUTPUT_TOML"}
val root=Path.of(args[0]);val output=Path.of(args[1]);require(!Files.exists(output))
fun hash(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
fun crc(b:ByteArray,offset:Int,count:Int)=CRC32().apply{update(b,offset,count)}.value
fun hx(n:Long)="0x"+n.toString(16)
data class Asset(val name:String,val count:Int,val expected:String)
val assets=listOf(
 Asset("cal_lsb.hex",192,"ee8fcfad06a5c3a18a265b0a46c2385c487bab4dcf5c04a398647358750bc4a2"),
 Asset("cal_vertical.hex",0x1b60c0,"ad347e84e76e258ecb894c77fd22e089c35e817e8052340c6ac3d3b8b4cce55c"),
 Asset("cal_adc.hex",1936,"")
)
Files.newBufferedWriter(output).use{w->
 w.appendLine("schema_version = \"mho900-lab.calibration-asset-inspection/1\"\nsource_scope = \"Provided extracted stock corpus only\"\nguest_state_observed = false")
 for(a in assets)for(prefix in listOf("firmware/data/","firmware/data/default/")){
  val relative=prefix+a.name;val path=root.resolve(relative)
  w.appendLine("\n[[assets]]\npath = \"$relative\"\npresent = ${Files.exists(path)}\nrequested_payload_bytes = ${a.count}")
  if(!Files.exists(path))continue
  val bytes=Files.readAllBytes(path);require(bytes.size>=28)
  val b=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
  fun u32(i:Int)=b.getInt(i).toLong()and 0xffffffffL
  val size=u32(20);require(u32(4)==20L&&size==a.count.toLong()&&size<=bytes.size-28)
  require(u32(0)==crc(bytes,8,20)&&u32(24)==crc(bytes,28,a.count))
  require(prefix.endsWith("default/")&&hash(bytes)==a.expected){"Asset set differs from reviewed stock corpus"}
  w.appendLine("file_bytes = ${bytes.size}\nsha256 = \"${hash(bytes)}\"\nheader_bytes = 28\nheader_crc32 = ${hx(u32(0))}\npayload_crc32 = ${hx(u32(24))}\npayload_sha256 = \"${hash(bytes.copyOfRange(28,28+a.count))}\"\ntrailing_bytes = ${bytes.size-28-a.count}\ncrc_valid = true")
 }
}
println("result = \"accepted\"\nmanifest_sha256 = \"${hash(Files.readAllBytes(output))}\"")
