// Starts Spelunky.exe suspended with hd-seed-search-hook.dll loaded into it, then
// waits for the hook to generate levels for the seeds and exit.
//
// usage: hd-seed-search <seeds.txt> <out.jsonl> [levels] [spelunky dir]
//
// seeds.txt has one seed per line. out.jsonl gets one line per seed as each
// is generated, and out.jsonl.log gets the hook's log. Stopping hd-seed-search
// stops the game with it.

#include <Windows.h>

#include <chrono>
#include <cstdio>
#include <filesystem>
#include <string>

namespace fs = std::filesystem;

static const wchar_t *DEFAULT_GAME_DIR =
    L"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Spelunky";

static int fail(const char *what) {
  std::fprintf(stderr, "hd-seed-search: %s (error %lu)\n", what, GetLastError());
  return 1;
}

static bool inject(HANDLE process, const fs::path &dll) {
  auto path = dll.wstring();
  auto size = (path.size() + 1) * sizeof(wchar_t);

  auto remote = VirtualAllocEx(process, nullptr, size, MEM_COMMIT | MEM_RESERVE,
                               PAGE_READWRITE);
  if (!remote || !WriteProcessMemory(process, remote, path.c_str(), size,
                                     nullptr)) {
    return false;
  }

  // kernel32 is at the same address in every process for a boot, and the
  // thread runs the loader's process setup before LoadLibraryW
  auto loadLibrary = reinterpret_cast<LPTHREAD_START_ROUTINE>(
      GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW"));
  auto thread =
      CreateRemoteThread(process, nullptr, 0, loadLibrary, remote, 0, nullptr);
  if (!thread) {
    return false;
  }

  WaitForSingleObject(thread, INFINITE);
  DWORD module = 0;
  GetExitCodeThread(thread, &module);
  CloseHandle(thread);
  VirtualFreeEx(process, remote, 0, MEM_RELEASE);
  return module != 0;
}

int wmain(int argc, wchar_t **argv) {
  if (argc < 3) {
    std::fprintf(stderr,
                 "usage: hd-seed-search <seeds.txt> <out.jsonl> [levels] [spelunky dir]\n");
    return 2;
  }

  auto seeds = fs::absolute(argv[1]);
  auto out = fs::absolute(argv[2]);
  auto levels = argc > 3 ? argv[3] : L"3";
  fs::path gameDir = argc > 4 ? argv[4] : DEFAULT_GAME_DIR;
  auto exe = gameDir / L"Spelunky.exe";

  wchar_t self[MAX_PATH];
  GetModuleFileNameW(nullptr, self, MAX_PATH);
  auto dll = fs::path(self).parent_path() / L"hd-seed-search-hook.dll";

  if (!fs::exists(exe) || !fs::exists(dll) || !fs::exists(seeds)) {
    std::fprintf(stderr, "hd-seed-search: missing %ls, %ls or %ls\n", exe.c_str(),
                 dll.c_str(), seeds.c_str());
    return 2;
  }

  // The game inherits these
  SetEnvironmentVariableW(L"SEED_SEARCH_SEEDS", seeds.c_str());
  SetEnvironmentVariableW(L"SEED_SEARCH_OUT", out.c_str());
  SetEnvironmentVariableW(L"SEED_SEARCH_LOG", (out.wstring() + L".log").c_str());
  SetEnvironmentVariableW(L"SEED_SEARCH_LEVELS", levels);

  auto started = std::chrono::steady_clock::now();

  // The game is killed when the job's last handle closes, which is when
  // hd-seed-search exits however it exits
  auto job = CreateJobObjectW(nullptr, nullptr);
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = {};
  limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
  if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                       &limits, sizeof(limits))) {
    return fail("couldn't create a job for the game");
  }

  STARTUPINFOW startup = {sizeof(startup)};
  PROCESS_INFORMATION info = {};
  if (!CreateProcessW(exe.c_str(), nullptr, nullptr, nullptr, FALSE,
                      CREATE_SUSPENDED, nullptr, gameDir.c_str(), &startup,
                      &info)) {
    return fail("couldn't start Spelunky.exe");
  }

  if (!AssignProcessToJobObject(job, info.hProcess)) {
    TerminateProcess(info.hProcess, 1);
    return fail("couldn't add the game to the job");
  }

  if (!inject(info.hProcess, dll)) {
    TerminateProcess(info.hProcess, 1);
    return fail("couldn't load hd-seed-search-hook.dll into the game");
  }

  std::printf("hd-seed-search: game pid %lu\n", info.dwProcessId);
  std::fflush(stdout);

  ResumeThread(info.hThread);
  CloseHandle(info.hThread);
  WaitForSingleObject(info.hProcess, INFINITE);

  DWORD exitCode = 0;
  GetExitCodeProcess(info.hProcess, &exitCode);
  CloseHandle(info.hProcess);

  auto seconds = std::chrono::duration<double>(
                     std::chrono::steady_clock::now() - started)
                     .count();
  std::printf("hd-seed-search: game exited with %#lx after %.1fs, see %ls.log\n",
              exitCode, seconds, out.c_str());
  return exitCode == 0 ? 0 : 1;
}
