#include <atomic>
#include <cassert>
#include <condition_variable>
#include <thread>
#include <mutex>
#include <iostream>
#include <fstream>
#include <functional>
#include <vector>
#include <string>
#include <sstream>
#include <csignal>
#include <ctime>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/vfs.h>
#include <cstring>

typedef std::function<std::string()> callbackFn;

std::mutex               barMtx;
std::vector<std::string> barStr;

std::atomic_bool        running = true;
std::mutex              runMtx;
std::condition_variable runCv;

std::vector<std::thread> thVec;

static void gracefully_quit(int sig) {
  if (sig == SIGTERM) {
    std::unique_lock<std::mutex> lck(runMtx);
    running = false;
    runCv.notify_all();
  }
}

static std::string get_battery() {
  std::string   res;
  std::ifstream ifs("/sys/class/power_supply/BAT0/capacity");
  ifs >> res;
  res.append(" batt");
  return res;
}

static std::string get_free_space_main_disk() {
  std::stringstream res;

  struct statfs sfs;
  statfs("/", &sfs);

  res << (1 - (sfs.f_bfree / (double)sfs.f_blocks)) * 100 << " 󰋊";

  return res.str();
}

static std::string get_date() {
  char       str[128]{0};
  time_t     now      = time(NULL);
  struct tm *timeinfo = localtime(&now);
  strftime(str, 128, "%c", timeinfo);
  return std::string(str);
}

static std::string update_bar() {
  std::stringstream            res;
  std::unique_lock<std::mutex> lck(barMtx);
  if (barStr.size() == 0) return "";
  for (size_t i = 0; i < (barStr.size() - 1); i++) res << barStr.at(i) << " | ";
  res << barStr[barStr.size() - 1];

  pid_t pid = fork();
  if (pid < 0) exit(0);
  if (pid == 0) {
    execl("/bin/xsetroot", "/bin/xsetroot", "-name", res.str().c_str(), NULL);
    assert(false);
  }

  waitpid(pid, NULL, 0);

  return res.str();
}

static void job_fun(size_t barI, std::chrono::milliseconds to, callbackFn fn) {
  while (running) {
    std::string res = fn();

    barMtx.lock();
    if (barStr.capacity() < barI + 1) {
      barStr.reserve(barI + 1);
      barStr.resize(barStr.capacity());
    }
    barStr.at(barI) = res;
    barMtx.unlock();

    {
      std::unique_lock<std::mutex> lck(runMtx);
      runCv.wait_for(lck, to, []() { return !running; });
    }
  }
}

template<class RT, class RA>
static void add_job(size_t barI, std::chrono::duration<RT, RA> to, callbackFn fn) {
  thVec.push_back(std::thread(job_fun, barI, to, fn));
}

int main() {
  auto tUnit = std::chrono::seconds(1);

  std::signal(SIGTERM, gracefully_quit);

  add_job(0, tUnit*10, get_free_space_main_disk);
  add_job(1, tUnit, get_battery);
  add_job(2, tUnit, get_date);

  thVec.push_back(std::thread(job_fun, 1, tUnit, update_bar));

  for (auto &th : thVec) {
    th.join();
  }
  return 0;
}
