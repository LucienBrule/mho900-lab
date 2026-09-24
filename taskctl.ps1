$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$TaskArguments = @($args)
function Get-Sha256([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}
try {
    $lockFile = Join-Path $PSScriptRoot '.taskctl/toolchain.lock'
    $pin = @{}
    $allowed = @('lockFormat','toolVersion','wrapperVersion','windows-x86_64.url','windows-x86_64.sha256','linux-x86_64.url','linux-x86_64.sha256','macos-aarch64.url','macos-aarch64.sha256')
    foreach ($line in [IO.File]::ReadAllLines($lockFile)) {
        if ($line -eq '' -or $line.StartsWith('#')) { continue }
        if ($line -notmatch '^([^=]+)=(.*)$') { throw 'Malformed taskctl lock' }
        $key = $Matches[1]; $value = $Matches[2]
        if ($key -cnotin $allowed -or $pin.ContainsKey($key)) { throw "Unknown or duplicate lock key: $key" }
        $pin[$key] = $value
    }
    if ($pin.lockFormat -cne '2' -or $pin.wrapperVersion -cnotin @('2','3') -or $pin.toolVersion -cnotmatch '^[0-9]+[.][0-9]+[.][0-9]+[-A-Za-z0-9.]*$') { throw 'Unsupported taskctl lock or wrapper version' }
    # The committed pin is available even when no runtime has been acquired.
    if ($TaskArguments.Count -gt 0 -and $TaskArguments[0] -cin @('--version','-V','version')) {
        if ($TaskArguments.Count -eq 1) { Write-Output ('taskctl ' + $pin.toolVersion); exit 0 }
        if ($TaskArguments.Count -eq 3 -and $TaskArguments[0] -ceq 'version' -and $TaskArguments[1] -ceq '--format') {
            if ($TaskArguments[2] -ceq 'json') { Write-Output ('{"api":"taskctl.cli/alpha1","command":"version","result":{"tool":"taskctl","version":"' + $pin.toolVersion + '"}}'); exit 0 }
            if ($TaskArguments[2] -ceq 'text') { Write-Output ('taskctl ' + $pin.toolVersion); exit 0 }
        }
        throw 'usage: taskctl --version | -V | version [--format json|text]'
    }
    if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'This launcher supports Windows x86_64' }
    $sha = $pin['windows-x86_64.sha256']
    if ($sha -cnotmatch '^[0-9a-f]{64}$') { throw 'Invalid locked checksum' }
    $url = [Uri]$pin['windows-x86_64.url']
    if ($url.Scheme -notin @('file','https')) { throw 'Only file or HTTPS artifact locations are accepted' }
    $cacheBase = if ($env:TASKCTL_CACHE) { $env:TASKCTL_CACHE } else { Join-Path $env:LOCALAPPDATA 'taskctl' }
    if (-not [IO.Path]::IsPathRooted($cacheBase)) { throw 'TASKCTL_CACHE must be absolute' }
    $cache = Join-Path $cacheBase $sha
    [IO.Directory]::CreateDirectory($cache) | Out-Null
    $archive = Join-Path $cache 'archive.zip'
    if (-not [IO.File]::Exists($archive)) {
        if ($env:TASKCTL_OFFLINE -eq '1') { throw 'Locked taskctl distribution is not cached (offline)' }
        $download = Join-Path $cache ('download-' + [Guid]::NewGuid().ToString('N'))
        try {
            if ($url.IsFile) { [IO.File]::Copy($url.LocalPath, $download) }
            else {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                $client = [Net.WebClient]::new()
                try {
                    if ($url.Host -eq 'api.github.com') {
                        $client.Headers['Accept'] = 'application/octet-stream'
                        $client.Headers['User-Agent'] = 'taskctl-bootstrap/2'
                        $token = if ($env:TASKCTL_GITHUB_TOKEN) { $env:TASKCTL_GITHUB_TOKEN } else { $env:GH_TOKEN }
                        if ($token) { $client.Headers['Authorization'] = 'Bearer ' + $token }
                    }
                    $client.DownloadFile($url, $download)
                } finally { $client.Dispose() }
            }
            if ((Get-Sha256 $download) -cne $sha) { throw 'taskctl distribution checksum mismatch' }
            try { [IO.File]::Move($download, $archive) } catch { if (-not [IO.File]::Exists($archive)) { throw } }
        } finally { if ([IO.File]::Exists($download)) { [IO.File]::Delete($download) } }
    }
    if ((Get-Sha256 $archive) -cne $sha) { throw 'Cached taskctl distribution checksum mismatch' }
    [void][Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem')
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $zip.Entries) {
            if ($entry.FullName -notmatch '^[A-Za-z0-9_./+\-]+$' -or $entry.FullName.StartsWith('/') -or $entry.FullName.Split('/') -contains '..') { throw 'Unsafe archive path' }
        }
        $entry = $zip.GetEntry('files.sha256')
        if (-not $entry) { throw 'Distribution file manifest missing' }
        $reader = [IO.StreamReader]::new($entry.Open())
        try { $manifest = $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $zip.Dispose() }
    $install = Join-Path $cache 'home'
    if (-not [IO.Directory]::Exists($install)) {
        $staging = Join-Path $cache ('install-' + [Guid]::NewGuid().ToString('N'))
        [IO.Compression.ZipFile]::ExtractToDirectory($archive, $staging)
        try { [IO.Directory]::Move($staging, $install) }
        catch { if (-not [IO.Directory]::Exists($install)) { throw } }
        finally {
            # This is a generated child of the verified cache directory only.
            if ([IO.Directory]::Exists($staging)) { [IO.Directory]::Delete($staging, $true) }
        }
    }
    $libraryPaths = @()
    foreach ($line in ($manifest -split "`n")) {
        if ($line -eq '') { continue }
        if ($line -cnotmatch '^([0-9a-f]{64})  ([A-Za-z0-9_./+\-]+)$') { throw 'Malformed distribution file manifest' }
        $expected = $Matches[1]; $relative = $Matches[2]
        if ($relative.StartsWith('/') -or $relative.Split('/') -contains '..') { throw 'Unsafe manifest path' }
        $file = Join-Path $install $relative
        if ((Get-Sha256 $file) -cne $expected) { throw "Cached taskctl file checksum mismatch: $relative" }
        if ($relative.StartsWith('lib/') -and $relative.EndsWith('.jar')) { $libraryPaths += $file }
    }
    $distribution = [IO.File]::ReadAllLines((Join-Path $install 'distribution.properties'))
    if ($distribution -cnotcontains ('toolVersion=' + $pin.toolVersion)) { throw 'Locked version does not match distribution' }
    $java = Join-Path $install 'runtime/bin/java.exe'
    $classpath = ($libraryPaths -join ';')
    # Windows PowerShell 5 does not preserve embedded quotes in native argument
    # arrays. Encode each argument using the Windows command-line rules.
    function ConvertTo-NativeArgument([string]$value) {
        $encoded = [Text.StringBuilder]::new()
        [void]$encoded.Append('"')
        $slashes = 0
        foreach ($character in $value.ToCharArray()) {
            if ($character -eq '\') { $slashes++; continue }
            if ($character -eq '"') {
                [void]$encoded.Append(('\' * (2 * $slashes + 1)))
                [void]$encoded.Append('"')
            } else {
                [void]$encoded.Append(('\' * $slashes))
                [void]$encoded.Append($character)
            }
            $slashes = 0
        }
        [void]$encoded.Append(('\' * (2 * $slashes)))
        [void]$encoded.Append('"')
        return $encoded.ToString()
    }
    $launchArguments = @(('-Dtaskctl.distribution=' + $install), ('-Dtaskctl.repository=' + $PSScriptRoot), '-cp', $classpath, 'io.brule.tasking.cli.MainKt') + $TaskArguments
    if ($distribution -ccontains 'launcherContract=taskctl.launcher/1') {
        $entries = @($distribution | Where-Object { $_.StartsWith('entrypoint=') })
        if ($entries.Count -ne 1) { throw 'Missing or duplicate artifact entry point' }
        $entry = $entries[0].Substring('entrypoint='.Length)
        switch -CaseSensitive ($entry) {
            'taskctl.exe' { $java = Join-Path $install $entry; $launchArguments = $TaskArguments }
            'taskctl.ps1' {
                $java = Join-Path $PSHOME 'powershell.exe'
                if (-not [IO.File]::Exists($java)) { $java = Join-Path $PSHOME 'pwsh.exe' }
                $launchArguments = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $install $entry)) + $TaskArguments
            }
            default { throw 'Unsupported artifact entry point' }
        }
    }
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $java
    $start.UseShellExecute = $false
    $start.EnvironmentVariables['TASKCTL_DISTRIBUTION'] = $install
    $start.EnvironmentVariables['TASKCTL_REPOSITORY'] = $PSScriptRoot
    $start.Arguments = ($launchArguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '
    $process = [Diagnostics.Process]::Start($start)
    $process.WaitForExit()
    exit $process.ExitCode
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
