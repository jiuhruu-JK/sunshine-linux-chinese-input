{
  description = "Sunshine 中文输入方案：带 fcitx5 文本桥的 Sunshine 主体 + fcitx5 原生扩展";

  inputs = {
    # 默认跟随 nixpkgs-unstable；使用方可以用 inputs.sunshine-cn-input.inputs.nixpkgs.follows
    # 把它钉到自己的 nixpkgs 上，保证与系统其它包同一套依赖。
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
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
