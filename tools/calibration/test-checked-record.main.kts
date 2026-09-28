// Public synthetic vectors use a bit-at-a-time CRC independent of the inspector's Java CRC32.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
require(args.size==1){"Usage: test-checked-record.main.kts NEW_OUTPUT_DIRECTORY"}
val out=Path.of(args[0]);require(!Files.exists(out));Files.createDirectories(out)
val inspector=Path.of("tools/calibration/InspectCheckedRecord.main.kts").toAbsolutePath()
fun sha(b:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b))
fun crc(b:ByteArray):Long{var value=0xffffffffL;for(byte in b){value=value xor(byte.toLong()and 255);repeat(8){value=(value ushr 1)xor(if(value and 1L!=0L)0xedb88320L else 0L)}};return value xor 0xffffffffL}
require(crc("123456789".toByteArray())==0xcbf43926L)
fun put(b:ByteArray,offset:Int,value:Long){ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).putInt(offset,value.toInt())}
fun headerCrc(b:ByteArray){put(b,0,crc(b.copyOfRange(8,28)))}
fun record(payload:ByteArray):ByteArray{val b=ByteArray(28+payload.size);put(b,4,20);put(b,8,0x78563412);(0..7).forEach{b[12+it]=(it+1).toByte()};put(b,20,payload.size.toLong());put(b,24,crc(payload));payload.copyInto(b,28);headerCrc(b);return b}
val payload="123456789".toByteArray();val valid=record(payload)
data class Case(val name:String,val bytes:ByteArray,val expectedLength:String,val reason:String?,val public:Boolean=true)
val cases=listOf(
 Case("valid",valid,"9",null),
 Case("one-byte",record(byteArrayOf(0)),"1",null),
 Case("opaque-metadata",valid.copyOf().also{b->(8..19).forEach{b[it]=255.toByte()};headerCrc(b)},"9",null),
 Case("trailing",valid+byteArrayOf(0xca.toByte(),0xfe.toByte(),0,1),"9",null),
 Case("empty",byteArrayOf(),"9","truncated_header"),
 Case("short-header",valid.copyOfRange(0,27),"9","truncated_header"),
 Case("body-length",valid.copyOf().also{put(it,4,19)},"9","unsupported_body_length"),
 Case("header-crc",valid.copyOf().also{it[8]=(it[8].toInt()xor 1).toByte()},"9","header_crc_mismatch"),
 Case("declared-length",valid.copyOf().also{put(it,20,8);headerCrc(it)},"9","expected_length_mismatch"),
 Case("requested-length",valid,"8","expected_length_mismatch"),
 Case("short-payload",valid.copyOfRange(0,valid.size-1),"9","truncated_payload"),
 Case("payload-crc",valid.copyOf().also{it[it.lastIndex]=(it.last().toInt()xor 1).toByte()},"9","payload_crc_mismatch"),
 Case("huge-declared-length",valid.copyOf().also{put(it,20,0xffffffffL);headerCrc(it)},"9","expected_length_mismatch"),
 Case("big-endian-body-length",valid.copyOf().also{put(it,4,0x14000000)},"9","unsupported_body_length"),
 Case("precedence-body-crc",valid.copyOf().also{put(it,4,19);it[8]=0},"9","unsupported_body_length"),
 Case("precedence-crc-length",valid.copyOf().also{put(it,20,8)},"9","header_crc_mismatch"),
 Case("precedence-length-truncation",valid.copyOfRange(0,28).also{put(it,20,8);headerCrc(it)},"9","expected_length_mismatch"),
 Case("precedence-truncation-payload-crc",valid.copyOfRange(0,valid.size-1).also{put(it,24,0);headerCrc(it)},"9","truncated_payload"),
 Case("zero-expected",valid,"0","invalid_argument"),
 Case("nonnumeric-expected",valid,"n/a","invalid_argument"),
 Case("resource-limit",valid.copyOf(16*1024*1024+1),"9","input_too_large",false)
)
val vectorText=StringBuilder("schema_version = \"mho900-lab.checked-record-vectors/1\"\nclassification = \"public-synthetic-no-instrument-calibration\"\ncrc_reference = \"bit-at-a-time reflected IEEE;123456789=cbf43926\"\n")
val results=StringBuilder("schema_version = \"mho900-lab.checked-record-controls/1\"\ninspector_sha256 = \"${sha(Files.readAllBytes(inspector))}\"\nguest_runs = 0\nphysical_access = false\n")
fun execute(name:String,file:Path,expected:String,reason:String?):String {
 val builder=ProcessBuilder("kotlin",inspector.toString(),file.toString(),expected).redirectOutput(out.resolve("$name.stdout.toml").toFile()).redirectError(out.resolve("$name.stderr.txt").toFile());builder.environment().remove("KOTLIN_RUNNER");val exit=builder.start().waitFor()
 val stdout=Files.readString(out.resolve("$name.stdout.toml"));val stderr=Files.readString(out.resolve("$name.stderr.txt"))
 require(exit==if(reason==null)0 else 2){"exit $name:$exit $stderr"}
 require(stdout.contains(if(reason==null)"result = \"valid-envelope\"" else "reason = \"$reason\"")){"outcome $name"}
 require(!stdout.contains(file.toString())&&!stderr.contains(file.toString())){"input path disclosure"}
 if(reason!=null)require(!stdout.contains("raw_metadata_word =")&&!stdout.contains("payload_sha256 =")){"invalid metadata exposed"}
 results.append("\n[[cases]]\nname = \"$name\"\nexit_code = $exit\nexpected_outcome = true\n")
 return stdout
}
for(c in cases){val file=out.resolve("${c.name}.bin");Files.write(file,c.bytes);val before=sha(c.bytes)
 val stdout=execute(c.name,file,c.expectedLength,c.reason);require(sha(Files.readAllBytes(file))==before){"input mutation"}
 if(c.reason==null){val n=c.expectedLength.toInt();val trailing=c.bytes.copyOfRange(28+n,c.bytes.size)
  require(stdout.contains("payload_sha256 = \"${sha(c.bytes.copyOfRange(28,28+n))}\""))
  require(stdout.contains("trailing_bytes = ${trailing.size}\n")&&stdout.contains("trailing_sha256 = \"${sha(trailing)}\""))
  val metadata=HexFormat.of().formatHex(c.bytes.copyOfRange(12,20));require(stdout.contains("time_metadata_hex = \"$metadata\""))
  val metadataWord=ByteBuffer.wrap(c.bytes).order(ByteOrder.LITTLE_ENDIAN).getInt(8).toLong()and 0xffffffffL;require(stdout.contains("raw_metadata_word = $metadataWord\n"))
 }
 if(c.public){vectorText.append("\n[[cases]]\nname = \"${c.name}\"\nfile_hex = \"${HexFormat.of().formatHex(c.bytes)}\"\nexpected_payload_argument = \"${c.expectedLength}\"\nexpected_result = \"${c.reason?:"valid-envelope"}\"\nfile_sha256 = \"$before\"\n")}
}
execute("missing",out.resolve("does-not-exist.bin"),"9","input_unavailable")
val link=out.resolve("record-link.bin");Files.createSymbolicLink(link,Path.of("valid.bin"));execute("symlink",link,"9","input_unavailable")
execute("directory",out,"9","input_unavailable")
Files.writeString(out.resolve("vectors.toml"),vectorText.toString());Files.writeString(out.resolve("results.toml"),results.toString());println("cases = ${cases.size+3}\nresult = \"accepted\"")
