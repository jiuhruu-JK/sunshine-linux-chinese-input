/*
 * sunshine-input-mvp —— fcitx5 原生扩展
 *
 * 目的（MVP）：
 *   让外部程序（sunshine-input-test 客户端、以及后续魔改的 Sunshine）通过
 *   本地 Unix 域套接字提交**一整段 UTF-8 文本**，由扩展在 fcitx5 自身的
 *   事件循环与执行上下文中，取得当前聚焦的 InputContext 并调用公开 API
 *   InputContext::commitString(text) 把文本提交给聚焦应用。
 *
 * 设计要点（逐条对应任务书）：
 *   1. 运行在 fcitx5 进程及其事件循环中（addon + EventLoop::addIOEvent）。
 *   2. 本地 IPC = Unix 域套接字（无需 D-Bus 私有接口）。
 *   3. 只在 fcitx5 执行上下文里处理请求，不跨进程操作 fcitx 内部对象。
 *   4. 提交前校验存在有效且获得焦点的 InputContext；无目标则返回明确错误，
 *      绝不把文本发给旧焦点窗口。
 *   5. 校验 UTF-8 合法性、拒绝空文本、限制消息大小、处理连接中断。
 *   6. 套接字文件权限 0600 + 仅当前用户可访问的目录，防止他人注入文本。
 *   7. 不修改 fcitx5 主体、不使用 Ctrl+Shift+U / 模拟逐字符键盘事件 /
 *      剪贴板粘贴。
 */

#include <fcitx/addonfactory.h>
#include <fcitx/addoninstance.h>
#include <fcitx/addonmanager.h>
#include <fcitx/event.h>
#include <fcitx/inputcontext.h>
#include <fcitx/inputcontextmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/event.h>
#include <fcitx-utils/eventloopinterface.h>
#include <fcitx-utils/log.h>

#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

namespace {

FCITX_DEFINE_LOG_CATEGORY(sunshine_input_log, "sunshineinput");

// 协议常量：4 字节大端长度前缀 + UTF-8 正文（与 client.cpp 一致）。
constexpr size_t kMaxMessageBytes = 1u << 20; // 1 MiB，防超长消息
constexpr int kMaxPendingClients = 8;

// 严格校验 UTF-8（拒绝非法字节序列，避免把乱码提交给应用）。
bool isValidUtf8(const std::string &s) {
    size_t i = 0;
    const size_t n = s.size();
    while (i < n) {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        size_t extra = 0;
        uint32_t cp = 0;
        if (c < 0x80) {
            i += 1;
            continue;
        } else if ((c & 0xE0) == 0xC0) {
            extra = 1;
            cp = c & 0x1F;
        } else if ((c & 0xF0) == 0xE0) {
            extra = 2;
            cp = c & 0x0F;
        } else if ((c & 0xF8) == 0xF0) {
            extra = 3;
            cp = c & 0x07;
        } else {
            return false; // 续字节或非法首字节
        }
        if (i + extra >= n) {
            return false; // 被截断
        }
        for (size_t k = 1; k <= extra; ++k) {
            const unsigned char cc = static_cast<unsigned char>(s[i + k]);
            if ((cc & 0xC0) != 0x80) {
                return false;
            }
            cp = (cp << 6) | (cc & 0x3F);
        }
        // 拒绝过长编码 / 代理区 / 越界码点
        if ((extra == 1 && cp < 0x80) || (extra == 2 && cp < 0x800) ||
            (extra == 3 && cp < 0x10000) || cp > 0x10FFFF ||
            (cp >= 0xD800 && cp <= 0xDFFF)) {
            return false;
        }
        i += extra + 1;
    }
    return true;
}

// 探测 path 上的 socket 是否已无活跃监听者。
// 返回 true = 没有活跃实例（文件不存在或 connect 被拒），可以安全重建；
// 返回 false = 有实例正在监听，绝不能 unlink 抢注。
// 背景：fcitx5 中途重启时，旧实例析构里的 unlink 会删掉新实例刚建好的
// socket（2026-10-13 宿主机实际踩坑），导致 socket 变成孤儿、客户端
// connect 报 ENOENT。两处防范：bind 前探测、析构按 inode 认领。
bool probeSocketDead(const std::string &path) {
    const int fd = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0) {
        return true; // 无法探测时按死处理，后续 bind 会给出真实错误
    }
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    if (path.size() >= sizeof(addr.sun_path)) {
        ::close(fd);
        return true;
    }
    std::strncpy(addr.sun_path, path.c_str(), sizeof(addr.sun_path) - 1);
    const int rc =
        ::connect(fd, reinterpret_cast<const sockaddr *>(&addr), sizeof(addr));
    const int err = errno;
    ::close(fd);
    if (rc == 0) {
        return false; // 有活跃监听者
    }
    return err == ENOENT || err == ECONNREFUSED;
}

// 每个接入的客户端连接：读满 4 字节长度头，再读正文。
struct ClientConn {
    int fd = -1;
    bool headerRead = false;
    size_t want = 0;
    size_t got = 0;
    std::vector<char> buf;
};

} // namespace

class SunshineInputAddon : public fcitx::AddonInstance {
public:
    explicit SunshineInputAddon(fcitx::AddonManager *manager)
        : instance_(manager->instance()), manager_(manager) {
        setupSocket();
    }

    ~SunshineInputAddon() override {
        // 事件源必须先于 fd 释放，避免事件循环持有已关闭 fd。
        clients_.clear();
        clientEvents_.clear();
        listenEvent_.reset();
        if (listenFd_ >= 0) {
            ::close(listenFd_);
            listenFd_ = -1;
        }
        // 只删除自己建的那个 socket 文件：若路径已被其他实例重建
        // （fcitx5 重启竞争），inode 不再匹配，绝不能误删别人的。
        if (!socketPath_.empty() && boundInode_ != 0) {
            struct stat st {};
            if (::stat(socketPath_.c_str(), &st) == 0 &&
                st.st_ino == boundInode_) {
                ::unlink(socketPath_.c_str());
            }
        }
    }

    void reloadConfig() override {}
    void save() override {}

private:
    // ---------- 套接字生命周期 ----------
    void setupSocket() {
        const char *runtimeDir = ::getenv("XDG_RUNTIME_DIR");
        std::string dir;
        if (runtimeDir && *runtimeDir) {
            dir = std::string(runtimeDir) + "/sunshine-input";
        } else {
            dir = "/tmp/sunshine-input-" + std::to_string(::getuid());
        }
        // 0700：只有当前用户能进入，他人无法连接套接字。
        if (::mkdir(dir.c_str(), 0700) != 0 && errno != EEXIST) {
            FCITX_LOGC(sunshine_input_log, Error)
                << "mkdir failed: " << ::strerror(errno) << " dir=" << dir;
            return;
        }
        socketPath_ = dir + "/sunshine-input.sock";

        // fcitx5 中途重启时，旧实例可能还握着 socket（文件仍在、connect
        // 仍通，退场要 ~1s）。既不能抢注（会把旧 socket 拆成孤儿，旧实例
        // 退场时还会误删新文件），也不能干等失败——有界等待它退场后接管。
        bool bound = false;
        for (int attempt = 0; attempt < 25 && !bound; ++attempt) {
            if (!probeSocketDead(socketPath_)) {
                ::usleep(200 * 1000); // 200ms × 25 = 最多等 5s
                continue;
            }
            bound = tryBind();
        }
        if (!bound) {
            FCITX_LOGC(sunshine_input_log, Error)
                << "cannot take over " << socketPath_
                << " (live instance or bind failure), extension stays passive";
            socketPath_.clear();
            return;
        }

        listenEvent_ = instance_->eventLoop().addIOEvent(
            listenFd_, fcitx::IOEventFlag::In,
            [this](fcitx::EventSourceIO *, int, fcitx::IOEventFlags) {
                return onAccept();
            });
        FCITX_LOGC(sunshine_input_log, Info)
            << "sunshine-input listening on " << socketPath_;
    }

    // 一次 bind 尝试：成功返回 true；失败时清理 fd 并返回 false。
    bool tryBind() {
        ::unlink(socketPath_.c_str());
        listenFd_ = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK,
                             0);
        if (listenFd_ < 0) {
            FCITX_LOGC(sunshine_input_log, Error)
                << "socket failed: " << ::strerror(errno);
            return false;
        }
        sockaddr_un addr{};
        addr.sun_family = AF_UNIX;
        if (socketPath_.size() >= sizeof(addr.sun_path)) {
            FCITX_LOGC(sunshine_input_log, Error) << "socket path too long";
            ::close(listenFd_);
            listenFd_ = -1;
            return false;
        }
        std::strncpy(addr.sun_path, socketPath_.c_str(), sizeof(addr.sun_path) - 1);
        if (::bind(listenFd_, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) !=
            0) {
            FCITX_LOGC(sunshine_input_log, Error)
                << "bind failed: " << ::strerror(errno) << " path=" << socketPath_;
            ::close(listenFd_);
            listenFd_ = -1;
            return false;
        }
        ::chmod(socketPath_.c_str(), 0600); // 仅属主可读写
        if (::listen(listenFd_, 4) != 0) {
            FCITX_LOGC(sunshine_input_log, Error)
                << "listen failed: " << ::strerror(errno);
            ::close(listenFd_);
            listenFd_ = -1;
            return false;
        }
        // 记下自己建的 socket 文件 inode：析构时只认这个 inode，
        // 防止误删重启竞争中新实例重建的同名 socket。
        struct stat st {};
        if (::stat(socketPath_.c_str(), &st) == 0) {
            boundInode_ = st.st_ino;
        }
        return true;
    }

    bool onAccept() {
        while (true) {
            const int fd = ::accept4(listenFd_, nullptr, nullptr,
                                     SOCK_CLOEXEC | SOCK_NONBLOCK);
            if (fd < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    return true; // 已排空
                }
                FCITX_LOGC(sunshine_input_log, Error)
                    << "accept failed: " << ::strerror(errno);
                return true; // 监听套接字仍有效，继续
            }
            if (clients_.size() >= kMaxPendingClients) {
                FCITX_LOGC(sunshine_input_log, Warn) << "too many clients, drop";
                ::close(fd);
                continue;
            }
            auto conn = std::make_unique<ClientConn>();
            conn->fd = fd;
            ClientConn *raw = conn.get();
            auto ev = instance_->eventLoop().addIOEvent(
                fd, fcitx::IOEventFlag::In,
                [this, raw](fcitx::EventSourceIO *, int, fcitx::IOEventFlags) {
                    return onReadable(raw);
                });
            clients_[raw] = std::move(conn);
            clientEvents_[raw] = std::move(ev);
        }
    }

    void dropClient(ClientConn *raw) {
        clientEvents_.erase(raw); // 先销毁事件源
        clients_.erase(raw);      // 再关闭 fd
    }

    bool onReadable(ClientConn *c) {
        // 读长度头
        if (!c->headerRead) {
            unsigned char hdr[4];
            const ssize_t n = ::recv(c->fd, hdr, sizeof(hdr), MSG_WAITALL);
            if (n == 0) {
                dropClient(c); // 对端关闭
                return true;
            }
            if (n < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
                    return true;
                }
                dropClient(c);
                return true;
            }
            if (n != 4) {
                FCITX_LOGC(sunshine_input_log, Warn) << "short header, drop";
                dropClient(c);
                return true;
            }
            const uint32_t len = (static_cast<uint32_t>(hdr[0]) << 24) |
                                 (static_cast<uint32_t>(hdr[1]) << 16) |
                                 (static_cast<uint32_t>(hdr[2]) << 8) |
                                 static_cast<uint32_t>(hdr[3]);
            if (len == 0 || len > kMaxMessageBytes) {
                FCITX_LOGC(sunshine_input_log, Warn)
                    << "bad length " << len << ", drop";
                dropClient(c);
                return true;
            }
            c->headerRead = true;
            c->want = len;
            c->buf.resize(len);
        }

        // 读正文
        while (c->got < c->want) {
            const ssize_t n =
                ::recv(c->fd, c->buf.data() + c->got, c->want - c->got, 0);
            if (n == 0) {
                dropClient(c);
                return true;
            }
            if (n < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
                    return true; // 等下一次可读
                }
                dropClient(c);
                return true;
            }
            c->got += static_cast<size_t>(n);
        }

        const std::string text(c->buf.data(), c->buf.size());
        const bool ok = commitToFocused(text);
        reply(c->fd, ok);
        dropClient(c);
        return true;
    }

    // ---------- 核心：把整段文本提交给当前聚焦应用 ----------
    bool commitToFocused(const std::string &text) {
        if (text.empty()) {
            FCITX_LOGC(sunshine_input_log, Warn) << "empty text rejected";
            return false;
        }
        if (!isValidUtf8(text)) {
            FCITX_LOGC(sunshine_input_log, Warn) << "invalid utf-8 rejected";
            return false;
        }
        fcitx::InputContextManager &icm = instance_->inputContextManager();
        fcitx::InputContext *ic = icm.mostRecentInputContext();
        if (!ic || !ic->hasFocus()) {
            FCITX_LOGC(sunshine_input_log, Warn)
                << "no focused input context, refuse to inject";
            return false; // 不发给旧焦点窗口
        }
        ic->commitString(text); // 公开 API，走标准文字提交路径
        FCITX_LOGC(sunshine_input_log, Info)
            << "committed " << text.size() << " bytes to focused IC";
        return true;
    }

    static void reply(int fd, bool ok) {
        const char status = ok ? 'K' : 'E';
        ssize_t ignored = ::send(fd, &status, 1, MSG_NOSIGNAL);
        (void)ignored;
    }

    fcitx::Instance *instance_;
    fcitx::AddonManager *manager_;
    int listenFd_ = -1;
    ino_t boundInode_ = 0; // 自己 bind 的 socket 文件 inode（析构认领用）
    std::string socketPath_;
    std::unique_ptr<fcitx::EventSourceIO> listenEvent_;
    std::map<ClientConn *, std::unique_ptr<ClientConn>> clients_;
    std::map<ClientConn *, std::unique_ptr<fcitx::EventSourceIO>> clientEvents_;
};

class SunshineInputFactory : public fcitx::AddonFactory {
public:
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override {
        return new SunshineInputAddon(manager);
    }
};

FCITX_ADDON_FACTORY(SunshineInputFactory);
