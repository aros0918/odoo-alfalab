{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell { 
  name = "slswww-nix";

  buildInputs = with pkgs; [
    ansible
    ansible-lint
    act
  ];
}
