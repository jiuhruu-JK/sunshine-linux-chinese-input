/*
 * sunshine-input-test —— MVP 测试客户端
 *
 * 用法：
 *   sunshine-input-test --text "远程中文输入测试"
 *   sunshine-input-test --file long-text.txt
 *   sunshine-input-test --sock /path/to/sock --text "..."
 *
 * 通过 Unix 域套接字把一整段 UTF-8 文本发给 fcitx5 扩展。
 * 退出码 0 = 扩展已接受并提交；1 = 明确失败（无焦点/非法输入/连接失败）。
 * 注意：退出码 0 只代表 IPC 请求被扩展处理，最终显示需在目标应用目验。
 */
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr uint32_t kMaxMessageBytes = 1u << 20;

std::string defaultSocketPath() {
    const char *runtimeDir = ::getenv("XDG_RUNTIME_DIR");
    if (runtimeDir && *runtimeDir) {
        return std::string(runtimeDir) + "/sunshine-input/sunshine-input.sock";
    }
    return std::string("/tmp/sunshine-input-") + std::to_string(::getuid()) +
           "/sunshine-input.sock";
}

bool sendAll(int fd, const char *data, size_t len) {
    size_t sent = 0;
    while (sent < len) {
        const ssize_t n = ::send(fd, data + sent, len - sent, MSG_NOSIGNAL);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        sent += static_cast<size_t>(n);
    }
    return true;
}

} // namespace

int main(int argc, char **argv) {
    std::string text;
    std::string sockPath = defaultSocketPath();

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--text" && i + 1 < argc) {
            text = argv[++i];
        } else if (arg == "--file" && i + 1 < argc) {
            std::ifstream in(argv[++i], std::ios::binary);
            if (!in) {
                std::cerr << "ERROR: cannot open file\n";
                return 1;
            }
            std::ostringstream ss;
            ss << in.rdbuf();
            text = ss.str();
        } else if (arg == "--sock" && i + 1 < argc) {
            sockPath = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            std::cout << "usage: sunshine-input-test [--sock PATH] (--text S | "
                         "--file F)\n";
            return 0;
        } else {
            std::cerr << "unknown arg: " << arg << "\n";
            return 2;
        }
    }

    if (text.empty()) {
        std::cerr << "ERROR: empty text\n";
        return 1;
    }
    if (text.size() > kMaxMessageBytes) {
        std::cerr << "ERROR: text too large (" << text.size() << " bytes)\n";
        return 1;
    }

    const int fd = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0) {
        std::cerr << "ERROR: socket: " << std::strerror(errno) << "\n";
        return 1;
    }
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    if (sockPath.size() >= sizeof(addr.sun_path)) {
        std::cerr << "ERROR: socket path too long\n";
        return 1;
    }
    std::strncpy(addr.sun_path, sockPath.c_str(), sizeof(addr.sun_path) - 1);
    if (::connect(fd, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) != 0) {
        std::cerr << "ERROR: connect " << sockPath << ": "
                  << std::strerror(errno) << "\n";
        std::cerr << "(fcitx5 + sunshineinput addon 未运行？)\n";
        return 1;
    }

    // 4 字节大端长度前缀 + 正文（与扩展协议一致）
    const uint32_t len = static_cast<uint32_t>(text.size());
    const unsigned char hdr[4] = {static_cast<unsigned char>(len >> 24),
                                  static_cast<unsigned char>(len >> 16),
                                  static_cast<unsigned char>(len >> 8),
                                  static_cast<unsigned char>(len)};
    if (!sendAll(fd, reinterpret_cast<const char *>(hdr), 4) ||
        !sendAll(fd, text.data(), text.size())) {
        std::cerr << "ERROR: send: " << std::strerror(errno) << "\n";
        return 1;
    }

    char status = 0;
    ssize_t n;
    do {
        n = ::recv(fd, &status, 1, 0);
    } while (n < 0 && errno == EINTR);
    ::close(fd);

    if (n == 1 && status == 'K') {
        std::cout << "OK: request accepted and committed (" << text.size()
                  << " bytes)\n";
        std::cout << "NOTE: 请在目标应用中目验文本是否逐字一致。\n";
        return 0;
    }
    std::cerr << "FAIL: extension rejected the request (status="
              << (n == 1 ? std::string(1, status) : std::string("EOF")) << ")\n";
    return 1;
}
