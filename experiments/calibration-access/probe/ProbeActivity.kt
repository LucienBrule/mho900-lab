package lab.mho900.calibration.access

import android.app.Activity
import android.os.Bundle
import android.os.Process
import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

class ProbeActivity : Activity() {
    private data class DirectoryResult(
        val index: Int,
        val path: String,
        val statOk: Boolean,
        val mode: Int,
        val size: Long,
        val errno: Int,
    )

    private data class FileResult(
        val index: Int,
        val path: String,
        val expectedSize: Long,
        var statOk: Boolean = false,
        var statMode: Int = 0,
        var statSize: Long = 0,
        var statErrno: Int = 0,
        var openOk: Boolean = false,
        var openErrno: Int = 0,
        var readAttempted: Boolean = false,
        var readOk: Boolean = false,
        var readBytes: Long = 0,
        var readErrno: Int = 0,
        var sha256: String = "",
        var closeAttempted: Boolean = false,
        var closeOk: Boolean = false,
        var closeErrno: Int = 0,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Thread({ runProbe() }, "calibration-access-probe").start()
    }

    private fun directory(index: Int, path: String): DirectoryResult = try {
        val stat = Os.stat(path)
        DirectoryResult(index, path, true, stat.st_mode, stat.st_size, 0)
    } catch (error: ErrnoException) {
        DirectoryResult(index, path, false, 0, 0, error.errno)
    }

    private fun file(index: Int, path: String, expectedSize: Long): FileResult {
        val result = FileResult(index, path, expectedSize)
        try {
            val stat = Os.stat(path)
            result.statOk = true
            result.statMode = stat.st_mode
            result.statSize = stat.st_size
        } catch (error: ErrnoException) {
            result.statErrno = error.errno
        }

        val descriptor = try {
            Os.open(path, OsConstants.O_RDONLY or OsConstants.O_CLOEXEC, 0)
        } catch (error: ErrnoException) {
            result.openErrno = error.errno
            return result
        }
        result.openOk = true
        result.readAttempted = true
        try {
            val digest = MessageDigest.getInstance("SHA-256")
            val buffer = ByteArray(65536)
            val limit = expectedSize + 1
            var complete = false
            while (result.readBytes < limit) {
                val remaining = limit - result.readBytes
                val count = Os.read(descriptor, buffer, 0, minOf(buffer.size.toLong(), remaining).toInt())
                if (count == 0) {
                    complete = true
                    break
                }
                digest.update(buffer, 0, count)
                result.readBytes += count.toLong()
            }
            result.readOk = complete
            if (complete) result.sha256 = hex(digest.digest())
        } catch (error: ErrnoException) {
            result.readErrno = error.errno
            result.readOk = false
            result.sha256 = ""
        } finally {
            result.closeAttempted = true
            try {
                Os.close(descriptor)
                result.closeOk = true
            } catch (error: ErrnoException) {
                result.closeErrno = error.errno
            }
        }
        return result
    }

    private fun runProbe() {
        val directories = listOf(
            directory(0, "/rigol"),
            directory(1, "/rigol/data"),
            directory(2, "/rigol/data/default"),
        )
        val files = listOf(
            file(0, "/rigol/data/default/cal_lsb.hex", 220),
            file(1, "/rigol/data/default/cal_vertical.hex", 1_794_268),
        )
        val label = try {
            File("/proc/self/attr/current").readText(Charsets.UTF_8).trim('\u0000', '\r', '\n', ' ')
        } catch (_: Exception) {
            ""
        }
        val report = render(Process.myPid(), Process.myUid(), label, directories, files)
        val temporary = File(filesDir, "report.toml.tmp")
        val final = File(filesDir, "report.toml")
        check(!temporary.exists() && !final.exists())
        FileOutputStream(temporary).use { output ->
            output.write(report.toByteArray(Charsets.UTF_8))
            output.fd.sync()
        }
        check(temporary.renameTo(final))
        Log.i("MhoCalibrationAccess", "probe-complete report=report.toml")
    }

    private fun render(
        pid: Int,
        uid: Int,
        label: String,
        directories: List<DirectoryResult>,
        files: List<FileResult>,
    ): String = buildString {
        append("schema_version = \"mho900-lab.calibration-access-probe/1\"\n")
        append("result = \"observed\"\n")
        append("pid = ").append(pid).append('\n')
        append("uid = ").append(uid).append('\n')
        append("process_label = ").append(quote(label)).append('\n')
        directories.forEach { value ->
            append("\n[[directories]]\n")
            append("index = ").append(value.index).append('\n')
            append("path = ").append(quote(value.path)).append('\n')
            append("stat_ok = ").append(value.statOk).append('\n')
            append("mode = ").append(value.mode).append('\n')
            append("size = ").append(value.size).append('\n')
            append("errno = ").append(value.errno).append('\n')
        }
        files.forEach { value ->
            append("\n[[files]]\n")
            append("index = ").append(value.index).append('\n')
            append("path = ").append(quote(value.path)).append('\n')
            append("expected_size = ").append(value.expectedSize).append('\n')
            append("stat_ok = ").append(value.statOk).append('\n')
            append("stat_mode = ").append(value.statMode).append('\n')
            append("stat_size = ").append(value.statSize).append('\n')
            append("stat_errno = ").append(value.statErrno).append('\n')
            append("open_ok = ").append(value.openOk).append('\n')
            append("open_errno = ").append(value.openErrno).append('\n')
            append("read_attempted = ").append(value.readAttempted).append('\n')
            append("read_ok = ").append(value.readOk).append('\n')
            append("read_bytes = ").append(value.readBytes).append('\n')
            append("read_errno = ").append(value.readErrno).append('\n')
            append("sha256 = ").append(quote(value.sha256)).append('\n')
            append("close_attempted = ").append(value.closeAttempted).append('\n')
            append("close_ok = ").append(value.closeOk).append('\n')
            append("close_errno = ").append(value.closeErrno).append('\n')
        }
    }

    private fun quote(value: String): String = "\"" + value
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n") + "\""

    private fun hex(bytes: ByteArray): String = buildString(bytes.size * 2) {
        bytes.forEach { byte -> append("%02x".format(byte.toInt() and 0xff)) }
    }
}
