{
  description = "Sunshine 中文输入方案：带 fcitx5 文本桥的 Sunshine 主体 + fcitx5 原生扩展";

  inputs = {
    # 钉到具体修订（而不是分支）：CI 编出来的产物路径只跟这个修订有关，
    # 使用方从 Cachix 拉到的二进制才和本仓库一致。
    # 这个修订的 boost 是 1.89.0，正好满足上游要求的最低版本
    # （低了就会退回 CPM 去下载 boost，Nix 沙箱里没有网，必然失败）。
    nixpkgs.url = "github:NixOS/nixpkgs/cd4ea8d57de16f4810bc5f14207bac45fbf19f67";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # 包版本跟着上游 Sunshine 的版本走（upstream-version 里记录的就是它）。
      version = builtins.replaceStrings [ "\n" ] [ "" ] (builtins.readFile ./upstream-version);

      packagesFor = pkgs: rec {
        # Sunshine 主体：唯一的功能改动是把远程文本交给 fcitx5 的文本桥。
        # src 必须显式给：callPackage 会用 pkgs 里的同名属性覆盖默认值。
        sunshine-cn-input = pkgs.callPackage ./nix/sunshine-cn-input.nix {
          inherit version;
          commit = self.rev;
          src = ./.;
        };

        # fcitx5 原生扩展：接收整段 UTF-8 文本并 commitString 到当前输入上下文。
        fcitx5-sunshine-input = pkgs.callPackage ./nix/fcitx5-sunshine-input.nix {
          inherit version;
          src = ./fcitx5-plugin;
        };

        # 单元测试变体：编 test_sunshine 并跑文本输入桥的用例。
        sunshine-cn-input-tests = pkgs.callPackage ./nix/sunshine-cn-input.nix {
          inherit version;
          commit = self.rev;
          withTests = true;
          src = ./.;
        };
      };
    in
    {
      packages = forAllSystems packagesFor;

      # 让使用方用 overlay 的方式拿到这两个包（跟系统其它包同一套 nixpkgs）。
      overlays.default = final: prev: {
        sunshine-cn-input = final.callPackage ./nix/sunshine-cn-input.nix {
          inherit version;
          commit = self.rev;
          src = ./.;
        };

        fcitx5-sunshine-input = final.callPackage ./nix/fcitx5-sunshine-input.nix {
          inherit version;
          src = ./fcitx5-plugin;
        };
      };

      # nix flake check 会跑这些。
      checks = forAllSystems (pkgs: {
        inherit (packagesFor pkgs) sunshine-cn-input-tests;
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.cmake
            pkgs.ninja
            pkgs.pkg-config
            pkgs.gdb
          ];
        };
      });
    };
}
