{
  description = "Sunshine + Linux 中文输入接管（fcitx5）";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      versionFile = ./upstream-version;
      version =
        if builtins.pathExists versionFile
        then lib.removeSuffix "\n" (builtins.readFile versionFile)
        else self.shortRev or "dev";
      lib = nixpkgs.lib;
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAll (pkgs: {
        sunshine-cn-input = pkgs.callPackage ./nix/sunshine-cn-input.nix {
          inherit version;
          src = ./.;
          commit = self.rev or self.dirtyRev or "unknown";
        };
        fcitx5-sunshine-input = pkgs.callPackage ./nix/fcitx5-sunshine-input.nix {
          inherit version;
          src = ./fcitx5-plugin;
        };
        default = self.packages.${pkgs.system}.sunshine-cn-input;
      });
    };
}
