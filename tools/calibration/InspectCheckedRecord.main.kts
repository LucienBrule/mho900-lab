// Read-only bounded inspection of the recovered stock .26 checked-record envelope.
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import java.util.zip.CRC32
import kotlin.system.exitProcess

val maximumFileBytes=16*1024*1024 // Inspector resource policy, not an instrument limit.
enum class Reason { INVALID_ARGUMENT, INPUT_UNAVAILABLE, INPUT_TOO_LARGE, TRUNCATED_HEADER,
    UNSUPPORTED_BODY_LENGTH, HEADER_CRC_MISMATCH, EXPECTED_LENGTH_MISMATCH,
    TRUNCATED_PAYLOAD, PAYLOAD_CRC_MISMATCH }
data class Envelope(val rawMetadataWord:Long,val timeBytes:String,val payloadBytes:Int,
    val headerCrc:Long,val payloadCrc:Long,val payloadSha256:String,val trailingBytes:Int,val trailingSha256:String)
sealed interface Inspection {
    data class Valid(val envelope:Envelope):Inspection
    data class Invalid(val reason:Reason):Inspection
}
fun sha(bytes:ByteArray)=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))
fun crc(bytes:ByteArray,offset:Int,size:Int)=CRC32().apply{update(bytes,offset,size)}.value
fun inspect(bytes:ByteArray,expected:Int):Inspection {
    fun invalid(reason:Reason)=Inspection.Invalid(reason)
    if(bytes.size<28)return invalid(Reason.TRUNCATED_HEADER)
    val buffer=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
    fun u32(offset:Int)=buffer.getInt(offset).toLong()and 0xffffffffL
    if(u32(4)!=20L)return invalid(Reason.UNSUPPORTED_BODY_LENGTH)
    if(u32(0)!=crc(bytes,8,20))return invalid(Reason.HEADER_CRC_MISMATCH)
    if(u32(20)!=expected.toLong())return invalid(Reason.EXPECTED_LENGTH_MISMATCH)
    if(expected>bytes.size-28)return invalid(Reason.TRUNCATED_PAYLOAD)
    if(u32(24)!=crc(bytes,28,expected))return invalid(Reason.PAYLOAD_CRC_MISMATCH)
    return Inspection.Valid(Envelope(u32(8),HexFormat.of().formatHex(bytes.copyOfRange(12,20)),expected,
        u32(0),u32(24),sha(bytes.copyOfRange(28,28+expected)),bytes.size-28-expected,
        sha(bytes.copyOfRange(28+expected,bytes.size))))
}
fun report(result:Inspection,bytes:ByteArray?):Int {
    println("schema_version = \"mho900-lab.checked-record-inspection/1\"")
    println("format_profile = \"stock-0.26-checked-record\"")
    println("reference_library_sha256 = \"4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e\"")
    println("physical_calibration_validated = false")
    println("maximum_file_bytes = $maximumFileBytes")
    if(bytes!=null){println("file_bytes = ${bytes.size}");println("file_sha256 = \"${sha(bytes)}\"")}
    when(result){
        is Inspection.Invalid->{println("result = \"rejected\"");println("reason = \"${result.reason.name.lowercase()}\"");return 2}
        is Inspection.Valid->{val e=result.envelope;println("result = \"valid-envelope\"")
            println("raw_metadata_word = ${e.rawMetadataWord}\ntime_metadata_hex = \"${e.timeBytes}\"\npayload_bytes = ${e.payloadBytes}")
            println("header_crc32 = ${e.headerCrc}\npayload_crc32 = ${e.payloadCrc}\npayload_sha256 = \"${e.payloadSha256}\"")
            println("trailing_bytes = ${e.trailingBytes}\ntrailing_sha256 = \"${e.trailingSha256}\"")
            return 0
        }
    }
}
val expected=args.getOrNull(1)?.toIntOrNull()
if(args.size!=2||expected==null||expected !in 1..maximumFileBytes-28)
    exitProcess(report(Inspection.Invalid(Reason.INVALID_ARGUMENT),null))
val input=try{Path.of(args[0])}catch(e:java.nio.file.InvalidPathException){exitProcess(report(Inspection.Invalid(Reason.INVALID_ARGUMENT),null))}
val bytes=try{
    if(!Files.isRegularFile(input,LinkOption.NOFOLLOW_LINKS))exitProcess(report(Inspection.Invalid(Reason.INPUT_UNAVAILABLE),null))
    Files.newInputStream(input,LinkOption.NOFOLLOW_LINKS).use{it.readNBytes(maximumFileBytes+1)}
}catch(e:java.io.IOException){exitProcess(report(Inspection.Invalid(Reason.INPUT_UNAVAILABLE),null))}
if(bytes.size>maximumFileBytes)exitProcess(report(Inspection.Invalid(Reason.INPUT_TOO_LARGE),null))
exitProcess(report(inspect(bytes,requireNotNull(expected)),bytes))
