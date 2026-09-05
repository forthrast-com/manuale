{
  description = "Manuale — a Latin missal and breviary, ready for offline reading";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { nixpkgs, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          perl = pkgs.perl.withPackages (ps: [ ps.CGI ]);
          python = pkgs.python3.withPackages (ps: [ ps.beautifulsoup4 ]);
        in {
          default = pkgs.mkShellNoCC {
            packages = [ perl python pkgs.nodejs pkgs.gnumake pkgs.git pkgs.curl pkgs.poppler-utils ];
          };
        });
    };
}
