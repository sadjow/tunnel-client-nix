{
  description = "OpenAI Secure MCP Tunnel client with hourly release updates";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    # Nixpkgs 26.11 removed the Intel macOS package set.
    nixpkgs-darwin.url = "github:NixOS/nixpkgs/nixpkgs-26.05-darwin";
  };

  outputs =
    {
      self,
      nixpkgs,
      nixpkgs-darwin,
    }:
    let
      inherit (nixpkgs) lib;
      platforms = builtins.fromJSON (builtins.readFile ./platforms.json);
      variants = builtins.fromJSON (builtins.readFile ./variants.json);
      eachSystem = lib.genAttrs (builtins.attrNames platforms);
      packageSet =
        system:
        import (if system == "x86_64-darwin" then nixpkgs-darwin else nixpkgs) {
          inherit system;
          overlays = [ self.overlays.default ];
        };
    in
    {
      overlays.default =
        final: _prev:
        lib.mapAttrs (
          variant: _:
          final.callPackage ./package.nix {
            inherit variant;
          }
        ) variants;

      packages = eachSystem (
        system:
        let
          pkgs = packageSet system;
        in
        lib.genAttrs (builtins.attrNames variants) (name: pkgs.${name})
        // {
          default = pkgs.tunnel-client;
        }
      );

      apps = eachSystem (
        system:
        lib.mapAttrs (name: package: {
          type = "app";
          inherit (package) meta;
          program = "${package}/bin/${package.meta.mainProgram}";
        }) self.packages.${system}
      );

      checks = eachSystem (
        system:
        let
          pkgs = packageSet system;
        in
        (builtins.removeAttrs self.packages.${system} [ "default" ])
        // {
          updater =
            pkgs.runCommand "tunnel-client-updater-tests"
              {
                nativeBuildInputs = [ pkgs.python3 ];
              }
              ''
                cd ${self}
                python3 -B -m unittest discover -s tests -v
                touch "$out"
              '';
        }
      );

      formatter = eachSystem (system: (packageSet system).nixfmt);
      devShells = eachSystem (
        system:
        let
          pkgs = packageSet system;
        in
        {
          default = pkgs.mkShellNoCC {
            packages = with pkgs; [
              python3
              gh
              nixfmt
              actionlint
              shellcheck
              cachix
            ];
          };
        }
      );
    };
}
